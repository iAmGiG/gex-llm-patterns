"""
Backtest Engine for GEX Pattern Strategies (Issue #8)

Adapted from AutoGen-Trader backtesting framework.
Provides walk-forward backtesting with no-lookahead validation.

Design Philosophy:
- Uses SQLiteOptionsManager for GEX/options data
- Uses Alpha Vantage premium API for price data
- Integrates with pattern library for signal generation
- Supports baseline strategy comparisons
- Provides statistical significance testing
"""

import logging
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.backtesting.portfolio import Portfolio
from src.backtesting.results import BacktestResults
from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtesting engine for GEX pattern strategies.

    Adapted from AutoGen-Trader BacktestEngine for gex-llm-patterns.

    Usage:
        ```python
        from src.backtesting import BacktestEngine
        from src.backtesting.signals import GEXPatternSignal

        # Initialize
        signal_gen = GEXPatternSignal()
        engine = BacktestEngine(initial_capital=100000)

        # Run backtest
        results = engine.run(
            signal_generator=signal_gen.generate_signal,
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )

        print(results)
        ```

    Attributes:
        initial_capital: Starting capital (default: $100,000)
        commission_per_share: Commission per share (default: $0.005)
        portfolio: Portfolio state tracker
        av_client: Alpha Vantage client for price data
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission_per_share: float = 0.005,
    ):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting capital (default: $100,000)
            commission_per_share: Commission per share (default: $0.005)
        """
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.portfolio = Portfolio(initial_capital, commission_per_share)
        self._price_cache: Dict[str, pd.DataFrame] = {}
        self.av_client = AlphaVantageGEXClient()

    def get_price_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Fetch price data for backtesting.

        Uses Alpha Vantage premium API for market data. Caches results to avoid
        redundant API calls.

        Args:
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data indexed by date
        """
        cache_key = f"{symbol}_{start_date}_{end_date}"

        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        logger.info(f"Fetching price data for {symbol} from {start_date} to {end_date}")

        try:
            # Use Alpha Vantage premium API for price data
            data = self.av_client.fetch_underlying_data(symbol, start_date, end_date)

            if data is None or data.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Standardize column names (Alpha Vantage client already does this)
            if not all(c.islower() for c in data.columns):
                data.columns = [c.lower() for c in data.columns]

            # Ensure datetime index
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)

            # Sort by date ascending for backtesting
            data = data.sort_index(ascending=True)

            self._price_cache[cache_key] = data
            logger.info(f"Loaded {len(data)} trading days for {symbol}")

            return data

        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return pd.DataFrame()

    def run(
        self,
        signal_generator: Callable,
        symbol: str,
        start_date: str,
        end_date: str,
        signal_kwargs: Optional[Dict[str, Any]] = None,
    ) -> BacktestResults:
        """
        Run backtest for a given signal generator.

        Args:
            signal_generator: Function that generates trading signals
                              Signature: (symbol, data, **kwargs) -> decision dict
                              Decision dict keys:
                              - action: "BUY", "SELL", or "HOLD"
                              - position_size: 0.0 to 1.0
                              - confidence: 0.0 to 1.0
                              - reasoning: str
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            signal_kwargs: Optional kwargs to pass to signal generator

        Returns:
            BacktestResults with performance metrics

        Raises:
            ValueError: If no data available for symbol/date range
        """
        # Reset portfolio
        self.portfolio.reset()

        # Load price data
        data = self.get_price_data(symbol, start_date, end_date)

        if data.empty:
            raise ValueError(f"No data available for {symbol} from {start_date} to {end_date}.")

        logger.info(f"Running backtest: {symbol} ({len(data)} trading days)")
        start_date_str = data.index[0].strftime("%Y-%m-%d")
        end_date_str = data.index[-1].strftime("%Y-%m-%d")
        logger.info(f"Date range: {start_date_str} to {end_date_str}")

        # Prepare price series
        prices = data["close"]
        portfolio_values = [self.initial_capital]
        daily_returns = []

        # Generate decisions and execute trades
        for i in range(len(data)):
            current_price = prices.iloc[i]

            if pd.isna(current_price):
                portfolio_values.append(portfolio_values[-1])
                daily_returns.append(0)
                continue

            # Generate signal using provided signal generator
            kwargs = signal_kwargs or {}
            try:
                decision = signal_generator(symbol, data.iloc[: i + 1], **kwargs)
            except Exception as e:
                logger.warning(f"Signal generation error on {data.index[i]}: {e}")
                decision = {"action": "HOLD", "position_size": 0.0}

            # Execute trade
            date_str = data.index[i].strftime("%Y-%m-%d")
            self.portfolio.execute_decision(date=date_str, decision=decision, current_price=current_price)

            # Calculate portfolio value
            portfolio_value = self.portfolio.get_value(current_price)
            portfolio_values.append(portfolio_value)

            # Calculate daily return
            if i > 0:
                daily_return = (portfolio_value - portfolio_values[-2]) / portfolio_values[-2]
                daily_returns.append(daily_return)

        # Create returns series
        if len(daily_returns) > 0:
            returns_series = pd.Series(daily_returns, index=data.index[: len(daily_returns)])
        else:
            returns_series = pd.Series()

        # Create results object
        results = BacktestResults.from_trading_simulation(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_value=portfolio_values[-1],
            trades=[
                {
                    "date": t.date,
                    "action": t.action,
                    "shares": t.shares,
                    "price": t.price,
                    "commission": t.commission,
                }
                for t in self.portfolio.trades
            ],
            returns_series=returns_series,
        )

        return results

    def run_multi_symbol(
        self,
        signal_generator: Callable,
        symbols: List[str],
        start_date: str,
        end_date: str,
        signal_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, BacktestResults]:
        """
        Run backtest across multiple symbols.

        Args:
            signal_generator: Signal generation function
            symbols: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            signal_kwargs: Optional kwargs to pass to signal generator

        Returns:
            Dictionary mapping symbol -> BacktestResults
        """
        results = {}

        for symbol in symbols:
            logger.info(f"Backtesting: {symbol}")

            try:
                result = self.run(
                    signal_generator=signal_generator,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    signal_kwargs=signal_kwargs,
                )
                results[symbol] = result
                logger.info(f"{symbol}: Sharpe={result.sharpe_ratio:.3f}, Return={result.total_return:.2f}%")

            except ValueError as exc:
                logger.warning(f"Skipping {symbol}: {exc}")
                continue

        return results

    def compare_strategies(
        self,
        strategies: Dict[str, Callable],
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, BacktestResults]:
        """
        Compare multiple strategies on the same symbol and period.

        Args:
            strategies: Dictionary mapping strategy name -> signal generator
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary mapping strategy name -> BacktestResults
        """
        results = {}

        for strategy_name, signal_generator in strategies.items():
            logger.info(f"Testing strategy: {strategy_name}")

            try:
                result = self.run(
                    signal_generator=signal_generator,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )
                results[strategy_name] = result
                logger.info(f"{strategy_name}: Sharpe={result.sharpe_ratio:.3f}, " f"Return={result.total_return:.2f}%")

            except Exception as exc:
                logger.error(f"Strategy {strategy_name} failed: {exc}")
                continue

        return results
