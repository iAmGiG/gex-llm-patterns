"""
Base GEX Strategy Interface
Common interface for all GEX strategy versions (V0-V4) in continuous experiment framework.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class GEXSignal:
    """Standardized GEX trading signal."""
    date: str
    signal_type: str  # 'long', 'short', 'neutral'
    confidence: float  # 0.0 to 1.0
    reasoning: str
    strike_level: Optional[float] = None  # For strike-specific strategies
    volume: Optional[int] = None
    gamma_exposure: Optional[float] = None
    metadata: Optional[Dict] = None


@dataclass
class StrategyMetrics:
    """Performance metrics for strategy evaluation."""
    total_trades: int
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    avg_hold_time: float
    metadata: Optional[Dict] = None


class BaseGEXStrategy(ABC):
    """
    Abstract base class for all GEX trading strategies.

    Provides common interface for V0-V4 strategy implementations
    in the continuous experiment framework.
    """

    def __init__(self, symbol: str = "SPY", config: Optional[Dict] = None):
        """
        Initialize strategy with symbol and configuration.

        Args:
            symbol: Trading symbol (e.g., "SPY")
            config: Strategy-specific configuration
        """
        self.symbol = symbol
        self.config = config or {}
        self.version = self._get_version()
        self.signals: List[GEXSignal] = []
        self.performance_metrics: Optional[StrategyMetrics] = None

    @abstractmethod
    def _get_version(self) -> str:
        """Return strategy version identifier (e.g., 'V0', 'V1', etc.)."""
        pass

    @abstractmethod
    def analyze_day(self, date: str, market_data: Dict, gex_data: Dict) -> GEXSignal:
        """
        Analyze single trading day and generate signal.

        Args:
            date: Trading date (YYYY-MM-DD format)
            market_data: Market data for the date
            gex_data: GEX data for the date

        Returns:
            GEXSignal for the trading day
        """
        pass

    def prepare_batch_data(self, start_date: str, end_date: str) -> Dict:
        """
        Prepare batch data for analysis (used by V4 LLM strategy).

        Args:
            start_date: Start date for batch
            end_date: End date for batch

        Returns:
            Prepared batch data dictionary
        """
        # Default implementation - override for batch strategies
        return {}

    def run_backtest(self, start_date: str, end_date: str,
                     market_data: pd.DataFrame, gex_data: Dict) -> List[GEXSignal]:
        """
        Run complete backtest for date range.

        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            market_data: Market data DataFrame
            gex_data: GEX data dictionary

        Returns:
            List of GEXSignals generated
        """
        self.signals = []

        # Filter data for date range
        date_range = pd.date_range(
            start=start_date, end=end_date, freq='B')  # Business days

        for date in date_range:
            date_str = date.strftime('%Y-%m-%d')

            # Get market data for date
            day_market_data = self._get_day_data(market_data, date_str)
            if day_market_data is None:
                continue

            # Get GEX data for date
            day_gex_data = gex_data.get(date_str, {})
            if not day_gex_data:
                continue

            # Generate signal
            signal = self.analyze_day(date_str, day_market_data, day_gex_data)
            if signal:
                self.signals.append(signal)

        return self.signals

    def calculate_performance(self, market_data: pd.DataFrame) -> StrategyMetrics:
        """
        Calculate performance metrics for generated signals.

        Args:
            market_data: Market data for performance calculation

        Returns:
            StrategyMetrics with performance results
        """
        if not self.signals:
            return StrategyMetrics(
                total_trades=0, win_rate=0.0, total_return=0.0,
                sharpe_ratio=0.0, max_drawdown=0.0, avg_hold_time=0.0
            )

        # Basic performance calculation - override for more sophisticated metrics
        total_trades = len(
            [s for s in self.signals if s.signal_type != 'neutral'])

        # Calculate returns based on signals
        returns = []
        for signal in self.signals:
            if signal.signal_type != 'neutral':
                # Simple next-day return calculation
                signal_return = self._calculate_signal_return(
                    signal, market_data)
                if signal_return is not None:
                    returns.append(signal_return)

        if not returns:
            win_rate = 0.0
            total_return = 0.0
            sharpe_ratio = 0.0
        else:
            win_rate = len([r for r in returns if r > 0]) / len(returns)
            total_return = sum(returns)
            sharpe_ratio = (sum(returns) / len(returns)) / \
                (pd.Series(returns).std() or 1.0)

        max_drawdown = self._calculate_max_drawdown(returns)
        avg_hold_time = 1.0  # Default to 1 day - override for longer holds

        self.performance_metrics = StrategyMetrics(
            total_trades=total_trades,
            win_rate=win_rate,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_hold_time=avg_hold_time,
            metadata={'version': self.version, 'symbol': self.symbol}
        )

        return self.performance_metrics

    def _get_day_data(self, market_data: pd.DataFrame, date_str: str) -> Optional[Dict]:
        """Extract market data for specific date."""
        try:
            # Try to find data for the date
            if 'date' in market_data.columns:
                day_data = market_data[market_data['date'] == date_str]
            else:
                # Assume index is date
                day_data = market_data[market_data.index == date_str]

            if day_data.empty:
                return None

            return day_data.iloc[0].to_dict()
        except Exception:
            return None

    def _calculate_signal_return(self, signal: GEXSignal, market_data: pd.DataFrame) -> Optional[float]:
        """Calculate return for a specific signal."""
        try:
            # Simple next-day return calculation
            signal_date = pd.to_datetime(signal.date)
            next_date = signal_date + pd.Timedelta(days=1)

            # Get prices
            current_price = self._get_price_for_date(market_data, signal.date)
            next_price = self._get_price_for_date(
                market_data, next_date.strftime('%Y-%m-%d'))

            if current_price is None or next_price is None:
                return None

            # Calculate return based on signal direction
            raw_return = (next_price - current_price) / current_price

            if signal.signal_type == 'long':
                return raw_return
            elif signal.signal_type == 'short':
                return -raw_return
            else:
                return 0.0

        except Exception:
            return None

    def _get_price_for_date(self, market_data: pd.DataFrame, date_str: str) -> Optional[float]:
        """Get closing price for specific date."""
        try:
            if 'date' in market_data.columns:
                day_data = market_data[market_data['date'] == date_str]
            else:
                day_data = market_data[market_data.index == date_str]

            if day_data.empty:
                return None

            # Try different price columns
            for col in ['close', 'Close', 'price', 'Price']:
                if col in day_data.columns:
                    return float(day_data.iloc[0][col])

            return None
        except Exception:
            return None

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns list."""
        if not returns:
            return 0.0

        cumulative = [1.0]
        for ret in returns:
            cumulative.append(cumulative[-1] * (1 + ret))

        peak = cumulative[0]
        max_dd = 0.0

        for value in cumulative[1:]:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)

        return max_dd

    def export_results(self) -> Dict:
        """Export strategy results for analysis."""
        return {
            'version': self.version,
            'symbol': self.symbol,
            'config': self.config,
            'signals': [
                {
                    'date': s.date,
                    'signal_type': s.signal_type,
                    'confidence': s.confidence,
                    'reasoning': s.reasoning,
                    'strike_level': s.strike_level,
                    'volume': s.volume,
                    'gamma_exposure': s.gamma_exposure,
                    'metadata': s.metadata
                }
                for s in self.signals
            ],
            'performance': self.performance_metrics.__dict__ if self.performance_metrics else None
        }
