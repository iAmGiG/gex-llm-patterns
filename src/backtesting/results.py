"""
Backtest Results and Performance Metrics

Refactored from experiment_293 calculate_metrics() function.
Calculates: Sharpe, max drawdown, win rate, volatility, total return.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class BacktestResults:
    """
    Backtest performance results.

    Attributes:
        symbol: Ticker symbol
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Starting capital
        final_value: Ending portfolio value
        total_return: Total return percentage
        sharpe_ratio: Sharpe ratio (annualized, 252 trading days)
        max_drawdown: Maximum drawdown percentage
        win_rate: Percentage of profitable days
        volatility: Annualized volatility percentage
        num_trades: Total number of trades executed
        trades: List of trade dictionaries
        returns_series: Pandas Series of daily returns
    """

    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    volatility: float
    num_trades: int
    trades: List[Dict] = field(default_factory=list)
    returns_series: pd.Series = field(default_factory=lambda: pd.Series())

    @classmethod
    def from_trading_simulation(
        cls,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        final_value: float,
        trades: List[Dict],
        returns_series: pd.Series,
    ) -> "BacktestResults":
        """
        Create BacktestResults from trading simulation output.

        Refactored from experiment_293 calculate_metrics() function.
        """
        metrics = calculate_metrics(returns_series)
        total_return = (final_value - initial_capital) / initial_capital * 100

        return cls(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_value=final_value,
            total_return=total_return,
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown=metrics["max_drawdown"],
            win_rate=metrics["win_rate"],
            volatility=metrics["volatility"],
            num_trades=len(trades),
            trades=trades,
            returns_series=returns_series,
        )

    def __str__(self) -> str:
        """Pretty print results."""
        return f"""
Backtest Results: {self.symbol} ({self.start_date} to {self.end_date})
{'=' * 70}
Total Return:    {self.total_return:>10.2f}%
Sharpe Ratio:    {self.sharpe_ratio:>10.3f}
Max Drawdown:    {self.max_drawdown:>10.2f}%
Win Rate:        {self.win_rate:>10.1f}%
Volatility:      {self.volatility:>10.2f}%
Number of Trades: {self.num_trades:>9}
Final Value:     ${self.final_value:>10,.2f} (started with ${self.initial_capital:>10,.2f})
{'=' * 70}
"""


def calculate_metrics(returns: pd.Series) -> Dict[str, float]:
    """
    Calculate performance metrics from returns series.

    Directly copied from experiment_293_macd_vs_voting.py (lines 172-213).
    Proven to calculate correct Sharpe ratio (0.856 on AAPL 2024).

    Args:
        returns: Pandas Series of daily returns

    Returns:
        Dictionary with total_return, sharpe_ratio, max_drawdown, win_rate, volatility
    """
    # Remove NaN values
    clean_returns = returns.dropna()

    if len(clean_returns) == 0:
        return {
            "total_return": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "win_rate": 0,
            "volatility": 0,
        }

    # Total return
    total_return = (1 + clean_returns).prod() - 1

    # Sharpe ratio (assuming 252 trading days)
    if clean_returns.std() != 0:
        sharpe = np.sqrt(252) * clean_returns.mean() / clean_returns.std()
    else:
        sharpe = 0

    # Max drawdown
    cumulative = (1 + clean_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()

    # Win rate
    win_rate = (clean_returns > 0).sum() / len(clean_returns) if len(clean_returns) > 0 else 0

    # Volatility (annualized)
    volatility = clean_returns.std() * np.sqrt(252)

    return {
        "total_return": total_return * 100,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd * 100,
        "win_rate": win_rate * 100,
        "volatility": volatility * 100,
    }
