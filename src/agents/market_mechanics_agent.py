"""
Market Mechanics Agent - Single Agent Architecture
Implements Issue #50: LLM as Market Mechanics Interpreter

Core hypothesis: LLM identifies WHO is forcing WHOM to do WHAT in market mechanics
"""

from typing import Dict, List, Optional
import logging
import pandas as pd
import numpy as np
import yaml
import sqlite3
from pathlib import Path

from src.utils.date_utils import (
    get_default_date_range,
    parse_date_string,
    is_business_day,
    date_range_trading_days,
    is_opex_week,
    add_business_days
)
from src.cache.unified_cache import UnifiedCacheManager
from src.gex.enhanced_pattern_detector import EnhancedPatternDetector
from src.gex.gex_calculator import GEXCalculator
from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder
import datetime

logger = logging.getLogger(__name__)

# Import autogen_tools at module level with fallback
try:
    from src.tools.autogen_tools import fetch_options_data, calculate_gamma_exposure, fetch_market_data
    AUTOGEN_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AutoGen tools not available: {e}")
    AUTOGEN_TOOLS_AVAILABLE = False


class MarketMechanicsAgent:
    """
    Single agent that interprets market mechanics from GEX data.
    Focus: WHO is forcing WHOM to do WHAT
    """

    def __init__(self, symbol: str = "SPY", llm_provider: Optional[object] = None, config: Optional[Dict] = None):
        """
        Initialize the Market Mechanics Agent.

        Args:
            symbol: Trading symbol to analyze
            llm_provider: LLM integration (OpenAI, Claude, etc.)
            config: Configuration dictionary (loads from file if None)
        """
        self.symbol = symbol
        self.config = config or self._load_config()
        self.gex_thresholds = self.config.get('gex_thresholds', {})
        self.strike_pattern_config = self.config.get('strike_level_patterns', {})
        self.cache = UnifiedCacheManager()
        self.pattern_detector = EnhancedPatternDetector()
        self.gex_calculator = GEXCalculator()
        self.prompt_builder = MechanicsPromptBuilder()

        # Auto-initialize LLM if not provided
        if llm_provider is None:
            # Use AutoGen for consistency with base_agent architecture
            try:
                from src.llm.autogen_market_mechanics import AutoGenMarketMechanics
                self.llm = AutoGenMarketMechanics()
                logger.info("Initialized AutoGen LLM for mechanics interpretation")
            except Exception as e:
                logger.warning(f"Could not initialize AutoGen LLM: {e}")
                self.llm = None
        else:
            self.llm = llm_provider

        # Market mechanics patterns library
        self.mechanics_patterns = {
            'dealer_hedging': {
                'description': 'Market makers hedging their gamma exposure',
                'indicators': ['high_gamma_concentration', 'pin_risk'],
                'who': 'Dealers/Market Makers',
                'whom': 'Directional traders',
                'what': 'Forced buying/selling to maintain delta neutrality'
            },
            'gamma_squeeze': {
                'description': 'Positive feedback loop forcing dealers to chase price',
                'indicators': ['positive_gamma_high', 'accelerating_delta_hedging'],
                'who': 'Options flow',
                'whom': 'Dealers',
                'what': 'Forced to buy high/sell low amplifying moves'
            },
            'pin_manipulation': {
                'description': 'Large players defending strike levels',
                'indicators': ['massive_oi_strikes', 'price_magnetism', 'vol_compression'],
                'who': 'Large options writers',
                'whom': 'Market price',
                'what': 'Defending profitable strike levels through spot manipulation'
            }
        }

    def _load_config(self) -> Dict:
        """Load configuration from analysis_config.yaml."""
        try:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config_defaults" / "analysis_config.yaml"

            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")
            return {
                'gex_thresholds': {
                    'positive_high': 5e9,
                    'negative_high': -5e9,
                    'gamma_concentration_threshold': 0.7,
                    'high_volume_threshold': 1e6,
                    'significant_flow_threshold': 5e5
                }
            }

    def _normalize_date(self, date) -> tuple[datetime.datetime, str]:
        """Normalize date input to (datetime_obj, date_string) tuple.

        Supports both daily dates ('2024-01-15') and intra-day timestamps ('2024-01-15 15:30:00').
        For intra-day timestamps, preserves the full timestamp format.
        """
        if isinstance(date, str):
            try:
                # Try intra-day timestamp format first
                if ' ' in date and ':' in date:
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                    date_str = date  # Preserve full timestamp
                else:
                    # Traditional daily date format
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    date_str = date
            except ValueError:
                # Try parsing other common formats
                try:
                    date_obj = pd.to_datetime(date).to_pydatetime()
                    # Determine if this has time component
                    if date_obj.hour != 0 or date_obj.minute != 0 or date_obj.second != 0:
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = date_obj.strftime('%Y-%m-%d')
                except Exception:
                    raise ValueError(f"Unable to parse date: {date}")
        elif hasattr(date, 'strftime'):
            date_obj = date
            # Determine if this has time component
            if date_obj.hour != 0 or date_obj.minute != 0 or date_obj.second != 0:
                date_str = date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_str = date.strftime('%Y-%m-%d')
        elif hasattr(date, 'to_pydatetime'):
            date_obj = date.to_pydatetime()
            # Determine if this has time component
            if date_obj.hour != 0 or date_obj.minute != 0 or date_obj.second != 0:
                date_str = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_str = date_obj.strftime('%Y-%m-%d')
        else:
            raise ValueError(f"Unsupported date type: {type(date)}")

        return date_obj, date_str

    def _normalize_gex_results(self, gex_profile: Dict, spot_price: float) -> Dict:
        """Normalize GEX results to consistent structure regardless of source."""
        return {
            'net_gex': gex_profile.get('net_gex', 0),
            'flip_point': gex_profile.get('flip_point', spot_price),
            'spot_price': spot_price,
            'gex_by_strike': gex_profile.get('gex_by_strike', {}),
            # Ensure these fields exist for downstream compatibility
            'total_gamma': gex_profile.get('total_gamma', 0),
            'gamma_concentration': gex_profile.get('gamma_concentration', {}),
            'max_strike': gex_profile.get('max_strike', spot_price)
        }

    def daily_analysis(self, date) -> Dict:
        """
        Perform complete daily market mechanics analysis.

        Returns:
            Dict containing:
            - mechanics_interpretation: WHO is forcing WHOM to do WHAT
            - actionable_signal: Trading recommendation
            - confidence: Statistical confidence in the signal
            - supporting_evidence: Data backing the interpretation
        """
        try:
            # Normalize date input
            date_obj, date_str = self._normalize_date(date)

            # 1. Get data
            logger.info(f"Starting daily analysis for {date_str}")

            # Try database GEX first for consistency with baseline
            gex_metrics = self._fetch_gex_from_database(date_str)

            if gex_metrics:
                # If we got GEX from database, we might not have options data
                logger.info(f"Using database GEX for {date_str}, skipping options data fetch")
                options_data = pd.DataFrame()  # Empty DataFrame for downstream functions
            else:
                # Fallback to normal options data flow
                options_data = self._fetch_options_data(date_str)
                if options_data is None or options_data.empty:
                    logger.warning(f"No options data for {date_str}")
                    return self._empty_analysis()

                # 2. Calculate GEX metrics from options data
                gex_metrics = self._calculate_gex_metrics(options_data, date_str)

            # 3. Build comprehensive context
            context = self._build_market_context(
                date_obj, gex_metrics, options_data)

            # 4. Detect patterns
            patterns = self._detect_mechanics_patterns(context)

            # 5. LLM interprets mechanics (if available)
            if self.llm:
                interpretation = self._llm_interpret_mechanics(
                    context, patterns)
            else:
                interpretation = self._rule_based_interpretation(patterns)

            # 6. Generate actionable signal
            # Add overall confidence and patterns to context for signal generation
            overall_confidence = self._calculate_confidence(patterns, context)
            context['overall_confidence'] = overall_confidence
            context['patterns_detected'] = patterns
            signal = self._generate_trading_signal(interpretation, context)

            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            return {
                'date': date_str,
                'mechanics_interpretation': interpretation,
                'actionable_signal': signal,
                'patterns_detected': patterns,
                'gex_metrics': gex_metrics,
                'confidence': self._calculate_confidence(patterns, context)
            }

        except Exception as e:
            import traceback
            logger.error(f"Error in daily analysis: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._empty_analysis()

    def _fetch_options_data(self, date) -> Optional[pd.DataFrame]:
        """Fetch options data using autogen_tools for better caching."""
        if not AUTOGEN_TOOLS_AVAILABLE:
            # Fallback to direct cache access
            _, date_str = self._normalize_date(date)
            return self.cache.get_options_data(self.symbol, date_str)

        # Convert date to string format
        _, date_str = self._normalize_date(date)

        # Use autogen tool which handles cache → API → sample data fallback
        try:
            result = fetch_options_data(symbol=self.symbol, trading_date=date_str, use_cache=True)

            if result['status'] == 'success':
                logger.info(f"Fetched options data from {result['source']} for {self.symbol} {date_str}")
                return result['data']
            else:
                logger.error(f"AutoGen fetch failed: {result.get('message', 'Unknown error')}")
                # Fallback to direct cache access
                return self.cache.get_options_data(self.symbol, date_str)

        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"AutoGen API connection issue: {e}, falling back to cache")
            return self.cache.get_options_data(self.symbol, date_str)
        except Exception as e:
            logger.error(f"AutoGen tools error: {e}, falling back to cache")
            return self.cache.get_options_data(self.symbol, date_str)

    def _fetch_gex_from_database(self, date_str: str) -> Optional[Dict]:
        """Fetch GEX data from database, calculate and populate if missing.

        Supports both daily data and intra-day data retrieval.
        For timestamps, queries intraday_gex_metrics table.
        For dates, queries daily_gex_metrics table.
        """
        try:
            conn = sqlite3.connect("./.cache/consolidated_historical.db")

            # Determine if this is intra-day timestamp or daily date
            is_intraday = ' ' in date_str and ':' in date_str

            if is_intraday:
                # Query intraday table for exact timestamp
                query = """
                    SELECT timestamp, total_gex, gex_regime, gamma_flip_point,
                           net_call_gex, net_put_gex, flip_ratio, spot_price
                    FROM intraday_gex_metrics
                    WHERE symbol = ? AND timestamp = ?
                """
            else:
                # Query daily table for date
                query = """
                    SELECT date, total_gex, gex_regime, gamma_flip_point,
                           net_call_gex, net_put_gex, flip_ratio, spot_price
                    FROM daily_gex_metrics
                    WHERE symbol = ? AND date = ?
                """

            cursor = conn.execute(query, (self.symbol, date_str))
            row = cursor.fetchone()

            if row:
                # Data exists - return it
                conn.close()
                total_gex = row[1]
                return {
                    'total_gamma': total_gex,
                    'net_gex': total_gex,
                    'gex_value': total_gex,
                    'regime': row[2] or ('NEGATIVE_GAMMA' if total_gex < 0 else 'POSITIVE_GAMMA'),
                    'flip_level': row[3] or 0,
                    'gamma_concentration': abs(row[6]) if row[6] else 0,  # Use flip_ratio as proxy
                    'call_gamma': row[4] or 0,
                    'put_gamma': row[5] or 0,
                    'zero_gamma_level': row[3] or 0,  # Use flip point as zero gamma
                    'spot_price': row[7] or 0,
                    'source': 'historical_database'
                }

            # Data missing - calculate and populate
            logger.info(f"No database GEX data for {date_str}, calculating and populating...")

            # Fetch options data for calculation
            options_data = self._fetch_options_data(date_str)
            if options_data is None or options_data.empty:
                conn.close()
                logger.warning(f"Cannot calculate GEX for {date_str} - no options data")
                return None

            # Calculate GEX metrics
            gex_metrics = self._calculate_gex_metrics(options_data, date_str)
            if not gex_metrics:
                conn.close()
                logger.warning(f"GEX calculation failed for {date_str}")
                return None

            # Populate database with calculated data
            self._populate_database_entry(conn, date_str, gex_metrics)
            conn.close()

            # Return calculated data with database source flag
            gex_metrics['source'] = 'calculated_and_populated'
            logger.info(f"Calculated and populated GEX for {date_str}: {gex_metrics.get('net_gex', 0):.2e}")
            return gex_metrics

        except Exception as e:
            logger.warning(f"Database GEX fetch/populate failed: {e}")
            return None

    def _calculate_gex_metrics(self, options_data: pd.DataFrame, date) -> Dict:
        """Calculate comprehensive GEX metrics using autogen_tools or direct calculation."""
        try:

            # Convert date to string format
            _, date_str = self._normalize_date(date)

            # Get market data for spot price using autogen tools
            if AUTOGEN_TOOLS_AVAILABLE:
                try:
                    market_result = fetch_market_data(symbol=self.symbol, end_date=date_str, use_cache=True)

                    if market_result['status'] == 'success':
                        market_data = market_result['data']
                        close_col = 'close' if 'close' in market_data.columns else 'Close'
                        spot_price = market_data[close_col].iloc[-1]
                    else:
                        # Fallback to options data spot price
                        spot_price = options_data['underlying_last'].iloc[0] if 'underlying_last' in options_data.columns else 0

                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"AutoGen market data API issue: {e}, using options data fallback")
                    spot_price = options_data['underlying_last'].iloc[0] if 'underlying_last' in options_data.columns else 0
                except Exception as e:
                    logger.error(f"AutoGen market data error: {e}, using options data fallback")
                    spot_price = options_data['underlying_last'].iloc[0] if 'underlying_last' in options_data.columns else 0
            else:
                # Direct fallback when AutoGen not available
                spot_price = options_data['underlying_last'].iloc[0] if 'underlying_last' in options_data.columns else 0

            # Use autogen tool for GEX calculation which handles caching
            if AUTOGEN_TOOLS_AVAILABLE:
                try:
                    gex_result = calculate_gamma_exposure(
                        symbol=self.symbol,
                        trading_date=date_str,
                        spot_price=spot_price,
                        use_cache=True
                    )

                    if gex_result['status'] == 'success':
                        gex_metrics = gex_result['metrics']
                        logger.info(f"GEX calculation via autogen_tools (fallback): cache_hit={gex_result.get('cache_hit', False)}")

                        # Convert to expected format
                        gex_profile = {
                            'net_gex': gex_metrics.get('net_gex', 0),
                            'flip_point': gex_metrics.get('flip_point', spot_price),
                            'spot_price': spot_price,
                            'gex_by_strike': gex_metrics.get('gex_by_strike', {})
                        }
                    else:
                        raise ValueError(f"AutoGen GEX calculation failed: {gex_result.get('message', 'Unknown error')}")

                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"AutoGen GEX API issue: {e}, falling back to direct calculation")
                    gex_profile = self.gex_calculator.calculate_gex_profile(
                        options_data=options_data,
                        underlying_price=spot_price
                    )
                except Exception as e:
                    logger.error(f"AutoGen GEX calculation error: {e}, falling back to direct calculation")
                    gex_profile = self.gex_calculator.calculate_gex_profile(
                        options_data=options_data,
                        underlying_price=spot_price
                    )
            else:
                # Direct calculation when AutoGen not available
                gex_profile = self.gex_calculator.calculate_gex_profile(
                    options_data=options_data,
                    underlying_price=spot_price
                )

            # Extract key metrics for compatibility - ensure consistent structure
            gex_results = self._normalize_gex_results(gex_profile, spot_price)

            # Add regime classification
            net_gex = gex_results.get('net_gex', 0)
            gex_results['gex_regime'] = self._classify_gex_regime(
                net_gex, spot_price)

            # Add Greeks concentration analysis
            gex_results['gamma_concentration'] = self._analyze_gamma_concentration(
                options_data, spot_price)
            # Skip vanna/charm for now - not needed for basic mechanics analysis
            # gex_results['vanna_estimate'] = self._estimate_vanna_flows(options_data)
            # gex_results['charm_estimate'] = self._estimate_charm_decay(options_data, date)

            return gex_results

        except Exception as e:
            logger.error(f"Error calculating GEX metrics: {e}")
            return {}

    def _build_market_context(self, date, gex_metrics: Dict, options_data: pd.DataFrame) -> Dict:
        """Build comprehensive market context for analysis."""
        # Enhanced temporal context with Friday 3:30 PM detection
        temporal_context = self._get_temporal_context(date)

        # Add Friday 3:30 PM flag for Issue #73 validation
        temporal_context['is_friday_330pm'] = (
            temporal_context.get('day_of_week') == 'Friday' and
            hasattr(date, 'hour') and hasattr(date, 'minute') and
            date.hour == 15 and date.minute == 30
        )

        context = {
            'date': date,
            'gex_metrics': gex_metrics,
            'options_data': options_data,  # Include options data for strike-level analysis
            'price_action': self._describe_price_action(date),
            'options_flow': self._analyze_flow_patterns(options_data),
            'temporal_context': temporal_context,
            'strike_distribution': self._analyze_strike_distribution(options_data),
            'volatility_surface': self._analyze_volatility_surface(options_data)
        }

        # Add strike-level patterns for enhanced analysis
        if not options_data.empty and gex_metrics.get('spot_price'):
            strike_patterns = {
                'gamma_concentration': self._detect_gamma_concentration_enhanced(options_data, gex_metrics['spot_price']),
                'volume_anomalies': self._detect_volume_anomalies(options_data),
                'gamma_walls': self._detect_gamma_walls(options_data, gex_metrics['spot_price']),
                'pin_setup': self._detect_pin_setup(options_data, gex_metrics['spot_price'], temporal_context),
                'dealer_positioning': self._calculate_dealer_exposure(options_data, gex_metrics['spot_price'])
            }
            context['strike_level_patterns'] = strike_patterns

        # Add Fed context if available
        fed_context = self._get_fed_context(date)
        if fed_context:
            context['fed_context'] = fed_context

        return context

    def _describe_price_action(self, date) -> Dict:
        """Describe recent price action patterns."""
        try:
            # Ensure date is a datetime object
            if isinstance(date, str):
                date = datetime.datetime.strptime(date, '%Y-%m-%d')

            # Get last 5 days of price data
            price_data = []
            for i in range(5):
                check_date = date - datetime.timedelta(days=i)
                check_date_str = check_date.strftime('%Y-%m-%d')
                market_data = self.cache.get_market_data(
                    self.symbol, check_date_str)
                if market_data is not None and not market_data.empty:
                    # Handle both lowercase and capitalized column names
                    open_col = 'open' if 'open' in market_data.columns else 'Open'
                    high_col = 'high' if 'high' in market_data.columns else 'High'
                    low_col = 'low' if 'low' in market_data.columns else 'Low'
                    close_col = 'close' if 'close' in market_data.columns else 'Close'
                    volume_col = 'volume' if 'volume' in market_data.columns else 'Volume'

                    price_data.append({
                        'date': check_date,
                        'open': market_data[open_col].iloc[0],
                        'high': market_data[high_col].iloc[0],
                        'low': market_data[low_col].iloc[0],
                        'close': market_data[close_col].iloc[0],
                        'volume': market_data[volume_col].iloc[0]
                    })

            if not price_data:
                return {}

            # Calculate price action metrics
            closes = [p['close'] for p in price_data]
            return {
                'trend': 'up' if closes[0] > closes[-1] else 'down',
                'volatility': np.std(closes) / np.mean(closes) if closes else 0,
                'recent_range': (max(closes) - min(closes)) / np.mean(closes) if closes else 0,
                'volume_trend': 'increasing' if price_data[0]['volume'] > price_data[-1]['volume'] else 'decreasing'
            }

        except Exception as e:
            logger.error(f"Error describing price action: {e}")
            return {}

    def _analyze_flow_patterns(self, options_data: pd.DataFrame) -> Dict:
        """Analyze options flow patterns."""
        if options_data.empty:
            return {}

        try:
            total_call_volume = options_data[options_data['type'] == 'call']['volume'].sum(
            )
            total_put_volume = options_data[options_data['type'] == 'put']['volume'].sum(
            )
            total_call_oi = options_data[options_data['type']
                                         == 'call']['open_interest'].sum()
            total_put_oi = options_data[options_data['type']
                                        == 'put']['open_interest'].sum()

            return {
                'put_call_ratio': total_put_volume / max(total_call_volume, 1),
                'oi_put_call_ratio': total_put_oi / max(total_call_oi, 1),
                'volume_vs_oi': (total_call_volume + total_put_volume) / max(total_call_oi + total_put_oi, 1),
                'call_skew': self._calculate_skew(options_data[options_data['type'] == 'call']),
                'put_skew': self._calculate_skew(options_data[options_data['type'] == 'put'])
            }

        except Exception as e:
            logger.error(f"Error analyzing flow patterns: {e}")
            return {}

    def _get_temporal_context(self, date) -> Dict:
        """Get temporal context (day of week, month, expiry cycles)."""
        # Convert date to datetime object for consistent handling
        if isinstance(date, str):
            date_obj = pd.Timestamp(date).to_pydatetime()
        elif hasattr(date, 'to_pydatetime'):
            date_obj = date.to_pydatetime()
        else:
            date_obj = date

        return {
            'day_of_week': date_obj.strftime('%A'),
            'day_of_month': date_obj.day,
            'month': date_obj.month,
            'is_opex': self._is_opex_week(date),
            'days_to_fomc': self._days_to_next_fomc(date),
            'is_month_end': date.day >= 25,
            'is_quarter_end': date.month in [3, 6, 9, 12] and date.day >= 25
        }

    def _detect_mechanics_patterns(self, context: Dict) -> List[Dict]:
        """Enhanced pattern detection with strike-level analysis."""
        detected_patterns = []

        # Get enhanced strike-level patterns
        strike_patterns = self._detect_strike_level_patterns(context)

        # Traditional mechanics patterns with enhanced strike-level data
        gex_metrics = context.get('gex_metrics', {})
        options_flow = context.get('options_flow', {})

        # Check for each mechanics pattern with enhanced detection
        for pattern_name, pattern_def in self.mechanics_patterns.items():
            confidence = 0
            evidence = []

            if pattern_name == 'dealer_hedging':
                # Enhanced with strike-level gamma concentration
                gamma_config = self.strike_pattern_config.get('gamma_concentration', {})
                threshold = gamma_config.get('high_concentration_pct', 0.20)

                gamma_data = strike_patterns.get('gamma_concentration', {})
                if gamma_data.get('concentration_pct', 0) > threshold:
                    confidence += 50
                    evidence.append(f"Gamma concentration: {gamma_data.get('concentration_pct', 0):.1%} at ${gamma_data.get('max_strike', 0):.0f}")

                # Strike-level volume validation
                volume_data = strike_patterns.get('volume_anomalies', {})
                if volume_data.get('detected', False):
                    confidence += 30
                    evidence.append(f"Volume anomaly: {volume_data.get('max_volume', 0):,.0f} contracts")

            elif pattern_name == 'gamma_squeeze':
                if gex_metrics.get('gex_regime') == 'POSITIVE_GAMMA_HIGH':
                    confidence += 40
                    evidence.append("Positive gamma regime")

                # Enhanced with gamma wall detection
                gamma_walls = strike_patterns.get('gamma_walls', {})
                if gamma_walls.get('resistance_strikes'):
                    confidence += 30
                    evidence.append(f"Gamma resistance at {gamma_walls.get('resistance_strikes')}")

            elif pattern_name == 'pin_manipulation':
                # Enhanced pin detection using Issue #73 validated approach
                pin_data = strike_patterns.get('pin_setup', {})
                if pin_data.get('pin_probability', 0) > 0.60:  # Validated 60% threshold
                    confidence += 70
                    evidence.append(f"Pin setup: {pin_data.get('pin_probability', 0):.1%} probability to ${pin_data.get('target_strike', 0):.0f}")

                # Add Friday 3:30 PM context if applicable
                time_context = context.get('temporal_context', {})
                if time_context.get('is_friday_330pm', False):
                    confidence += 20
                    evidence.append("Friday 3:30 PM expiration timing")

            if confidence > 30:
                detected_patterns.append({
                    'pattern': pattern_name,
                    'confidence': confidence,
                    'who': pattern_def['who'],
                    'whom': pattern_def['whom'],
                    'what': pattern_def['what'],
                    'evidence': evidence
                })

        # Add compound pattern detection (main chat suggestion)
        compound_patterns = self._detect_compound_patterns(strike_patterns, context)
        detected_patterns.extend(compound_patterns)

        return sorted(detected_patterns, key=lambda x: x['confidence'], reverse=True)

    def _detect_strike_level_patterns(self, context: Dict) -> Dict:
        """Enhanced strike-level pattern detection based on Issue #73 validation."""
        options_data = context.get('options_data', pd.DataFrame())
        gex_metrics = context.get('gex_metrics', {})
        temporal_context = context.get('temporal_context', {})
        spot_price = gex_metrics.get('spot_price', 0)

        if options_data.empty or not spot_price:
            return {}

        patterns = {
            'gamma_concentration': self._detect_gamma_concentration_enhanced(options_data, spot_price),
            'volume_anomalies': self._detect_volume_anomalies(options_data),
            'gamma_walls': self._detect_gamma_walls(options_data, spot_price),
            'pin_setup': self._detect_pin_setup(options_data, spot_price, temporal_context),
            'dealer_positioning': self._calculate_dealer_exposure(options_data, spot_price)
        }

        return patterns

    def _detect_compound_patterns(self, strike_patterns: Dict, context: Dict) -> List[Dict]:
        """
        Detect compound patterns where multiple signals align for higher probability.
        Based on main chat suggestion for pattern combination detection.
        """
        compound_patterns = []
        temporal_context = context.get('temporal_context', {})

        # High Probability Pin (validated from Issue #73 - 75% success rate)
        gamma_data = strike_patterns.get('gamma_concentration', {})
        volume_data = strike_patterns.get('volume_anomalies', {})
        pin_data = strike_patterns.get('pin_setup', {})

        if (gamma_data.get('concentration_pct', 0) > 0.20 and  # 20% gamma concentration
            volume_data.get('detected', False) and               # Volume anomaly present
            temporal_context.get('is_friday_330pm', False)):     # Friday 3:30 PM timing

            combined_confidence = min(0.95,
                gamma_data.get('confidence', 0.5) * 0.4 +
                volume_data.get('confidence', 0.5) * 0.3 +
                0.85  # Issue #73 validated Friday 3:30 PM boost
            )

            compound_patterns.append({
                'pattern': 'high_probability_pin',
                'confidence': combined_confidence * 100,  # Convert to percentage
                'who': 'Market makers and institutional traders',
                'whom': 'Price action and retail traders',
                'what': 'Coordinated gamma pinning toward max concentration strike',
                'evidence': [
                    f"Gamma concentration: {gamma_data.get('concentration_pct', 0):.1%} at ${gamma_data.get('max_strike', 0):.0f}",
                    f"Volume anomaly: {volume_data.get('max_volume', 0):,.0f} contracts",
                    "Friday 3:30 PM expiration timing (75% historical success)",
                    f"Target pin level: ${pin_data.get('target_strike', gamma_data.get('max_strike', 0)):.0f}"
                ],
                'historical_validation': {
                    'source': 'Issue #73 June 2024 validation',
                    'success_rate': '75%',
                    'sample_size': 4,
                    'methodology': 'Friday 3:30 PM gamma pinning analysis'
                }
            })

        # Volume + Gamma Squeeze Combination
        gamma_walls = strike_patterns.get('gamma_walls', {})
        if (volume_data.get('detected', False) and
            gamma_walls.get('resistance_strikes') and
            gamma_data.get('concentration_pct', 0) > 0.15):

            compound_patterns.append({
                'pattern': 'volume_gamma_breakout',
                'confidence': 75,
                'who': 'Large options players',
                'whom': 'Market makers and short-term traders',
                'what': 'Force breakout through gamma resistance levels',
                'evidence': [
                    f"Volume surge: {volume_data.get('max_volume', 0):,.0f} contracts",
                    f"Gamma resistance: {gamma_walls.get('resistance_strikes')}",
                    f"Concentration: {gamma_data.get('concentration_pct', 0):.1%}"
                ]
            })

        return compound_patterns

    def _detect_gamma_concentration_enhanced(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Enhanced gamma concentration detection based on Issue #73 validation."""
        try:
            if 'gamma' not in options_data.columns:
                return {}

            # Group by strike and sum absolute gamma exposure
            gamma_by_strike = options_data.groupby('strike')['gamma'].sum().abs()
            total_gamma = gamma_by_strike.sum()

            if total_gamma == 0:
                return {}

            # Find max gamma strike and concentration percentage
            max_gamma_strike = gamma_by_strike.idxmax()
            max_gamma_value = gamma_by_strike.max()
            concentration_pct = max_gamma_value / total_gamma

            # Distance from spot price
            distance_from_spot = (max_gamma_strike - spot_price) / spot_price

            return {
                'max_strike': float(max_gamma_strike),
                'concentration_pct': concentration_pct,
                'distance_from_spot': distance_from_spot,
                'max_gamma_value': max_gamma_value,
                'confidence': min(1.0, concentration_pct * 2)  # Higher concentration = higher confidence
            }

        except Exception as e:
            logger.error(f"Error in enhanced gamma concentration detection: {e}")
            return {}

    def _detect_volume_anomalies(self, options_data: pd.DataFrame) -> Dict:
        """Detect unusual volume spikes indicating institutional activity."""
        try:
            if 'volume' not in options_data.columns:
                return {'detected': False}

            # Find strikes with high volume
            high_volume_threshold = self.config.get('gex_thresholds', {}).get('high_volume_threshold', 100000)
            volume_by_strike = options_data.groupby('strike')['volume'].sum()

            # Detect anomalies (>3x average volume)
            avg_volume = volume_by_strike.mean()
            anomaly_threshold = max(high_volume_threshold, avg_volume * 3)

            anomalous_strikes = volume_by_strike[volume_by_strike > anomaly_threshold]

            if anomalous_strikes.empty:
                return {'detected': False}

            max_volume_strike = anomalous_strikes.idxmax()
            max_volume = anomalous_strikes.max()

            return {
                'detected': True,
                'max_volume_strike': float(max_volume_strike),
                'max_volume': int(max_volume),
                'anomalous_strikes': anomalous_strikes.index.tolist(),
                'vs_average': max_volume / avg_volume if avg_volume > 0 else 0,
                'confidence': min(1.0, max_volume / 500000)  # Confidence based on volume level
            }

        except Exception as e:
            logger.error(f"Error in volume anomaly detection: {e}")
            return {'detected': False}

    def _detect_gamma_walls(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Identify resistance/support levels from gamma buildup."""
        try:
            if 'gamma' not in options_data.columns:
                return {}

            gamma_by_strike = options_data.groupby('strike')['gamma'].sum()

            # Find significant gamma levels (>20% of total)
            total_gamma = gamma_by_strike.abs().sum()
            significant_threshold = total_gamma * 0.20

            significant_strikes = gamma_by_strike[gamma_by_strike.abs() > significant_threshold]

            if significant_strikes.empty:
                return {}

            # Classify as resistance (above spot) or support (below spot)
            resistance_strikes = [s for s in significant_strikes.index if s > spot_price]
            support_strikes = [s for s in significant_strikes.index if s <= spot_price]

            return {
                'resistance_strikes': resistance_strikes,
                'support_strikes': support_strikes,
                'strength': 'high' if len(significant_strikes) >= 3 else 'medium'
            }

        except Exception as e:
            logger.error(f"Error in gamma walls detection: {e}")
            return {}

    def _detect_pin_setup(self, options_data: pd.DataFrame, spot_price: float, temporal_context: Dict) -> Dict:
        """Detect pin setup using Issue #73 validated methodology."""
        try:
            # Get gamma concentration data
            gamma_data = self._detect_gamma_concentration_enhanced(options_data, spot_price)

            if not gamma_data:
                return {}

            max_gamma_strike = gamma_data.get('max_strike', 0)
            concentration_pct = gamma_data.get('concentration_pct', 0)

            # Friday 3:30 PM gets boost from Issue #73 validation (75% success rate)
            is_friday_330pm = temporal_context.get('is_friday_330pm', False)
            base_probability = concentration_pct

            if is_friday_330pm and concentration_pct > 0.15:
                # Apply Issue #73 validated 75% success rate
                pin_probability = 0.75
            else:
                # Standard calculation
                pin_probability = min(0.90, base_probability * 2)

            return {
                'target_strike': max_gamma_strike,
                'pin_probability': pin_probability,
                'distance_to_target': abs(spot_price - max_gamma_strike) / spot_price,
                'friday_330pm_boost': is_friday_330pm,
                'validated_setup': is_friday_330pm and concentration_pct > 0.15
            }

        except Exception as e:
            logger.error(f"Error in pin setup detection: {e}")
            return {}

    def _calculate_dealer_exposure(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Calculate net dealer gamma exposure and positioning."""
        try:
            if 'gamma' not in options_data.columns:
                return {}

            # Estimate dealer positioning (simplified)
            total_gamma = options_data['gamma'].sum()
            call_gamma = options_data[options_data['type'] == 'call']['gamma'].sum()
            put_gamma = options_data[options_data['type'] == 'put']['gamma'].sum()

            # Find approximate gamma flip point
            gamma_by_strike = options_data.groupby('strike')['gamma'].sum()

            # Simple flip point estimation
            cumulative_gamma = gamma_by_strike.cumsum()
            zero_crossings = cumulative_gamma[cumulative_gamma.abs() < abs(total_gamma) * 0.1]

            flip_point = zero_crossings.index[0] if not zero_crossings.empty else spot_price

            return {
                'total_gamma': total_gamma,
                'call_gamma': call_gamma,
                'put_gamma': put_gamma,
                'flip_point': flip_point,
                'distance_to_flip': (spot_price - flip_point) / flip_point if flip_point > 0 else 0,
                'regime': 'short_gamma' if total_gamma < 0 else 'long_gamma'
            }

        except Exception as e:
            logger.error(f"Error in dealer exposure calculation: {e}")
            return {}

    def _llm_interpret_mechanics(self, context: Dict, patterns: List[Dict]) -> Dict:
        """Use LLM to interpret market mechanics."""
        if not self.llm:
            logger.warning("No LLM available, falling back to rule-based interpretation")
            return self._rule_based_interpretation(patterns)

        # Build LLM prompt
        try:
            prompt = self._build_mechanics_prompt(context, patterns)
            logger.debug(f"Built prompt for LLM (length: {len(prompt)} chars)")
        except Exception as e:
            logger.error(f"Prompt building failed: {e}")
            return self._rule_based_interpretation(patterns)

        try:
            # Use duck typing with proper error handling
            logger.debug("Invoking LLM for mechanics interpretation...")
            interpretation = self._invoke_llm_safely(prompt)
            logger.info(f"LLM interpretation successful: confidence={interpretation.get('confidence', 'Unknown')}")
            return interpretation

        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return self._rule_based_interpretation(patterns)

    def _invoke_llm_safely(self, prompt: str) -> Dict:
        """Safely invoke LLM with proper interface detection."""
        # Try structured interpretation method first (preferred)
        try:
            if callable(getattr(self.llm, 'interpret_mechanics', None)):
                return self.llm.interpret_mechanics(prompt)
        except (AttributeError, TypeError):
            pass

        # Try AutoGen-style interpretation
        try:
            if callable(getattr(self.llm, 'analyze_market_mechanics', None)):
                return self.llm.analyze_market_mechanics(prompt)
        except (AttributeError, TypeError):
            pass

        # Fall back to generic generate method
        try:
            if callable(getattr(self.llm, 'generate', None)):
                response = self.llm.generate(prompt)
                return self._parse_llm_response(response)
        except (AttributeError, TypeError):
            pass

        # Last resort: try calling the object directly
        try:
            response = self.llm(prompt)
            return self._parse_llm_response(response)
        except (AttributeError, TypeError, Exception):
            raise ValueError(f"LLM object {type(self.llm)} does not implement any recognized interface")

    def _rule_based_interpretation(self, patterns: List[Dict]) -> Dict:
        """Fallback rule-based interpretation when LLM unavailable."""
        if not patterns:
            return {
                'primary_mechanic': 'No clear mechanics detected',
                'who': 'Market participants',
                'whom': 'Price action',
                'what': 'Normal trading activity',
                'confidence': 0,
                'narrative': 'No significant market mechanics patterns detected.'
            }

        # Use highest confidence pattern
        primary = patterns[0]

        narrative = f"{primary['who']} are forcing {primary['whom']} to {primary['what']}. "
        narrative += f"Evidence: {', '.join(primary['evidence'])}. "

        if len(patterns) > 1:
            narrative += f"Secondary pattern: {patterns[1]['pattern']} (confidence: {patterns[1]['confidence']}%)"

        return {
            'primary_mechanic': primary['pattern'],
            'who': primary['who'],
            'whom': primary['whom'],
            'what': primary['what'],
            'confidence': primary['confidence'],
            'narrative': narrative
        }

    def _generate_trading_signal(self, interpretation: Dict, context: Dict) -> Dict:
        """Generate actionable trading signal from mechanics interpretation."""

        # Default signal
        signal = {
            'action': 'HOLD',
            'confidence': 0,
            'rationale': 'Insufficient edge detected',
            'risk_reward': None,
            'entry': None,
            'stop_loss': None,
            'target': None
        }

        # Check for sufficient confidence patterns (configurable threshold)
        min_confidence = self.config.get('min_signal_confidence', 30)  # Default 30%

        # Use pattern confidence if interpretation confidence is missing/low
        interp_confidence = interpretation.get('confidence', 0)
        pattern_confidence = context.get('overall_confidence', 0)
        effective_confidence = max(interp_confidence, pattern_confidence)

        if effective_confidence < min_confidence:
            return signal

        primary_mechanic = interpretation.get('primary_mechanic')
        gex_metrics = context.get('gex_metrics', {})

        # Also check detected patterns directly
        patterns = context.get('patterns_detected', [])
        top_pattern = patterns[0]['pattern'] if patterns else None

        logger.info(f"Signal generation: confidence {effective_confidence}% >= {min_confidence}%, pattern: {top_pattern}")

        # Apply contrarian logic for specific patterns (check both LLM and pattern detection)
        active_mechanic = primary_mechanic or top_pattern
        if active_mechanic == 'dealer_hedging':
            if gex_metrics.get('regime') == 'NEGATIVE_GAMMA_LOW':  # Fixed key name
                signal = {
                    'action': 'BUY',
                    'confidence': effective_confidence,
                    'rationale': 'Dealers forced to buy dips in negative gamma - fade the move',
                    'risk_reward': 1.5,
                    'entry': 'Market',
                    'stop_loss': '1%',
                    'target': '1.5%'
                }

        elif primary_mechanic == 'gamma_squeeze':
            signal = {
                'action': 'SELL',
                'confidence': interpretation['confidence'],
                'rationale': 'Gamma squeeze exhaustion likely - fade the squeeze',
                'risk_reward': 1.5,
                'entry': 'Market',
                'stop_loss': '1%',
                'target': '1.5%'
            }

        elif primary_mechanic == 'pin_manipulation':
            # Trade toward the pin
            signal = {
                'action': 'NEUTRAL',
                'confidence': interpretation['confidence'],
                'rationale': f"Price likely pinned to {gex_metrics.get('max_strike', 'major strike')}",
                'risk_reward': None,
                'entry': 'Sell straddle at pin',
                'stop_loss': 'Gamma flip',
                'target': 'Expiry'
            }

        return signal

    def _calculate_confidence(self, patterns: List[Dict], context: Dict) -> float:
        """Calculate overall confidence in the analysis."""
        if not patterns:
            # Base confidence from GEX regime alone
            gex_metrics = context.get('gex_metrics', {})
            if gex_metrics.get('regime') in ['NEGATIVE_GAMMA_HIGH', 'NEGATIVE_GAMMA_LOW']:
                return 30.0  # Base 30% confidence for negative GEX
            return 0.0

        # Use max pattern confidence instead of average
        max_confidence = max(p['confidence'] for p in patterns)

        # Bonus for multiple confirming patterns
        if len(patterns) > 1:
            max_confidence += 10 * (len(patterns) - 1)  # +10% per additional pattern

        # Adjust for context factors
        temporal = context.get('temporal_context', {})
        if temporal.get('is_opex'):
            max_confidence *= 1.2  # Higher confidence during OPEX
        if temporal.get('days_to_fomc', 999) < 3:
            max_confidence *= 0.8  # Lower confidence near FOMC

        return min(max_confidence, 100.0)

    def _build_mechanics_prompt(self, context: Dict, patterns: List[Dict]) -> str:
        """Build prompt for LLM mechanics interpretation using exact format."""

        # Prepare data for prompt builder
        gex_metrics = context.get('gex_metrics', {})

        # Add key strikes info if available
        if 'strike_distribution' in context:
            strike_dist = context['strike_distribution']
            if strike_dist:
                # Find heavy put OI and call walls
                gex_metrics['key_strikes'] = {
                    'heavy_put_oi': strike_dist.get('max_oi_strike', 0),
                    'call_walls': strike_dist.get('top_3_strikes', [0])[0] if strike_dist.get('top_3_strikes') else 0
                }

        # Enhance options flow with specific patterns
        options_flow = context.get('options_flow', {})

        # Add detected unusual activity
        if patterns:
            top_pattern = patterns[0]
            if top_pattern['pattern'] == 'gamma_squeeze':
                options_flow['unusual_activity'] = 'Aggressive call buying to force squeeze'
            elif top_pattern['pattern'] == 'pin_manipulation':
                options_flow['unusual_activity'] = 'Straddle selling at pin strike'
            elif top_pattern['pattern'] == 'dealer_hedging':
                options_flow['unusual_activity'] = 'Dealer hedging flows dominating price action'

        # Add market context with strike-level patterns
        market_context = {
            'price_action': context.get('price_action', {}),
            'temporal_context': context.get('temporal_context', {}),
            'strike_distribution': context.get('strike_distribution', {}),
            'volatility_surface': context.get('volatility_surface', {}),
            'strike_level_patterns': context.get('strike_level_patterns', {})  # Add enhanced patterns
        }

        # Use prompt builder with exact format
        return self.prompt_builder.build_analysis_prompt(
            date=context['date'],
            gex_metrics=gex_metrics,
            options_flow=options_flow,
            market_context=market_context
        )

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured interpretation."""
        # Use the prompt builder's parser
        parsed = self.prompt_builder.parse_llm_response(response)

        # Convert to our expected format
        primary_mechanic = parsed.get('pattern_identified', 'Unknown')

        # Extract WHO, WHOM, WHAT from key players
        who = 'Unknown'
        whom = 'Unknown'
        what = 'Unknown'

        if parsed.get('key_players'):
            if len(parsed['key_players']) >= 2:
                who = parsed['key_players'][0].get('who', 'Unknown')
                whom = parsed['key_players'][1].get('who', 'Unknown')
                what = parsed['key_players'][0].get('what', 'Unknown')

        # Calculate confidence from outcome probabilities
        confidence = 0
        if parsed.get('likely_outcomes'):
            # Use highest probability outcome as confidence
            confidences = [o.get('probability', 0)
                           for o in parsed['likely_outcomes']]
            if confidences:
                confidence = max(confidences)

        # Build narrative from mechanics and actionable intelligence
        narrative = parsed.get('mechanics', '')
        if parsed.get('actionable_intelligence'):
            narrative += '\n\nActionable: ' + \
                '; '.join(parsed['actionable_intelligence'])

        return {
            'primary_mechanic': primary_mechanic,
            'who': who,
            'whom': whom,
            'what': what,
            'confidence': confidence,
            'narrative': narrative,
            'parsed_response': parsed
        }

    # Helper methods
    def _classify_gex_regime(self, net_gex: float, spot_price: float) -> str:
        """Classify GEX regime."""
        positive_high = self.gex_thresholds.get('positive_high', 5e9)
        negative_high = self.gex_thresholds.get('negative_high', -5e9)

        if net_gex > positive_high:
            return 'POSITIVE_GAMMA_HIGH'
        elif net_gex > 0:
            return 'POSITIVE_GAMMA_LOW'
        elif net_gex > negative_high:
            return 'NEGATIVE_GAMMA_LOW'
        else:
            return 'NEGATIVE_GAMMA_HIGH'

    def _analyze_gamma_concentration(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze gamma concentration around spot."""
        if options_data.empty:
            return {}

        try:
            # Find strikes near spot (within 2%)
            near_strikes = options_data[
                (options_data['strike'] >= spot_price * 0.98) &
                (options_data['strike'] <= spot_price * 1.02)
            ]

            total_gamma = options_data['gamma'].sum(
            ) if 'gamma' in options_data.columns else 0
            near_gamma = near_strikes['gamma'].sum(
            ) if 'gamma' in near_strikes.columns else 0

            return {
                'concentration_score': near_gamma / max(total_gamma, 1),
                'near_strikes_count': len(near_strikes['strike'].unique()),
                'peak_gamma_strike': options_data.loc[options_data['gamma'].idxmax(), 'strike'] if 'gamma' in options_data.columns else 0
            }

        except Exception as e:
            logger.error(f"Error analyzing gamma concentration: {e}")
            return {}


    def _analyze_strike_distribution(self, options_data: pd.DataFrame) -> Dict:
        """Analyze strike distribution and OI concentration."""
        if options_data.empty or 'open_interest' not in options_data.columns:
            return {}

        try:
            strike_oi = options_data.groupby('strike')['open_interest'].sum()
            total_oi = strike_oi.sum()

            if total_oi == 0:
                return {}

            max_oi_strike = strike_oi.idxmax()
            max_oi_concentration = strike_oi.max() / total_oi

            return {
                'max_oi_strike': max_oi_strike,
                'max_oi_concentration': max_oi_concentration,
                'top_3_strikes': strike_oi.nlargest(3).index.tolist(),
                'oi_dispersion': strike_oi.std() / strike_oi.mean() if strike_oi.mean() > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error analyzing strike distribution: {e}")
            return {}

    def _analyze_volatility_surface(self, options_data: pd.DataFrame) -> Dict:
        """Analyze volatility surface characteristics."""
        if options_data.empty or 'iv' not in options_data.columns:
            return {}

        try:
            # Separate calls and puts
            calls = options_data[options_data['type'] == 'call']
            puts = options_data[options_data['type'] == 'put']

            # Calculate skew
            atm_iv = options_data['iv'].median()
            otm_put_iv = puts[puts['delta'] < -
                              0.3]['iv'].mean() if len(puts) > 0 else atm_iv
            otm_call_iv = calls[calls['delta'] >
                                0.3]['iv'].mean() if len(calls) > 0 else atm_iv

            return {
                'atm_iv': atm_iv,
                'put_skew': otm_put_iv - atm_iv,
                'call_skew': otm_call_iv - atm_iv,
                'term_structure': self._analyze_term_structure(options_data)
            }

        except Exception as e:
            logger.error(f"Error analyzing volatility surface: {e}")
            return {}

    def _analyze_term_structure(self, options_data: pd.DataFrame) -> str:
        """Analyze IV term structure."""
        if 'expiry' not in options_data.columns or 'iv' not in options_data.columns:
            return 'unknown'

        try:
            # Group by expiry and get average IV
            options_data['expiry'] = pd.to_datetime(options_data['expiry'])
            term_structure = options_data.groupby(
                'expiry')['iv'].mean().sort_index()

            if len(term_structure) < 2:
                return 'insufficient_data'

            # Check if contango or backwardation
            if term_structure.iloc[-1] > term_structure.iloc[0]:
                return 'contango'
            else:
                return 'backwardation'

        except Exception as e:
            logger.error(f"Error analyzing term structure: {e}")
            return 'error'

    def _calculate_skew(self, options_data: pd.DataFrame) -> float:
        """Calculate skew for options."""
        if options_data.empty or 'iv' not in options_data.columns:
            return 0.0

        try:
            # Simple skew: OTM vs ATM IV difference
            if 'delta' in options_data.columns:
                otm = options_data[abs(options_data['delta']) < 0.3]
                atm = options_data[abs(options_data['delta']) >= 0.3]

                if len(otm) > 0 and len(atm) > 0:
                    return otm['iv'].mean() - atm['iv'].mean()

        except Exception as e:
            logger.error(f"Error calculating skew: {e}")

        return 0.0

    def _is_opex_week(self, date) -> bool:
        """Check if date is in OPEX week."""
        # Use the date_utils function
        return is_opex_week(date)

    def _days_to_next_fomc(self, date) -> int:
        """Calculate days to next FOMC meeting."""
        # Simplified - would need actual FOMC calendar
        # For now, assume FOMC every 6 weeks on Wednesday
        days_since_epoch = (date - datetime.datetime(2024, 1, 31)).days
        days_until_fomc = 42 - (days_since_epoch % 42)
        return days_until_fomc

    def _get_fed_context(self, date) -> Optional[Dict]:
        """Get Fed context for the date."""
        # Would integrate with Fed calendar/news
        # For now, return based on proximity to FOMC
        days_to_fomc = self._days_to_next_fomc(date)

        if days_to_fomc <= 3:
            return {
                'event': 'FOMC_WEEK',
                'days_to_event': days_to_fomc,
                'blackout': True,
                'impact': 'HIGH'
            }
        elif days_to_fomc <= 10:
            return {
                'event': 'PRE_FOMC',
                'days_to_event': days_to_fomc,
                'blackout': days_to_fomc <= 7,
                'impact': 'MEDIUM'
            }

        return None

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure."""
        return {
            'date': None,
            'mechanics_interpretation': {
                'primary_mechanic': 'No data',
                'who': 'Unknown',
                'whom': 'Unknown',
                'what': 'No analysis possible',
                'confidence': 0,
                'narrative': 'Insufficient data for analysis'
            },
            'actionable_signal': {
                'action': 'NO_TRADE',
                'confidence': 0,
                'rationale': 'No data available'
            },
            'patterns_detected': [],
            'gex_metrics': {},
            'confidence': 0
        }

    def _populate_database_entry(self, conn, date_str: str, gex_metrics: Dict):
        """Populate database with calculated GEX metrics.

        Handles both daily and intra-day data population.
        """
        try:
            # Determine regime
            net_gex = gex_metrics.get('net_gex', 0)
            if net_gex < -5e9:
                regime = 'NEGATIVE_GAMMA_HIGH'
            elif net_gex < 0:
                regime = 'NEGATIVE_GAMMA_LOW'
            elif net_gex > 5e9:
                regime = 'POSITIVE_GAMMA_HIGH'
            else:
                regime = 'POSITIVE_GAMMA_LOW'

            # Determine if this is intra-day timestamp or daily date
            is_intraday = ' ' in date_str and ':' in date_str

            cursor = conn.cursor()

            if is_intraday:
                # Insert into intraday table
                cursor.execute("""
                    INSERT OR REPLACE INTO intraday_gex_metrics
                    (symbol, timestamp, spot_price, total_gex, net_call_gex, net_put_gex,
                     gamma_flip_point, flip_ratio, gex_regime, data_quality_score,
                     options_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.symbol,
                    date_str,  # This is actually a timestamp for intraday
                    gex_metrics.get('spot_price', 0),
                    net_gex,
                    gex_metrics.get('call_gamma', 0),
                    gex_metrics.get('put_gamma', 0),
                    gex_metrics.get('flip_level', 0),
                    gex_metrics.get('gamma_concentration', {}).get('concentration_score', 0)
                        if isinstance(gex_metrics.get('gamma_concentration'), dict)
                        else gex_metrics.get('gamma_concentration', 0),
                    regime,
                    1.0,  # data_quality_score
                    0,    # options_count (would need to count from options_data)
                    datetime.datetime.now().isoformat()
                ))
            else:
                # Insert into daily table
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_gex_metrics
                    (symbol, date, spot_price, total_gex, net_call_gex, net_put_gex,
                     gamma_flip_point, flip_ratio, gex_regime, data_quality_score,
                     options_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.symbol,
                    date_str,
                    gex_metrics.get('spot_price', 0),
                    net_gex,
                    gex_metrics.get('call_gamma', 0),
                    gex_metrics.get('put_gamma', 0),
                    gex_metrics.get('flip_level', 0),
                    gex_metrics.get('gamma_concentration', {}).get('concentration_score', 0)
                        if isinstance(gex_metrics.get('gamma_concentration'), dict)
                        else gex_metrics.get('gamma_concentration', 0),
                    regime,
                    1.0,  # data_quality_score
                    0,    # options_count (would need to count from options_data)
                    datetime.datetime.now().isoformat()
                ))

            conn.commit()
            table_type = "intraday" if is_intraday else "daily"
            logger.debug(f"Populated {table_type} database entry for {self.symbol} {date_str}")

        except Exception as e:
            logger.error(f"Failed to populate database entry for {date_str}: {e}")
            # Don't raise - we still want to return the calculated data
