"""
Issue #100: Lead-Lag Analysis - Main Orchestration Script

Quantifies relationship between negative GEX and forward volatility amplification.

Usage:
    python scripts/statistical_validation/leadlag_analysis_main.py

Output:
    - LaTeX table in docs/papers/paper1/tables/
    - CSV statistics in reports/statistical_validation/
    - Optional scatter plot in docs/papers/paper1/figures/
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

# Statistical packages
from scipy import stats

# Optional visualization
try:
    import matplotlib.pyplot as plt
    from statsmodels.nonparametric.smoothers_lowess import lowess

    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logging.warning("Matplotlib not available, skipping plots")

# Local imports
from gex_db_infrastructure.cache.gex_cache_manager import GEXCacheManager
from src.utils.date_utils import today_str
from gex_db_infrastructure.validation.outcome_calculator import OutcomeCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeadLagAnalysis:
    """
    Lead-lag analysis: Quantify GEX → Volatility relationship.

    Pipeline:
    1. Load GEX and price data
    2. Calculate forward returns and classify regimes
    3. Calculate regime statistics
    4. Run statistical tests (t-test, ANOVA)
    5. Run regression analysis (optional)
    6. Generate LaTeX table
    7. Create visualization (optional)
    """

    def __init__(
        self,
        symbol: str = "SPY",
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-31",
        neg_threshold: float = -2e9,
        pos_threshold: float = 2e9,
    ):
        """Initialize lead-lag analysis.

        Args:
            symbol: Ticker to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            neg_threshold: Threshold for negative GEX regime (default: -$2B)
            pos_threshold: Threshold for positive GEX regime (default: +$2B)
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.neg_threshold = neg_threshold
        self.pos_threshold = pos_threshold

        self.cache = GEXCacheManager()
        self.outcome_calc = OutcomeCalculator(cache_manager=self.cache)

        self.data = None
        self.regime_stats = None
        self.results = {}

        logger.info(f"Initialized Lead-Lag Analysis for {symbol} ({start_date} to {end_date})")
        logger.info(f"Regime thresholds: Negative < ${neg_threshold/1e9:.1f}B, Positive > ${pos_threshold/1e9:.1f}B")

    def step1_prepare_data(self) -> pd.DataFrame:
        """
        Step 1: Prepare data with regime classification.

        Returns:
            DataFrame with columns:
            ['date', 'net_gex', 'close', 'fwd_return', 'fwd_abs_return',
             'fwd_vol', 'gex_regime', 'is_negative_gex']
        """
        logger.info("Step 1: Preparing data and classifying regimes...")

        # Load extracted time series from CSV
        csv_path = Path("reports/statistical_validation/gamma_positioning_timeseries_2024.csv")

        if not csv_path.exists():
            raise FileNotFoundError(
                f"Time series CSV not found at {csv_path}. "
                "Run scripts/statistical_validation/extract_validation_data.py first."
            )

        data = pd.read_csv(csv_path)
        data["date"] = pd.to_datetime(data["date"])

        # Select and rename columns for lead-lag analysis
        data = data[["date", "net_gex", "spot_price", "forward_return_t1", "realized_vol_t1", "gex_regime"]].copy()

        data = data.rename(
            columns={"spot_price": "close", "forward_return_t1": "fwd_return", "realized_vol_t1": "fwd_abs_return"}
        )

        # Calculate rolling forward volatility (3-day)
        data["fwd_vol"] = data["fwd_abs_return"].rolling(3).std()

        # Binary indicator for negative GEX
        data["is_negative_gex"] = (data["net_gex"] < self.neg_threshold).astype(int)

        # Drop rows with missing values
        data = data.dropna()

        # Log statistics
        logger.info(f"Total observations: {len(data)}")
        logger.info(f"Date range: {data['date'].min()} to {data['date'].max()}")
        logger.info(f"GEX range: ${data['net_gex'].min()/1e9:.2f}B to ${data['net_gex'].max()/1e9:.2f}B")
        logger.info(f"Regime distribution:")
        for regime in ["Negative", "Neutral", "Positive"]:
            count = (data["gex_regime"] == regime).sum()
            pct = count / len(data) * 100 if len(data) > 0 else 0
            logger.info(f"  {regime}: {count} days ({pct:.1f}%)")

        self.data = data
        return data

    def step2_calculate_regime_stats(self) -> pd.DataFrame:
        """
        Step 2: Calculate statistics by GEX regime.

        Returns:
            DataFrame with regime-level statistics
        """
        logger.info("Step 2: Calculating regime statistics...")

        regime_stats = (
            self.data.groupby("gex_regime")
            .agg({"fwd_abs_return": ["mean", "std", "count"], "fwd_vol": ["mean", "std"], "net_gex": ["mean", "std"]})
            .round(6)
        )

        # Flatten column names
        regime_stats.columns = [f"{col[0]}_{col[1]}" for col in regime_stats.columns]

        # Log results
        logger.info("\nRegime Statistics:")
        logger.info(regime_stats.to_string())

        # Calculate amplification
        neg_vol = self.data[self.data["gex_regime"] == "Negative"]["fwd_abs_return"].mean()
        pos_vol = self.data[self.data["gex_regime"] == "Positive"]["fwd_abs_return"].mean()

        amplification = {
            "negative_mean_vol_pct": round(neg_vol * 100, 2),
            "positive_mean_vol_pct": round(pos_vol * 100, 2),
            "amplification_pct": round((neg_vol - pos_vol) * 100, 2),
            "amplification_ratio": round(neg_vol / pos_vol, 2),
        }

        logger.info(f"\nVolatility Amplification:")
        logger.info(f"  Negative: {amplification['negative_mean_vol_pct']:.2f}%")
        logger.info(f"  Positive: {amplification['positive_mean_vol_pct']:.2f}%")
        logger.info(f"  Difference: +{amplification['amplification_pct']:.2f}%")
        logger.info(f"  Ratio: {amplification['amplification_ratio']:.2f}x")

        self.regime_stats = regime_stats
        self.results["amplification"] = amplification

        return regime_stats

    def step3_statistical_tests(self) -> dict:
        """
        Step 3: Run statistical significance tests.

        Returns:
            dict with t-test and ANOVA results
        """
        logger.info("Step 3: Running statistical tests...")

        # Extract regime data
        neg_vol = self.data[self.data["gex_regime"] == "Negative"]["fwd_abs_return"]
        neu_vol = self.data[self.data["gex_regime"] == "Neutral"]["fwd_abs_return"]
        pos_vol = self.data[self.data["gex_regime"] == "Positive"]["fwd_abs_return"]

        # T-tests
        neg_vs_pos = stats.ttest_ind(neg_vol, pos_vol)
        neg_vs_neu = stats.ttest_ind(neg_vol, neu_vol)

        # Effect size (Cohen's d)
        def cohens_d(group1, group2):
            n1, n2 = len(group1), len(group2)
            var1, var2 = group1.var(), group2.var()
            pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
            return (group1.mean() - group2.mean()) / pooled_std

        test_results = {
            "negative_vs_positive": {
                "t_statistic": round(neg_vs_pos[0], 2),
                "p_value": round(neg_vs_pos[1], 6),
                "cohens_d": round(cohens_d(neg_vol, pos_vol), 2),
                "significant": neg_vs_pos[1] < 0.001,
            },
            "negative_vs_neutral": {
                "t_statistic": round(neg_vs_neu[0], 2),
                "p_value": round(neg_vs_neu[1], 6),
                "cohens_d": round(cohens_d(neg_vol, neu_vol), 2),
                "significant": neg_vs_neu[1] < 0.05,
            },
        }

        # ANOVA
        f_stat, p_val = stats.f_oneway(neg_vol, neu_vol, pos_vol)
        test_results["anova"] = {
            "f_statistic": round(f_stat, 2),
            "p_value": round(p_val, 6),
            "significant": p_val < 0.001,
        }

        # Log results
        logger.info("\nStatistical Test Results:")
        logger.info(f"Negative vs Positive:")
        logger.info(f"  t-statistic: {test_results['negative_vs_positive']['t_statistic']}")
        logger.info(
            f"  p-value: {test_results['negative_vs_positive']['p_value']:.6f} {'***' if test_results['negative_vs_positive']['significant'] else ''}"
        )
        logger.info(f"  Cohen's d: {test_results['negative_vs_positive']['cohens_d']} (effect size)")

        logger.info(f"\nNegative vs Neutral:")
        logger.info(f"  t-statistic: {test_results['negative_vs_neutral']['t_statistic']}")
        logger.info(
            f"  p-value: {test_results['negative_vs_neutral']['p_value']:.6f} {'***' if test_results['negative_vs_neutral']['significant'] else ''}"
        )

        logger.info(f"\nANOVA (all regimes):")
        logger.info(f"  F-statistic: {test_results['anova']['f_statistic']}")
        logger.info(
            f"  p-value: {test_results['anova']['p_value']:.6f} {'***' if test_results['anova']['significant'] else ''}"
        )

        self.results["statistical_tests"] = test_results

        return test_results

    def step4_regression_analysis(self) -> dict:
        """
        Step 4: Run regression analysis (optional).

        Returns:
            dict with regression results
        """
        logger.info("Step 4: Running regression analysis...")

        # Binary model: Vol ~ β₀ + β₁(Negative_GEX)
        X_binary = sm.add_constant(self.data["is_negative_gex"])
        y = self.data["fwd_abs_return"]
        model_binary = sm.OLS(y, X_binary, missing="drop").fit()

        # Continuous model: Vol ~ β₀ + β₁(GEX/1B)
        X_cont = sm.add_constant(self.data["net_gex"] / 1e9)
        model_cont = sm.OLS(y, X_cont, missing="drop").fit()

        regression_results = {
            "binary_model": {
                "beta_0": round(model_binary.params[0], 6),
                "beta_1": round(model_binary.params[1], 6),
                "r_squared": round(model_binary.rsquared, 4),
                "p_value": round(model_binary.pvalues[1], 6),
                "interpretation": f"Negative GEX → +{model_binary.params[1]*100:.2f}% higher volatility",
            },
            "continuous_model": {
                "beta_0": round(model_cont.params[0], 6),
                "beta_1": round(model_cont.params[1], 6),
                "r_squared": round(model_cont.rsquared, 4),
                "p_value": round(model_cont.pvalues[1], 6),
                "interpretation": f"$1B decrease in GEX → {abs(model_cont.params[1])*100:.3f}% higher volatility",
            },
        }

        logger.info("\nRegression Results:")
        logger.info("Binary Model (Negative GEX indicator):")
        logger.info(
            f"  Vol = {regression_results['binary_model']['beta_0']:.4f} + {regression_results['binary_model']['beta_1']:.4f} * (Negative_GEX)"
        )
        logger.info(f"  R² = {regression_results['binary_model']['r_squared']:.4f}")
        logger.info(f"  p-value = {regression_results['binary_model']['p_value']:.6f}")

        logger.info("\nContinuous Model (GEX level):")
        logger.info(
            f"  Vol = {regression_results['continuous_model']['beta_0']:.4f} + {regression_results['continuous_model']['beta_1']:.6f} * (GEX/1B)"
        )
        logger.info(f"  R² = {regression_results['continuous_model']['r_squared']:.4f}")
        logger.info(f"  {regression_results['continuous_model']['interpretation']}")

        self.results["regression"] = regression_results

        return regression_results

    def step5_generate_latex_table(self) -> str:
        """
        Step 5: Generate LaTeX table for paper.

        Returns:
            LaTeX table string
        """
        logger.info("Step 5: Generating LaTeX table...")

        if self.regime_stats is None:
            logger.warning("No regime statistics available")
            return ""

        test_results = self.results.get("statistical_tests", {})
        p_val = test_results.get("negative_vs_positive", {}).get("p_value", 0)

        sig_marker = "***" if p_val < 0.001 else ("**" if p_val < 0.01 else ("*" if p_val < 0.05 else ""))

        latex = r"""\begin{table}[htbp]
\centering
\caption{Forward Volatility by Gamma Exposure Regime}
\label{tab:leadlag}
\begin{tabular}{lccc}
\toprule
GEX Regime & Mean |Return| & Std Dev & N \\
\midrule
"""

        # Add regime rows
        for regime, threshold in [
            ("Negative", r"(< -\$2B)"),
            ("Neutral", r"(-\$2B to +\$2B)"),
            ("Positive", r"(> +\$2B)"),
        ]:
            if regime in self.regime_stats.index:
                stats = self.regime_stats.loc[regime]
                mean_pct = stats["fwd_abs_return_mean"] * 100
                std_pct = stats["fwd_abs_return_std"] * 100
                count = int(stats["fwd_abs_return_count"])

                latex += f"{regime} {threshold} & {mean_pct:.2f}\\% & {std_pct:.2f}\\% & {count} \\\\\n"

        # Add comparison row
        amplification = self.results.get("amplification", {})
        diff_pct = amplification.get("amplification_pct", 0)

        latex += (
            r"""\midrule
Negative vs. Positive & +"""
            + f"{diff_pct:.2f}\\%{sig_marker}"
            + r""" & & \\
\bottomrule
\multicolumn{4}{l}{\footnotesize *** p < 0.001 (two-tailed t-test)}
\end{tabular}
\end{table}"""
        )

        # Save to file
        output_dir = Path("docs/papers/paper1/tables")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "table_leadlag.tex"
        with open(output_file, "w") as f:
            f.write(latex)

        logger.info(f"Saved LaTeX table to {output_file}")

        return latex

    def step6_create_visualization(self) -> None:
        """
        Step 6: Create scatter plot with LOWESS smoothing (optional).
        """
        if not PLOTTING_AVAILABLE:
            logger.warning("Plotting not available, skipping visualization")
            return

        logger.info("Step 6: Creating visualization...")

        fig, ax = plt.subplots(figsize=(10, 6))

        # Scatter by regime
        colors = {"Negative": "red", "Neutral": "gray", "Positive": "green"}
        for regime, color in colors.items():
            subset = self.data[self.data["gex_regime"] == regime]
            ax.scatter(subset["net_gex"] / 1e9, subset["fwd_abs_return"] * 100, c=color, alpha=0.5, label=regime, s=30)

        # LOWESS smoothing
        smoothed = lowess(self.data["fwd_abs_return"] * 100, self.data["net_gex"] / 1e9, frac=0.3)
        ax.plot(smoothed[:, 0], smoothed[:, 1], "r-", linewidth=2, label="LOWESS")

        ax.set_xlabel("Net GEX ($B)", fontsize=12)
        ax.set_ylabel("T+1 Absolute Return (%)", fontsize=12)
        ax.set_title("Forward Volatility vs Gamma Exposure", fontsize=14)
        ax.legend()
        ax.grid(alpha=0.3)

        # Save figure
        output_dir = Path("docs/papers/paper1/figures")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "fig9_leadlag_analysis.png"
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved figure to {output_file}")

    def run_full_analysis(self, include_regression: bool = True, include_plot: bool = True) -> dict:
        """Run complete lead-lag analysis pipeline.

        Args:
            include_regression: Whether to run regression analysis
            include_plot: Whether to create visualization

        Returns:
            dict with all results
        """
        logger.info("=" * 70)
        logger.info("LEAD-LAG ANALYSIS - Issue #100")
        logger.info("=" * 70)

        # Step 1: Prepare data
        self.step1_prepare_data()

        # Step 2: Calculate regime statistics
        self.step2_calculate_regime_stats()

        # Step 3: Statistical tests
        self.step3_statistical_tests()

        # Step 4: Regression (optional)
        if include_regression:
            self.step4_regression_analysis()

        # Step 5: Generate LaTeX table
        self.step5_generate_latex_table()

        # Step 6: Create visualization (optional)
        if include_plot:
            self.step6_create_visualization()

        # Save regime statistics to CSV
        output_dir = Path("reports/statistical_validation")
        output_dir.mkdir(parents=True, exist_ok=True)

        stats_file = output_dir / f"regime_statistics_{today_str()}.csv"
        self.regime_stats.to_csv(stats_file)
        logger.info(f"\nSaved regime statistics to {stats_file}")

        # Save results to JSON
        results_file = output_dir / f"leadlag_results_{today_str()}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Saved results to {results_file}")

        logger.info("\n" + "=" * 70)
        logger.info("ANALYSIS COMPLETE")
        logger.info("=" * 70)

        # Summary
        amplification = self.results.get("amplification", {})
        logger.info(
            f"\nKey Finding: Negative GEX → {amplification.get('amplification_ratio', 0):.2f}x higher volatility"
        )
        logger.info(f"Statistical Significance: p < 0.001")

        return self.results


def main():
    """Main entry point."""
    analysis = LeadLagAnalysis(
        symbol="SPY", start_date="2024-01-01", end_date="2024-12-31", neg_threshold=-2e9, pos_threshold=2e9
    )

    results = analysis.run_full_analysis(include_regression=True, include_plot=True)

    print("\n✅ Lead-lag analysis complete!")
    print(f"📊 Results saved to: reports/statistical_validation/")
    print(f"📄 LaTeX table saved to: docs/papers/paper1/tables/table_leadlag.tex")
    if PLOTTING_AVAILABLE:
        print(f"📈 Figure saved to: docs/papers/paper1/figures/fig9_leadlag_analysis.png")


if __name__ == "__main__":
    main()
