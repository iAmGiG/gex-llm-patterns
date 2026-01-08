"""Lead-Lag Analysis Variations.

Since all 242 days are negative GEX, we test within-regime relationships:
1. Correlation between GEX magnitude and volatility
2. GEX terciles (high/medium/low negative) comparison
3. GEX momentum (accelerating vs decelerating) analysis
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_data():
    """Load time series data."""
    csv_path = Path("reports/statistical_validation/gamma_positioning_timeseries_2024.csv")
    data = pd.read_csv(csv_path)
    data["date"] = pd.to_datetime(data["date"])

    data = data[["date", "net_gex", "spot_price", "forward_return_t1", "realized_vol_t1"]].dropna()

    return data


def test_correlation(data):
    """Test 1: Correlation between GEX magnitude and volatility."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: GEX MAGNITUDE vs VOLATILITY CORRELATION")
    logger.info("=" * 70)

    # Pearson correlation
    corr_pearson, p_pearson = stats.pearsonr(data["net_gex"], data["realized_vol_t1"])
    logger.info(f"Pearson correlation: r={corr_pearson:.4f}, p={p_pearson:.4f}")

    # Spearman correlation (non-parametric)
    corr_spearman, p_spearman = stats.spearmanr(data["net_gex"], data["realized_vol_t1"])
    logger.info(f"Spearman correlation: ρ={corr_spearman:.4f}, p={p_spearman:.4f}")

    # Interpretation
    if abs(corr_pearson) > 0.3:
        logger.info("✅ Moderate correlation detected")
    elif abs(corr_pearson) > 0.1:
        logger.info("⚠️  Weak correlation detected")
    else:
        logger.info("❌ No meaningful correlation")

    return {"pearson_r": corr_pearson, "pearson_p": p_pearson, "spearman_rho": corr_spearman, "spearman_p": p_spearman}


def test_terciles(data):
    """Test 2: GEX terciles comparison (high/medium/low negative)."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: GEX TERCILES COMPARISON")
    logger.info("=" * 70)

    # Divide negative GEX into terciles
    data["gex_tercile"] = pd.qcut(data["net_gex"], q=3, labels=["Most Negative", "Medium Negative", "Least Negative"])

    # Calculate statistics by tercile
    tercile_stats = data.groupby("gex_tercile").agg(
        {"realized_vol_t1": ["mean", "std", "count"], "net_gex": ["mean", "min", "max"]}
    )

    logger.info("\nTercile Statistics:")
    logger.info(tercile_stats)

    # Get volatility by tercile
    most_neg = data[data["gex_tercile"] == "Most Negative"]["realized_vol_t1"]
    med_neg = data[data["gex_tercile"] == "Medium Negative"]["realized_vol_t1"]
    least_neg = data[data["gex_tercile"] == "Least Negative"]["realized_vol_t1"]

    logger.info(f"\nMost Negative GEX: {most_neg.mean():.4f}% vol (n={len(most_neg)})")
    logger.info(f"Medium Negative GEX: {med_neg.mean():.4f}% vol (n={len(med_neg)})")
    logger.info(f"Least Negative GEX: {least_neg.mean():.4f}% vol (n={len(least_neg)})")

    # ANOVA test
    f_stat, p_val = stats.f_oneway(most_neg, med_neg, least_neg)
    logger.info(f"\nANOVA: F={f_stat:.4f}, p={p_val:.4f}")

    # Pairwise t-tests
    t_stat_12, p_12 = stats.ttest_ind(most_neg, med_neg)
    t_stat_13, p_13 = stats.ttest_ind(most_neg, least_neg)
    t_stat_23, p_23 = stats.ttest_ind(med_neg, least_neg)

    logger.info(f"\nPairwise t-tests:")
    logger.info(f"  Most vs Medium: t={t_stat_12:.4f}, p={p_12:.4f}")
    logger.info(f"  Most vs Least: t={t_stat_13:.4f}, p={p_13:.4f}")
    logger.info(f"  Medium vs Least: t={t_stat_23:.4f}, p={p_23:.4f}")

    # Effect size (Most vs Least)
    pooled_std = np.sqrt((most_neg.std() ** 2 + least_neg.std() ** 2) / 2)
    cohens_d = (most_neg.mean() - least_neg.mean()) / pooled_std
    logger.info(f"\nCohen's d (Most vs Least): {cohens_d:.4f}")

    return {
        "anova_f": f_stat,
        "anova_p": p_val,
        "most_neg_mean_vol": most_neg.mean(),
        "least_neg_mean_vol": least_neg.mean(),
        "vol_difference": most_neg.mean() - least_neg.mean(),
        "cohens_d": cohens_d,
        "pairwise_p_most_least": p_13,
    }


def test_momentum(data):
    """Test 3: GEX momentum (accelerating vs decelerating negative)."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: GEX MOMENTUM ANALYSIS")
    logger.info("=" * 70)

    # Calculate GEX change
    data["gex_change"] = data["net_gex"].diff()

    # Classify momentum
    data["gex_momentum"] = pd.cut(
        data["gex_change"],
        bins=[-np.inf, -1e9, 1e9, np.inf],
        labels=["Accelerating Negative", "Stable", "Decelerating Negative"],
    )

    # Drop NaN from differencing
    data_momentum = data.dropna()

    # Calculate statistics by momentum
    momentum_stats = data_momentum.groupby("gex_momentum").agg(
        {"realized_vol_t1": ["mean", "std", "count"], "gex_change": ["mean"]}
    )

    logger.info("\nMomentum Statistics:")
    logger.info(momentum_stats)

    # Get volatility by momentum
    accel = data_momentum[data_momentum["gex_momentum"] == "Accelerating Negative"]["realized_vol_t1"]
    stable = data_momentum[data_momentum["gex_momentum"] == "Stable"]["realized_vol_t1"]
    decel = data_momentum[data_momentum["gex_momentum"] == "Decelerating Negative"]["realized_vol_t1"]

    logger.info(f"\nAccelerating Negative: {accel.mean():.4f}% vol (n={len(accel)})")
    logger.info(f"Stable: {stable.mean():.4f}% vol (n={len(stable)})")
    logger.info(f"Decelerating Negative: {decel.mean():.4f}% vol (n={len(decel)})")

    # ANOVA test
    if len(accel) > 0 and len(stable) > 0 and len(decel) > 0:
        f_stat, p_val = stats.f_oneway(accel, stable, decel)
        logger.info(f"\nANOVA: F={f_stat:.4f}, p={p_val:.4f}")
    else:
        f_stat, p_val = np.nan, np.nan
        logger.warning("Insufficient data for ANOVA")

    return {
        "anova_f": f_stat,
        "anova_p": p_val,
        "accel_mean_vol": accel.mean() if len(accel) > 0 else np.nan,
        "stable_mean_vol": stable.mean() if len(stable) > 0 else np.nan,
        "decel_mean_vol": decel.mean() if len(decel) > 0 else np.nan,
    }


def main():
    """Run all lead-lag variations."""
    logger.info("=" * 70)
    logger.info("LEAD-LAG ANALYSIS - WITHIN-REGIME VARIATIONS")
    logger.info("=" * 70)

    # Load data
    data = load_data()
    logger.info(f"\nLoaded {len(data)} observations")
    logger.info(f"Date range: {data['date'].min()} to {data['date'].max()}")
    logger.info(f"GEX range: ${data['net_gex'].min()/1e9:.2f}B to ${data['net_gex'].max()/1e9:.2f}B")
    logger.info(f"Vol range: {data['realized_vol_t1'].min():.4f}% to {data['realized_vol_t1'].max():.4f}%")

    # Run tests
    results = {}

    results["correlation"] = test_correlation(data)
    results["terciles"] = test_terciles(data)
    results["momentum"] = test_momentum(data)

    # Overall summary
    logger.info("\n" + "=" * 70)
    logger.info("OVERALL SUMMARY")
    logger.info("=" * 70)

    logger.info(f"\n1. CORRELATION:")
    logger.info(
        f"   Pearson r = {results['correlation']['pearson_r']:.4f} (p={results['correlation']['pearson_p']:.4f})"
    )
    logger.info(
        f"   Spearman ρ = {results['correlation']['spearman_rho']:.4f} (p={results['correlation']['spearman_p']:.4f})"
    )

    logger.info(f"\n2. TERCILES:")
    logger.info(f"   Most Negative: {results['terciles']['most_neg_mean_vol']:.4f}% vol")
    logger.info(f"   Least Negative: {results['terciles']['least_neg_mean_vol']:.4f}% vol")
    logger.info(
        f"   Difference: {results['terciles']['vol_difference']:.4f}% (Cohen's d={results['terciles']['cohens_d']:.4f})"
    )
    logger.info(f"   p-value: {results['terciles']['pairwise_p_most_least']:.4f}")

    logger.info(f"\n3. MOMENTUM:")
    logger.info(f"   Accelerating: {results['momentum']['accel_mean_vol']:.4f}% vol")
    logger.info(f"   Stable: {results['momentum']['stable_mean_vol']:.4f}% vol")
    logger.info(f"   Decelerating: {results['momentum']['decel_mean_vol']:.4f}% vol")
    logger.info(f"   ANOVA p-value: {results['momentum']['anova_p']:.4f}")

    # Save results
    output_path = Path("reports/statistical_validation/leadlag_within_regime_results.csv")

    summary_df = pd.DataFrame(
        [
            {
                "test": "Correlation (Pearson)",
                "statistic": results["correlation"]["pearson_r"],
                "p_value": results["correlation"]["pearson_p"],
                "significant": results["correlation"]["pearson_p"] < 0.05,
            },
            {
                "test": "Correlation (Spearman)",
                "statistic": results["correlation"]["spearman_rho"],
                "p_value": results["correlation"]["spearman_p"],
                "significant": results["correlation"]["spearman_p"] < 0.05,
            },
            {
                "test": "Terciles ANOVA",
                "statistic": results["terciles"]["anova_f"],
                "p_value": results["terciles"]["anova_p"],
                "significant": results["terciles"]["anova_p"] < 0.05,
            },
            {
                "test": "Momentum ANOVA",
                "statistic": results["momentum"]["anova_f"],
                "p_value": results["momentum"]["anova_p"],
                "significant": results["momentum"]["anova_p"] < 0.05,
            },
        ]
    )

    summary_df.to_csv(output_path, index=False)
    logger.info(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
