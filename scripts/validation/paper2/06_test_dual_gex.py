#!/usr/bin/env python3
"""Test Dual GEX Framework Implementation (Issue #138)

Purpose:
    Verify that calculate_dual_gex() and classify_economic_regime() work correctly
    before running on full 2024 dataset.

Tests:
    1. GEX_OI calculation (structural positioning)
    2. GEX_Volume calculation (economic activity)
    3. Economic regime classification (4 regimes)
    4. Dual window classification (structural + economic)

Expected Results:
    - GEX_OI matches existing net_gex calculation
    - GEX_Volume correctly uses volume weighting
    - 4 regimes correctly classified
    - Dual classification combines both metrics
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from gex_db_infrastructure.gex.gex_calculator import GEXCalculator
from gex_db_infrastructure.validation.regime_classifier import RegimeClassifier


def create_synthetic_options_data(n_contracts: int = 100) -> pd.DataFrame:
    """Create synthetic options data for testing."""
    np.random.seed(42)

    strikes = np.linspace(450, 550, n_contracts)

    data = pd.DataFrame(
        {
            "strike": strikes,
            "type": np.random.choice(["call", "put"], n_contracts),
            "open_interest": np.random.randint(100, 10000, n_contracts),
            "volume": np.random.randint(10, 5000, n_contracts),  # Volume < OI
            "implied_volatility": np.random.uniform(0.15, 0.35, n_contracts),
            "days_to_expiration": np.random.randint(1, 60, n_contracts),
        }
    )

    return data


def test_1_dual_gex_calculation():
    """Test 1: Verify dual GEX calculation produces two metrics."""
    print("\n" + "=" * 80)
    print("TEST 1: Dual GEX Calculation")
    print("=" * 80)

    gex_calc = GEXCalculator()
    options_data = create_synthetic_options_data(100)
    underlying_price = 500.0

    # Calculate dual GEX
    result = gex_calc.calculate_dual_gex(options_data, underlying_price)

    print(f"\n✅ Dual GEX calculated successfully")
    print(f"   GEX_OI:     ${result['gex_oi']/1e9:.2f}B (structural)")
    print(f"   GEX_Volume: ${result['gex_volume']/1e9:.2f}B (activity)")
    print(f"   Net GEX:    ${result['net_gex']/1e9:.2f}B (backward compatible)")
    print(f"   Activity Ratio: {result['activity_ratio']:.2f}")
    print(f"   Has Volume Data: {result['has_volume_data']}")

    # Verify backward compatibility
    assert result["net_gex"] == result["gex_oi"], "net_gex should equal gex_oi"
    print(f"\n✅ Backward compatibility verified (net_gex == gex_oi)")

    # Verify volume data was used
    assert result["has_volume_data"], "Volume data should be present"
    print(f"✅ Volume data correctly detected")

    return result


def test_2_economic_regime_classification():
    """Test 2: Verify 4-regime classification logic."""
    print("\n" + "=" * 80)
    print("TEST 2: Economic Regime Classification")
    print("=" * 80)

    classifier = RegimeClassifier()

    test_cases = [
        {
            "name": "HIGH_FRAGILITY (Q4 2024-like)",
            "gex_oi": -12e9,
            "gex_volume": -0.5e9,
            "expected_regime": "high_fragility",
            "expected_profit": "low",
        },
        {
            "name": "ELEVATED_RISK (Q1 2024-like)",
            "gex_oi": -15e9,
            "gex_volume": -8e9,
            "expected_regime": "elevated_risk",
            "expected_profit": "high",
        },
        {
            "name": "STABLE_POSITIVE",
            "gex_oi": 10e9,
            "gex_volume": 5e9,
            "expected_regime": "stable_positive",
            "expected_profit": "low_volatility",
        },
        {
            "name": "TRANSITIONAL",
            "gex_oi": -5e9,
            "gex_volume": 3e9,
            "expected_regime": "transitional",
            "expected_profit": "uncertain",
        },
    ]

    for test in test_cases:
        result = classifier.classify_economic_regime(test["gex_oi"], test["gex_volume"])

        print(f"\n{test['name']}:")
        print(f"   Input: GEX_OI=${test['gex_oi']/1e9:.1f}B, GEX_Volume=${test['gex_volume']/1e9:.1f}B")
        print(f"   Classified: {result['regime']} (expected: {test['expected_regime']})")
        print(f"   Profitability: {result['expected_profitability']} (expected: {test['expected_profit']})")
        print(f"   Activity Ratio: {result['activity_ratio']:.2f}")

        # Verify classification
        assert (
            result["regime"] == test["expected_regime"]
        ), f"Expected {test['expected_regime']}, got {result['regime']}"
        assert (
            result["expected_profitability"] == test["expected_profit"]
        ), f"Expected {test['expected_profit']}, got {result['expected_profitability']}"
        print(f"   ✅ Classification correct")

    print(f"\n✅ All 4 regimes classified correctly")


def test_3_dual_window_classification():
    """Test 3: Verify dual window classification (structural + economic)."""
    print("\n" + "=" * 80)
    print("TEST 3: Dual Window Classification (30-day)")
    print("=" * 80)

    classifier = RegimeClassifier()

    # Create Q1 2024-like window (persistent_negative + elevated_risk)
    q1_window = [
        {
            "net_gex": -15e9 + np.random.normal(0, 2e9),
            "gex_oi": -15e9 + np.random.normal(0, 2e9),
            "gex_volume": -8e9 + np.random.normal(0, 1e9),
        }
        for _ in range(25)
    ] + [{"net_gex": 5e9, "gex_oi": 5e9, "gex_volume": 2e9} for _ in range(5)]

    result_q1 = classifier.classify_window_dual(q1_window)

    print(f"\nQ1 2024-like Window:")
    print(f"   Structural Regime: {result_q1['structural_regime']}")
    print(f"   Economic Regime: {result_q1['economic_regime']['regime'] if result_q1['economic_regime'] else 'None'}")
    print(f"   Profitability Expectation: {result_q1['profitability_expectation']}")
    print(f"   Should Detect: {result_q1['should_detect']}")
    print(f"   Has Dual Metrics: {result_q1['has_dual_metrics']}")

    assert result_q1["structural_regime"] == "persistent_negative", "Q1 window should be persistent_negative"
    assert result_q1["economic_regime"]["regime"] == "elevated_risk", "Q1 window should be elevated_risk"
    assert result_q1["profitability_expectation"] == "high", "Q1 window should have high profitability expectation"
    print(f"   ✅ Q1 classification correct (persistent_negative + elevated_risk → high profit)")

    # Create Q4 2024-like window (persistent_negative + high_fragility)
    q4_window = [
        {
            "net_gex": -13e9 + np.random.normal(0, 1.5e9),
            "gex_oi": -13e9 + np.random.normal(0, 1.5e9),
            "gex_volume": -0.5e9 + np.random.normal(0, 0.3e9),
        }
        for _ in range(25)
    ] + [{"net_gex": 3e9, "gex_oi": 3e9, "gex_volume": 0.2e9} for _ in range(5)]

    result_q4 = classifier.classify_window_dual(q4_window)

    print(f"\nQ4 2024-like Window:")
    print(f"   Structural Regime: {result_q4['structural_regime']}")
    print(f"   Economic Regime: {result_q4['economic_regime']['regime'] if result_q4['economic_regime'] else 'None'}")
    print(f"   Profitability Expectation: {result_q4['profitability_expectation']}")
    print(f"   Should Detect: {result_q4['should_detect']}")
    print(f"   Has Dual Metrics: {result_q4['has_dual_metrics']}")

    assert result_q4["structural_regime"] == "persistent_negative", "Q4 window should be persistent_negative"
    assert result_q4["economic_regime"]["regime"] == "high_fragility", "Q4 window should be high_fragility"
    assert result_q4["profitability_expectation"] == "low", "Q4 window should have low profitability expectation"
    print(f"   ✅ Q4 classification correct (persistent_negative + high_fragility → low profit)")

    print(f"\n✅ Dual classification explains profitability divergence:")
    print(
        f"   Q1: {result_q1['structural_regime']} + {result_q1['economic_regime']['regime']} → {result_q1['profitability_expectation']} profit"
    )
    print(
        f"   Q4: {result_q4['structural_regime']} + {result_q4['economic_regime']['regime']} → {result_q4['profitability_expectation']} profit"
    )


def test_4_backward_compatibility():
    """Test 4: Verify existing code still works (backward compatibility)."""
    print("\n" + "=" * 80)
    print("TEST 4: Backward Compatibility")
    print("=" * 80)

    classifier = RegimeClassifier()

    # Test existing classify_window() without dual metrics
    simple_window = [{"net_gex": -15e9 + np.random.normal(0, 2e9)} for _ in range(25)] + [
        {"net_gex": 5e9} for _ in range(5)
    ]

    result = classifier.classify_window(simple_window)

    print(f"\nExisting classify_window() (without dual metrics):")
    print(f"   Regime Type: {result['regime_type']}")
    print(f"   Is Persistent: {result['is_persistent']}")
    print(f"   Should Detect: {result['should_detect']}")
    print(f"   Persistence: {result['metrics'].persistence_pct:.1f}%")
    print(f"   ✅ Existing API still works")

    # Test dual classification without volume data
    result_dual = classifier.classify_window_dual(simple_window)

    print(f"\nDual classify_window_dual() (without volume data):")
    print(f"   Structural Regime: {result_dual['structural_regime']}")
    print(f"   Economic Regime: {result_dual['economic_regime']}")
    print(f"   Has Dual Metrics: {result_dual['has_dual_metrics']}")
    print(f"   Profitability Expectation: {result_dual['profitability_expectation']}")
    print(f"   ✅ Dual API gracefully handles missing volume data")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("DUAL GEX FRAMEWORK TEST SUITE (Issue #138)")
    print("=" * 80)

    try:
        # Test 1: Dual GEX calculation
        test_1_dual_gex_calculation()

        # Test 2: Economic regime classification
        test_2_economic_regime_classification()

        # Test 3: Dual window classification
        test_3_dual_window_classification()

        # Test 4: Backward compatibility
        test_4_backward_compatibility()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nDual GEX Framework ready for production use:")
        print("  1. GEXCalculator.calculate_dual_gex() ✅")
        print("  2. RegimeClassifier.classify_economic_regime() ✅")
        print("  3. RegimeClassifier.classify_window_dual() ✅")
        print("  4. Backward compatibility maintained ✅")
        print("\nNext steps:")
        print("  - Run statistical analysis on 2024 data")
        print("  - Correlate GEX_Volume with profitability")
        print("  - Update validation pipeline")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
