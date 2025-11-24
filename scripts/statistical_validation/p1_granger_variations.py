"""
Additional Granger Causality Tests - Multiple Specifications

Tests various specifications to ensure robustness of null finding.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_data():
    """Load time series data."""
    csv_path = Path("reports/statistical_validation/gamma_positioning_timeseries_2024.csv")
    data = pd.read_csv(csv_path)
    data["date"] = pd.to_datetime(data["date"])

    # Rename columns
    data = data.rename(columns={"net_gex": "gex", "realized_vol_t1": "realized_vol"})

    data = data[["date", "gex", "realized_vol"]].dropna()
    return data


def test_specification(data, gex_transform, vol_transform, maxlag, name):
    """Test a specific specification.

    Args:
        data: Input DataFrame
        gex_transform: 'level', 'diff', 'pct_change'
        vol_transform: 'level', 'diff', 'pct_change'
        maxlag: Maximum lag to test
        name: Specification name
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Testing: {name}")
    logger.info(f"  GEX: {gex_transform}, Vol: {vol_transform}, MaxLag: {maxlag}")
    logger.info(f"{'='*70}")

    df = data.copy()

    # Transform GEX
    if gex_transform == "diff":
        df["gex_t"] = df["gex"].diff()
    elif gex_transform == "pct_change":
        df["gex_t"] = df["gex"].pct_change()
    else:
        df["gex_t"] = df["gex"]

    # Transform volatility
    if vol_transform == "diff":
        df["vol_t"] = df["realized_vol"].diff()
    elif vol_transform == "pct_change":
        df["vol_t"] = df["realized_vol"].pct_change()
    else:
        df["vol_t"] = df["realized_vol"]

    df = df[["vol_t", "gex_t"]].dropna()

    if len(df) < 50:
        logger.warning(f"  Sample too small: {len(df)} observations")
        return None

    logger.info(f"  Sample size: {len(df)} observations")

    # Run Granger test
    try:
        results = grangercausalitytests(df[["vol_t", "gex_t"]], maxlag=maxlag, verbose=False)

        # Extract p-values
        p_values = []
        for lag in range(1, maxlag + 1):
            test_result = results[lag][0]
            p_val = test_result["ssr_ftest"][1]
            p_values.append(p_val)
            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
            logger.info(f"  Lag {lag}: p={p_val:.4f} {sig}")

        # Check if any lag is significant
        min_p = min(p_values)
        sig_lags = sum(1 for p in p_values if p < 0.05)

        logger.info(f"  Min p-value: {min_p:.4f}")
        logger.info(f"  Significant lags (p<0.05): {sig_lags}/{maxlag}")

        return {
            "name": name,
            "gex_transform": gex_transform,
            "vol_transform": vol_transform,
            "maxlag": maxlag,
            "min_p": min_p,
            "sig_lags": sig_lags,
            "p_values": p_values,
        }

    except Exception as e:
        logger.error(f"  Error: {e}")
        return None


def main():
    """Run multiple Granger specifications."""
    logger.info("=" * 70)
    logger.info("GRANGER CAUSALITY - ROBUSTNESS CHECKS")
    logger.info("=" * 70)

    # Load data
    data = load_data()
    logger.info(f"\nLoaded {len(data)} observations")
    logger.info(f"GEX range: ${data['gex'].min()/1e9:.2f}B to ${data['gex'].max()/1e9:.2f}B")
    logger.info(f"Vol range: {data['realized_vol'].min():.4f} to {data['realized_vol'].max():.4f}")

    # Test multiple specifications
    results = []

    # Spec 1: Original (differenced GEX, level vol)
    results.append(test_specification(data, "diff", "level", 5, "Original: Differenced GEX vs Level Vol (Lags 1-5)"))

    # Spec 2: Both in levels
    results.append(test_specification(data, "level", "level", 5, "Both Levels (Lags 1-5)"))

    # Spec 3: Both differenced
    results.append(test_specification(data, "diff", "diff", 5, "Both Differenced (Lags 1-5)"))

    # Spec 4: Extended lags
    results.append(
        test_specification(data, "diff", "level", 10, "Extended Lags: Differenced GEX vs Level Vol (Lags 1-10)")
    )

    # Spec 5: Percentage changes
    results.append(test_specification(data, "pct_change", "pct_change", 5, "Percentage Changes (Lags 1-5)"))

    # Spec 6: Short lags only (1-3)
    results.append(
        test_specification(data, "diff", "level", 3, "Short Lags Only: Differenced GEX vs Level Vol (Lags 1-3)")
    )

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY OF ALL SPECIFICATIONS")
    logger.info("=" * 70)

    results = [r for r in results if r is not None]

    for i, r in enumerate(results, 1):
        logger.info(f"\n{i}. {r['name']}")
        logger.info(f"   Min p-value: {r['min_p']:.4f}")
        logger.info(f"   Significant lags: {r['sig_lags']}/{r['maxlag']}")
        logger.info(f"   Result: {'SIGNIFICANT' if r['sig_lags'] > 0 else 'NULL'}")

    # Overall conclusion
    total_specs = len(results)
    sig_specs = sum(1 for r in results if r["sig_lags"] > 0)

    logger.info("\n" + "=" * 70)
    logger.info("OVERALL CONCLUSION")
    logger.info("=" * 70)
    logger.info(f"Specifications tested: {total_specs}")
    logger.info(f"Significant results: {sig_specs}/{total_specs}")

    if sig_specs == 0:
        logger.info("\n✅ ROBUST NULL FINDING: No Granger causality across all specifications")
    else:
        logger.info(f"\n⚠️  MIXED RESULTS: {sig_specs} specifications show significance")

    # Save results
    output_path = Path("reports/statistical_validation/granger_robustness_results.csv")

    summary_df = pd.DataFrame(
        [
            {
                "specification": r["name"],
                "gex_transform": r["gex_transform"],
                "vol_transform": r["vol_transform"],
                "maxlag": r["maxlag"],
                "min_p_value": r["min_p"],
                "significant_lags": r["sig_lags"],
                "result": "SIGNIFICANT" if r["sig_lags"] > 0 else "NULL",
            }
            for r in results
        ]
    )

    summary_df.to_csv(output_path, index=False)
    logger.info(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
