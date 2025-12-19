"""
Signal Generators for Backtesting (Issue #8)

Signal generators produce trading decisions based on various inputs:
- GEX patterns from options data
- Technical indicators
- Time series momentum
"""

from src.backtesting.signals.gex_pattern_signal import GEXPatternSignal

__all__ = ["GEXPatternSignal"]
