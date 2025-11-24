"""Extract GEX and forward return data from validation YAML files.

This script reads the existing validation reports and extracts the time series
data needed for statistical validation (Issues #99 and #100).

Usage:
    python scripts/statistical_validation/extract_validation_data.py
"""

import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationDataExtractor:
    """Extract time series data from validation YAML files."""

    def __init__(self, validation_dir: str = "reports/validation/pattern_taxonomy"):
        """Initialize extractor.

        Args:
            validation_dir: Directory containing validation YAML files
        """
        self.validation_dir = Path(validation_dir)

    def load_yaml_file(self, filepath: Path) -> Dict:
        """Load a YAML validation file."""
        with open(filepath, "r") as f:
            return yaml.safe_load(f)

    def extract_time_series(self, pattern: str = "gamma_positioning", use_unbiased: bool = True) -> pd.DataFrame:
        """Extract time series data from validation reports.

        Args:
            pattern: Pattern name (gamma_positioning, stock_pinning, 0dte_hedging)
            use_unbiased: If True, use *_unbiased.yaml files (recommended for statistical validation)
                         If False, use quarterly Q*.yaml files

        Returns:
            DataFrame with columns: date, net_gex, spot_price, forward_return_t1,
                                    forward_return_t3, prediction_correct, detected
        """
        logger.info(f"Extracting time series for pattern: {pattern}")

        # Load validation reports
        if use_unbiased:
            # Use unbiased full-year file (consistent methodology)
            yaml_files = sorted(self.validation_dir.glob(f"{pattern}_SPY_2024_unbiased.yaml"))
            logger.info("Using unbiased full-year validation file (recommended)")
        else:
            # Use quarterly reports (mixed methodologies)
            yaml_files = sorted(self.validation_dir.glob(f"{pattern}_SPY_2024Q*.yaml"))
            logger.info("Using quarterly validation files")

        if not yaml_files:
            logger.warning(f"No YAML files found for pattern {pattern}")
            return pd.DataFrame()

        all_data = []

        for yaml_file in yaml_files:
            logger.info(f"Processing {yaml_file.name}")
            data = self.load_yaml_file(yaml_file)

            # Extract per-day detections
            detections = data.get("detections", [])

            for detection in detections:
                # Extract basic info
                date = detection.get("date")
                detected = detection.get("detected", False)

                # Extract GEX metrics
                quant = detection.get("quantitative_evidence", {})
                gex_metrics = quant.get("gex_metrics", {})
                net_gex = gex_metrics.get("net_gex_usd")
                spot_price = gex_metrics.get("spot_price")

                # Extract outcome metrics (check both locations)
                # Newer format: inside quantitative_evidence
                outcome = quant.get("outcome_metrics", {})
                # Older format: top-level in detection
                if not outcome:
                    outcome = detection.get("outcome_metrics", {})

                forward_return_t1 = outcome.get("forward_1d_return_pct")
                forward_return_t3 = outcome.get("forward_3d_return_pct")

                # Extract prediction correctness
                prediction_correct = detection.get("prediction_correct")

                # Compile row
                row = {
                    "date": pd.to_datetime(date),
                    "net_gex": net_gex,
                    "spot_price": spot_price,
                    "forward_return_t1": forward_return_t1,
                    "forward_return_t3": forward_return_t3,
                    "prediction_correct": prediction_correct,
                    "detected": detected,
                }

                all_data.append(row)

        # Create DataFrame
        df = pd.DataFrame(all_data)
        df = df.sort_values("date").reset_index(drop=True)

        # Convert to numeric and drop missing values
        df["net_gex"] = pd.to_numeric(df["net_gex"], errors="coerce")
        df["spot_price"] = pd.to_numeric(df["spot_price"], errors="coerce")
        df["forward_return_t1"] = pd.to_numeric(df["forward_return_t1"], errors="coerce")
        df["forward_return_t3"] = pd.to_numeric(df["forward_return_t3"], errors="coerce")

        # Calculate realized volatility (absolute returns)
        df["realized_vol_t1"] = df["forward_return_t1"].abs()
        df["realized_vol_t3"] = df["forward_return_t3"].abs()

        # Calculate rolling volatility
        df["realized_vol_rolling_3d"] = df["forward_return_t1"].rolling(3).std()
        df["realized_vol_rolling_5d"] = df["forward_return_t1"].rolling(5).std()

        # Classify GEX regimes
        df["gex_regime"] = pd.cut(
            df["net_gex"], bins=[-np.inf, -2e9, 2e9, np.inf], labels=["Negative", "Neutral", "Positive"]
        )

        logger.info(f"Extracted {len(df)} trading days")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"GEX range: ${df['net_gex'].min()/1e9:.2f}B to ${df['net_gex'].max()/1e9:.2f}B")
        logger.info(f"Detection rate: {df['detected'].sum()/len(df)*100:.1f}%")

        return df

    def extract_full_year(self, pattern: str = "gamma_positioning", use_unbiased: bool = True) -> pd.DataFrame:
        """Extract full 2024 data (all quarters combined).

        Args:
            pattern: Pattern name
            use_unbiased: If True, use *_unbiased.yaml files (recommended)

        Returns:
            DataFrame with full year time series
        """
        df = self.extract_time_series(pattern, use_unbiased=use_unbiased)

        if len(df) == 0:
            logger.warning("No data extracted")
            return df

        # Summary statistics
        logger.info("\n=== Full Year Summary ===")
        logger.info(f"Total days: {len(df)}")
        logger.info(f"Mean net GEX: ${df['net_gex'].mean()/1e9:.2f}B")
        logger.info(f"Mean T+1 return: {df['forward_return_t1'].mean():.4f}%")
        logger.info(f"Mean realized vol (T+1): {df['realized_vol_t1'].mean():.4f}%")

        # Regime breakdown
        logger.info("\n=== Regime Breakdown ===")
        regime_stats = df.groupby("gex_regime").agg(
            {"net_gex": "count", "realized_vol_t1": "mean", "forward_return_t1": "mean"}
        )
        logger.info(f"\n{regime_stats}")

        return df

    def save_to_csv(self, df: pd.DataFrame, output_file: str):
        """Save extracted data to CSV."""
        df.to_csv(output_file, index=False)
        logger.info(f"Saved to {output_file}")


def main():
    """Main execution."""
    extractor = ValidationDataExtractor()

    # Extract gamma positioning data (full year - UNBIASED methodology)
    df = extractor.extract_full_year(pattern="gamma_positioning", use_unbiased=True)

    if len(df) > 0:
        # Save to CSV
        output_dir = Path("reports/statistical_validation")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "gamma_positioning_timeseries_2024.csv"
        extractor.save_to_csv(df, output_file)

        logger.info(f"\n✅ Data extraction complete!")
        logger.info(f"   Output: {output_file}")
        logger.info(f"   Ready for Granger and Lead-Lag analysis")
    else:
        logger.error("No data extracted. Check YAML files exist.")


if __name__ == "__main__":
    main()
