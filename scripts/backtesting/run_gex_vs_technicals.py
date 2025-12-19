"""
GEX Pattern vs Technical Strategies Comparison

Compares GEX-based signals against pure technical strategies
on symbols where we have deep options data.

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
from src.backtesting.signals.gex_pattern_signal import GEXPatternSignal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Symbols with deep options data (1400+ days)
SYMBOLS = ["SPY", "QQQ", "TQQQ", "SQQQ", "SOXL", "IWM"]

# Test period (where we have options data)
START_DATE = "2024-01-02"
END_DATE = "2024-11-30"
INITIAL_CAPITAL = 100000

# Output path
OUTPUT_DIR = Path(__file__).parent.parent.parent / "reports" / "backtesting_research"


def run_comparison(symbol: str, engine: BacktestEngine) -> dict:
    """Run GEX and technical strategies for comparison."""
    # Technical strategies
    technical_strategies = {
        "buy_and_hold": BuyAndHoldStrategy(),
        "macd": MACDStrategy(),
        "rsi": RSIStrategy(),
        "momentum": MomentumStrategy(lookback=20),
    }

    # GEX-based strategy
    gex_signal = GEXPatternSignal(
        db_path=".cache/options_historical.db",
        gex_flip_threshold=0.0,
        confidence_threshold=0.5,
    )

    results = {"technical": {}, "gex": {}}

    # Run technical strategies
    for name, strategy in technical_strategies.items():
        try:
            result = engine.run(
                signal_generator=strategy.generate_signal,
                symbol=symbol,
                start_date=START_DATE,
                end_date=END_DATE,
            )

            results["technical"][name] = {
                "total_return": round(result.total_return, 4),
                "sharpe_ratio": round(result.sharpe_ratio, 4),
                "max_drawdown": round(result.max_drawdown, 4),
                "win_rate": round(result.win_rate, 2),
                "num_trades": result.num_trades,
            }

        except Exception as e:
            results["technical"][name] = {"error": str(e)}

    # Run GEX strategy
    try:
        gex_signal.reset()
        result = engine.run(
            signal_generator=gex_signal.generate_signal,
            symbol=symbol,
            start_date=START_DATE,
            end_date=END_DATE,
        )

        results["gex"]["gex_pattern"] = {
            "total_return": round(result.total_return, 4),
            "sharpe_ratio": round(result.sharpe_ratio, 4),
            "max_drawdown": round(result.max_drawdown, 4),
            "win_rate": round(result.win_rate, 2),
            "num_trades": result.num_trades,
        }

        # Calculate enhanced metrics if we have trades
        if len(result.returns_series) > 0 and result.num_trades > 0:
            try:
                enhanced = calculate_enhanced_metrics(
                    returns=result.returns_series,
                    trades=result.trades,
                    max_drawdown=result.max_drawdown / 100 if result.max_drawdown != 0 else -0.01,
                    initial_capital=INITIAL_CAPITAL,
                )
                results["gex"]["gex_pattern"].update(
                    {
                        "sortino_ratio": round(enhanced.sortino_ratio, 4),
                        "calmar_ratio": round(enhanced.calmar_ratio, 4),
                        "profit_factor": round(enhanced.profit_factor, 4),
                    }
                )
            except Exception:
                pass

    except Exception as e:
        results["gex"]["gex_pattern"] = {"error": str(e)}

    return results


def calculate_improvement(gex_result: dict, best_technical: dict) -> float:
    """Calculate GEX improvement over best technical strategy."""
    if "error" in gex_result or "error" in best_technical:
        return 0.0

    gex_sharpe = gex_result.get("sharpe_ratio", 0)
    tech_sharpe = best_technical.get("sharpe_ratio", 0)

    if tech_sharpe == 0:
        return 0.0

    return round((gex_sharpe - tech_sharpe) / abs(tech_sharpe) * 100, 2)


def find_best_technical(results: dict) -> tuple:
    """Find best technical strategy by Sharpe ratio."""
    best_name = None
    best_metrics = {}
    best_sharpe = float("-inf")

    for name, metrics in results.items():
        if "error" not in metrics and metrics.get("sharpe_ratio", 0) > best_sharpe:
            best_sharpe = metrics["sharpe_ratio"]
            best_name = name
            best_metrics = metrics

    return best_name, best_metrics


def main():
    """Run GEX vs Technicals comparison."""
    logger.info("=" * 70)
    logger.info("GEX PATTERN vs TECHNICAL STRATEGIES COMPARISON")
    logger.info(f"Period: {START_DATE} to {END_DATE}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info("=" * 70)

    engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
    all_results = {}
    summary = []

    for symbol in SYMBOLS:
        logger.info(f"\nTesting {symbol}...")
        try:
            results = run_comparison(symbol, engine)

            # Find best technical strategy
            best_tech_name, best_tech_metrics = find_best_technical(results["technical"])

            # Calculate improvement
            gex_result = results["gex"].get("gex_pattern", {})
            improvement = calculate_improvement(gex_result, best_tech_metrics)

            # Determine winner
            gex_sharpe = gex_result.get("sharpe_ratio", 0) if "error" not in gex_result else 0
            tech_sharpe = best_tech_metrics.get("sharpe_ratio", 0) if best_tech_metrics else 0
            winner = "GEX" if gex_sharpe > tech_sharpe else "TECHNICAL"

            all_results[symbol] = {
                "period": f"{START_DATE} to {END_DATE}",
                "winner": winner,
                "best_technical": best_tech_name,
                "gex_improvement_pct": improvement,
                "results": results,
            }

            summary.append(
                {
                    "symbol": symbol,
                    "winner": winner,
                    "gex_sharpe": gex_sharpe,
                    "tech_sharpe": tech_sharpe,
                    "improvement": improvement,
                }
            )

            logger.info(f"  Winner: {winner}")
            logger.info(f"  GEX Sharpe: {gex_sharpe:.3f}")
            logger.info(f"  Best Tech ({best_tech_name}): {tech_sharpe:.3f}")

        except Exception as e:
            logger.error(f"  Failed: {e}")
            all_results[symbol] = {"error": str(e)}

    # Calculate overall statistics
    gex_wins = sum(1 for s in summary if s["winner"] == "GEX")
    tech_wins = sum(1 for s in summary if s["winner"] == "TECHNICAL")
    avg_improvement = sum(s["improvement"] for s in summary) / len(summary) if summary else 0

    # Compile final output
    output = {
        "metadata": {
            "run_date": datetime.now().isoformat(),
            "period": f"{START_DATE} to {END_DATE}",
            "symbols": SYMBOLS,
            "initial_capital": INITIAL_CAPITAL,
        },
        "summary": {
            "gex_wins": gex_wins,
            "technical_wins": tech_wins,
            "avg_improvement_pct": round(avg_improvement, 2),
            "symbol_results": summary,
        },
        "detailed_results": all_results,
    }

    # Save to YAML
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "gex_vs_technicals_results.yaml"

    with open(output_file, "w") as f:
        yaml.dump(convert_to_native(output), f, default_flow_style=False, sort_keys=False)

    logger.info(f"\nResults saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("GEX vs TECHNICALS SUMMARY")
    print("=" * 70)
    print(f"GEX Wins: {gex_wins}")
    print(f"Technical Wins: {tech_wins}")
    print(f"Average GEX Improvement: {avg_improvement:.2f}%")
    print("\nPer-Symbol Results:")
    for s in summary:
        print(f"  {s['symbol']}: {s['winner']} (GEX: {s['gex_sharpe']:.3f}, Tech: {s['tech_sharpe']:.3f})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
