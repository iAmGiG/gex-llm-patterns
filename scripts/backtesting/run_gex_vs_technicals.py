"""
GEX Pattern vs Technical Strategies Comparison

Compares GEX-based signals against pure technical strategies
on symbols where we have deep options data.

Stores results in YAML format for research notes.
"""

import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
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
from src.backtesting.signals.gex_regime_signal import GEXRegimeSignal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Symbols with deep options data (1400+ days)
SYMBOLS = ["SPY", "QQQ", "TQQQ", "SQQQ", "SOXL", "IWM"]

# Full test period (2020-2025 - full options data range)
START_DATE = "2020-01-02"
END_DATE = "2025-12-01"
INITIAL_CAPITAL = 100000

# Market regimes for detailed analysis
REGIMES = {
    "covid_crash": ("2020-02-01", "2020-03-31"),
    "recovery_2020": ("2020-04-01", "2020-12-31"),
    "bull_2021": ("2021-01-01", "2021-12-31"),
    "bear_2022": ("2022-01-01", "2022-12-31"),
    "mixed_2023": ("2023-01-01", "2023-12-31"),
    "bull_2024": ("2024-01-01", "2024-11-30"),
}

# Output path
OUTPUT_DIR = Path(__file__).parent.parent.parent / "reports" / "backtesting_research"


def run_comparison(symbol: str, engine: BacktestEngine, start_date: str = None, end_date: str = None) -> dict:
    """Run GEX and technical strategies for comparison.

    Args:
        symbol: Stock symbol
        engine: BacktestEngine instance
        start_date: Start date (defaults to global START_DATE)
        end_date: End date (defaults to global END_DATE)
    """
    start_date = start_date or START_DATE
    end_date = end_date or END_DATE

    # Technical strategies
    technical_strategies = {
        "buy_and_hold": BuyAndHoldStrategy(),
        "macd": MACDStrategy(),
        "rsi": RSIStrategy(),
        "momentum": MomentumStrategy(lookback=20),
    }

    # GEX-based strategies
    # 1. Flip-based (original approach)
    gex_flip_signal = GEXPatternSignal(
        # db_path=".cache/options_historical.db"  # Migrated to PostgreSQL,
        gex_flip_threshold=0.0,
        confidence_threshold=0.5,
    )

    # 2. Regime-based (AutoGen-Trader approach - uses pre-calculated regimes)
    gex_regime_signal = GEXRegimeSignal(
        use_precalculated=True,
        transition_weight=1.0,
        maintenance_weight=0.5,
    )

    results = {"technical": {}, "gex": {}}

    # Run technical strategies
    for name, strategy in technical_strategies.items():
        try:
            result = engine.run(
                signal_generator=strategy.generate_signal,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
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

    # Run GEX flip-based strategy (original approach)
    try:
        gex_flip_signal.reset()
        result = engine.run(
            signal_generator=gex_flip_signal.generate_signal,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        results["gex"]["gex_flip"] = {
            "total_return": round(result.total_return, 4),
            "sharpe_ratio": round(result.sharpe_ratio, 4),
            "max_drawdown": round(result.max_drawdown, 4),
            "win_rate": round(result.win_rate, 2),
            "num_trades": result.num_trades,
        }
    except Exception as e:
        results["gex"]["gex_flip"] = {"error": str(e)}

    # Run GEX regime-based strategy (AutoGen-Trader approach)
    try:
        gex_regime_signal.reset()
        result = engine.run(
            signal_generator=gex_regime_signal.generate_signal,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        results["gex"]["gex_regime"] = {
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
                results["gex"]["gex_regime"].update(
                    {
                        "sortino_ratio": round(enhanced.sortino_ratio, 4),
                        "calmar_ratio": round(enhanced.calmar_ratio, 4),
                        "profit_factor": round(enhanced.profit_factor, 4),
                    }
                )
            except Exception:
                pass

    except Exception as e:
        results["gex"]["gex_regime"] = {"error": str(e)}

    return results


def find_best_gex(results: dict) -> tuple:
    """Find best GEX strategy by Sharpe ratio."""
    best_name = None
    best_metrics = {}
    best_sharpe = float("-inf")

    for name, metrics in results.items():
        if "error" not in metrics and metrics.get("sharpe_ratio", 0) > best_sharpe:
            best_sharpe = metrics["sharpe_ratio"]
            best_name = name
            best_metrics = metrics

    return best_name, best_metrics


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


def run_single_symbol(args):
    """Run comparison for a single symbol (for parallel execution)."""
    symbol, start_date, end_date = args
    try:
        engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
        comparison = run_comparison(symbol, engine, start_date, end_date)

        # Find best technical strategy
        best_tech_name, best_tech_metrics = find_best_technical(comparison["technical"])

        # Find best GEX strategy (regime-based vs flip-based)
        best_gex_name, best_gex_metrics = find_best_gex(comparison["gex"])

        # Calculate improvement
        improvement = calculate_improvement(best_gex_metrics, best_tech_metrics)

        # Determine winner
        gex_sharpe = best_gex_metrics.get("sharpe_ratio", 0) if best_gex_metrics else 0
        tech_sharpe = best_tech_metrics.get("sharpe_ratio", 0) if best_tech_metrics else 0
        winner = "GEX" if gex_sharpe > tech_sharpe else "TECHNICAL"

        # Get both GEX strategy results for detailed comparison
        gex_flip = comparison["gex"].get("gex_flip", {})
        gex_regime = comparison["gex"].get("gex_regime", {})

        return {
            "symbol": symbol,
            "winner": winner,
            "best_technical": best_tech_name,
            "best_gex": best_gex_name,
            "gex_sharpe": gex_sharpe,
            "tech_sharpe": tech_sharpe,
            "gex_improvement_pct": improvement,
            "gex_trades": best_gex_metrics.get("num_trades", 0),
            "gex_flip_sharpe": gex_flip.get("sharpe_ratio", 0) if "error" not in gex_flip else 0,
            "gex_regime_sharpe": gex_regime.get("sharpe_ratio", 0) if "error" not in gex_regime else 0,
            "results": comparison,
            "error": None,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def run_period_analysis_parallel(start_date: str, end_date: str, period_name: str, max_workers: int = 4):
    """Run analysis for a specific period across all symbols IN PARALLEL."""
    results = {}
    summary = []

    # Create work items
    work_items = [(symbol, start_date, end_date) for symbol in SYMBOLS]

    # Run in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_single_symbol, item): item[0] for item in work_items}

        for future in as_completed(futures):
            symbol = futures[future]
            try:
                result = future.result()
                if result.get("error"):
                    logger.warning(f"  {symbol} failed: {result['error']}")
                    results[symbol] = {"error": result["error"]}
                else:
                    results[symbol] = result
                    summary.append(
                        {
                            "symbol": symbol,
                            "winner": result["winner"],
                            "best_gex": result.get("best_gex", "unknown"),
                            "gex_sharpe": result["gex_sharpe"],
                            "gex_flip_sharpe": result.get("gex_flip_sharpe", 0),
                            "gex_regime_sharpe": result.get("gex_regime_sharpe", 0),
                            "tech_sharpe": result["tech_sharpe"],
                            "improvement": result["gex_improvement_pct"],
                        }
                    )
            except Exception as e:
                logger.warning(f"  {symbol} failed in {period_name}: {e}")
                results[symbol] = {"error": str(e)}

    # Calculate stats
    gex_wins = sum(1 for s in summary if s["winner"] == "GEX")
    tech_wins = sum(1 for s in summary if s["winner"] == "TECHNICAL")
    avg_improvement = sum(s["improvement"] for s in summary) / len(summary) if summary else 0

    return {
        "period": f"{start_date} to {end_date}",
        "gex_wins": gex_wins,
        "technical_wins": tech_wins,
        "avg_improvement_pct": round(avg_improvement, 2),
        "symbol_results": results,
        "summary": summary,
    }


def main():
    """Run GEX vs Technicals comparison across full period and regimes."""
    import multiprocessing

    max_workers = min(6, multiprocessing.cpu_count())

    logger.info("=" * 70)
    logger.info("GEX PATTERN vs TECHNICAL STRATEGIES COMPARISON (PARALLEL)")
    logger.info(f"Full Period: {START_DATE} to {END_DATE}")
    logger.info(f"Regimes: {list(REGIMES.keys())}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Workers: {max_workers}")
    logger.info("=" * 70)

    # Run full period analysis in parallel
    logger.info("\n" + "=" * 50)
    logger.info("FULL PERIOD ANALYSIS (parallel)")
    logger.info("=" * 50)
    full_period = run_period_analysis_parallel(START_DATE, END_DATE, "full_period", max_workers)
    logger.info(f"Full Period: GEX wins {full_period['gex_wins']}, Tech wins {full_period['technical_wins']}")

    # Run regime-specific analysis in parallel
    regime_results = {}
    logger.info("\n" + "=" * 50)
    logger.info("REGIME-SPECIFIC ANALYSIS (parallel)")
    logger.info("=" * 50)

    for regime_name, (start, end) in REGIMES.items():
        logger.info(f"\n{regime_name} ({start} to {end})...")
        regime_results[regime_name] = run_period_analysis_parallel(start, end, regime_name, max_workers)
        logger.info(
            f"  GEX wins: {regime_results[regime_name]['gex_wins']}, "
            f"Tech wins: {regime_results[regime_name]['technical_wins']}"
        )

    # Identify best regimes for GEX
    regime_gex_performance = []
    for regime_name, data in regime_results.items():
        gex_win_rate = data["gex_wins"] / len(SYMBOLS) if SYMBOLS else 0
        regime_gex_performance.append(
            {
                "regime": regime_name,
                "gex_win_rate": gex_win_rate,
                "gex_wins": data["gex_wins"],
                "avg_improvement": data["avg_improvement_pct"],
            }
        )

    regime_gex_performance.sort(key=lambda x: x["gex_win_rate"], reverse=True)

    # Compile final output
    output = {
        "metadata": {
            "run_date": datetime.now().isoformat(),
            "full_period": f"{START_DATE} to {END_DATE}",
            "regimes_tested": list(REGIMES.keys()),
            "symbols": SYMBOLS,
            "initial_capital": INITIAL_CAPITAL,
        },
        "full_period_summary": {
            "gex_wins": full_period["gex_wins"],
            "technical_wins": full_period["technical_wins"],
            "avg_improvement_pct": full_period["avg_improvement_pct"],
            "symbol_summary": full_period["summary"],
        },
        "regime_analysis": {
            "best_regimes_for_gex": regime_gex_performance[:3],
            "worst_regimes_for_gex": regime_gex_performance[-3:],
            "detailed_by_regime": regime_results,
        },
        "full_period_detailed": full_period["symbol_results"],
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

    print(f"\nFULL PERIOD ({START_DATE} to {END_DATE}):")
    print(f"  GEX Wins: {full_period['gex_wins']}")
    print(f"  Technical Wins: {full_period['technical_wins']}")
    print(f"  Average GEX Improvement: {full_period['avg_improvement_pct']:.2f}%")

    print("\nPer-Symbol Results (Full Period):")
    for s in full_period["summary"]:
        print(f"  {s['symbol']}: {s['winner']} (GEX: {s['gex_sharpe']:.3f}, Tech: {s['tech_sharpe']:.3f})")

    print("\n" + "-" * 70)
    print("REGIME ANALYSIS:")
    print("-" * 70)
    for regime_name, data in regime_results.items():
        print(
            f"  {regime_name}: GEX {data['gex_wins']}/{len(SYMBOLS)}, "
            f"Improvement: {data['avg_improvement_pct']:.1f}%"
        )

    print("\nBest Regimes for GEX:")
    for r in regime_gex_performance[:3]:
        print(f"  {r['regime']}: {r['gex_wins']}/{len(SYMBOLS)} wins, " f"avg improvement: {r['avg_improvement']:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
