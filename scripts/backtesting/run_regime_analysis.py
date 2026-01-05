"""
Market Regime Analysis

Tests strategy performance across different market conditions:
- COVID crash (2020-02 to 2020-03)
- Recovery (2020-04 to 2020-12)
- Bull run 2021
- Bear market 2022
- Bull run 2024

Stores results in YAML format for research notes.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml


def convert_to_native(obj):
    """Convert numpy types to native Python types for YAML serialization."""
    if isinstance(obj, dict):
        return {k: convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, float) and (np.isinf(obj) or np.isnan(obj)):
        return str(obj)
    return obj


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting import BacktestEngine
from src.backtesting.baselines import BuyAndHoldStrategy, MACDStrategy, MomentumStrategy, RSIStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Market regimes to analyze
REGIMES = {
    "covid_crash": {
        "start": "2020-02-01",
        "end": "2020-03-31",
        "description": "COVID-19 market crash",
    },
    "recovery_2020": {
        "start": "2020-04-01",
        "end": "2020-12-31",
        "description": "Post-COVID recovery rally",
    },
    "bull_2021": {
        "start": "2021-01-01",
        "end": "2021-12-31",
        "description": "2021 bull market",
    },
    "bear_2022": {
        "start": "2022-01-01",
        "end": "2022-12-31",
        "description": "2022 bear market / rate hikes",
    },
    "mixed_2023": {
        "start": "2023-01-01",
        "end": "2023-12-31",
        "description": "2023 mixed market",
    },
    "bull_2024": {
        "start": "2024-01-01",
        "end": "2024-11-30",
        "description": "2024 bull market",
    },
}

# Test on major indices
SYMBOLS = ["SPY", "QQQ", "IWM"]
INITIAL_CAPITAL = 100000

# Output path
OUTPUT_DIR = Path(__file__).parent.parent.parent / "reports" / "backtesting_research"


def run_regime_test(symbol: str, regime: dict, engine: BacktestEngine) -> dict:
    """Run all strategies for a single symbol in a specific regime."""
    strategies = {
        "buy_and_hold": BuyAndHoldStrategy(),
        "macd": MACDStrategy(),
        "rsi": RSIStrategy(),
        "momentum": MomentumStrategy(lookback=20),
    }

    results = {}
    for strategy_name, strategy in strategies.items():
        try:
            result = engine.run(
                signal_generator=strategy.generate_signal,
                symbol=symbol,
                start_date=regime["start"],
                end_date=regime["end"],
            )

            results[strategy_name] = {
                "total_return": round(result.total_return, 4),
                "sharpe_ratio": round(result.sharpe_ratio, 4),
                "max_drawdown": round(result.max_drawdown, 4),
                "win_rate": round(result.win_rate, 2),
                "num_trades": result.num_trades,
            }

        except Exception as e:
            results[strategy_name] = {"error": str(e)}

    return results


def find_best_strategy(results: dict) -> str:
    """Find the strategy with highest return."""
    best = None
    best_return = float("-inf")
    for name, metrics in results.items():
        if "error" not in metrics and metrics.get("total_return", 0) > best_return:
            best_return = metrics["total_return"]
            best = name
    return best or "none"


def main():
    """Run market regime analysis."""
    logger.info("=" * 70)
    logger.info("MARKET REGIME ANALYSIS")
    logger.info(f"Regimes: {list(REGIMES.keys())}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info("=" * 70)

    engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
    all_results = {}

    for regime_name, regime in REGIMES.items():
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Regime: {regime_name} ({regime['description']})")
        logger.info(f"Period: {regime['start']} to {regime['end']}")
        logger.info("=" * 50)

        regime_results = {
            "period": f"{regime['start']} to {regime['end']}",
            "description": regime["description"],
            "symbols": {},
        }

        for symbol in SYMBOLS:
            logger.info(f"\n  Testing {symbol}...")
            try:
                results = run_regime_test(symbol, regime, engine)
                best = find_best_strategy(results)

                regime_results["symbols"][symbol] = {
                    "best_strategy": best,
                    "strategies": results,
                }

                # Log best result
                if best != "none" and best in results:
                    ret = results[best].get("total_return", 0)
                    logger.info(f"    Best: {best} ({ret:.2f}%)")

            except Exception as e:
                logger.error(f"    Failed: {e}")
                regime_results["symbols"][symbol] = {"error": str(e)}

        all_results[regime_name] = regime_results

    # Compile insights
    insights = {}
    for regime_name, data in all_results.items():
        strategy_performance = {}
        for symbol, sym_data in data.get("symbols", {}).items():
            if "error" not in sym_data:
                for strat, metrics in sym_data.get("strategies", {}).items():
                    if "error" not in metrics:
                        if strat not in strategy_performance:
                            strategy_performance[strat] = []
                        strategy_performance[strat].append(metrics.get("total_return", 0))

        # Average performance per strategy in this regime
        avg_performance = {}
        for strat, returns in strategy_performance.items():
            avg_performance[strat] = round(sum(returns) / len(returns), 2) if returns else 0

        insights[regime_name] = {
            "avg_strategy_returns": avg_performance,
            "best_overall": max(avg_performance.items(), key=lambda x: x[1])[0] if avg_performance else "none",
        }

    # Compile final output
    output = {
        "metadata": {
            "run_date": datetime.now().isoformat(),
            "symbols": SYMBOLS,
            "initial_capital": INITIAL_CAPITAL,
        },
        "regime_insights": insights,
        "detailed_results": all_results,
    }

    # Save to YAML
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "regime_analysis_results.yaml"

    with open(output_file, "w") as f:
        yaml.dump(convert_to_native(output), f, default_flow_style=False, sort_keys=False)

    logger.info(f"\nResults saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("REGIME INSIGHTS SUMMARY")
    print("=" * 70)
    for regime, insight in insights.items():
        print(f"\n{regime}:")
        print(f"  Best strategy: {insight['best_overall']}")
        print(f"  Avg returns: {insight['avg_strategy_returns']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
