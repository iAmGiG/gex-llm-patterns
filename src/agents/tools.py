"""
Tool definitions for GEX-LLM agents using AutoGen 0.7.4 pattern.

Provides data retrieval, calculation, and analysis tools that agents
can use to interact with market data and perform GEX calculations.
"""

from autogen_core.tools import FunctionTool
from src.cache import UnifiedCacheManager
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.data_sources.polygon_client import PolygonClient
from src.gex.sample_data_gex import SampleDataGEXInterface
from src.validation.options_data_validator import OptionsDataValidator
from src.utils.reports_manager import reports_manager
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Initialize shared components
cache_manager = UnifiedCacheManager()
alpha_vantage_client = AlphaVantageGEXClient()
sample_gex = SampleDataGEXInterface()
validator = OptionsDataValidator()

# ===========================
# Data Retrieval Tools
# ===========================


def fetch_options_data(symbol: str = "SPY", trading_date: str = None, use_cache: bool = True):
    """
    Fetch options data from cache or API.

    Args:
        symbol: Stock symbol (SPY, SPX, etc.)
        trading_date: Date in YYYY-MM-DD format (defaults to latest)
        use_cache: Whether to check cache first

    Returns:
        Dictionary with options DataFrame and metadata
    """
    try:
        # Default to today if no date specified
        if not trading_date:
            trading_date = datetime.now().strftime('%Y-%m-%d')

        # Check cache first
        if use_cache:
            cached_data = cache_manager.get_options_data(symbol, trading_date)
            if cached_data is not None:
                logger.info(
                    f"Cache hit for {symbol} options on {trading_date}")
                return {
                    'status': 'success',
                    'source': 'cache',
                    'data': cached_data,
                    'symbol': symbol,
                    'date': trading_date
                }

        # Try Alpha Vantage API
        logger.info(f"Fetching {symbol} options from Alpha Vantage")
        api_data = alpha_vantage_client.fetch_historical_options(
            symbol, trading_date)

        if api_data is not None and not api_data.empty:
            # Cache the data
            cache_manager.store_options_data(symbol, trading_date, api_data)
            return {
                'status': 'success',
                'source': 'alpha_vantage',
                'data': api_data,
                'symbol': symbol,
                'date': trading_date
            }

        # Fallback to sample data
        logger.warning(f"No API data available, using sample data")
        sample_data = sample_gex.load_sample_options(symbol, trading_date)

        return {
            'status': 'success',
            'source': 'sample',
            'data': sample_data,
            'symbol': symbol,
            'date': trading_date
        }

    except Exception as e:
        logger.error(f"Error fetching options data: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def fetch_market_data(symbol: str = "SPY", start_date: str = None, end_date: str = None, use_cache: bool = True):
    """
    Fetch stock/market data from cache or API.

    Args:
        symbol: Stock symbol
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        use_cache: Whether to check cache first

    Returns:
        Dictionary with OHLCV DataFrame and metadata
    """
    try:
        # Default dates if not specified
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)
                          ).strftime('%Y-%m-%d')

        # Check cache
        if use_cache:
            cached_data = cache_manager.get_market_data(
                symbol, start_date, end_date)
            if cached_data is not None:
                logger.info(f"Cache hit for {symbol} market data")
                return {
                    'status': 'success',
                    'source': 'cache',
                    'data': cached_data,
                    'symbol': symbol
                }

        # Try Polygon if API key available
        polygon = PolygonClient()
        if polygon.test_connection():
            market_data = polygon.fetch_daily_bars(
                symbol, start_date, end_date)
            if market_data is not None:
                cache_manager.store_market_data(symbol, market_data)
                return {
                    'status': 'success',
                    'source': 'polygon',
                    'data': market_data,
                    'symbol': symbol
                }

        # Fallback to sample data
        logger.warning("Using sample market data")
        from src.cache import SampleDataLoader
        sample_loader = SampleDataLoader()
        sample_data = sample_loader.get_sample_stocks(symbol)

        return {
            'status': 'success',
            'source': 'sample',
            'data': sample_data,
            'symbol': symbol
        }

    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


# ===========================
# GEX Calculation Tools
# ===========================

def calculate_gamma_exposure(symbol: str = "SPY", trading_date: str = None, spot_price: float = None):
    """
    Calculate gamma exposure metrics for a symbol.

    Args:
        symbol: Stock symbol
        trading_date: Options data date
        spot_price: Current underlying price (auto-detect if None)

    Returns:
        Dictionary with GEX metrics
    """
    try:
        # Get options data
        options_result = fetch_options_data(symbol, trading_date)

        if options_result['status'] != 'success':
            return options_result

        options_df = options_result['data']

        # Calculate GEX using sample interface (works with any data)
        gex_results = sample_gex.calculate_gex_for_symbol(
            symbol,
            trading_date or datetime.now().strftime('%Y-%m-%d'),
            spot_price
        )

        # Save results to reports (not cache!)
        result_data = {
            'status': 'success',
            'symbol': symbol,
            'metrics': gex_results,
            'contracts_analyzed': len(options_df)
        }

        # Save to reports with demo flag for testing
        reports_manager.save_gex_results(
            symbol=symbol,
            results=result_data,
            trading_date=trading_date,
            is_demo=True  # Mark as demo for testing
        )

        return result_data

    except Exception as e:
        logger.error(f"Error calculating GEX: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def validate_options_data(options_df):
    """
    Validate options data quality.

    Args:
        options_df: DataFrame with options data

    Returns:
        Dictionary with validation results
    """
    try:
        validated_df, report = validator.validate(options_df)

        return {
            'status': 'success',
            'valid_contracts': len(validated_df),
            'original_contracts': len(options_df),
            'report': report,
            'data': validated_df
        }

    except Exception as e:
        logger.error(f"Error validating data: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


# ===========================
# Analysis Tools
# ===========================

def find_gex_flip_points(symbol: str = "SPY", trading_date: str = None):
    """
    Find gamma flip points where dealer hedging changes direction.

    Args:
        symbol: Stock symbol
        trading_date: Analysis date

    Returns:
        Dictionary with flip point analysis
    """
    try:
        # Calculate GEX
        gex_result = calculate_gamma_exposure(symbol, trading_date)

        if gex_result['status'] != 'success':
            return gex_result

        metrics = gex_result['metrics']

        # Extract flip points
        flip_analysis = {
            'status': 'success',
            'symbol': symbol,
            'flip_point': metrics.get('flip_point'),
            'current_spot': metrics.get('spot_price'),
            'net_gex': metrics.get('net_gex'),
            'interpretation': _interpret_flip_point(metrics)
        }

        # Save flip point analysis to reports (not cache!)
        reports_manager.save_pattern_analysis(
            pattern_type="flip_point_analysis",
            results=flip_analysis,
            symbol=symbol,
            is_demo=True  # Mark as demo for testing
        )

        return flip_analysis

    except Exception as e:
        logger.error(f"Error finding flip points: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def _interpret_flip_point(metrics: dict):
    """Interpret GEX flip point relative to spot price."""
    flip = metrics.get('flip_point')
    spot = metrics.get('spot_price')

    if not flip or not spot:
        return "Unable to determine flip point"

    distance_pct = ((flip - spot) / spot) * 100

    if abs(distance_pct) < 0.5:
        return f"Near flip point - expect high volatility"
    elif distance_pct > 0:
        return f"Flip point {distance_pct:.1f}% above - positive gamma regime"
    else:
        return f"Flip point {abs(distance_pct):.1f}% below - negative gamma regime"


# ===========================
# AutoGen Tool Registration
# ===========================

# Data retrieval tools
fetch_options_tool = FunctionTool(
    func=fetch_options_data,
    name="fetch_options_data",
    description="Fetch options chain data from cache or API for GEX analysis"
)

fetch_market_tool = FunctionTool(
    func=fetch_market_data,
    name="fetch_market_data",
    description="Fetch stock market OHLCV data from cache or API"
)

# Calculation tools
calculate_gex_tool = FunctionTool(
    func=calculate_gamma_exposure,
    name="calculate_gamma_exposure",
    description="Calculate gamma exposure metrics including net GEX and flip points"
)

# Note: validate_data_tool not exposed through AutoGen due to DataFrame parameter
# Validation happens internally within other tools

# Analysis tools
find_flip_points_tool = FunctionTool(
    func=find_gex_flip_points,
    name="find_gex_flip_points",
    description="Find gamma flip points where dealer hedging behavior changes"
)

# Tool collections by agent type
DATA_COLLECTION_TOOLS = [
    fetch_options_tool,
    fetch_market_tool
    # Note: validate_data_tool removed - can't pass DataFrame through AutoGen
]

GEX_CALCULATION_TOOLS = [
    calculate_gex_tool,
    find_flip_points_tool
]

PATTERN_ANALYSIS_TOOLS = [
    fetch_options_tool,
    calculate_gex_tool,
    find_flip_points_tool
]

# All tools combined
ALL_TOOLS = list(set(
    DATA_COLLECTION_TOOLS +
    GEX_CALCULATION_TOOLS +
    PATTERN_ANALYSIS_TOOLS
))
