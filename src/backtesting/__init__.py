"""
GEX Pattern Backtesting Framework (Issue #8)

Walk-forward backtesting with no-lookahead validation for GEX pattern strategies.
Adapted from AutoGen-Trader backtesting framework.

Components:
- BacktestEngine: Core backtesting engine
- Portfolio: Position and trade management
- BacktestResults: Performance metrics
- EnhancedMetrics: Advanced metrics (Calmar, Sortino, profit factor)
- Baseline strategies: Buy-and-hold, MACD, RSI
- GEX pattern signals: Pattern-based signal generators
"""

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.enhanced_metrics import EnhancedMetrics, calculate_enhanced_metrics
from src.backtesting.portfolio import Portfolio
from src.backtesting.results import BacktestResults

__all__ = [
    "BacktestEngine",
    "Portfolio",
    "BacktestResults",
    "EnhancedMetrics",
    "calculate_enhanced_metrics",
]
