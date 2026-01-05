"""
Multi-Symbol Baseline Strategy Study

Tests all baseline strategies across major symbols with sufficient data.
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
from src.backtesting.enhanced_metrics import calculate_enhanced_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test configuration
SYMBOLS = ["SPY", "QQQ", "IWM", "TQQQ", "SQQQ", "SOXL", "SOXS", "UVXY"]
START_DATE = "2020-01-02"
END_DATE = "2024-12-01"
INITIAL_CAPITAL = 100000

# Output path
OUTPUT_DIR = Path(__file__).parent.parent.parent / "reports" / "backtesting_research"


def run_symbol_backtest(symbol: str, engine: BacktestEngine) -> dict:
    """Run all strategies for a single symbol."""
    strategies = {
        "buy_and_hold": BuyAndHoldStrategy(),
        "macd_crossover": MACDStrategy(),
        "rsi_mean_revert": RSIStrategy(),
        "momentum_20d": MomentumStrategy(lookback=20),
        "momentum_50d": MomentumStrategy(lookback=50),
    }

    results = {}
    for strategy_name, strategy in strategies.items():
        try:
            result = engine.run(
                signal_generator=strategy.generate_signal,
                symbol=symbol,
                start_date=START_DATE,
                end_date=END_DATE,
            )

            # Calculate enhanced metrics
            enhanced = None
            if len(result.returns_series) > 0 and result.max_drawdown != 0:
                try:
                    enhanced = calculate_enhanced_metrics(
                        returns=result.returns_series,
                        trades=result.trades,
                        max_drawdown=result.max_drawdown / 100,
                        initial_capital=INITIAL_CAPITAL,
                    )
                except Exception:
                    pass

            results[strategy_name] = {
                "total_return": round(result.total_return, 4),
                "sharpe_ratio": round(result.sharpe_ratio, 4),
                "max_drawdown": round(result.max_drawdown, 4),
                "win_rate": round(result.win_rate, 2),
                "volatility": round(result.volatility, 4),
                "num_trades": result.num_trades,
            }

            if enhanced:
                results[strategy_name].update(
                    {
                        "sortino_ratio": round(enhanced.sortino_ratio, 4),
                        "calmar_ratio": round(enhanced.calmar_ratio, 4),
                        "profit_factor": round(enhanced.profit_factor, 4),
                    }
                )

            logger.info(f"  {strategy_name}: Return={result.total_return:.2f}%, Sharpe={result.sharpe_ratio:.3f}")

        except Exception as e:
            logger.warning(f"  {strategy_name} failed: {e}")
            results[strategy_name] = {"error": str(e)}

    return results


def find_best_strategy(results: dict) -> str:
    """Find the strategy with highest Sharpe ratio."""
    best = None
    best_sharpe = float("-inf")
    for name, metrics in results.items():
        if "error" not in metrics and metrics.get("sharpe_ratio", 0) > best_sharpe:
            best_sharpe = metrics["sharpe_ratio"]
            best = name
    return best or "none"


def main():
    """Run multi-symbol baseline study."""
    logger.info("=" * 70)
    logger.info("MULTI-SYMBOL BASELINE STRATEGY STUDY")
    logger.info(f"Period: {START_DATE} to {END_DATE}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info("=" * 70)

    engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
    all_results = {}

    for symbol in SYMBOLS:
        logger.info(f"\nTesting {symbol}...")
        try:
            results = run_symbol_backtest(symbol, engine)
            best = find_best_strategy(results)

            all_results[symbol] = {
                "period": f"{START_DATE} to {END_DATE}",
                "best_strategy": best,
                "strategies": results,
            }
        except Exception as e:
            logger.error(f"Failed to test {symbol}: {e}")
            all_results[symbol] = {"error": str(e)}

    # Calculate summary statistics
    summary = {
        "run_date": datetime.now().isoformat(),
        "period": f"{START_DATE} to {END_DATE}",
        "symbols_tested": len([s for s in all_results if "error" not in all_results[s]]),
        "initial_capital": INITIAL_CAPITAL,
    }

    # Strategy win counts
    strategy_wins = {}
    for symbol, data in all_results.items():
        if "error" not in data:
            best = data.get("best_strategy", "none")
            strategy_wins[best] = strategy_wins.get(best, 0) + 1

    summary["strategy_win_counts"] = strategy_wins

    # Compile final output
    output = {
        "metadata": summary,
        "results": all_results,
    }

    # Save to YAML
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "baseline_study_results.yaml"

    with open(output_file, "w") as f:
        yaml.dump(convert_to_native(output), f, default_flow_style=False, sort_keys=False)

    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 70)
    logger.info("STUDY COMPLETE")
    logger.info("=" * 70)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Symbols tested: {summary['symbols_tested']}")
    print(f"Strategy wins: {strategy_wins}")
    print(f"Results saved: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
