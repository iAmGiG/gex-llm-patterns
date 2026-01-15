"""
Clean Tools Configuration for GEX-LLM Analysis
Active tools: Alpha Vantage Premium (options & market data), Unified Cache

IMPORTANT: These are direct Python function calls, NOT LLM calls.
- No token limits needed for tool functions
- Tools fetch data and perform calculations directly
- Only the market mechanics analysis uses LLM (O3-mini with 4000 tokens)

Organized by agent type for clean tool assignment and efficient agent workflows.
"""

# Standard library imports
import logging
import os

import pandas as pd

# Project imports for date handling
from src.utils.date_utils import (
    add_business_days,
    calculate_duration_minutes,
    format_for_filename,
    is_valid_trading_date,
    parse_date_string,
    today_str,
)


def filter_options_data(df: pd.DataFrame, min_volume: int = 1, min_oi: int = 1) -> pd.DataFrame:
    """Filter options data to remove strikes with zero or low volume/open interest.

    Args:
        df: Options DataFrame
        min_volume: Minimum volume threshold (default 1 to remove 0 volume)
        min_oi: Minimum open interest threshold (default 1 to remove 0 OI)

    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df

    original_count = len(df)

    # Filter by volume if column exists
    if "volume" in df.columns:
        df = df[df["volume"] >= min_volume]

    # Filter by open interest if column exists
    if "open_interest" in df.columns:
        df = df[df["open_interest"] >= min_oi]

    filtered_count = len(df)
    if filtered_count < original_count:
        logger.info(
            f"Filtered options data: {original_count} -> {filtered_count} contracts "
            f"(removed {original_count - filtered_count} with volume < {min_volume} or OI < {min_oi})"
        )

    return df


import pandas as pd

# Third-party imports
from autogen_core.tools import FunctionTool

# Project imports - only tools actually used
from gex_db_infrastructure.cache import SQLiteOptionsManager, PostgreSQLOptionsManager, UnifiedCacheManager
from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient

# from gex_db_infrastructure.data_sources.polygon_client import PolygonClient  # Using Alpha Vantage Premium instead
from gex_db_infrastructure.gex.live_gex_interface import LiveGEXInterface
from src.utils.indicator_library import enhanced_gex_context, gex_volatility_regime
from src.utils.market_intelligence import market_intelligence
from src.utils.unified_reports_manager import reports_manager
from gex_db_infrastructure.validation.options_data_validator import OptionsDataValidator

logger = logging.getLogger(__name__)

##################################
# Agent Types
##################################

DATA_AGENT = "data"
GEX_AGENT = "gex"
ANALYSIS_AGENT = "analysis"
ALL_AGENTS = [DATA_AGENT, GEX_AGENT, ANALYSIS_AGENT]

# Initialize shared components
# Use PostgreSQL by default (migrated from SQLite)
# Issue #16: Validation enabled at ingress by default
# UnifiedCacheManager is used for market data and GEX calculations (not options)
options_db = PostgreSQLOptionsManager()  # Primary database for options data
cache_manager = UnifiedCacheManager()  # For market data and GEX (not options)
alpha_vantage_client = AlphaVantageGEXClient()
live_gex = LiveGEXInterface()
validator = OptionsDataValidator()  # Used for GEX calculation data cleaning (different from ingress validation)

##################################
# Data Retrieval Tools
##################################


def fetch_options_data(symbol: str = "SPY", trading_date: str = None, use_cache: bool = True):
    """Fetch options data from SQLite database or API.

    Data source priority (Issue #180: SQLite is now primary and only storage):
    1. SQLite database (options_historical.db) - Primary storage
    2. Alpha Vantage API - Live fetch and store in SQLite

    Args:
        symbol: Stock symbol (SPY, SPX, etc.)
        trading_date: Date in YYYY-MM-DD format (defaults to latest)
        use_cache: Whether to check cache/database first

    Returns:
        Dictionary with options DataFrame and metadata
    """
    try:
        # Default to today if no date specified
        if not trading_date:
            trading_date = today_str()

        # Validate the date
        if not is_valid_trading_date(trading_date):
            logger.error(f"Invalid trading date: {trading_date} (future date or non-trading day)")
            return {
                "status": "error",
                "message": f"Invalid trading date: {trading_date}. Must be a past/current business day.",
            }

        if use_cache:
            # 1. Check SQLite database first (primary storage)
            sqlite_data = options_db.get_options_chain(symbol, trading_date)
            if sqlite_data is not None and not sqlite_data.empty:
                logger.info(f"SQLite hit for {symbol} options on {trading_date}")
                filtered_data = filter_options_data(sqlite_data)
                return {
                    "status": "success",
                    "source": "sqlite",
                    "data": filtered_data,
                    "symbol": symbol,
                    "date": trading_date,
                }

            # Issue #180: Legacy pickle fallback removed - SQLite is now primary and only storage

        # 2. Try Alpha Vantage API
        logger.info(f"Fetching {symbol} options from Alpha Vantage")
        api_data = alpha_vantage_client.fetch_historical_options(symbol, trading_date)

        if api_data is not None and not api_data.empty:
            # Store in SQLite (primary) - no longer storing in pickle
            options_db.store_options_chain(symbol, trading_date, api_data)
            filtered_data = filter_options_data(api_data)
            return {
                "status": "success",
                "source": "alpha_vantage",
                "data": filtered_data,
                "symbol": symbol,
                "date": trading_date,
            }

        # No data available
        logger.error(f"No options data available for {symbol} on {trading_date}")
        return {"status": "error", "message": f"No options data available for {symbol} on {trading_date}"}

    except Exception as e:
        logger.error(f"Error fetching options data: {e}")
        return {"status": "error", "message": str(e)}


def fetch_market_data(symbol: str = "SPY", start_date: str = None, end_date: str = None, use_cache: bool = True):
    """Fetch stock/market data from cache or API.

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
            end_date = today_str()
        if not start_date:
            start_date = add_business_days(end_date, -30)

        # Check cache
        if use_cache:
            cached_data = cache_manager.get_market_data(symbol, start_date, end_date)
            if cached_data is not None:
                logger.info(f"Cache hit for {symbol} market data")
                return {"status": "success", "source": "cache", "data": cached_data, "symbol": symbol}

        # Try Alpha Vantage Premium for market data
        logger.info(f"Fetching {symbol} market data from Alpha Vantage Premium")
        market_data = alpha_vantage_client.fetch_underlying_data(symbol, start_date, end_date)

        if market_data is not None and not market_data.empty:
            # Cache the data
            cache_manager.store_market_data(symbol, market_data)
            return {"status": "success", "source": "alpha_vantage_premium", "data": market_data, "symbol": symbol}

        # No fallback to sample data - return error
        logger.error(f"No live market data available for {symbol}")
        return {"status": "error", "message": f"No live market data available for {symbol}"}

    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return {"status": "error", "message": str(e)}


# ===========================
# GEX Calculation Tools
# ===========================


def calculate_gamma_exposure(
    symbol: str = "SPY", trading_date: str = None, spot_price: float = None, use_cache: bool = True
):
    """Calculate gamma exposure metrics for a symbol with caching support.

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
            trading_date = today_str()

        # Use cached GEX calculation if enabled
        if use_cache:
            cached_gex = cache_manager.get_or_calculate_gex(symbol, trading_date)

            if cached_gex:
                # Add cache metadata and return
                result_data = {
                    "status": "success",
                    "symbol": symbol,
                    "metrics": cached_gex,
                    "cache_hit": cached_gex.get("_cache_info", {}).get("cache_hit", True),
                    "calculation_method": "cached",
                }

                logger.info(f"Returned cached GEX for {symbol} {trading_date}")
                return result_data

        # Fallback to direct calculation if cache disabled or failed
        # Get options data
        options_result = fetch_options_data(symbol, trading_date)

        if options_result["status"] != "success":
            return options_result

        options_df = options_result["data"]

        # Calculate GEX using live interface (works with any data)
        gex_results = live_gex.calculate_gex_for_symbol(
            symbol=symbol,
            trading_date=trading_date,
            spot_price=spot_price,
            options_data=options_df,  # Pass the live fetched data
        )

        # Save results to reports (not cache!)
        result_data = {
            "status": "success",
            "symbol": symbol,
            "metrics": gex_results,
            "contracts_analyzed": len(options_df),
            "cache_hit": False,
            "calculation_method": "direct",
        }

        # Save to reports with demo flag for testing
        reports_manager.save_gex_results(
            symbol=symbol, results=result_data, trading_date=trading_date, is_demo=True  # Mark as demo for testing
        )

        return result_data

    except Exception as e:
        logger.error(f"Error calculating GEX: {e}")
        return {"status": "error", "message": str(e)}


def validate_options_data(options_df):
    """Validate options data quality.

    Args:
        options_df: DataFrame with options data

    Returns:
        Dictionary with validation results
    """
    try:
        validated_df, report = validator.validate(options_df)

        return {
            "status": "success",
            "valid_contracts": len(validated_df),
            "original_contracts": len(options_df),
            "report": report,
            "data": validated_df,
        }

    except Exception as e:
        logger.error(f"Error validating data: {e}")
        return {"status": "error", "message": str(e)}


# ===========================
# Analysis Tools
# ===========================


def fetch_algo_time_analysis(
    symbol: str = "SPY",
    start_date: str = None,
    end_date: str = None,
    algo_time: str = "15:30:00",
    weekday_filter: str = None,
):
    """Fetch data for specific algo times with flexible parameters.

    Perfect for advanced plays that happen at different algo times like 3:50 PM.
    Supports both 0DTE tickers (SPY/QQQ daily) and regular tickers (Friday only).

    Args:
        symbol: Trading symbol (SPY/QQQ have daily 0DTE, others Friday only)
        start_date: Start date (YYYY-MM-DD), defaults to 5 days ago
        end_date: End date (YYYY-MM-DD), defaults to today
        algo_time: Algo time to analyze (15:30:00, 15:50:00, etc.) or name like 'gamma_350pm'
        weekday_filter: Specific weekday ('monday', 'friday', etc.) or None for smart detection

    Returns:
        Dictionary with algo time analysis data
    """
    try:
        from src.data.market_data_system import UnifiedDataSystem
        from src.utils.date_utils import get_processed_date_range

        # Initialize data system
        data_system = UnifiedDataSystem()

        # Process date range
        if not start_date or not end_date:
            start_date, end_date = get_processed_date_range(start_date, end_date, default_days_back=14)

        # Handle algo time names vs raw times
        if ":" not in algo_time:
            # It's a name like 'gamma_350pm'
            algo_time = data_system.get_algo_time_from_config(algo_time)

        # Convert weekday filter to number if specified
        weekday_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4}
        weekday_num = None
        if weekday_filter:
            weekday_num = weekday_map.get(weekday_filter.lower())

        # Fetch algo time data
        algo_data = data_system.get_algo_time_data(
            start_date=start_date, end_date=end_date, symbol=symbol, algo_time=algo_time, weekday=weekday_num
        )

        # Get symbol info for context
        has_daily_0dte = symbol.upper() in ["SPY", "QQQ"]

        return {
            "success": True,
            "symbol": symbol,
            "algo_time": algo_time,
            "date_range": f"{start_date} to {end_date}",
            "weekday_filter": weekday_filter,
            "has_daily_0dte": has_daily_0dte,
            "data_points": len(algo_data),
            "algo_data": algo_data,
            "analysis_notes": {
                "symbol_type": "Daily 0DTE available" if has_daily_0dte else "Friday expiration only",
                "recommended_times": [
                    "15:30:00 (3:30 PM - Standard gamma time)",
                    "15:40:00 (3:40 PM - Mid-session)",
                    "15:50:00 (3:50 PM - Advanced plays, late algo)",
                    "16:00:00 (Market close)",
                ],
            },
        }

    except Exception as e:
        logger.error(f"Error in fetch_algo_time_analysis: {e}")
        return {"success": False, "error": f"Algo time analysis failed: {e}", "symbol": symbol, "algo_time": algo_time}


def find_gex_flip_points(symbol: str = "SPY", trading_date: str = None):
    """Find gamma flip points where dealer hedging changes direction.

    Args:
        symbol: Stock symbol
        trading_date: Analysis date

    Returns:
        Dictionary with flip point analysis
    """
    try:
        # Calculate GEX
        gex_result = calculate_gamma_exposure(symbol, trading_date)

        if gex_result["status"] != "success":
            return gex_result

        metrics = gex_result["metrics"]

        # Extract flip points
        flip_analysis = {
            "status": "success",
            "symbol": symbol,
            "flip_point": metrics.get("flip_point"),
            "current_spot": metrics.get("spot_price"),
            "net_gex": metrics.get("net_gex"),
            "interpretation": _interpret_flip_point(metrics),
        }

        # Save flip point analysis to reports (not cache!)
        reports_manager.save_pattern_analysis(
            pattern_type="flip_point_analysis",
            results=flip_analysis,
            symbol=symbol,
            is_demo=True,  # Mark as demo for testing
        )

        return flip_analysis

    except Exception as e:
        logger.error(f"Error finding flip points: {e}")
        return {"status": "error", "message": str(e)}


def _interpret_flip_point(metrics: dict):
    """Interpret GEX flip point relative to spot price."""
    flip = metrics.get("flip_point")
    spot = metrics.get("spot_price")

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
    """Analyze user query to extract trading intent and market context.

    Args:
        query: User's natural language query

    Returns:
        Dictionary with extracted ticker, sector, dates, and context
    """
    try:
        # Extract query details using market intelligence
        details = market_intelligence.extract_query_details(query)

        # Enhance with sector context
        if details["sector"]:
            related_symbols = market_intelligence.get_related_symbols(details["sector"])
            details["related_symbols"] = related_symbols

        # Add sector identification for ticker
        if details["ticker"] and not details["sector"]:
            identified_sector = market_intelligence.identify_sector(details["ticker"])
            if identified_sector:
                details["sector"] = identified_sector
                details["related_symbols"] = market_intelligence.get_related_symbols(identified_sector)

        return {"status": "success", "intent": details, "recommendations": _generate_analysis_recommendations(details)}

    except Exception as e:
        logger.error(f"Error analyzing query intent: {e}")
        return {
            "status": "error",
            "message": f"Query analysis failed: {str(e)}",
            "intent": {"ticker": "SPY", "start_date": "-5d"},
        }


def _generate_analysis_recommendations(details: dict) -> dict:
    """Generate analysis recommendations based on query details."""
    recommendations = {
        "primary_analysis": "gamma_exposure",
        "secondary_metrics": ["flip_points", "net_gex"],
        "market_context": [],
    }

    # Sector-specific recommendations
    if details.get("sector") == "technology":
        recommendations["market_context"].append("High volatility sector - focus on gamma flip dynamics")
    elif details.get("sector") == "finance":
        recommendations["market_context"].append("Interest rate sensitive - monitor GEX around Fed events")
    elif details.get("sector") == "energy":
        recommendations["market_context"].append("Commodity driven - correlate with oil volatility")

    # Time-based recommendations
    if details.get("anchor"):
        if details["anchor"] == "earnings":
            recommendations["market_context"].append("Earnings period - expect elevated IV and gamma")
        elif details["anchor"] == "fomc":
            recommendations["market_context"].append("FOMC period - focus on zero-gamma levels")

    return recommendations


def analyze_gex_technical_confluence(symbol: str = "SPY", trading_date: str = None):
    """Analyze technical indicators in confluence with GEX levels.

    Args:
        symbol: Stock symbol
        trading_date: Analysis date

    Returns:
        Dictionary with technical-GEX confluence analysis
    """
    try:
        # Get market data
        market_result = fetch_market_data(symbol, trading_date)
        if market_result["status"] != "success":
            return market_result

        market_data = market_result["data"]

        # Get GEX calculation
        gex_result = calculate_gamma_exposure(symbol, trading_date)
        gex_data = None
        if gex_result["status"] == "success":
            gex_data = gex_result

        # Analyze technical confluence with GEX
        confluence_analysis = enhanced_gex_context(market_data, gex_data)

        # Add volatility regime assessment
        vol_regime = gex_volatility_regime(market_data)

        # Save analysis to reports
        analysis_results = {
            "symbol": symbol,
            "trading_date": trading_date,
            "confluence_analysis": confluence_analysis,
            "volatility_regime": vol_regime,
            "gex_summary": gex_data.get("metrics", {}) if gex_data else None,
        }

        reports_manager.save_analysis_results(
            symbol, analysis_results, trading_date, analysis_type="technical_gex_confluence"
        )

        return {
            "status": "success",
            "symbol": symbol,
            "analysis": confluence_analysis,
            "volatility_regime": vol_regime,
            "key_insights": _generate_confluence_insights(confluence_analysis, vol_regime),
        }

    except Exception as e:
        logger.error(f"Error in GEX technical confluence analysis: {e}")
        return {"status": "error", "message": f"Technical confluence analysis failed: {str(e)}"}


def _generate_confluence_insights(confluence: dict, vol_regime: dict) -> list:
    """Generate key insights from technical-GEX confluence analysis."""
    insights = []

    # Volatility insights
    if vol_regime.get("volatility_regime") == "low_volatility":
        insights.append("Low volatility regime detected - gamma effects likely amplified")
    elif vol_regime.get("volatility_regime") == "high_volatility":
        insights.append("High volatility regime - reduced gamma sensitivity due to wide spreads")

    # Technical level insights
    tech_levels = confluence.get("technical_levels", {})
    if abs(tech_levels.get("nearest_distance", 100)) < 1:
        nearest = tech_levels.get("nearest_technical_level", "unknown")
        insights.append(f"Price near key technical level: {nearest}")

    # GEX correlation insights
    correlations = tech_levels.get("gex_correlations", [])
    if correlations:
        insights.append(f"Technical-GEX convergence: {len(correlations)} levels aligned")

    # Trading recommendations
    recommendations = confluence.get("trading_recommendations", [])
    insights.extend(recommendations)

    return insights


def process_historical_gex_range(
    symbol: str = "SPY", start_date: str = None, end_date: str = None, max_workers: int = 4
):
    """Process GEX calculations for a date range using concurrent processing.

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
            end_date = today_str()
        if not start_date:
            start_date = add_business_days(end_date, -30)

        # Initialize concurrent processor
        from gex_db_infrastructure.cache.concurrent_gex_processor import ConcurrentGEXProcessor

        processor = ConcurrentGEXProcessor(max_workers=max_workers, unified_cache_manager=cache_manager)

        # Process the date range
        processing_results = processor.process_symbol_date_range(
            symbol=symbol, start_date=start_date, end_date=end_date, force_recalculate=False
        )

        # Get historical flip points for analysis
        historical_gex = cache_manager.gex_cache.get_historical_flip_points(
            symbol=symbol, start_date=start_date, end_date=end_date
        )

        # Save comprehensive results to reports
        analysis_results = {
            "symbol": symbol,
            "date_range": f"{start_date} to {end_date}",
            "processing_summary": processing_results,
            "historical_data": historical_gex.to_dict("records") if not historical_gex.empty else [],
            "analysis_timestamp": format_for_filename(),
        }

        reports_manager.save_analysis_results(symbol, analysis_results, end_date, analysis_type="historical_gex_range")

        # Shutdown processor
        processor.shutdown(wait=True)

        return {
            "status": "success",
            "symbol": symbol,
            "date_range": f"{start_date} to {end_date}",
            "processing_results": processing_results,
            "historical_flip_points": len(historical_gex) if not historical_gex.empty else 0,
            "recommendations": _generate_historical_recommendations(processing_results, historical_gex),
        }

    except Exception as e:
        logger.error(f"Error in historical GEX range processing: {e}")
        return {"status": "error", "message": f"Historical GEX processing failed: {str(e)}"}


def _generate_historical_recommendations(processing_results: dict, historical_data: pd.DataFrame) -> list:
    """Generate recommendations based on historical GEX analysis."""
    recommendations = []

    # Processing efficiency insights
    if processing_results.get("cache_hits", 0) > processing_results.get("new_calculations", 0):
        recommendations.append("High cache hit rate - GEX caching system performing well")

    # Historical pattern insights
    if not historical_data.empty and len(historical_data) > 5:
        flip_points = historical_data["flip_point"].dropna()
        if not flip_points.empty:
            avg_flip = flip_points.mean()
            flip_std = flip_points.std()
            current_flip = flip_points.iloc[-1] if len(flip_points) > 0 else None

            if current_flip and abs(current_flip - avg_flip) > flip_std:
                if current_flip > avg_flip:
                    recommendations.append(
                        f"Current flip point ({current_flip:.2f}) above historical average - bullish gamma regime"
                    )
                else:
                    recommendations.append(
                        f"Current flip point ({current_flip:.2f}) below historical average - bearish gamma regime"
                    )

    # Processing performance insights
    total_dates = processing_results.get("total_dates", 0)
    successful = processing_results.get("successful", 0)
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
    description="Fetch options chain data from cache or API for GEX analysis",
)
fetch_options_tool.agent_types = [DATA_AGENT]

fetch_market_tool = FunctionTool(
    func=fetch_market_data, name="fetch_market_data", description="Fetch stock market OHLCV data from cache or API"
)
fetch_market_tool.agent_types = [DATA_AGENT]

# GEX calculation tools
calculate_gex_tool = FunctionTool(
    func=calculate_gamma_exposure,
    name="calculate_gamma_exposure",
    description="Calculate gamma exposure metrics including net GEX and flip points",
)
calculate_gex_tool.agent_types = [GEX_AGENT]

# Analysis tools
find_flip_points_tool = FunctionTool(
    func=find_gex_flip_points,
    name="find_gex_flip_points",
    description="Find gamma flip points where dealer hedging behavior changes",
)
find_flip_points_tool.agent_types = [ANALYSIS_AGENT]

# Flexible algo time analysis tool
algo_time_analysis_tool = FunctionTool(
    func=fetch_algo_time_analysis,
    name="fetch_algo_time_analysis",
    description="Fetch data for specific algo times (3:30, 3:50, etc.) with support for 0DTE vs Friday-only symbols",
)
algo_time_analysis_tool.agent_types = [ANALYSIS_AGENT, DATA_AGENT]

# Market intelligence tools
query_analysis_tool = FunctionTool(
    func=analyze_query_intent,
    name="analyze_query_intent",
    description="Analyze user query to extract ticker, sector, dates, and trading context for GEX analysis",
)
query_analysis_tool.agent_types = [ANALYSIS_AGENT, DATA_AGENT]

# Technical confluence tools
technical_confluence_tool = FunctionTool(
    func=analyze_gex_technical_confluence,
    name="analyze_gex_technical_confluence",
    description="Analyze technical indicators in confluence with GEX levels for enhanced trading insights",
)
technical_confluence_tool.agent_types = [ANALYSIS_AGENT]

# Historical GEX processing tools
historical_gex_tool = FunctionTool(
    func=process_historical_gex_range,
    name="process_historical_gex_range",
    description="Process GEX calculations for date range using high-performance concurrent processing and caching",
)
historical_gex_tool.agent_types = [GEX_AGENT, ANALYSIS_AGENT]

##################################
# Tool Collections by Agent Type
##################################

# DATA_AGENT tools - Data retrieval and caching
_data_tools_raw = [
    fetch_options_tool,  # Options chain data from Alpha Vantage or cache
    fetch_market_tool,  # Market data from Polygon.io or cache
    query_analysis_tool,  # Query intent analysis with market intelligence
    algo_time_analysis_tool,  # Flexible algo time data (3:30, 3:50, etc.)
    # Note: validate_data_tool removed - can't pass DataFrame through AutoGen
]
DATA_COLLECTION_TOOLS = [tool for tool in _data_tools_raw if tool is not None]

# GEX_AGENT tools - Gamma exposure calculations
_gex_tools_raw = [
    calculate_gex_tool,  # Core GEX calculations with Black-Scholes
    find_flip_points_tool,  # Flip point identification and analysis
    historical_gex_tool,  # Historical range processing with caching
]
GEX_CALCULATION_TOOLS = [tool for tool in _gex_tools_raw if tool is not None]

# ANALYSIS_AGENT tools - Pattern detection and analysis
_analysis_tools_raw = [
    fetch_options_tool,  # Data access for analysis
    calculate_gex_tool,  # GEX calculations for patterns
    find_flip_points_tool,  # Flip point analysis for patterns
    algo_time_analysis_tool,  # Flexible algo time analysis (3:30, 3:50, etc.)
    query_analysis_tool,  # Market intelligence and query parsing
    technical_confluence_tool,  # Technical-GEX confluence analysis
    historical_gex_tool,  # Historical GEX range analysis
]
ANALYSIS_TOOLS = [tool for tool in _analysis_tools_raw if tool is not None]

# All tools combined (filter out None values from conditional imports)
ALL_TOOLS = list(
    set(tool for tool in (DATA_COLLECTION_TOOLS + GEX_CALCULATION_TOOLS + ANALYSIS_TOOLS) if tool is not None)
)

# Tool dispatcher dictionary for efficient lookup by name
ALL_TOOLS_DICT = {tool.name: tool for tool in ALL_TOOLS if tool is not None}

##################################
# Helper function to get tools for a specific agent type
##################################


def get_tools_for_agent(agent_type, use_registry: bool = False):
    """Get the list of tools that should be used by a specific agent type.

    Args:
        agent_type: Type of agent (e.g., 'data', 'gex', 'analysis')
        use_registry: If True, use the new ToolRegistry system (Issue #152)

    Returns:
        List of FunctionTool objects appropriate for the agent type
    """
    # Use new registry system if requested
    if use_registry:
        try:
            from src.tools.registry_integration import get_autogen_tools_for_agent

            return get_autogen_tools_for_agent(agent_type)
        except ImportError:
            logger.warning("ToolRegistry not available, falling back to legacy tools")

    # Legacy tool assignment (backward compatible)
    if agent_type == DATA_AGENT:
        return DATA_COLLECTION_TOOLS
    elif agent_type == GEX_AGENT:
        return GEX_CALCULATION_TOOLS
    elif agent_type == ANALYSIS_AGENT:
        return ANALYSIS_TOOLS
    else:
        # Return all tools if agent type is unknown
        return ALL_TOOLS


##################################
# Tool Registry Integration (Issue #152)
##################################


def initialize_registry():
    """Initialize the tool registry with all defined tools.

    Call this during application startup to enable registry features. Returns the registry instance for further
    configuration.
    """
    try:
        from src.tools.registry_integration import initialize_tool_registry

        return initialize_tool_registry()
    except ImportError as e:
        logger.warning(f"Could not initialize tool registry: {e}")
        return None
