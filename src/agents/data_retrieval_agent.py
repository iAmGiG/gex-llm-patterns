"""Data Retrieval Agent Production-ready agent for retrieving and processing options data. Uses cache-first approach
with Alpha Vantage Premium API and sample fallback.

Data Flow: Cache → Alpha Vantage Premium → Sample (fallback only)
"""

import datetime
import logging
import sys
from pathlib import Path

from cache.sqlite_options_manager import SQLiteOptionsManager
from cache.postgresql_options_manager import PostgreSQLOptionsManager
from cache.unified_cache import UnifiedCacheManager
from data_sources.alpha_vantage_gex import AlphaVantageGEXClient

# Use date_utils instead of datetime
from utils.date_utils import add_business_days, calculate_duration_minutes, now_timestamp, parse_date_string, today_str
from validation.options_data_validator import OptionsDataValidator

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# LiveGEXInterface removed during consolidation - use MarketMechanicsAgent instead


logger = logging.getLogger(__name__)


class DataRetrievalAgent:
    """Production agent for retrieving and processing options data.

    Uses cache-first approach with Alpha Vantage Premium API and sample fallback.
    """

    def __init__(self, data_source="production", cache_dir=None, validate=True, enable_sample_fallback=True):
        """Initialize the production data retrieval agent.

        Args:
            data_source: "production" for live data, "sample" for testing only
            cache_dir: Directory for cached data (defaults to .cache/)
            validate: Whether to validate retrieved data
            enable_sample_fallback: Use sample data if live data unavailable
        """
        self.data_source = data_source
        self.validate = validate
        self.enable_sample_fallback = enable_sample_fallback

        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / ".cache"

        # Initialize data providers based on source
        if data_source == "production":
            # Use PostgreSQL by default (migrated from SQLite)
            self.db = PostgreSQLOptionsManager()
            self.cache_manager = UnifiedCacheManager(base_dir=str(self.cache_dir))
            self.alpha_vantage_client = AlphaVantageGEXClient(self.cache_manager)
            # LiveGEXInterface removed - use direct calculation instead
            self.provider = None  # Will use db + alpha_vantage_client
            logger.info("Initialized production data retrieval with PostgreSQL + Alpha Vantage Premium")

        elif data_source == "sample":
            # Sample mode no longer supported - must use real data
            raise ValueError("Sample data mode is deprecated. Use 'production' mode with real data only.")

        else:
            raise ValueError(f"Invalid data source: {data_source}. Use 'production' or 'sample'")

        self.validator = OptionsDataValidator() if validate else None

        # Agent state
        self.current_symbol = None
        self.current_date = None
        self.data_cache = {}

        # Statistics
        self.request_stats = {"total_requests": 0, "cache_hits": 0, "api_calls": 0, "sample_fallbacks": 0}

    def initialize(self):
        """Initialize the agent and return available data info.

        Returns:
            Dictionary with available symbols, dates, and status
        """
        logger.info(f"Initializing DataRetrievalAgent with {self.data_source} data")

        if self.data_source == "production":
            # Production mode: report cache status and API availability
            symbols = ["SPY", "SPX"]  # Primary symbols supported
            symbol_info = {}

            for symbol in symbols:
                # Check cache for recent data
                try:
                    recent_dates = self._get_recent_cached_dates(symbol)
                    symbol_info[symbol] = {
                        "dates": recent_dates,
                        "count": len(recent_dates),
                        "first": recent_dates[0] if recent_dates else None,
                        "last": recent_dates[-1] if recent_dates else None,
                        "cache_status": "available" if recent_dates else "empty",
                    }
                except Exception as e:
                    symbol_info[symbol] = {
                        "dates": [],
                        "count": 0,
                        "first": None,
                        "last": None,
                        "cache_status": f"error: {str(e)}",
                    }

            return {
                "status": "initialized",
                "data_source": self.data_source,
                "symbols": symbols,
                "symbol_info": symbol_info,
                "cache_dir": str(self.cache_dir),
                "validation_enabled": self.validate,
                "alpha_vantage_available": self.alpha_vantage_client.api_key is not None,
                "sample_fallback_enabled": self.enable_sample_fallback,
            }

        else:  # sample mode
            self.provider.initialize()
            symbols = self.provider.fetch_available_symbols()

            # Get date range for each symbol
            symbol_info = {}
            for symbol in symbols:
                dates = self.provider.fetch_available_dates(symbol)
                symbol_info[symbol] = {
                    "dates": dates,
                    "count": len(dates),
                    "first": dates[0] if dates else None,
                    "last": dates[-1] if dates else None,
                }

            return {
                "status": "initialized",
                "data_source": self.data_source,
                "symbols": symbols,
                "symbol_info": symbol_info,
                "cache_dir": str(self.cache_dir),
                "validation_enabled": self.validate,
            }

    def retrieve_options_data(self, symbol, date=None, filters=None):
        """Retrieve options data for analysis using production data flow.

        Args:
            symbol: Stock symbol
            date: Options date (YYYY-MM-DD), uses latest if None
            filters: Optional filters (e.g., min_volume, strike_range)

        Returns:
            Dictionary with data and metadata
        """
        logger.info(f"Retrieving options data: symbol={symbol}, date={date}")
        self.request_stats["total_requests"] += 1

        # Check local cache first
        cache_key = f"{symbol}_{date}_{str(filters)}"
        if cache_key in self.data_cache:
            logger.info("Using agent local cache")
            return self.data_cache[cache_key]

        # Production vs Sample data flow
        if self.data_source == "production":
            result = self._retrieve_production_data(symbol, date, filters)
        else:
            # Sample mode no longer supported
            raise ValueError("Sample data mode is deprecated. Use production mode only.")

        # Cache result locally
        if result["status"] == "success":
            self.data_cache[cache_key] = result

            # Update agent state
            self.current_symbol = symbol
            df = result["data"]
            if not df.empty and "date" in df.columns:
                self.current_date = df["date"].max().strftime("%Y-%m-%d")
            else:
                self.current_date = date or datetime.datetime.now().strftime("%Y-%m-%d")

        return result

    def _retrieve_production_data(self, symbol, date, filters):
        """Retrieve data using production flow: Cache → API → Sample."""
        try:
            # Use production flow through tools.py style access
            result = self._fetch_via_production_flow(symbol, date)

            if result["status"] != "success":
                return result

            df = result["data"]

            # Track data source for stats
            if result["source"] == "cache":
                self.request_stats["cache_hits"] += 1
            elif result["source"] == "alpha_vantage":
                self.request_stats["api_calls"] += 1
            elif result["source"] == "sample":
                self.request_stats["sample_fallbacks"] += 1

            # Validate if enabled
            validation_report = None
            if self.validate and self.validator:
                original_count = len(df)
                df, validation_report = self.validator.validate(df)
                logger.info(f"Validation: {len(df)}/{original_count} valid contracts")

            # Apply filters
            if filters:
                df = self._apply_filters(df, filters)

            # Prepare enhanced response
            return {
                "status": "success",
                "symbol": symbol,
                "date": date or df["date"].max().strftime("%Y-%m-%d") if "date" in df.columns else "unknown",
                "data": df,
                "source": result["source"],
                "metadata": {
                    "total_contracts": len(df),
                    "unique_strikes": df["strike"].nunique() if "strike" in df.columns else 0,
                    "unique_expirations": df["expiration"].nunique() if "expiration" in df.columns else 0,
                    "put_call_ratio": (
                        len(df[df["type"] == "put"]) / max(1, len(df[df["type"] == "call"]))
                        if "type" in df.columns
                        else 0
                    ),
                    "total_volume": df["volume"].sum() if "volume" in df.columns else 0,
                    "total_open_interest": df["open_interest"].sum() if "open_interest" in df.columns else 0,
                },
                "validation_report": validation_report,
                "request_stats": self.request_stats.copy(),
            }

        except Exception as e:
            logger.error(f"Production data retrieval failed: {e}")
            return {
                "status": "error",
                "symbol": symbol,
                "date": date,
                "message": f"Production data retrieval failed: {str(e)}",
            }

    def _retrieve_sample_data(self, symbol, date, filters):
        """Sample data retrieval is deprecated."""
        raise NotImplementedError("Sample data mode is deprecated. Use real production data only.")

    def _apply_filters(self, df, filters):
        """Apply filters to options data."""
        if df.empty:
            return df

        # Apply any filters if provided
        if filters:
            if "min_volume" in filters and "volume" in df.columns:
                df = df[df["volume"] >= filters["min_volume"]]
            if "min_open_interest" in filters and "open_interest" in df.columns:
                df = df[df["open_interest"] >= filters["min_open_interest"]]
            if "option_type" in filters and "type" in df.columns:
                df = df[df["type"] == filters["option_type"]]

        return df

    def _fetch_via_production_flow(self, symbol, date):
        """Fetch via the production flow: SQLite → API.

        Issue #180: Now uses SQLiteOptionsManager as primary storage.
        """
        # Default to today if no date specified
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")

        # Step 1: Check SQLite first (Issue #180: primary storage)
        if self.db:
            cached_data = self.db.get_options_chain(symbol, date)
            if cached_data is not None and not cached_data.empty:
                logger.info(f"SQLite hit for {symbol} options on {date}")
                return {"status": "success", "source": "sqlite", "data": cached_data}

        # Step 2: Try Alpha Vantage API
        if self.alpha_vantage_client:
            try:
                api_data = self.alpha_vantage_client.fetch_historical_options(symbol, date)
                if api_data is not None and not api_data.empty:
                    # Store in SQLite (Issue #180)
                    if self.db:
                        self.db.store_options_chain(symbol, date, api_data)
                    return {"status": "success", "source": "alpha_vantage", "data": api_data}
            except Exception as e:
                logger.warning(f"Alpha Vantage API failed: {e}")

        # No sample data fallback - fail if no real data available
        logger.error(f"No real options data available for {symbol} on {date}")

        return {"status": "error", "message": f"No options data available for {symbol} on {date}"}

    def calculate_gex(self, symbol=None, date=None, spot_price=None):
        """Calculate GEX metrics using production interface.

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
            return {"status": "error", "message": "No symbol specified or in context"}

        logger.info(f"Calculating GEX for {symbol} on {date}")

        # Use MarketMechanicsAgent for GEX calculation instead of removed LiveGEXInterface
        from agents.market_mechanics_agent import MarketMechanicsAgent

        agent = MarketMechanicsAgent(symbol)

        # Get options data first
        options_data = self.retrieve_options_data(symbol, date)
        if options_data["status"] != "success":
            return {
                "status": "error",
                "message": f'Cannot calculate GEX: {options_data.get("message", "No options data")}',
            }

        # Calculate GEX using autogen tools
        from tools.autogen_tools import calculate_gamma_exposure

        gex_results = calculate_gamma_exposure(symbol, date or self.current_date)

        # Add agent metadata and consolidate stats
        gex_results["agent"] = "DataRetrievalAgent"
        gex_results["data_source"] = self.data_source

        # Add agent stats
        gex_results["agent_stats"] = self.request_stats.copy()

        return gex_results

    def get_pattern_candidates(self, pattern_type="short_put_arbitrage", min_volume=100):
        """Identify potential pattern candidates from available data.

        Args:
            pattern_type: Type of pattern to search for
            min_volume: Minimum volume threshold

        Returns:
            List of pattern candidates with details
        """
        logger.info(f"Searching for {pattern_type} patterns")

        candidates = []

        if self.data_source == "production":
            # Search across SPY and SPX
            symbols = ["SPY", "SPX"]
        else:
            # Get all available symbols from sample data
            symbols = self.provider.fetch_available_symbols()

        for symbol in symbols:
            # Get latest data for symbol
            data = self.retrieve_options_data(symbol)

            if data["status"] != "success":
                continue

            df = data["data"]

            # Pattern-specific detection
            if pattern_type == "short_put_arbitrage":
                # Look for high-volume OTM puts
                if "type" in df.columns:
                    puts = df[df["type"] == "put"]

                    if "volume" in puts.columns:
                        high_vol_puts = puts[puts["volume"] >= min_volume]

                        for _, put in high_vol_puts.iterrows():
                            # Calculate metrics
                            if "implied_volatility" in put and put["implied_volatility"] > 0:
                                candidates.append(
                                    {
                                        "symbol": symbol,
                                        "strike": put["strike"],
                                        "expiration": put["expiration"],
                                        "volume": put["volume"],
                                        "open_interest": put.get("open_interest", 0),
                                        "implied_vol": put["implied_volatility"],
                                        "delta": put.get("delta", None),
                                        "pattern_score": self._calculate_pattern_score(put),
                                        "data_source": data["source"],
                                    }
                                )

        # Sort by pattern score
        candidates.sort(key=lambda x: x["pattern_score"], reverse=True)

        logger.info(f"Found {len(candidates)} pattern candidates")
        return candidates

    def _get_recent_cached_dates(self, symbol, days_back=30):
        """Get list of dates with cached data for symbol."""
        if not self.db:
            return []

        recent_dates = []
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days_back)

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            try:
                # Issue #180: Use SQLite for options data
                cached_data = self.db.get_options_chain(symbol, date_str)
                if cached_data is not None and not cached_data.empty:
                    recent_dates.append(date_str)
            except Exception:
                pass  # Skip dates with errors

            current_date += datetime.timedelta(days=1)

        return sorted(recent_dates)

    def _apply_filters(self, df, filters):
        """Apply filters to options data."""
        filtered = df.copy()

        # Volume filter
        if "min_volume" in filters and "volume" in filtered.columns:
            filtered = filtered[filtered["volume"] >= filters["min_volume"]]

        # Strike range filter
        if "strike_min" in filters and "strike" in filtered.columns:
            filtered = filtered[filtered["strike"] >= filters["strike_min"]]
        if "strike_max" in filters and "strike" in filtered.columns:
            filtered = filtered[filtered["strike"] <= filters["strike_max"]]

        # Expiration filter
        if "max_days_to_expiry" in filters:
            if "date" in filtered.columns and "expiration" in filtered.columns:
                days_to_exp = (filtered["expiration"] - filtered["date"]).dt.days
                filtered = filtered[days_to_exp <= filters["max_days_to_expiry"]]

        # Option type filter
        if "option_type" in filters and "type" in filtered.columns:
            filtered = filtered[filtered["type"] == filters["option_type"]]

        # Greeks filters
        if "min_delta" in filters and "delta" in filtered.columns:
            filtered = filtered[abs(filtered["delta"]) >= filters["min_delta"]]
        if "min_gamma" in filters and "gamma" in filtered.columns:
            filtered = filtered[filtered["gamma"] >= filters["min_gamma"]]

        return filtered

    def _calculate_pattern_score(self, option_row):
        """Calculate a pattern score for ranking candidates."""
        score = 0.0

        # Volume component
        if "volume" in option_row and option_row["volume"] > 0:
            score += min(option_row["volume"] / 1000, 10)  # Cap at 10

        # Open interest component
        if "open_interest" in option_row and option_row["open_interest"] > 0:
            score += min(option_row["open_interest"] / 10000, 5)  # Cap at 5

        # IV component (higher is more interesting)
        if "implied_volatility" in option_row:
            score += option_row["implied_volatility"] * 10

        # Delta component (OTM options more interesting)
        if "delta" in option_row:
            score += (1 - abs(option_row["delta"])) * 5

        return score

    def generate_summary_report(self) -> str:
        """Generate a summary report of available data and agent status."""
        info = self.initialize()

        report = []
        report.append("=" * 70)
        report.append("DATA RETRIEVAL AGENT SUMMARY")
        report.append("=" * 70)
        report.append(f"Data Source: {self.data_source}")
        report.append(f"Cache Directory: {self.cache_dir}")
        report.append(f"Validation: {'Enabled' if self.validate else 'Disabled'}")

        if self.data_source == "production":
            report.append(f"Alpha Vantage: {'Available' if info.get('alpha_vantage_available') else 'Unavailable'}")
            report.append(f"Sample Fallback: {'Enabled' if self.enable_sample_fallback else 'Disabled'}")

        report.append("")

        # Request statistics
        if self.request_stats["total_requests"] > 0:
            total = self.request_stats["total_requests"]
            report.append("REQUEST STATISTICS")
            report.append("-" * 30)
            report.append(f"Total Requests: {total}")
            report.append(f"Cache Hit Rate: {self.request_stats['cache_hits'] / total * 100:.1f}%")
            report.append(f"API Call Rate: {self.request_stats['api_calls'] / total * 100:.1f}%")
            report.append(f"Sample Fallback Rate: {self.request_stats['sample_fallbacks'] / total * 100:.1f}%")
            report.append("")

        report.append("AVAILABLE DATA")
        report.append("-" * 30)
        for symbol, details in info["symbol_info"].items():
            report.append(f"\n{symbol}:")
            if self.data_source == "production":
                report.append(f"  Cache Status: {details['cache_status']}")
            report.append(f"  Date Range: {details['first']} to {details['last']}")
            report.append(f"  Total Days: {details['count']}")

        # Get sample GEX for first symbol
        if info["symbols"]:
            symbol = info["symbols"][0]
            try:
                gex = self.calculate_gex(symbol)

                if gex.get("status") == "success" and "net_gex" in gex:
                    report.append("")
                    report.append(f"SAMPLE GEX CALCULATION ({symbol})")
                    report.append("-" * 30)
                    report.append(f"Net GEX: ${gex['net_gex']:,.0f}")
                    report.append(f"Spot Price: ${gex['spot_price']:.2f}")
                    report.append(f"Data Source: {gex.get('data_source', 'unknown')}")

                    if gex.get("flip_point"):
                        report.append(f"Flip Point: ${gex['flip_point']:.2f}")
            except Exception as e:
                report.append(f"\nSample GEX calculation failed: {e}")

        report.append("")
        report.append("=" * 70)

        return "\n".join(report)

    def get_agent_stats(self):
        """Get comprehensive agent statistics."""
        return {
            "data_source": self.data_source,
            "cache_enabled": self.cache_manager is not None,
            "api_enabled": self.alpha_vantage_client is not None,
            "validation_enabled": self.validate,
            "sample_fallback_enabled": self.enable_sample_fallback,
            "request_stats": self.request_stats.copy(),
            "current_state": {
                "symbol": self.current_symbol,
                "date": self.current_date,
                "local_cache_size": len(self.data_cache),
            },
        }


# Main agent class - defaults to production mode


class AgentOrchestrator:
    """Orchestrates multiple production data retrieval agents for parallel processing."""

    def __init__(self, num_agents=3, **agent_kwargs):
        """Initialize the orchestrator.

        Args:
            num_agents: Number of parallel agents to create
            **agent_kwargs: Arguments to pass to each agent
        """
        self.agents = [DataRetrievalAgent(**agent_kwargs) for _ in range(num_agents)]
        self.results = {}

    def parallel_gex_calculation(self, symbols, date=None):
        """Calculate GEX for multiple symbols in parallel.

        Args:
            symbols: List of symbols to process
            date: Options date

        Returns:
            Dictionary mapping symbols to GEX results
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

    def find_highest_gex(self):
        """Find symbol with highest absolute net GEX."""
        if not self.results:
            return None

        max_symbol = None
        max_gex = 0

        for symbol, result in self.results.items():
            if result.get("status") == "success" and "net_gex" in result:
                abs_gex = abs(result["net_gex"])
                if abs_gex > max_gex:
                    max_gex = abs_gex
                    max_symbol = symbol

        return max_symbol

    def get_orchestrator_stats(self):
        """Get combined statistics from all agents."""
        combined_stats = {
            "num_agents": len(self.agents),
            "total_requests": 0,
            "total_cache_hits": 0,
            "total_api_calls": 0,
            "total_sample_fallbacks": 0,
            "agent_details": [],
        }

        for i, agent in enumerate(self.agents):
            agent_stats = agent.get_agent_stats()
            combined_stats["total_requests"] += agent_stats["request_stats"]["total_requests"]
            combined_stats["total_cache_hits"] += agent_stats["request_stats"]["cache_hits"]
            combined_stats["total_api_calls"] += agent_stats["request_stats"]["api_calls"]
            combined_stats["total_sample_fallbacks"] += agent_stats["request_stats"]["sample_fallbacks"]

            combined_stats["agent_details"].append({"agent_id": i, "stats": agent_stats})

        # Calculate combined rates
        if combined_stats["total_requests"] > 0:
            total = combined_stats["total_requests"]
            combined_stats["cache_hit_rate"] = combined_stats["total_cache_hits"] / total
            combined_stats["api_usage_rate"] = combined_stats["total_api_calls"] / total
            combined_stats["fallback_rate"] = combined_stats["total_sample_fallbacks"] / total

        return combined_stats
