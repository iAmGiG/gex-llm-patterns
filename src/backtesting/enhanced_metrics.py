"""
Enhanced Backtesting Metrics (#270)

Additional performance metrics beyond the core BacktestResults.
Focused on practical trading insights for research deliverables.

Metrics Added:
- Calmar ratio (return / max drawdown)
- Profit factor (gross profit / gross loss)
- Win/loss streak analysis
- Execution-cost adjusted returns
- Monthly/quarterly performance breakdown
- Trade quality metrics
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class EnhancedMetrics:
    """
    Extended performance metrics for detailed analysis.

    Supplements BacktestResults with additional risk/return metrics
    commonly used in professional trading analysis.
    """

    # Risk-adjusted returns
    calmar_ratio: float = 0.0  # Annualized return / max drawdown
    sortino_ratio: float = 0.0  # Return / downside deviation

    # Trade quality
    profit_factor: float = 0.0  # Gross profit / gross loss
    avg_win: float = 0.0  # Average winning trade return
    avg_loss: float = 0.0  # Average losing trade return
    win_loss_ratio: float = 0.0  # avg_win / avg_loss
    expectancy: float = 0.0  # Expected value per trade

    # Streak analysis
    max_win_streak: int = 0
    max_loss_streak: int = 0
    current_streak: int = 0
    current_streak_type: str = ""  # "win" or "loss"

    # Execution costs
    gross_return: float = 0.0  # Before costs
    net_return: float = 0.0  # After costs
    total_commissions: float = 0.0
    cost_drag: float = 0.0  # Percentage reduction from costs

    # Periodic performance
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    quarterly_returns: Dict[str, float] = field(default_factory=dict)
    best_month: Tuple[str, float] = ("", 0.0)
    worst_month: Tuple[str, float] = ("", 0.0)

    # Trade statistics
    avg_trade_duration: float = 0.0  # Days
    avg_bars_in_trade: float = 0.0
    trades_per_month: float = 0.0


def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float, trading_days: int = 252) -> float:
    """
    Calculate Calmar ratio (annualized return / max drawdown).

    Args:
        returns: Daily returns series
        max_drawdown: Maximum drawdown as decimal (negative value)
        trading_days: Trading days per year

    Returns:
        Calmar ratio (higher is better)
    """
    if max_drawdown == 0 or len(returns) == 0:
        return 0.0

    # Annualized return
    total_return = (1 + returns).prod() - 1
    years = len(returns) / trading_days
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    # Calmar = annualized return / |max drawdown|
    return annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0


def calculate_sortino_ratio(returns: pd.Series, risk_free: float = 0.0, trading_days: int = 252) -> float:
    """
    Calculate Sortino ratio (return / downside deviation).

    Only penalizes downside volatility, unlike Sharpe.

    Args:
        returns: Daily returns series
        risk_free: Risk-free rate (annualized)
        trading_days: Trading days per year

    Returns:
        Sortino ratio (higher is better)
    """
    if len(returns) == 0:
        return 0.0

    # Daily risk-free rate
    daily_rf = risk_free / trading_days

    # Excess returns
    excess = returns - daily_rf

    # Downside deviation (only negative returns)
    downside = returns[returns < 0]
    if len(downside) == 0:
        return float("inf") if excess.mean() > 0 else 0.0

    downside_std = downside.std()
    if downside_std == 0:
        return 0.0

    # Annualized
    return np.sqrt(trading_days) * excess.mean() / downside_std


def calculate_profit_factor(trades: List[Dict]) -> Tuple[float, float, float]:
    """
    Calculate profit factor and related trade metrics.

    Args:
        trades: List of trade dictionaries with 'action', 'price', 'shares'

    Returns:
        (profit_factor, avg_win, avg_loss)
    """
    if not trades:
        return 0.0, 0.0, 0.0

    # Calculate P&L for each trade
    wins = []
    losses = []
    position_entry = None

    for trade in trades:
        action = trade.get("action", "")
        price = trade.get("price", 0)
        shares = trade.get("shares", 0)

        if action == "BUY":
            position_entry = price
        elif action == "SELL" and position_entry is not None:
            pnl = (price - position_entry) * shares
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))
            position_entry = None

    gross_profit = sum(wins) if wins else 0
    gross_loss = sum(losses) if losses else 0

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    return profit_factor, avg_win, avg_loss


def analyze_streaks(returns: pd.Series) -> Dict[str, int]:
    """
    Analyze win/loss streaks in returns.

    Args:
        returns: Daily returns series

    Returns:
        Dictionary with max_win_streak, max_loss_streak, current_streak, streak_type
    """
    if len(returns) == 0:
        return {
            "max_win_streak": 0,
            "max_loss_streak": 0,
            "current_streak": 0,
            "streak_type": "",
        }

    # Convert to win/loss sequence
    signs = np.sign(returns)

    max_win = 0
    max_loss = 0
    current = 0
    current_sign = 0

    for s in signs:
        if s == 0:
            continue

        if s == current_sign:
            current += 1
        else:
            current = 1
            current_sign = s

        if s > 0:
            max_win = max(max_win, current)
        else:
            max_loss = max(max_loss, current)

    return {
        "max_win_streak": max_win,
        "max_loss_streak": max_loss,
        "current_streak": current,
        "streak_type": "win" if current_sign > 0 else "loss" if current_sign < 0 else "",
    }


def calculate_periodic_returns(
    returns: pd.Series,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Calculate monthly and quarterly returns.

    Args:
        returns: Daily returns series with DatetimeIndex

    Returns:
        (monthly_returns, quarterly_returns) as dictionaries
    """
    if len(returns) == 0 or not isinstance(returns.index, pd.DatetimeIndex):
        return {}, {}

    # Monthly returns
    monthly = {}
    for month, group in returns.groupby(returns.index.to_period("M")):
        month_return = (1 + group).prod() - 1
        monthly[str(month)] = round(month_return * 100, 2)

    # Quarterly returns
    quarterly = {}
    for quarter, group in returns.groupby(returns.index.to_period("Q")):
        quarter_return = (1 + group).prod() - 1
        quarterly[str(quarter)] = round(quarter_return * 100, 2)

    return monthly, quarterly


def calculate_execution_costs(
    trades: List[Dict], gross_return: float, commission_per_share: float = 0.005
) -> Tuple[float, float, float]:
    """
    Calculate execution cost impact.

    Args:
        trades: List of trade dictionaries
        gross_return: Gross return before costs (percentage)
        commission_per_share: Commission per share

    Returns:
        (total_commissions, net_return, cost_drag)
    """
    total_commissions = sum(
        trade.get("commission", 0) or trade.get("shares", 0) * commission_per_share for trade in trades
    )

    # Rough approximation - actual depends on capital deployed
    # Assume average position of 100 shares for cost calculation
    avg_shares = np.mean([t.get("shares", 0) for t in trades]) if trades else 0
    estimated_cost_impact = total_commissions / (avg_shares * 100) if avg_shares else 0

    net_return = gross_return - (estimated_cost_impact * 100)
    cost_drag = estimated_cost_impact * 100

    return total_commissions, net_return, cost_drag


def calculate_enhanced_metrics(
    returns: pd.Series,
    trades: List[Dict],
    max_drawdown: float,
    initial_capital: float = 10000,
    commission_per_share: float = 0.005,
) -> EnhancedMetrics:
    """
    Calculate all enhanced metrics from backtest results.

    Args:
        returns: Daily returns series
        trades: List of trade dictionaries
        max_drawdown: Maximum drawdown (as decimal, e.g., -0.10 for -10%)
        initial_capital: Starting capital
        commission_per_share: Commission per share

    Returns:
        EnhancedMetrics dataclass with all calculated values
    """
    metrics = EnhancedMetrics()

    # Risk-adjusted ratios
    metrics.calmar_ratio = calculate_calmar_ratio(returns, max_drawdown)
    metrics.sortino_ratio = calculate_sortino_ratio(returns)

    # Trade quality
    pf, avg_win, avg_loss = calculate_profit_factor(trades)
    metrics.profit_factor = pf
    metrics.avg_win = avg_win
    metrics.avg_loss = avg_loss
    metrics.win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    # Win rate from returns
    wins = (returns > 0).sum()
    total = len(returns[returns != 0])
    win_rate = wins / total if total > 0 else 0

    # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    metrics.expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    # Streak analysis
    streaks = analyze_streaks(returns)
    metrics.max_win_streak = streaks["max_win_streak"]
    metrics.max_loss_streak = streaks["max_loss_streak"]
    metrics.current_streak = streaks["current_streak"]
    metrics.current_streak_type = streaks["streak_type"]

    # Execution costs
    gross_return = (1 + returns).prod() - 1 if len(returns) > 0 else 0
    metrics.gross_return = gross_return * 100
    total_comm, net_ret, cost_drag = calculate_execution_costs(trades, metrics.gross_return, commission_per_share)
    metrics.total_commissions = total_comm
    metrics.net_return = net_ret
    metrics.cost_drag = cost_drag

    # Periodic returns
    monthly, quarterly = calculate_periodic_returns(returns)
    metrics.monthly_returns = monthly
    metrics.quarterly_returns = quarterly

    if monthly:
        best = max(monthly.items(), key=lambda x: x[1])
        worst = min(monthly.items(), key=lambda x: x[1])
        metrics.best_month = best
        metrics.worst_month = worst

    # Trade statistics
    if len(trades) > 0 and len(returns) > 0:
        days = len(returns)
        months = days / 21  # ~21 trading days per month
        metrics.trades_per_month = len(trades) / months if months > 0 else 0

        # Average bars in trade (approximation)
        metrics.avg_bars_in_trade = days / len(trades) if len(trades) > 0 else 0

    return metrics


def format_enhanced_report(
    symbol: str,
    start_date: str,
    end_date: str,
    base_metrics: Dict,
    enhanced: EnhancedMetrics,
) -> str:
    """
    Generate formatted markdown report with enhanced metrics.

    Args:
        symbol: Ticker symbol
        start_date: Backtest start date
        end_date: Backtest end date
        base_metrics: Basic metrics (sharpe, return, etc.)
        enhanced: EnhancedMetrics dataclass

    Returns:
        Markdown formatted report string
    """
    lines = [
        f"# Backtest Report: {symbol}",
        f"**Period**: {start_date} to {end_date}",
        "",
        "## Performance Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Return | {base_metrics.get('total_return', 0):.2f}% |",
        f"| Sharpe Ratio | {base_metrics.get('sharpe_ratio', 0):.3f} |",
        f"| Calmar Ratio | {enhanced.calmar_ratio:.3f} |",
        f"| Sortino Ratio | {enhanced.sortino_ratio:.3f} |",
        f"| Max Drawdown | {base_metrics.get('max_drawdown', 0):.2f}% |",
        f"| Volatility | {base_metrics.get('volatility', 0):.2f}% |",
        "",
        "## Trade Quality",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Win Rate | {base_metrics.get('win_rate', 0):.1f}% |",
        f"| Profit Factor | {enhanced.profit_factor:.2f} |",
        f"| Win/Loss Ratio | {enhanced.win_loss_ratio:.2f} |",
        f"| Expectancy | ${enhanced.expectancy:.2f} |",
        f"| Avg Win | ${enhanced.avg_win:.2f} |",
        f"| Avg Loss | ${enhanced.avg_loss:.2f} |",
        "",
        "## Streak Analysis",
        "",
        f"- **Max Win Streak**: {enhanced.max_win_streak} days",
        f"- **Max Loss Streak**: {enhanced.max_loss_streak} days",
        f"- **Current Streak**: {enhanced.current_streak} days ({enhanced.current_streak_type})",
        "",
        "## Execution Costs",
        "",
        f"- **Gross Return**: {enhanced.gross_return:.2f}%",
        f"- **Net Return**: {enhanced.net_return:.2f}%",
        f"- **Total Commissions**: ${enhanced.total_commissions:.2f}",
        f"- **Cost Drag**: {enhanced.cost_drag:.2f}%",
        "",
    ]

    # Monthly returns table
    if enhanced.monthly_returns:
        lines.extend(
            [
                "## Monthly Returns",
                "",
                "| Month | Return |",
                "|-------|--------|",
            ]
        )
        for month, ret in sorted(enhanced.monthly_returns.items()):
            sign = "+" if ret > 0 else ""
            lines.append(f"| {month} | {sign}{ret:.2f}% |")

        lines.extend(
            [
                "",
                f"**Best Month**: {enhanced.best_month[0]} ({enhanced.best_month[1]:+.2f}%)",
                f"**Worst Month**: {enhanced.worst_month[0]} ({enhanced.worst_month[1]:+.2f}%)",
                "",
            ]
        )

    # Trade statistics
    lines.extend(
        [
            "## Trade Statistics",
            "",
            f"- **Total Trades**: {base_metrics.get('num_trades', 0)}",
            f"- **Trades per Month**: {enhanced.trades_per_month:.1f}",
            f"- **Avg Bars in Trade**: {enhanced.avg_bars_in_trade:.1f}",
            "",
            "---",
            "Generated by enhanced_metrics.py",
        ]
    )

    return "\n".join(lines)


def generate_comparison_table(results: List[Dict], metric_keys: Optional[List[str]] = None) -> str:
    """
    Generate markdown comparison table for multiple backtest results.

    Args:
        results: List of result dictionaries with 'symbol' and metrics
        metric_keys: Specific metrics to include (default: common metrics)

    Returns:
        Markdown table string
    """
    if not results:
        return "No results to compare."

    if metric_keys is None:
        metric_keys = [
            "total_return",
            "sharpe_ratio",
            "calmar_ratio",
            "max_drawdown",
            "win_rate",
            "profit_factor",
        ]

    # Header
    symbols = [r.get("symbol", "?") for r in results]
    header = "| Metric | " + " | ".join(symbols) + " |"
    separator = "|--------|" + "|".join(["-------"] * len(symbols)) + "|"

    lines = [header, separator]

    # Metric rows
    metric_labels = {
        "total_return": "Total Return (%)",
        "sharpe_ratio": "Sharpe Ratio",
        "calmar_ratio": "Calmar Ratio",
        "sortino_ratio": "Sortino Ratio",
        "max_drawdown": "Max Drawdown (%)",
        "win_rate": "Win Rate (%)",
        "profit_factor": "Profit Factor",
        "volatility": "Volatility (%)",
        "num_trades": "Trades",
    }

    for key in metric_keys:
        label = metric_labels.get(key, key)
        values = []
        for r in results:
            val = r.get(key, 0)
            if isinstance(val, float):
                values.append(f"{val:.2f}")
            else:
                values.append(str(val))
        lines.append(f"| {label} | " + " | ".join(values) + " |")

    return "\n".join(lines)
