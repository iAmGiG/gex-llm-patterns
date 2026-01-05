#!/usr/bin/env python3
"""
Issue #160: Price Normalization Experiment
===========================================

Tests whether 2020 vs 2024 detection rate difference (12.1% vs 81.2%) is due to:
- H0 (Inflation Trap): SPY price growth inflating GEX magnitude → detection jumps to 80%+
- H1 (Structural Shift): True market structure change → detection stays low (15-25%)

Approach:
1. Query 2020 GEX data from database
2. Calculate price scaling factor: (SPY_2024 / SPY_2020)^2 ≈ 2.3x
3. Apply normalization: GEX_normalized = GEX_2020 * 2.3x
4. Re-calculate regime detection on both original and normalized data
5. Compare detection rates and analyze which criteria drive discrimination

Expected Result:
Detection stays LOW (15-25%) because persistence and stability criteria dominate,
not just magnitude. This would validate structural shift theory.

Author: Chat B
Date: November 25, 2025
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Add project root to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))


class PriceNormalizationTester:
    """Tests price normalization hypothesis for Issue #160."""

    def __init__(self, db_path: str = None):
        """Initialize tester with database connection."""
        if db_path is None:
            # Use main worktree database (shared across all worktrees)
            db_path = "/mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache/consolidated_historical.db"

        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(str(self.db_path))

        # Price scaling factor: (500/330)^2 ≈ 2.30
        self.avg_spy_2020 = 330.0  # Pre-0DTE average SPY price
        self.avg_spy_2024 = 500.0  # Post-0DTE average SPY price
        self.scaling_factor = (self.avg_spy_2024 / self.avg_spy_2020) ** 2

        print(f"Price Scaling Factor: {self.scaling_factor:.3f}x")
        print(f"  (SPY 2024/2020)^2 = ({self.avg_spy_2024}/{self.avg_spy_2020})^2")

    def query_2020_data(self) -> List[Dict]:
        """Query all 2020 GEX data from database.

        NOTE: Uses gex_oi (open-interest based) to match Phase 4 validation methodology.
        """
        query = """
        SELECT date, gex_oi, spot_price
        FROM daily_gex_metrics
        WHERE symbol = 'SPY'
          AND date >= '2020-01-02'
          AND date <= '2020-12-31'
        ORDER BY date ASC
        """

        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        data = []
        for date_str, net_gex, spot_price in rows:
            data.append(
                {
                    "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
                    "net_gex": float(net_gex) / 1e9 if net_gex else 0.0,  # Convert to billions
                    "spot_price": float(spot_price) if spot_price else 0.0,
                }
            )

        print(f"\nQueried {len(data)} trading days from 2020")
        print(f"Sample GEX_OI values (billions): {[round(d['net_gex'], 2) for d in data[:5]]}")
        print(f"  (Using gex_oi column to match Phase 4 validation)")
        return data

    def generate_rolling_windows(self, data: List[Dict]) -> List[Dict]:
        """Generate 223 rolling 30-day windows (matching Phase 4 methodology)."""
        windows = []

        for i in range(len(data) - 29):  # 30-day windows
            window_data = data[i : i + 30]

            window = {
                "start_date": window_data[0]["date"],
                "end_date": window_data[-1]["date"],
                "gex_values": [d["net_gex"] for d in window_data],
                "spot_prices": [d["spot_price"] for d in window_data],
            }

            windows.append(window)

        print(f"Generated {len(windows)} rolling 30-day windows")
        return windows

    def calculate_regime_metrics(self, gex_values: List[float]) -> Dict:
        """Calculate persistence, magnitude, stability metrics."""
        gex_array = np.array(gex_values)

        # Dominant sign
        positive_days = np.sum(gex_array > 0)
        negative_days = np.sum(gex_array < 0)
        dominant_sign = "positive" if positive_days > negative_days else "negative"

        # Persistence: fraction of days with dominant sign
        dominant_days = max(positive_days, negative_days)
        persistence = dominant_days / 30.0

        # Magnitude: average absolute GEX
        magnitude = np.mean(np.abs(gex_array))

        # Stability: count sign flips
        signs = np.sign(gex_array)
        sign_changes = np.sum(signs[1:] != signs[:-1])
        stability = sign_changes

        return {
            "persistence": persistence,
            "magnitude": magnitude,
            "stability": stability,
            "dominant_sign": dominant_sign,
            "dominant_days": dominant_days,
        }

    def classify_regime(self, metrics: Dict) -> Tuple[str, bool]:
        """Classify regime based on criteria (same as Phase 4 methodology)."""
        persistence_pass = metrics["persistence"] >= 0.70
        magnitude_pass = metrics["magnitude"] >= 5.0  # $5B threshold (already in billions)
        stability_pass = metrics["stability"] <= 5

        # All three criteria must pass
        detected = persistence_pass and magnitude_pass and stability_pass

        if detected:
            regime_type = f"persistent_{metrics['dominant_sign']}"
        elif not persistence_pass or not stability_pass:
            regime_type = "transitional"
        else:
            regime_type = "low_conviction"

        return regime_type, detected

    def run_experiment(self) -> Dict:
        """Run full price normalization experiment."""
        print("\n" + "=" * 70)
        print("ISSUE #160: PRICE NORMALIZATION EXPERIMENT")
        print("=" * 70)

        # Step 1: Query 2020 data
        data_2020 = self.query_2020_data()

        # Step 2: Generate rolling windows
        windows = self.generate_rolling_windows(data_2020)

        # Step 3: Calculate detection for ORIGINAL data
        print("\n" + "-" * 70)
        print("ORIGINAL 2020 DATA (No Normalization)")
        print("-" * 70)

        original_results = []
        for window in windows:
            metrics = self.calculate_regime_metrics(window["gex_values"])
            regime_type, detected = self.classify_regime(metrics)

            original_results.append(
                {
                    "start_date": window["start_date"],
                    "end_date": window["end_date"],
                    "detected": detected,
                    "regime_type": regime_type,
                    "persistence": metrics["persistence"],
                    "magnitude": metrics["magnitude"],
                    "stability": metrics["stability"],
                }
            )

        original_detection_rate = sum(r["detected"] for r in original_results) / len(original_results)
        print(
            f"Original Detection Rate: {original_detection_rate*100:.1f}% ({sum(r['detected'] for r in original_results)}/{len(original_results)} windows)"
        )

        # Step 4: Calculate detection for NORMALIZED data
        print("\n" + "-" * 70)
        print(f"NORMALIZED 2020 DATA (Scaling Factor: {self.scaling_factor:.3f}x)")
        print("-" * 70)

        normalized_results = []
        for window in windows:
            # Apply price normalization
            normalized_gex = [gex * self.scaling_factor for gex in window["gex_values"]]

            metrics = self.calculate_regime_metrics(normalized_gex)
            regime_type, detected = self.classify_regime(metrics)

            normalized_results.append(
                {
                    "start_date": window["start_date"],
                    "end_date": window["end_date"],
                    "detected": detected,
                    "regime_type": regime_type,
                    "persistence": metrics["persistence"],
                    "magnitude": metrics["magnitude"],
                    "stability": metrics["stability"],
                }
            )

        normalized_detection_rate = sum(r["detected"] for r in normalized_results) / len(normalized_results)
        print(
            f"Normalized Detection Rate: {normalized_detection_rate*100:.1f}% ({sum(r['detected'] for r in normalized_results)}/{len(normalized_results)} windows)"
        )

        # Step 5: Analyze results
        print("\n" + "=" * 70)
        print("HYPOTHESIS TEST RESULTS")
        print("=" * 70)

        detection_increase = (normalized_detection_rate - original_detection_rate) * 100

        print(f"\nDetection Rate Change: {detection_increase:+.1f} percentage points")
        print(f"  Original:   {original_detection_rate*100:.1f}%")
        print(f"  Normalized: {normalized_detection_rate*100:.1f}%")

        # Determine which hypothesis is supported
        if normalized_detection_rate >= 0.80:
            print("\n⚠️  H0 (INFLATION TRAP) SUPPORTED")
            print("   Detection jumped to 80%+ after normalization")
            print("   → Structural shift theory is WEAKENED")
            conclusion = "inflation_trap"
        elif normalized_detection_rate <= 0.25:
            print("\n✅ H1 (STRUCTURAL SHIFT) SUPPORTED")
            print("   Detection stayed low (≤25%) after normalization")
            print("   → Structural shift theory is BULLETPROOF")
            conclusion = "structural_shift"
        else:
            print("\n⚠️  AMBIGUOUS RESULT")
            print(f"   Detection rate {normalized_detection_rate*100:.1f}% falls in gray zone (25-80%)")
            print("   → Requires additional analysis")
            conclusion = "ambiguous"

        # Analyze which criteria changed
        print("\n" + "-" * 70)
        print("CRITERIA ANALYSIS")
        print("-" * 70)

        # Count how many windows passed each criterion
        original_persistence = sum(r["persistence"] >= 0.70 for r in original_results)
        original_magnitude = sum(r["magnitude"] >= 5.0e9 for r in original_results)
        original_stability = sum(r["stability"] <= 5 for r in original_results)

        normalized_persistence = sum(r["persistence"] >= 0.70 for r in normalized_results)
        normalized_magnitude = sum(r["magnitude"] >= 5.0e9 for r in normalized_results)
        normalized_stability = sum(r["stability"] <= 5 for r in normalized_results)

        print("\nCriterion Pass Rates:")
        print(
            f"  Persistence (≥70%):     {original_persistence}/{len(original_results)} → {normalized_persistence}/{len(normalized_results)} ({normalized_persistence-original_persistence:+d})"
        )
        print(
            f"  Magnitude (≥$5B):       {original_magnitude}/{len(original_results)} → {normalized_magnitude}/{len(normalized_results)} ({normalized_magnitude-original_magnitude:+d})"
        )
        print(
            f"  Stability (≤5 flips):   {original_stability}/{len(original_results)} → {normalized_stability}/{len(normalized_results)} ({normalized_stability-original_stability:+d})"
        )

        # Calculate average metrics
        avg_original_persistence = np.mean([r["persistence"] for r in original_results])
        avg_normalized_persistence = np.mean([r["persistence"] for r in normalized_results])

        avg_original_magnitude = np.mean([r["magnitude"] for r in original_results])
        avg_normalized_magnitude = np.mean([r["magnitude"] for r in normalized_results])

        avg_original_stability = np.mean([r["stability"] for r in original_results])
        avg_normalized_stability = np.mean([r["stability"] for r in normalized_results])

        print("\nAverage Metric Values:")
        print(f"  Persistence: {avg_original_persistence:.1%} → {avg_normalized_persistence:.1%}")
        print(f"  Magnitude:   ${avg_original_magnitude/1e9:.1f}B → ${avg_normalized_magnitude/1e9:.1f}B")
        print(f"  Stability:   {avg_original_stability:.1f} → {avg_normalized_stability:.1f} flips")

        return {
            "conclusion": conclusion,
            "original_detection_rate": original_detection_rate,
            "normalized_detection_rate": normalized_detection_rate,
            "detection_increase_pp": detection_increase,
            "scaling_factor": self.scaling_factor,
            "original_results": original_results,
            "normalized_results": normalized_results,
            "criteria_analysis": {
                "original": {
                    "persistence": original_persistence,
                    "magnitude": original_magnitude,
                    "stability": original_stability,
                },
                "normalized": {
                    "persistence": normalized_persistence,
                    "magnitude": normalized_magnitude,
                    "stability": normalized_stability,
                },
            },
        }

    def generate_latex_table(self, results: Dict, output_path: Path):
        """Generate LaTeX table comparing original vs normalized results."""
        latex = (
            r"""\begin{table}[t]
\centering
\caption{Price Normalization Experiment Results (2020 Data)}
\label{tab:price_normalization}
\begin{tabular}{lcc}
\hline
\textbf{Metric} & \textbf{Original} & \textbf{Normalized} \\
\hline
Detection Rate & """
            + f"{results['original_detection_rate']*100:.1f}\\%"
            + r""" & """
            + f"{results['normalized_detection_rate']*100:.1f}\\%"
            + r""" \\
Scaling Factor & 1.00x & """
            + f"{results['scaling_factor']:.2f}x"
            + r""" \\
\hline
\multicolumn{3}{l}{\textit{Criterion Pass Rates (out of 223 windows)}} \\
\hline
Persistence ($\geq$70\%) & """
            + f"{results['criteria_analysis']['original']['persistence']}"
            + r""" & """
            + f"{results['criteria_analysis']['normalized']['persistence']}"
            + r""" \\
Magnitude ($\geq$\$5B) & """
            + f"{results['criteria_analysis']['original']['magnitude']}"
            + r""" & """
            + f"{results['criteria_analysis']['normalized']['magnitude']}"
            + r""" \\
Stability ($\leq$5 flips) & """
            + f"{results['criteria_analysis']['original']['stability']}"
            + r""" & """
            + f"{results['criteria_analysis']['normalized']['stability']}"
            + r""" \\
\hline
\multicolumn{3}{l}{\textbf{"""
            + f"Conclusion: {results['conclusion'].replace('_', ' ').title()}"
            + r"""}} \\
\hline
\end{tabular}
\end{table}
"""
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(latex)

        print(f"\n✅ LaTeX table saved to: {output_path}")

    def generate_csv_output(self, results: Dict, output_path: Path):
        """Generate CSV with detailed window-by-window results."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write("start_date,end_date,original_detected,normalized_detected,changed,")
            f.write("original_persistence,original_magnitude,original_stability,")
            f.write("normalized_persistence,normalized_magnitude,normalized_stability\n")

            for i in range(len(results["original_results"])):
                orig = results["original_results"][i]
                norm = results["normalized_results"][i]

                changed = "YES" if orig["detected"] != norm["detected"] else "NO"

                f.write(f"{orig['start_date']},{orig['end_date']},")
                f.write(f"{orig['detected']},{norm['detected']},{changed},")
                f.write(f"{orig['persistence']:.3f},{orig['magnitude']:.2e},{orig['stability']},")
                f.write(f"{norm['persistence']:.3f},{norm['magnitude']:.2e},{norm['stability']}\n")

        print(f"✅ CSV results saved to: {output_path}")

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Run Issue #160 price normalization experiment."""
    tester = PriceNormalizationTester()

    try:
        # Run experiment
        results = tester.run_experiment()

        # Generate outputs
        output_dir = Path(project_root) / "reports" / "validation" / "paper2_mc_defenses"

        tester.generate_latex_table(results, output_dir / "issue_160_price_normalization_table.tex")

        tester.generate_csv_output(results, output_dir / "issue_160_price_normalization_results.csv")

        print("\n" + "=" * 70)
        print("EXPERIMENT COMPLETE")
        print("=" * 70)
        print(f"\nConclusion: {results['conclusion'].replace('_', ' ').title()}")
        print(f"Detection Rate Change: {results['detection_increase_pp']:+.1f} percentage points")

        return 0

    finally:
        tester.close()


if __name__ == "__main__":
    sys.exit(main())
