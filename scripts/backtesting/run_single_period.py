"""Run GEX vs Technicals for a single period - designed for parallel execution."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting import BacktestEngine
from src.backtesting.baselines import BuyAndHoldStrategy, MACDStrategy, MomentumStrategy, RSIStrategy
from src.backtesting.signals.gex_pattern_signal import GEXPatternSignal

SYMBOLS = ["SPY", "QQQ", "TQQQ", "SQQQ", "SOXL", "IWM"]


def run_period(period_name: str, start_date: str, end_date: str):
    """Run all symbols for a single period."""
    results = []

    for symbol in SYMBOLS:
        try:
            engine = BacktestEngine(initial_capital=100000)

            # GEX strategy
            gex = GEXPatternSignal()
            gex.reset()
            gex_res = engine.run(gex.generate_signal, symbol, start_date, end_date)
            gex_sharpe = round(gex_res.sharpe_ratio, 4)
            gex_trades = gex_res.num_trades

            # Technical strategies - find best
            best_tech_name = "none"
            best_tech_sharpe = float("-inf")

            for name, strat in [
                ("buy_hold", BuyAndHoldStrategy()),
                ("macd", MACDStrategy()),
                ("rsi", RSIStrategy()),
                ("momentum", MomentumStrategy()),
            ]:
                res = engine.run(strat.generate_signal, symbol, start_date, end_date)
                if res.sharpe_ratio > best_tech_sharpe:
                    best_tech_sharpe = res.sharpe_ratio
                    best_tech_name = name

            best_tech_sharpe = round(best_tech_sharpe, 4)
            winner = "GEX" if gex_sharpe > best_tech_sharpe else "TECH"

            results.append(
                {
                    "symbol": symbol,
                    "gex_sharpe": gex_sharpe,
                    "tech_sharpe": best_tech_sharpe,
                    "tech_name": best_tech_name,
                    "gex_trades": gex_trades,
                    "winner": winner,
                }
            )

        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})

    # Summary
    gex_wins = sum(1 for r in results if r.get("winner") == "GEX")
    tech_wins = sum(1 for r in results if r.get("winner") == "TECH")

    output = {
        "period": period_name,
        "start": start_date,
        "end": end_date,
        "gex_wins": gex_wins,
        "tech_wins": tech_wins,
        "results": results,
    }

    print(json.dumps(output))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    run_period(args.period, args.start, args.end)
