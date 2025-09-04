"""
Clean Tools Configuration for GEX-LLM Analysis
Active tools: Alpha Vantage (options), Polygon.io (market data), Sample Data (fallback)

Organized by agent type for clean tool assignment and efficient agent workflows.
"""

# Standard library imports
import logging
from datetime import datetime, timedelta

# Third-party imports
from autogen_core.tools import FunctionTool
import pandas as pd

# Project imports - only tools actually used
from src.cache import UnifiedCacheManager
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.data_sources.polygon_client import PolygonClient
from src.gex.sample_data_gex import SampleDataGEXInterface
from src.validation.options_data_validator import OptionsDataValidator
from src.utils.reports_manager import reports_manager
from src.agents.market_intelligence import market_intelligence
from src.agents.gex_indicators import enhanced_gex_context, gex_volatility_regime

logger = logging.getLogger(__name__)

##################################
# Agent Types
##################################

DATA_AGENT = "data"
GEX_AGENT = "gex"
ANALYSIS_AGENT = "analysis"
ALL_AGENTS = [DATA_AGENT, GEX_AGENT, ANALYSIS_AGENT]

# Initialize shared components
cache_manager = UnifiedCacheManager()
alpha_vantage_client = AlphaVantageGEXClient()
sample_gex = SampleDataGEXInterface()
validator = OptionsDataValidator()

##################################
# Data Retrieval Tools
##################################


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

def calculate_gamma_exposure(symbol: str = "SPY", trading_date: str = None, spot_price: float = None, use_cache: bool = True):
    """
    Calculate gamma exposure metrics for a symbol with caching support.

    Args:
        symbol: Stock symbol
        trading_date: Options data date
        spot_price: Current underlying price (auto-detect if None)
        use_cache: Whether to use GEX caching (default True)

    Returns:
        Dictionary with GEX metrics
    """
    try:
        # Default to current date if not specified
        if not trading_date:
            trading_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use cached GEX calculation if enabled
        if use_cache:
            cached_gex = cache_manager.get_or_calculate_gex(symbol, trading_date)
            
            if cached_gex:
                # Add cache metadata and return
                result_data = {
                    'status': 'success',
                    'symbol': symbol,
                    'metrics': cached_gex,
                    'cache_hit': cached_gex.get('_cache_info', {}).get('cache_hit', True),
                    'calculation_method': 'cached'
                }
                
                logger.info(f"Returned cached GEX for {symbol} {trading_date}")
                return result_data
        
        # Fallback to direct calculation if cache disabled or failed
        # Get options data
        options_result = fetch_options_data(symbol, trading_date)

        if options_result['status'] != 'success':
            return options_result

        options_df = options_result['data']

        # Calculate GEX using sample interface (works with any data)
        gex_results = sample_gex.calculate_gex_for_symbol(
            symbol,
            trading_date,
            spot_price
        )

        # Save results to reports (not cache!)
        result_data = {
            'status': 'success',
            'symbol': symbol,
            'metrics': gex_results,
            'contracts_analyzed': len(options_df),
            'cache_hit': False,
            'calculation_method': 'direct'
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


##################################
# Market Intelligence Tools
##################################

def analyze_query_intent(query: str):
    """
    Analyze user query to extract trading intent and market context.
    
    Args:
        query: User's natural language query
        
    Returns:
        Dictionary with extracted ticker, sector, dates, and context
    """
    try:
        # Extract query details using market intelligence
        details = market_intelligence.extract_query_details(query)
        
        # Enhance with sector context
        if details['sector']:
            related_symbols = market_intelligence.get_related_symbols(details['sector'])
            details['related_symbols'] = related_symbols
        
        # Add sector identification for ticker
        if details['ticker'] and not details['sector']:
            identified_sector = market_intelligence.identify_sector(details['ticker'])
            if identified_sector:
                details['sector'] = identified_sector
                details['related_symbols'] = market_intelligence.get_related_symbols(identified_sector)
        
        return {
            'status': 'success',
            'intent': details,
            'recommendations': _generate_analysis_recommendations(details)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing query intent: {e}")
        return {
            'status': 'error',
            'message': f"Query analysis failed: {str(e)}",
            'intent': {'ticker': 'SPY', 'start_date': '-5d'}
        }

def _generate_analysis_recommendations(details: dict) -> dict:
    """Generate analysis recommendations based on query details."""
    recommendations = {
        'primary_analysis': 'gamma_exposure',
        'secondary_metrics': ['flip_points', 'net_gex'],
        'market_context': []
    }
    
    # Sector-specific recommendations
    if details.get('sector') == 'technology':
        recommendations['market_context'].append('High volatility sector - focus on gamma flip dynamics')
    elif details.get('sector') == 'finance':
        recommendations['market_context'].append('Interest rate sensitive - monitor GEX around Fed events')
    elif details.get('sector') == 'energy':
        recommendations['market_context'].append('Commodity driven - correlate with oil volatility')
    
    # Time-based recommendations
    if details.get('anchor'):
        if details['anchor'] == 'earnings':
            recommendations['market_context'].append('Earnings period - expect elevated IV and gamma')
        elif details['anchor'] == 'fomc':
            recommendations['market_context'].append('FOMC period - focus on zero-gamma levels')
    
    return recommendations

def analyze_gex_technical_confluence(symbol: str = "SPY", trading_date: str = None):
    """
    Analyze technical indicators in confluence with GEX levels.
    
    Args:
        symbol: Stock symbol
        trading_date: Analysis date
        
    Returns:
        Dictionary with technical-GEX confluence analysis
    """
    try:
        # Get market data
        market_result = fetch_market_data(symbol, trading_date)
        if market_result['status'] != 'success':
            return market_result
        
        market_data = market_result['data']
        
        # Get GEX calculation
        gex_result = calculate_gamma_exposure(symbol, trading_date)
        gex_data = None
        if gex_result['status'] == 'success':
            gex_data = gex_result
        
        # Analyze technical confluence with GEX
        confluence_analysis = enhanced_gex_context(market_data, gex_data)
        
        # Add volatility regime assessment
        vol_regime = gex_volatility_regime(market_data)
        
        # Save analysis to reports
        analysis_results = {
            'symbol': symbol,
            'trading_date': trading_date,
            'confluence_analysis': confluence_analysis,
            'volatility_regime': vol_regime,
            'gex_summary': gex_data.get('metrics', {}) if gex_data else None
        }
        
        reports_manager.save_analysis_results(
            symbol, analysis_results, trading_date, 
            analysis_type='technical_gex_confluence'
        )
        
        return {
            'status': 'success',
            'symbol': symbol,
            'analysis': confluence_analysis,
            'volatility_regime': vol_regime,
            'key_insights': _generate_confluence_insights(confluence_analysis, vol_regime)
        }
        
    except Exception as e:
        logger.error(f"Error in GEX technical confluence analysis: {e}")
        return {
            'status': 'error',
            'message': f"Technical confluence analysis failed: {str(e)}"
        }

def _generate_confluence_insights(confluence: dict, vol_regime: dict) -> list:
    """Generate key insights from technical-GEX confluence analysis."""
    insights = []
    
    # Volatility insights
    if vol_regime.get('volatility_regime') == 'low_volatility':
        insights.append("Low volatility regime detected - gamma effects likely amplified")
    elif vol_regime.get('volatility_regime') == 'high_volatility':
        insights.append("High volatility regime - reduced gamma sensitivity due to wide spreads")
    
    # Technical level insights
    tech_levels = confluence.get('technical_levels', {})
    if abs(tech_levels.get('nearest_distance', 100)) < 1:
        nearest = tech_levels.get('nearest_technical_level', 'unknown')
        insights.append(f"Price near key technical level: {nearest}")
    
    # GEX correlation insights
    correlations = tech_levels.get('gex_correlations', [])
    if correlations:
        insights.append(f"Technical-GEX convergence: {len(correlations)} levels aligned")
    
    # Trading recommendations
    recommendations = confluence.get('trading_recommendations', [])
    insights.extend(recommendations)
    
    return insights

def process_historical_gex_range(symbol: str = "SPY", start_date: str = None, end_date: str = None, max_workers: int = 4):
    """
    Process GEX calculations for a date range using concurrent processing.
    
    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM-DD), defaults to 30 days ago
        end_date: End date (YYYY-MM-DD), defaults to today
        max_workers: Number of concurrent workers
        
    Returns:
        Dictionary with processing results and historical GEX data
    """
    try:
        # Default date range if not provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_dt = datetime.now() - timedelta(days=30)
            start_date = start_dt.strftime('%Y-%m-%d')
        
        # Initialize concurrent processor
        from src.cache.concurrent_gex_processor import ConcurrentGEXProcessor
        processor = ConcurrentGEXProcessor(max_workers=max_workers, unified_cache_manager=cache_manager)
        
        # Process the date range
        processing_results = processor.process_symbol_date_range(
            symbol=symbol,
            start_date=start_date, 
            end_date=end_date,
            force_recalculate=False
        )
        
        # Get historical flip points for analysis
        historical_gex = cache_manager.gex_cache.get_historical_flip_points(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        # Save comprehensive results to reports
        analysis_results = {
            'symbol': symbol,
            'date_range': f"{start_date} to {end_date}",
            'processing_summary': processing_results,
            'historical_data': historical_gex.to_dict('records') if not historical_gex.empty else [],
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        reports_manager.save_analysis_results(
            symbol, analysis_results, end_date,
            analysis_type='historical_gex_range'
        )
        
        # Shutdown processor
        processor.shutdown(wait=True)
        
        return {
            'status': 'success',
            'symbol': symbol,
            'date_range': f"{start_date} to {end_date}",
            'processing_results': processing_results,
            'historical_flip_points': len(historical_gex) if not historical_gex.empty else 0,
            'recommendations': _generate_historical_recommendations(processing_results, historical_gex)
        }
        
    except Exception as e:
        logger.error(f"Error in historical GEX range processing: {e}")
        return {
            'status': 'error',
            'message': f"Historical GEX processing failed: {str(e)}"
        }

def _generate_historical_recommendations(processing_results: dict, historical_data: pd.DataFrame) -> list:
    """Generate recommendations based on historical GEX analysis."""
    recommendations = []
    
    # Processing efficiency insights
    if processing_results.get('cache_hits', 0) > processing_results.get('new_calculations', 0):
        recommendations.append("High cache hit rate - GEX caching system performing well")
    
    # Historical pattern insights
    if not historical_data.empty and len(historical_data) > 5:
        flip_points = historical_data['flip_point'].dropna()
        if not flip_points.empty:
            avg_flip = flip_points.mean()
            flip_std = flip_points.std()
            current_flip = flip_points.iloc[-1] if len(flip_points) > 0 else None
            
            if current_flip and abs(current_flip - avg_flip) > flip_std:
                if current_flip > avg_flip:
                    recommendations.append(f"Current flip point ({current_flip:.2f}) above historical average - bullish gamma regime")
                else:
                    recommendations.append(f"Current flip point ({current_flip:.2f}) below historical average - bearish gamma regime")
    
    # Processing performance insights
    total_dates = processing_results.get('total_dates', 0)
    successful = processing_results.get('successful', 0)
    if total_dates > 0:
        success_rate = (successful / total_dates) * 100
        if success_rate > 90:
            recommendations.append("High processing success rate - data quality excellent")
        elif success_rate < 70:
            recommendations.append("Lower processing success rate - check data availability")
    
    return recommendations


##################################
# AutoGen Tool Registration
##################################

# Data retrieval tools with agent type assignment
fetch_options_tool = FunctionTool(
    func=fetch_options_data,
    name="fetch_options_data",
    description="Fetch options chain data from cache or API for GEX analysis"
)
fetch_options_tool.agent_types = [DATA_AGENT]

fetch_market_tool = FunctionTool(
    func=fetch_market_data,
    name="fetch_market_data",
    description="Fetch stock market OHLCV data from cache or API"
)
fetch_market_tool.agent_types = [DATA_AGENT]

# GEX calculation tools
calculate_gex_tool = FunctionTool(
    func=calculate_gamma_exposure,
    name="calculate_gamma_exposure",
    description="Calculate gamma exposure metrics including net GEX and flip points"
)
calculate_gex_tool.agent_types = [GEX_AGENT]

# Analysis tools
find_flip_points_tool = FunctionTool(
    func=find_gex_flip_points,
    name="find_gex_flip_points",
    description="Find gamma flip points where dealer hedging behavior changes"
)
find_flip_points_tool.agent_types = [ANALYSIS_AGENT]

# Market intelligence tools
query_analysis_tool = FunctionTool(
    func=analyze_query_intent,
    name="analyze_query_intent",
    description="Analyze user query to extract ticker, sector, dates, and trading context for GEX analysis"
)
query_analysis_tool.agent_types = [ANALYSIS_AGENT, DATA_AGENT]

# Technical confluence tools
technical_confluence_tool = FunctionTool(
    func=analyze_gex_technical_confluence,
    name="analyze_gex_technical_confluence", 
    description="Analyze technical indicators in confluence with GEX levels for enhanced trading insights"
)
technical_confluence_tool.agent_types = [ANALYSIS_AGENT]

# Historical GEX processing tools
historical_gex_tool = FunctionTool(
    func=process_historical_gex_range,
    name="process_historical_gex_range",
    description="Process GEX calculations for date range using high-performance concurrent processing and caching"
)
historical_gex_tool.agent_types = [GEX_AGENT, ANALYSIS_AGENT]

##################################
# Tool Collections by Agent Type
##################################

# DATA_AGENT tools - Data retrieval and caching
_data_tools_raw = [
    fetch_options_tool,     # Options chain data from Alpha Vantage or cache
    fetch_market_tool,      # Market data from Polygon.io or cache
    query_analysis_tool,    # Query intent analysis with market intelligence
    # Note: validate_data_tool removed - can't pass DataFrame through AutoGen
]
DATA_COLLECTION_TOOLS = [tool for tool in _data_tools_raw if tool is not None]

# GEX_AGENT tools - Gamma exposure calculations
_gex_tools_raw = [
    calculate_gex_tool,     # Core GEX calculations with Black-Scholes
    find_flip_points_tool,  # Flip point identification and analysis
    historical_gex_tool,    # Historical range processing with caching
]
GEX_CALCULATION_TOOLS = [tool for tool in _gex_tools_raw if tool is not None]

# ANALYSIS_AGENT tools - Pattern detection and analysis
_analysis_tools_raw = [
    fetch_options_tool,         # Data access for analysis
    calculate_gex_tool,         # GEX calculations for patterns
    find_flip_points_tool,      # Flip point analysis for patterns
    query_analysis_tool,        # Market intelligence and query parsing
    technical_confluence_tool,  # Technical-GEX confluence analysis
    historical_gex_tool,        # Historical GEX range analysis
]
ANALYSIS_TOOLS = [tool for tool in _analysis_tools_raw if tool is not None]

# All tools combined (filter out None values from conditional imports)
ALL_TOOLS = list(set(
    tool for tool in (
        DATA_COLLECTION_TOOLS +
        GEX_CALCULATION_TOOLS +
        ANALYSIS_TOOLS
    ) if tool is not None
))

# Tool dispatcher dictionary for efficient lookup by name
ALL_TOOLS_DICT = {tool.name: tool for tool in ALL_TOOLS if tool is not None}

##################################
# Helper function to get tools for a specific agent type
##################################


def get_tools_for_agent(agent_type):
    """
    Get the list of tools that should be used by a specific agent type.

    Args:
        agent_type: Type of agent (e.g., 'data', 'gex', 'analysis')

    Returns:
        List of FunctionTool objects appropriate for the agent type
    """
    if agent_type == DATA_AGENT:
        return DATA_COLLECTION_TOOLS
    elif agent_type == GEX_AGENT:
        return GEX_CALCULATION_TOOLS
    elif agent_type == ANALYSIS_AGENT:
        return ANALYSIS_TOOLS
    else:
        # Return all tools if agent type is unknown
        return ALL_TOOLS
