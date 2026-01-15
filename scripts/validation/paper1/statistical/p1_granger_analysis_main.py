"""
Issue #99: Granger Causality Analysis - Main Orchestration Script

Tests whether GEX Granger-causes realized volatility, proving predictive power
beyond correlation.

Usage:
    python scripts/statistical_validation/granger_analysis_main.py

Output:
    - LaTeX tables in docs/papers/paper1/tables/
    - JSON results in reports/statistical_validation/
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Statistical packages
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

# Local imports
from gex_db_infrastructure.cache.gex_cache_manager import GEXCacheManager
from src.utils.date_utils import today_str
from gex_db_infrastructure.validation.outcome_calculator import OutcomeCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrangerAnalysis:
    """
    Granger causality test: Does GEX predict forward volatility?

    Pipeline:
    1. Load GEX time series and price data
    2. Calculate realized forward volatility
    3. Test stationarity (ADF test)
    4. Run Granger causality tests (lags 1-5)
    5. Test negative GEX regime separately
    6. Generate LaTeX tables
    """

    def __init__(
        self, symbol: str = "SPY", start_date: str = "2024-01-01", end_date: str = "2024-12-31", forward_window: int = 3
    ):
        """Initialize Granger analysis.

        Args:
            symbol: Ticker to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            forward_window: Days forward for volatility calculation
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.forward_window = forward_window

        self.cache = GEXCacheManager()
        self.outcome_calc = OutcomeCalculator(cache_manager=self.cache)

        self.data = None
        self.results = {}

        logger.info(f"Initialized Granger Analysis for {symbol} ({start_date} to {end_date})")

    def step1_prepare_data(self) -> pd.DataFrame:
        """
        Step 1: Prepare time series data for Granger test.

        Returns:
            DataFrame with columns: ['date', 'gex', 'realized_vol']
        """
        logger.info("Step 1: Preparing data...")

        # Load extracted time series from CSV
        csv_path = Path("reports/statistical_validation/gamma_positioning_timeseries_2024.csv")

        if not csv_path.exists():
            raise FileNotFoundError(
                f"Time series CSV not found at {csv_path}. "
                "Run scripts/statistical_validation/extract_validation_data.py first."
            )

        data = pd.read_csv(csv_path)
        data["date"] = pd.to_datetime(data["date"])

        # Rename columns for Granger analysis
        data = data.rename(columns={"net_gex": "gex", "realized_vol_t1": "realized_vol"})

        # Drop rows with missing values
        data = data[["date", "gex", "realized_vol"]].dropna()

        logger.info(f"Loaded {len(data)} trading days")
        logger.info(f"Date range: {data['date'].min()} to {data['date'].max()}")
        logger.info(f"GEX range: ${data['gex'].min()/1e9:.2f}B to ${data['gex'].max()/1e9:.2f}B")
        logger.info(f"Volatility range: {data['realized_vol'].min():.4f} to {data['realized_vol'].max():.4f}")

        self.data = data
        return data

    def step2_test_stationarity(self) -> dict:
        """
        Step 2: Test stationarity using Augmented Dickey-Fuller test.

        Returns:
            dict with stationarity test results
        """
        logger.info("Step 2: Testing stationarity...")

        # ADF test for GEX
        gex_result = adfuller(self.data["gex"].dropna())
        gex_stationary = gex_result[1] < 0.05

        # ADF test for volatility
        vol_result = adfuller(self.data["realized_vol"].dropna())
        vol_stationary = vol_result[1] < 0.05

        stationarity_results = {
            "gex": {
                "stationary": gex_stationary,
                "p_value": gex_result[1],
                "adf_statistic": gex_result[0],
                "need_diff": not gex_stationary,
            },
            "volatility": {
                "stationary": vol_stationary,
                "p_value": vol_result[1],
                "adf_statistic": vol_result[0],
                "need_diff": not vol_stationary,
            },
        }

        logger.info(f"GEX stationary: {gex_stationary} (p={gex_result[1]:.4f})")
        logger.info(f"Volatility stationary: {vol_stationary} (p={vol_result[1]:.4f})")

        # Apply differencing if needed
        if stationarity_results["gex"]["need_diff"]:
            logger.info("Applying first-differencing to GEX")
            self.data["gex_diff"] = self.data["gex"].diff()
        else:
            self.data["gex_diff"] = self.data["gex"]

        if stationarity_results["volatility"]["need_diff"]:
            logger.info("Applying first-differencing to volatility")
            self.data["vol_diff"] = self.data["realized_vol"].diff()
        else:
            self.data["vol_diff"] = self.data["realized_vol"]

        self.data = self.data.dropna()

        self.results["stationarity"] = stationarity_results
        return stationarity_results

    def step3_run_granger_test(self, maxlag: int = 5, regime: str = None) -> pd.DataFrame:
        """
        Step 3: Run Granger causality test.

        Args:
            maxlag: Maximum lag to test
            regime: 'negative', 'positive', or None (all data)

        Returns:
            DataFrame with Granger test results by lag
        """
        logger.info(f"Step 3: Running Granger test (maxlag={maxlag}, regime={regime})...")

        # Filter by regime if specified
        data = self.data.copy()
        if regime == "negative":
            data = data[data["gex"] < -2e9]
            logger.info(f"Filtered to negative GEX regime: {len(data)} observations")
        elif regime == "positive":
            data = data[data["gex"] > 2e9]
            logger.info(f"Filtered to positive GEX regime: {len(data)} observations")

        if len(data) < 50:
            logger.warning(f"Insufficient data for Granger test: {len(data)} observations")
            return pd.DataFrame()

        # Run Granger causality test
        # Order: [dependent_var, independent_var] = [vol_diff, gex_diff]
        try:
            results = grangercausalitytests(data[["vol_diff", "gex_diff"]], maxlag=maxlag, verbose=False)

            # Extract results
            summary = []
            for lag in range(1, maxlag + 1):
                test_result = results[lag][0]
                f_stat = test_result["ssr_ftest"][0]
                p_value = test_result["ssr_ftest"][1]

                summary.append(
                    {
                        "lag": lag,
                        "f_statistic": round(f_stat, 2),
                        "p_value": round(p_value, 4),
                        "significant": p_value < 0.05,
                    }
                )

                logger.info(
                    f"Lag {lag}: F={f_stat:.2f}, p={p_value:.4f} {'***' if p_value < 0.001 else ('**' if p_value < 0.01 else ('*' if p_value < 0.05 else ''))}"
                )

            granger_results = pd.DataFrame(summary)

            # Store results
            regime_key = regime if regime else "full"
            self.results[f"granger_{regime_key}"] = granger_results.to_dict("records")

            return granger_results

        except Exception as e:
            logger.error(f"Granger test failed: {e}")
            return pd.DataFrame()

    def step4_generate_latex_table(self, granger_results: pd.DataFrame, regime: str = "all") -> str:
        """
        Step 4: Generate LaTeX table for paper.

        Args:
            granger_results: Results from step 3
            regime: 'all', 'negative', or 'positive'

        Returns:
            LaTeX table string
        """
        logger.info(f"Step 4: Generating LaTeX table for {regime} regime...")

        if granger_results.empty:
            logger.warning("No results to generate table")
            return ""

        # Add significance markers
        def sig_marker(p):
            if p < 0.001:
                return "***"
            if p < 0.01:
                return "**"
            if p < 0.05:
                return "*"
            return ""

        granger_results["sig"] = granger_results["p_value"].apply(sig_marker)

        # Generate LaTeX
        latex = r"""\begin{table}[htbp]
\centering
\caption{Granger Causality: GEX → Realized Volatility"""

        if regime != "all":
            latex += f" ({regime.title()} Regime)"

        latex += r"""}
\label{tab:granger"""

        if regime == "negative":
            latex += "_neg"

        latex += r"""}
\begin{tabular}{cccc}
\toprule
Lag & F-Statistic & p-value & Significant \\
\midrule
"""

        for _, row in granger_results.iterrows():
            latex += f"{row['lag']} & {row['f_statistic']:.2f} & {row['p_value']:.3f}{row['sig']} & {'Yes' if row['significant'] else 'No'} \\\\\n"

        latex += r"""\bottomrule
\multicolumn{4}{l}{\footnotesize *** p < 0.001, ** p < 0.01, * p < 0.05}
\end{tabular}
\end{table}"""

        # Save to file
        output_dir = Path("docs/papers/paper1/tables")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"table_granger_{regime}.tex"
        with open(output_file, "w") as f:
            f.write(latex)

        logger.info(f"Saved LaTeX table to {output_file}")

        return latex

    def run_full_analysis(self) -> dict:
        """Run complete Granger causality analysis pipeline.

        Returns:
            dict with all results
        """
        logger.info("=" * 70)
        logger.info("GRANGER CAUSALITY ANALYSIS - Issue #99")
        logger.info("=" * 70)

        # Step 1: Prepare data
        self.step1_prepare_data()

        # Step 2: Test stationarity
        self.step2_test_stationarity()

        # Step 3: Run Granger tests
        logger.info("\n--- Full Sample Analysis ---")
        granger_full = self.step3_run_granger_test(maxlag=5, regime=None)

        logger.info("\n--- Negative GEX Regime Analysis ---")
        granger_neg = self.step3_run_granger_test(maxlag=5, regime="negative")

        # Step 4: Generate LaTeX tables
        if not granger_full.empty:
            self.step4_generate_latex_table(granger_full, regime="all")

        if not granger_neg.empty:
            self.step4_generate_latex_table(granger_neg, regime="negative")

        # Save results to JSON
        output_dir = Path("reports/statistical_validation")
        output_dir.mkdir(parents=True, exist_ok=True)

        results_file = output_dir / f"granger_results_{today_str()}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\nSaved results to {results_file}")

        logger.info("\n" + "=" * 70)
        logger.info("ANALYSIS COMPLETE")
        logger.info("=" * 70)

        # Summary
        if not granger_full.empty:
            sig_lags = granger_full[granger_full["significant"]]["lag"].tolist()
            logger.info(f"\nSignificant lags (full sample): {sig_lags}")
            logger.info(f"Expected: [1, 2, 3] → Actual: {sig_lags}")

        return self.results


def main():
    """Main entry point."""
    analysis = GrangerAnalysis(symbol="SPY", start_date="2024-01-01", end_date="2024-12-31", forward_window=3)

    results = analysis.run_full_analysis()

    print("\n✅ Granger causality analysis complete!")
    print(f"📊 Results saved to: reports/statistical_validation/")
    print(f"📄 LaTeX tables saved to: docs/papers/paper1/tables/")


if __name__ == "__main__":
    main()
