"""
Live GEX Interface for Real-Time Data
Cache-first + Alpha Vantage integration with sample data fallback.

Data Flow: Cache → Alpha Vantage → Sample (fallback only)
"""

import pandas as pd
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from cache.unified_cache import UnifiedCacheManager
from validation.options_data_validator import OptionsDataValidator
from gex.gex_calculator import GEXCalculator
from gex.sample_data_gex import SampleDataGEXInterface  # Fallback only
from utils.date_utils import process_date_param, get_default_date_range

logger = logging.getLogger(__name__)


class LiveGEXInterface:
    """
    Live GEX interface using cache-first + Alpha Vantage.
    Handles real-time GEX calculations with automatic fallback.
    """
    
    def __init__(self, 
                 risk_free_rate: float = 0.05,
                 validate_data: bool = True,
                 enable_sample_fallback: bool = True):
        """
        Initialize live GEX interface.
        
        Args:
            risk_free_rate: Risk-free rate for Black-Scholes calculations
            validate_data: Whether to validate data before GEX calculations
            enable_sample_fallback: Use sample data if live data unavailable
        """
        # Initialize core components
        self.cache_manager = UnifiedCacheManager()
        self.alpha_vantage_client = AlphaVantageGEXClient(self.cache_manager)
        self.validator = OptionsDataValidator(strict_mode=False)
        self.gex_calculator = GEXCalculator(risk_free_rate=risk_free_rate)
        
        # Configuration
        self.validate_data = validate_data
        self.enable_sample_fallback = enable_sample_fallback
        
        # Fallback interface (only if enabled)
        self._sample_interface = None
        if enable_sample_fallback:
            try:
                self._sample_interface = SampleDataGEXInterface(
                    risk_free_rate=risk_free_rate,
                    validate_data=validate_data
                )
                logger.info("Sample data fallback enabled")
            except Exception as e:
                logger.warning(f"Sample fallback unavailable: {e}")
                self._sample_interface = None
        
        # Statistics tracking
        self.stats = {
            'cache_hits': 0,
            'api_calls': 0,
            'sample_fallbacks': 0,
            'total_requests': 0
        }
        
    def calculate_gex_for_symbol(self, 
                               symbol: str, 
                               date: str = None, 
                               spot_price: float = None) -> dict:
        """
        Calculate GEX using live data flow.
        
        Args:
            symbol: Stock symbol (SPY, SPX, etc.)
            date: Trading date (YYYY-MM-DD), defaults to latest
            spot_price: Current spot price, auto-detected if None
            
        Returns:
            Dictionary with GEX results and metadata
        """
        self.stats['total_requests'] += 1
        
        try:
            # Step 1: Get options data via live data flow
            options_data = self._fetch_options_data(symbol, date)
            
            if options_data['status'] != 'success':
                return {
                    'status': 'error',
                    'message': f"Failed to fetch options data: {options_data.get('message', 'Unknown error')}",
                    'symbol': symbol,
                    'date': date
                }
            
            df = options_data['data']
            data_source = options_data['source']
            
            # Step 2: Validate data if enabled
            if self.validate_data:
                df, validation_report = self.validator.validate(df)
                if df.empty:
                    return {
                        'status': 'error',
                        'message': 'No valid options data after validation',
                        'symbol': symbol,
                        'date': date,
                        'validation_report': validation_report
                    }
            else:
                validation_report = None
            
            # Step 3: Determine spot price
            if spot_price is None:
                spot_price = self._get_spot_price(symbol, date, df)
            
            # Step 4: Calculate GEX
            gex_results = self.gex_calculator.calculate_gex_profile(
                options_data=df,
                underlying_price=spot_price
            )
            
            # Step 5: Enhanced results with metadata
            enhanced_results = {
                'status': 'success',
                'symbol': symbol,
                'date': date or df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else 'unknown',
                'spot_price': spot_price,
                'data_source': data_source,
                'validation_report': validation_report,
                'stats': self.stats.copy(),
                **gex_results
            }
            
            # Step 6: Cache results if from API
            if data_source == 'alpha_vantage' and date:
                self._cache_gex_results(symbol, date, enhanced_results)
            
            logger.info(f"GEX calculated for {symbol}: ${enhanced_results.get('net_gex', 0):,.0f}")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"GEX calculation failed for {symbol}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'symbol': symbol,
                'date': date,
                'stats': self.stats.copy()
            }
    
    def _fetch_options_data(self, symbol: str, date: str = None) -> dict:
        """
        Fetch options data using live data flow: Cache → API → Sample.
        
        Args:
            symbol: Stock symbol
            date: Trading date
            
        Returns:
            Dictionary with status, source, and data
        """
        # Process date parameter using date_utils
        if not date:
            date = process_date_param("today")
        
        # Step 1: Check cache first
        logger.debug(f"Checking cache for {symbol} options on {date}")
        cached_data = self.cache_manager.get_options_data(symbol, date)
        
        if cached_data is not None and not cached_data.empty:
            self.stats['cache_hits'] += 1
            logger.info(f"Cache hit for {symbol} options on {date}")
            return {
                'status': 'success',
                'source': 'cache',
                'data': cached_data
            }
        
        # Step 2: Try Alpha Vantage API
        logger.info(f"Fetching {symbol} options from Alpha Vantage API")
        try:
            api_data = self.alpha_vantage_client.fetch_historical_options(symbol, date)
            
            if api_data is not None and not api_data.empty:
                self.stats['api_calls'] += 1
                
                # Cache the fresh data
                self.cache_manager.store_options_data(symbol, date, api_data)
                logger.info(f"Cached fresh API data for {symbol} on {date}")
                
                return {
                    'status': 'success',
                    'source': 'alpha_vantage',
                    'data': api_data
                }
        except Exception as e:
            logger.warning(f"Alpha Vantage API call failed: {e}")
        
        # Step 3: Sample data fallback (if enabled)
        if self.enable_sample_fallback and self._sample_interface:
            logger.warning(f"Using sample data fallback for {symbol}")
            try:
                sample_data = self._sample_interface.load_sample_options(symbol, date)
                self.stats['sample_fallbacks'] += 1
                
                return {
                    'status': 'success',
                    'source': 'sample',
                    'data': sample_data
                }
            except Exception as e:
                logger.error(f"Sample fallback failed: {e}")
        
        # Step 4: No data available
        return {
            'status': 'error',
            'message': f'No options data available for {symbol} on {date}',
            'source': 'none'
        }
    
    def _get_spot_price(self, symbol: str, date: str, options_df: pd.DataFrame) -> float:
        """
        Determine spot price from available data.
        
        Args:
            symbol: Stock symbol
            date: Trading date
            options_df: Options DataFrame
            
        Returns:
            Spot price as float
        """
        # Try to get from cache/API first
        try:
            market_data = self.cache_manager.get_market_data(symbol, date)
            if market_data is not None and 'close' in market_data:
                return float(market_data['close'])
        except Exception:
            pass
        
        # Fallback: estimate from options data
        if not options_df.empty and 'underlying_price' in options_df.columns:
            spot_price = options_df['underlying_price'].iloc[0]
            logger.debug(f"Using spot price from options data: ${spot_price:.2f}")
            return float(spot_price)
        
        # Last resort: estimate from strikes
        if not options_df.empty and 'strike' in options_df.columns:
            median_strike = options_df['strike'].median()
            logger.warning(f"Estimating spot price from median strike: ${median_strike:.2f}")
            return float(median_strike)
        
        raise ValueError(f"Cannot determine spot price for {symbol}")
    
    def _cache_gex_results(self, symbol: str, date: str, results: dict):
        """Cache GEX calculation results for faster future access."""
        try:
            # Extract key metrics for caching
            cache_data = {
                'net_gex': results.get('net_gex'),
                'flip_point': results.get('flip_point'),
                'total_gamma': results.get('total_gamma'),
                'spot_price': results.get('spot_price'),
                'calculated_at': process_date_param("today") + "T" + str(pd.Timestamp.now().time())
            }
            
            cache_key = f"gex_{symbol}_{date}"
            # Note: This would require extending UnifiedCacheManager to support GEX results
            # For now, just log the intent
            logger.debug(f"Would cache GEX results for {cache_key}")
            
        except Exception as e:
            logger.warning(f"Failed to cache GEX results: {e}")
    
    def get_stats(self) -> dict:
        """Get interface usage statistics."""
        total = self.stats['total_requests']
        return {
            **self.stats,
            'cache_hit_rate': self.stats['cache_hits'] / max(1, total),
            'api_usage_rate': self.stats['api_calls'] / max(1, total),
            'fallback_rate': self.stats['sample_fallbacks'] / max(1, total)
        }
    
    def reset_stats(self):
        """Reset usage statistics."""
        self.stats = {
            'cache_hits': 0,
            'api_calls': 0,
            'sample_fallbacks': 0,
            'total_requests': 0
        }
        logger.info("Usage statistics reset")

    # Compatibility methods for existing code
    def load_sample_options(self, symbol: str, date: str = None) -> pd.DataFrame:
        """
        Compatibility method - fetches via live data flow.
        Maintains API compatibility with SampleDataGEXInterface.
        """
        result = self._fetch_options_data(symbol, date)
        if result['status'] == 'success':
            return result['data']
        return pd.DataFrame()