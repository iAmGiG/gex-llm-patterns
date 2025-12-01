"""Baseline Comparison System Compares pattern-based trading strategies against simple baselines to validate edge."""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)


class BaselineComparison:
    """Compare pattern trading vs simple strategies to prove incremental value."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def calculate_baselines(self, start_date: str = None, end_date: str = None) -> Dict:
        """Calculate performance of all baseline strategies vs pattern strategy."""

        conn = sqlite3.connect(self.db_path)

        # Get date range from database if not specified
        if not start_date or not end_date:
            date_range = pd.read_sql(
                """
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM daily_gex_metrics
            """,
                conn,
            )
            start_date = start_date or date_range["min_date"][0]
            end_date = end_date or date_range["max_date"][0]

        print(f"BASELINE COMPARISON: {start_date} to {end_date}")
        print("=" * 60)

        # Get all market data for the period
        market_data = pd.read_sql(
            f"""
            SELECT date, symbol, spot_price, total_gex, gex_regime
            FROM daily_gex_metrics
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
            AND symbol = 'SPY'
            ORDER BY date
        """,
            conn,
        )

        if market_data.empty:
            print("No market data found for specified period")
            return {}

        results = {}

        # 1. Buy and Hold Strategy
        results["buy_hold"] = self._calculate_buy_hold(market_data)

        # 2. Simple GEX Strategy
        results["simple_gex"] = self._calculate_simple_gex_strategy(market_data)

        # 3. Random Entries Baseline
        results["random"] = self._calculate_random_baseline(market_data)

        # 4. Pattern-Based Contrarian Strategy
        results["pattern_contrarian"] = self._calculate_pattern_strategy(conn, start_date, end_date)

        # 5. Always Long Strategy (for comparison)
        results["always_long"] = self._calculate_always_long(market_data)

        # 6. Always Short Strategy (for comparison)
        results["always_short"] = self._calculate_always_short(market_data)

        conn.close()

        # Calculate comparative metrics
        self._print_comparison_results(results)

        return results

    def _calculate_buy_hold(self, market_data: pd.DataFrame) -> Dict:
        """Calculate buy and hold returns."""

        start_price = market_data["spot_price"].iloc[0]
        end_price = market_data["spot_price"].iloc[-1]

        total_return = (end_price - start_price) / start_price * 100
        days = len(market_data)

        # Calculate daily returns for Sharpe
        market_data["daily_return"] = market_data["spot_price"].pct_change() * 100
        daily_returns = market_data["daily_return"].dropna()

        return {
            "strategy": "Buy & Hold",
            "total_return": total_return,
            "annualized_return": (total_return / days) * 252 if days > 0 else 0,
            "volatility": daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0,
            "sharpe": (
                (daily_returns.mean() * np.sqrt(252)) / (daily_returns.std() * np.sqrt(252))
                if daily_returns.std() > 0
                else 0
            ),
            "max_drawdown": self._calculate_max_drawdown(daily_returns),
            "trades": 1,  # Just one buy and hold
            "win_rate": 100.0 if total_return > 0 else 0.0,
        }

    def _calculate_simple_gex_strategy(self, market_data: pd.DataFrame) -> Dict:
        """Simple GEX strategy: Long when GEX > 0, Short when GEX < 0."""

        trades = []
        position = None
        entry_price = None

        for i in range(len(market_data) - 1):
            current_gex = market_data.iloc[i]["total_gex"]
            current_price = market_data.iloc[i]["spot_price"]

            # Determine position based on GEX
            if current_gex > 0:  # Positive GEX - go long
                target_position = "LONG"
            else:  # Negative GEX - go short
                target_position = "SHORT"

            # Execute trades when position changes
            if position != target_position:
                # Close existing position if any
                if position is not None:
                    if position == "LONG":
                        trade_return = (current_price - entry_price) / entry_price * 100
                    else:  # SHORT
                        trade_return = (entry_price - current_price) / entry_price * 100
                    trades.append(trade_return)

                # Open new position
                position = target_position
                entry_price = current_price

        # Close final position
        if position is not None:
            final_price = market_data.iloc[-1]["spot_price"]
            if position == "LONG":
                trade_return = (final_price - entry_price) / entry_price * 100
            else:
                trade_return = (entry_price - final_price) / entry_price * 100
            trades.append(trade_return)

        if trades:
            trades_array = np.array(trades)
            total_return = np.sum(trades_array)
            win_rate = (trades_array > 0).mean() * 100

            return {
                "strategy": "Simple GEX",
                "total_return": total_return,
                "annualized_return": (total_return / len(market_data)) * 252,
                "volatility": (
                    trades_array.std() * np.sqrt(len(trades_array) * 252 / len(market_data))
                    if len(trades_array) > 1
                    else 0
                ),
                "sharpe": (
                    (trades_array.mean() * np.sqrt(252)) / (trades_array.std() * np.sqrt(252))
                    if trades_array.std() > 0
                    else 0
                ),
                "max_drawdown": self._calculate_max_drawdown(trades_array),
                "trades": len(trades),
                "win_rate": win_rate,
                "avg_trade": trades_array.mean(),
            }

        return {"strategy": "Simple GEX", "total_return": 0, "trades": 0}

    def _calculate_random_baseline(self, market_data: pd.DataFrame) -> Dict:
        """Random entry baseline with same frequency as actual patterns."""

        # Generate random entry dates matching pattern frequency
        pattern_frequency = 7 / len(market_data)  # 7 patterns over our dataset
        n_random_trades = max(1, int(len(market_data) * pattern_frequency))

        # Multiple random simulations for robustness
        simulation_results = []

        for sim in range(100):  # 100 simulations
            np.random.seed(sim)  # Reproducible results
            random_indices = np.random.choice(len(market_data) - 1, n_random_trades, replace=False)

            trades = []
            for idx in random_indices:
                entry_price = market_data.iloc[idx]["spot_price"]
                if idx + 1 < len(market_data):
                    exit_price = market_data.iloc[idx + 1]["spot_price"]
                    # Random direction (50/50 long/short)
                    if np.random.random() > 0.5:
                        trade_return = (exit_price - entry_price) / entry_price * 100
                    else:
                        trade_return = (entry_price - exit_price) / entry_price * 100
                    trades.append(trade_return)

            if trades:
                simulation_results.append(
                    {
                        "total_return": np.sum(trades),
                        "win_rate": (np.array(trades) > 0).mean() * 100,
                        "avg_trade": np.mean(trades),
                    }
                )

        # Average across simulations
        if simulation_results:
            avg_total_return = np.mean([r["total_return"] for r in simulation_results])
            avg_win_rate = np.mean([r["win_rate"] for r in simulation_results])
            avg_trade_return = np.mean([r["avg_trade"] for r in simulation_results])

            return {
                "strategy": "Random Baseline",
                "total_return": avg_total_return,
                "annualized_return": (avg_total_return / len(market_data)) * 252,
                "volatility": np.std([r["total_return"] for r in simulation_results]),
                "sharpe": 0.0,  # Random should be ~0
                "max_drawdown": 0.0,
                "trades": n_random_trades,
                "win_rate": avg_win_rate,
                "avg_trade": avg_trade_return,
                "simulations": len(simulation_results),
            }

        return {"strategy": "Random Baseline", "total_return": 0}

    def _load_validation_results(
        self, pattern_name: str, symbol: str = "SPY", start_date: str = None, end_date: str = None
    ) -> List[Dict]:
        """Load pattern validation results from YAML files.

        Returns list of detections with outcome metrics.
        """
        # Look for validation YAML files
        validation_dir = Path("reports/validation/pattern_taxonomy")

        # Find matching YAML file (e.g., dealer_gamma_hedging_SPY_2024Q1.yaml)
        pattern_files = list(validation_dir.glob(f"{pattern_name}_{symbol}_*.yaml"))

        # Fallback: try legacy pattern names if consolidated pattern not found
        if not pattern_files and pattern_name == "dealer_gamma_hedging":
            legacy_names = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
            for legacy_name in legacy_names:
                pattern_files = list(validation_dir.glob(f"{legacy_name}_{symbol}_*.yaml"))
                if pattern_files:
                    logger.info(f"Using legacy pattern file: {legacy_name} (consolidated as dealer_gamma_hedging)")
                    break

        if not pattern_files:
            logger.warning(f"No validation file found for pattern {pattern_name}")
            return []

        # Load the most recent file
        validation_file = sorted(pattern_files)[-1]

        with open(validation_file, "r") as f:
            validation_data = yaml.safe_load(f)

        detections = validation_data.get("detections", [])

        # Filter by date range if specified
        if start_date or end_date:
            filtered = []
            for det in detections:
                det_date = det.get("date")
                if start_date and det_date < start_date:
                    continue
                if end_date and det_date > end_date:
                    continue
                filtered.append(det)
            return filtered

        return detections

    def _calculate_pattern_strategy(self, conn: sqlite3.Connection, start_date: str, end_date: str) -> Dict:
        """Calculate performance of our validated contrarian pattern strategy."""

        # NEW: Load from validation YAML files instead of database
        # Using consolidated dealer_gamma_hedging pattern (Issue #79 consolidation)
        # Note: gamma_positioning, stock_pinning, 0dte_hedging are aliases of same pattern
        detections = self._load_validation_results(
            pattern_name="dealer_gamma_hedging",  # Consolidated pattern (Oct 2025)
            symbol="SPY",
            start_date=start_date,
            end_date=end_date,
        )

        if not detections:
            logger.warning("No pattern detections found in validation files")
            return {"strategy": "Pattern Contrarian", "total_return": 0, "trades": 0}

        # Extract returns from validation results
        pattern_returns = []
        high_confidence_count = 0

        for det in detections:
            # Check confidence threshold (>= 85 for high confidence)
            confidence = det.get("narrative", {}).get("confidence", 0)

            if confidence >= 85:
                high_confidence_count += 1

                # Get outcome metrics
                outcome = det.get("outcome_metrics", {})
                forward_return = outcome.get("forward_1d_return_pct", 0)

                # Trade WITH the prediction (not against it!)
                # Negative GEX → market goes down → LLM predicts correctly
                # We capture the actual forward return as our PnL
                pattern_returns.append(forward_return)

        if not pattern_returns:
            return {"strategy": "Dealer Gamma Hedge", "total_return": 0, "trades": 0}

        # Calculate performance metrics from validation results
        returns_array = np.array(pattern_returns)
        wins = returns_array > 0
        win_rate = wins.mean() * 100
        total_return = np.sum(returns_array)

        return {
            "strategy": "Dealer Gamma Hedge",
            "total_return": total_return,
            "annualized_return": (total_return / len(returns_array)) * 252,
            "volatility": returns_array.std() * np.sqrt(252) if len(returns_array) > 1 else 0,
            "sharpe": (
                (returns_array.mean() * np.sqrt(252)) / (returns_array.std() * np.sqrt(252))
                if returns_array.std() > 0
                else 0
            ),
            "max_drawdown": self._calculate_max_drawdown(returns_array),
            "trades": len(returns_array),
            "win_rate": win_rate,
            "avg_trade": returns_array.mean(),
            "confidence_threshold": 85,
            "data_source": "validation_yaml",
            "pattern_name": "dealer_gamma_hedging",  # Consolidated pattern
        }

    def _calculate_always_long(self, market_data: pd.DataFrame) -> Dict:
        """Always long strategy - buy every day, sell next day."""

        daily_returns = []
        for i in range(len(market_data) - 1):
            entry_price = market_data.iloc[i]["spot_price"]
            exit_price = market_data.iloc[i + 1]["spot_price"]
            daily_return = (exit_price - entry_price) / entry_price * 100
            daily_returns.append(daily_return)

        if daily_returns:
            returns_array = np.array(daily_returns)
            win_rate = (returns_array > 0).mean() * 100

            return {
                "strategy": "Always Long",
                "total_return": np.sum(returns_array),
                "annualized_return": returns_array.mean() * 252,
                "volatility": returns_array.std() * np.sqrt(252),
                "sharpe": (
                    (returns_array.mean() * np.sqrt(252)) / (returns_array.std() * np.sqrt(252))
                    if returns_array.std() > 0
                    else 0
                ),
                "max_drawdown": self._calculate_max_drawdown(returns_array),
                "trades": len(returns_array),
                "win_rate": win_rate,
                "avg_trade": returns_array.mean(),
            }

        return {"strategy": "Always Long", "total_return": 0}

    def _calculate_always_short(self, market_data: pd.DataFrame) -> Dict:
        """Always short strategy - sell every day, cover next day."""

        daily_returns = []
        for i in range(len(market_data) - 1):
            entry_price = market_data.iloc[i]["spot_price"]
            exit_price = market_data.iloc[i + 1]["spot_price"]
            daily_return = (entry_price - exit_price) / entry_price * 100  # Inverse for short
            daily_returns.append(daily_return)

        if daily_returns:
            returns_array = np.array(daily_returns)
            win_rate = (returns_array > 0).mean() * 100

            return {
                "strategy": "Always Short",
                "total_return": np.sum(returns_array),
                "annualized_return": returns_array.mean() * 252,
                "volatility": returns_array.std() * np.sqrt(252),
                "sharpe": (
                    (returns_array.mean() * np.sqrt(252)) / (returns_array.std() * np.sqrt(252))
                    if returns_array.std() > 0
                    else 0
                ),
                "max_drawdown": self._calculate_max_drawdown(returns_array),
                "trades": len(returns_array),
                "win_rate": win_rate,
                "avg_trade": returns_array.mean(),
            }

        return {"strategy": "Always Short", "total_return": 0}

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns series."""
        if len(returns) == 0:
            return 0.0

        cumulative = np.cumprod(1 + returns / 100) - 1
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (1 + running_max) * 100

        return np.min(drawdown) if len(drawdown) > 0 else 0.0

    def _print_comparison_results(self, results: Dict):
        """Print formatted comparison results."""

        print("\nSTRATEGY COMPARISON RESULTS:")
        print("=" * 80)
        print(f"{'Strategy':<20} {'Total Return':<12} {'Win Rate':<10} {'Sharpe':<8} {'Trades':<8} {'Avg Trade':<10}")
        print("-" * 80)

        # Sort by total return for ranking
        sorted_results = sorted(results.items(), key=lambda x: x[1].get("total_return", 0), reverse=True)

        for strategy_name, result in sorted_results:
            if "total_return" in result:
                print(
                    f"{result['strategy']:<20} "
                    f"{result['total_return']:>10.2f}% "
                    f"{result.get('win_rate', 0):>8.1f}% "
                    f"{result.get('sharpe', 0):>6.2f} "
                    f"{result.get('trades', 0):>6} "
                    f"{result.get('avg_trade', 0):>8.3f}%"
                )

        # Highlight the pattern strategy performance
        if "pattern_contrarian" in results:
            pattern_result = results["pattern_contrarian"]
            if pattern_result.get("trades", 0) > 0:
                print("\n🎯 PATTERN STRATEGY ANALYSIS:")
                print(
                    f"   Dealer Gamma Hedging (LLM-filtered) vs Random: {pattern_result['total_return']:.2f}% vs {results.get('random', {}).get('total_return', 0):.2f}%"
                )

                # Compare to buy and hold
                bh_return = results.get("buy_hold", {}).get("total_return", 0)
                if pattern_result["total_return"] > bh_return:
                    print(f"   ✅ Outperformed Buy & Hold: {pattern_result['total_return']:.2f}% vs {bh_return:.2f}%")
                else:
                    print(f"   ⚠️ Underperformed Buy & Hold: {pattern_result['total_return']:.2f}% vs {bh_return:.2f}%")

                print(f"   Win Rate: {pattern_result['win_rate']:.1f}% (target: >50%)")
                print(f"   Sharpe Ratio: {pattern_result['sharpe']:.2f} (target: >1.0)")
