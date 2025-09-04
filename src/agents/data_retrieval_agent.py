"""
Data Retrieval Agent
Provides agent-based interface for retrieving and processing options data.
Mimics cache retrieval patterns for seamless transition to production data.

NOTE: Currently uses sample_data/ for testing. Will transition to .cache/
      directory when live data pipeline is implemented.
"""

from src.gex.sample_data_gex import SampleDataGEXInterface
from src.validation.options_data_validator import OptionsDataValidator
import pandas as pd
from pathlib import Path
import logging
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import after path setup
from src.data_sources.sample_data_loader import SampleDataProvider


logger = logging.getLogger(__name__)


class DataRetrievalAgent:
    """
    Agent for retrieving and processing options data.
    Provides a unified interface that will work with both sample and production data.
    """

    def __init__(self,
                 data_source="sample",
                 cache_dir=None,
                 validate=True):
        """
        Initialize the data retrieval agent.

        Args:
            data_source: "sample" for test data, "cache" for production (future)
            cache_dir: Directory for cached data (defaults to .cache/)
            validate: Whether to validate retrieved data
        """
        self.data_source = data_source
        self.validate = validate

        # Set up cache directory (for future use)
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / ".cache"

        # Initialize data provider based on source
        if data_source == "sample":
            self.provider = SampleDataProvider()
            self.gex_interface = SampleDataGEXInterface()
        else:
            # Future: Initialize production data provider
            raise NotImplementedError(
                f"Data source '{data_source}' not yet implemented")

        self.validator = OptionsDataValidator() if validate else None

        # Agent state
        self.current_symbol = None
        self.current_date = None
        self.data_cache = {}

    def initialize(self):
        """
        Initialize the agent and return available data info.

        Returnsionary with available symbols, dates, and status
        """
        logger.info(
            f"Initializing DataRetrievalAgent with {self.data_source} data")

        self.provider.initialize()

        symbols = self.provider.fetch_available_symbols()

        # Get date range for each symbol
        symbol_info = {}
        for symbol in symbols:
            dates = self.provider.fetch_available_dates(symbol)
            symbol_info[symbol] = {
                'dates': dates,
                'count': len(dates),
                'first': dates[0] if dates else None,
                'last': dates[-1] if dates else None
            }

        return {
            'status': 'initialized',
            'data_source': self.data_source,
            'symbols': symbols,
            'symbol_info': symbol_info,
            'cache_dir': str(self.cache_dir),
            'validation_enabled': self.validate
        }

    def retrieve_options_data(self,
                              symbol,
                              date=None,
                              filters=None):
        """
        Retrieve options data for analysis.

        Args:
            symbol: Stock symbol
            date: Options date (YYYY-MM-DD), uses latest if None
            filters: Optional filters (e.g., min_volume, strike_range)

        Returnsionary with data and metadata
        """
        logger.info(f"Retrieving options data: symbol={symbol}, date={date}")

        # Check cache
        cache_key = f"{symbol}_{date}_{str(filters)}"
        if cache_key in self.data_cache:
            logger.info("Using cached data")
            return self.data_cache[cache_key]

        # Fetch data
        df = self.provider.fetch_options_data(symbol, date)

        if df.empty:
            return {
                'status': 'no_data',
                'symbol': symbol,
                'date': date,
                'message': f"No options data found for {symbol} on {date}"
            }

        # Validate if enabled
        if self.validate and self.validator:
            df, validation_report = self.validator.validate(df)
            logger.info(f"Validation complete: {len(df)} valid contracts")
        else:
            validation_report = None

        # Apply filters
        if filters:
            df = self._apply_filters(df, filters)

        # Update agent state
        self.current_symbol = symbol
        self.current_date = date or df['date'].max().strftime('%Y-%m-%d')

        # Prepare response
        result = {
            'status': 'success',
            'symbol': symbol,
            'date': self.current_date,
            'data': df,
            'metadata': {
                'total_contracts': len(df),
                'unique_strikes': df['strike'].nunique(),
                'unique_expirations': df['expiration'].nunique(),
                'put_call_ratio': len(df[df['type'] == 'put']) / max(1, len(df[df['type'] == 'call'])),
                'total_volume': df['volume'].sum() if 'volume' in df.columns else 0,
                'total_open_interest': df['open_interest'].sum()
            },
            'validation_report': validation_report
        }

        # Cache result
        self.data_cache[cache_key] = result

        return result

    def calculate_gex(self,
                      symbol= None,
                      date= None,
                      spot_price= None) :
        """
        Calculate GEX metrics using retrieved data.

        Args:
            symbol: Stock symbol (uses current if None)
            date: Options date (uses current if None)
            spot_price: Current spot price (auto-detects if None)

        Returns:
            GEX calculation results
        """
        symbol = symbol or self.current_symbol
        date = date or self.current_date

        if not symbol:
            return {
                'status': 'error',
                'message': 'No symbol specified or in context'
            }

        logger.info(f"Calculating GEX for {symbol} on {date}")

        # Use GEX interface
        gex_results = self.gex_interface.calculate_gex_for_symbol(
            symbol, date, spot_price
        )

        # Add agent metadata
        gex_results['agent'] = 'DataRetrievalAgent'
        gex_results['data_source'] = self.data_source

        return gex_results

    def get_pattern_candidates(self,
                               pattern_type = "short_put_arbitrage",
                               min_volume = 100) :
        """
        Identify potential pattern candidates from available data.

        Args:
            pattern_type: Type of pattern to search for
            min_volume: Minimum volume threshold

        Returns of pattern candidates with details
        """
        logger.info(f"Searching for {pattern_type} patterns")

        candidates = []

        # Get all available symbols
        symbols = self.provider.fetch_available_symbols()

        for symbol in symbols:
            # Get latest data for symbol
            data = self.retrieve_options_data(symbol)

            if data['status'] != 'success':
                continue

            df = data['data']

            # Pattern-specific detection
            if pattern_type == "short_put_arbitrage":
                # Look for high-volume OTM puts
                puts = df[df['type'] == 'put']

                if 'volume' in puts.columns:
                    high_vol_puts = puts[puts['volume'] >= min_volume]

                    for _, put in high_vol_puts.iterrows():
                        # Calculate metrics
                        if 'implied_volatility' in put and put['implied_volatility'] > 0:
                            candidates.append({
                                'symbol': symbol,
                                'strike': put['strike'],
                                'expiration': put['expiration'],
                                'volume': put['volume'],
                                'open_interest': put['open_interest'],
                                'implied_vol': put['implied_volatility'],
                                'delta': put.get('delta', None),
                                'pattern_score': self._calculate_pattern_score(put)
                            })

        # Sort by pattern score
        candidates.sort(key=lambda x: x['pattern_score'], reverse=True)

        logger.info(f"Found {len(candidates)} pattern candidates")
        return candidates

    def _apply_filters(self, df, filters):
        """Apply filters to options data."""
        filtered = df.copy()

        # Volume filter
        if 'min_volume' in filters and 'volume' in filtered.columns:
            filtered = filtered[filtered['volume'] >= filters['min_volume']]

        # Strike range filter
        if 'strike_min' in filters:
            filtered = filtered[filtered['strike'] >= filters['strike_min']]
        if 'strike_max' in filters:
            filtered = filtered[filtered['strike'] <= filters['strike_max']]

        # Expiration filter
        if 'max_days_to_expiry' in filters:
            if 'date' in filtered.columns and 'expiration' in filtered.columns:
                days_to_exp = (filtered['expiration'] -
                               filtered['date']).dt.days
                filtered = filtered[days_to_exp <=
                                    filters['max_days_to_expiry']]

        # Option type filter
        if 'option_type' in filters:
            filtered = filtered[filtered['type'] == filters['option_type']]

        # Greeks filters
        if 'min_delta' in filters and 'delta' in filtered.columns:
            filtered = filtered[abs(filtered['delta']) >= filters['min_delta']]
        if 'min_gamma' in filters and 'gamma' in filtered.columns:
            filtered = filtered[filtered['gamma'] >= filters['min_gamma']]

        return filtered

    def _calculate_pattern_score(self, option_row):
        """Calculate a pattern score for ranking candidates."""
        score = 0.0

        # Volume component
        if 'volume' in option_row and option_row['volume'] > 0:
            score += min(option_row['volume'] / 1000, 10)  # Cap at 10

        # Open interest component
        if 'open_interest' in option_row and option_row['open_interest'] > 0:
            score += min(option_row['open_interest'] / 10000, 5)  # Cap at 5

        # IV component (higher is more interesting)
        if 'implied_volatility' in option_row:
            score += option_row['implied_volatility'] * 10

        # Delta component (OTM options more interesting)
        if 'delta' in option_row:
            score += (1 - abs(option_row['delta'])) * 5

        return score

    def generate_summary_report(self) -> str:
        """Generate a summary report of available data."""
        info = self.initialize()

        report = []
        report.append("=" * 60)
        report.append("DATA RETRIEVAL AGENT SUMMARY")
        report.append("=" * 60)
        report.append(f"Data Source: {self.data_source}")
        report.append(f"Cache Directory: {self.cache_dir}")
        report.append(
            f"Validation: {'Enabled' if self.validate else 'Disabled'}")
        report.append("")

        report.append("AVAILABLE DATA")
        report.append("-" * 30)
        for symbol, details in info['symbol_info'].items():
            report.append(f"\n{symbol}:")
            report.append(
                f"  Date Range: {details['first']} to {details['last']}")
            report.append(f"  Total Days: {details['count']}")

        # Get sample GEX for first symbol
        if info['symbols']:
            symbol = info['symbols'][0]
            gex = self.calculate_gex(symbol)

            if 'net_gex' in gex:
                report.append("")
                report.append(f"SAMPLE GEX CALCULATION ({symbol})")
                report.append("-" * 30)
                report.append(f"Net GEX: ${gex['net_gex']:,.0f}")
                report.append(f"Spot Price: ${gex['spot_price']:.2f}")

                if gex.get('flip_point'):
                    report.append(f"Flip Point: ${gex['flip_point']:.2f}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


class AgentOrchestrator:
    """
    Orchestrates multiple data retrieval agents for parallel processing.
    Useful for analyzing multiple symbols or dates simultaneously.
    """

    def __init__(self, num_agents = 3):
        """
        Initialize the orchestrator.

        Args:
            num_agents: Number of parallel agents to create
        """
        self.agents = [
            DataRetrievalAgent() for _ in range(num_agents)
        ]
        self.results = {}

    def parallel_gex_calculation(self,
                                 symbols,
                                 date= None) :
        """
        Calculate GEX for multiple symbols in parallel.

        Args:
            symbols of symbols to process
            date: Options date

        Returnsionary mapping symbols to GEX results
        """
        results = {}

        # Distribute work among agents
        for i, symbol in enumerate(symbols):
            agent_idx = i % len(self.agents)
            agent = self.agents[agent_idx]

            # Calculate GEX
            gex_result = agent.calculate_gex(symbol, date)
            results[symbol] = gex_result

            logger.info(f"Agent {agent_idx} processed {symbol}")

        self.results = results
        return results

    def find_highest_gex(self) :
        """Find symbol with highest absolute net GEX."""
        if not self.results:
            return None

        max_symbol = None
        max_gex = 0

        for symbol, result in self.results.items():
            if 'net_gex' in result:
                abs_gex = abs(result['net_gex'])
                if abs_gex > max_gex:
                    max_gex = abs_gex
                    max_symbol = symbol

        return max_symbol
