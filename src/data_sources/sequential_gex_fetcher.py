"""
Sequential GEX Data Fetcher - Paper #2
Retrieves N-day GEX windows for regime and trajectory analysis.

Issues: #89, #107, #108
Created: November 3, 2025
Updated: November 5, 2025 (30-day regime pivot)

Key Design Principles:
1. Reuse existing GEXCacheManager (don't duplicate infrastructure)
2. Strict sequence completeness (all N days required)
3. Support variable window sizes (5-day trajectories, 30-day regimes)
4. Pre-calculate metrics (not in LLM prompt)

Historical Context:
- Originally designed for 5-day trajectory analysis
- Pivoted to 30-day regime windows (Nov 5, 2025)
- Reason: 5-day detected universal hedging (98-100%), not distinctive patterns
- 30-day expected to show selectivity (30-50% detection on persistent regimes)
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from gex_db_infrastructure.cache.gex_cache_manager import GEXCacheManager
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager

logger = logging.getLogger(__name__)


class SequentialGEXFetcher:
    """Fetch N-day GEX sequences for regime and trajectory analysis (Paper #2).

    Architecture:
    - Delegates to existing GEXCacheManager for single-day retrieval
    - Scans cache directory for trading days (robust to holidays)
    - Strict mode: Skips incomplete sequences (all N days required)
    - Calculates trajectory/regime metrics for LLM prompt generation
    - Supports variable window sizes (5-day, 30-day, etc.)

    Usage Examples:
        # 30-day regime windows (Paper #2 pivot)
        fetcher = SequentialGEXFetcher(unified_cache_manager, window_size=30)
        result = fetcher.get_sequential_gex('SPY', '2024-01-31')

        # 5-day trajectory windows (original approach)
        fetcher = SequentialGEXFetcher(unified_cache_manager, window_size=5)
        result = fetcher.get_sequential_gex('SPY', '2024-01-12')

        # Returns None if incomplete sequence
        if result:
            gex_sequence = result['gex_sequence']  # N days
            metrics = result['trajectory_metrics']  # Trend, velocity, drift
    """

    def __init__(self, cache_manager: UnifiedCacheManager, window_size: int = 30):
        """Initialize Sequential GEX Fetcher.

        Args:
            cache_manager: UnifiedCacheManager instance (provides GEX cache access)
            window_size: Number of days in sequence window (default 30 for regime analysis)
                         Set to 5 for legacy trajectory analysis

        Note: Default changed from 5 to 30 on Nov 5, 2025 (regime pivot)
        """
        self.cache = cache_manager
        self.gex_cache = cache_manager.gex_cache
        self.window_size = window_size

        logger.info(f"SequentialGEXFetcher initialized with window_size={window_size} days")

    def get_sequential_gex(self, symbol: str, end_date: str, lookback_days: Optional[int] = None) -> Optional[Dict]:
        """Fetch GEX data for N-day window ending at end_date.

        Args:
            symbol: Trading symbol (SPY, SPX, etc.)
            end_date: Final date in sequence (Day T+0)
            lookback_days: Number of historical days (default: self.window_size)
                          Override to use different window size for specific call

        Returns:
            Dictionary with:
            {
                'gex_sequence': [  # List of N daily GEX summaries
                    {
                        'date': '2024-01-02',
                        'obfuscated_date': 'T-29',  # For 30-day window
                        'net_gex': -2.1,
                        'flip_point': 520.0,
                        'spot_price': 518.5,
                        'call_gex': -1.5,
                        'put_gex': -0.6,
                        ...
                    },
                    ...
                ],
                'trajectory_metrics': {
                    'gex_trend': 'INCREASING',  # INCREASING | DECREASING | STABLE
                    'gex_velocity': -0.55,      # Avg daily change (B$/day)
                    'flip_drift': 3.0,          # Flip point movement
                    'price_drift': 5.5,         # Underlying price movement
                    'trajectory_classification': 'accumulation'
                }
            }

            Returns None if:
            - Incomplete sequence (< lookback_days)
            - Missing data for any day in window
            - Invalid end_date (no trading day)

        Examples:
            # Use instance window_size (30 days)
            result = fetcher.get_sequential_gex('SPY', '2024-01-31')

            # Override for specific call (5 days)
            result = fetcher.get_sequential_gex('SPY', '2024-01-12', lookback_days=5)

            if result:
                print(f"GEX trajectory: {result['trajectory_metrics']['gex_trend']}")
                print(f"Classification: {result['trajectory_metrics']['trajectory_classification']}")
        """
        # Use instance window_size if not specified
        if lookback_days is None:
            lookback_days = self.window_size

        # Get trading days before end_date (inclusive)
        dates = self._get_trading_days_before(symbol, end_date, lookback_days)

        # Validate sequence completeness
        if len(dates) < lookback_days:
            logger.warning(
                f"Incomplete sequence for {symbol} ending {end_date}: "
                f"Expected {lookback_days} days, found {len(dates)}"
            )
            return None

        # Fetch GEX summary for each day
        gex_sequence = []
        for i, date in enumerate(dates):
            gex_summary = self.gex_cache.get_gex_summary(symbol, date)

            if not gex_summary:
                logger.warning(f"Missing GEX data for {symbol} on {date}")
                return None  # Strict: skip incomplete sequences

            # Add metadata for sequential analysis
            days_back = lookback_days - i - 1
            gex_summary["date"] = date
            gex_summary["obfuscated_date"] = f"T-{days_back}" if days_back > 0 else "T+0"

            gex_sequence.append(gex_summary)

        # Calculate trajectory metrics
        trajectory_metrics = self.calculate_trajectory_metrics(gex_sequence)

        return {
            "gex_sequence": gex_sequence,
            "trajectory_metrics": trajectory_metrics,
            "metadata": {
                "symbol": symbol,
                "end_date": end_date,
                "lookback_days": lookback_days,
                "window_size": self.window_size,
                "sequence_complete": True,
            },
        }

    def _get_trading_days_before(self, symbol: str, end_date: str, n_days: int) -> List[str]:
        """Get N trading days before end_date (inclusive).

        Strategy: Query database for actual trading days (Nov 20, 2025 update).
        Rationale: Database is single source of truth with complete historical data.

        Args:
            symbol: Trading symbol
            end_date: Final date (inclusive)
            n_days: Number of trading days to retrieve

        Returns:
            List of date strings: ['2024-01-08', '2024-01-09', ..., '2024-01-12']
            Empty list if database not found or insufficient data

        Example:
            dates = fetcher._get_trading_days_before('SPY', '2024-01-12', 5)
            # Returns: ['2024-01-08', '2024-01-09', '2024-01-10', '2024-01-11', '2024-01-12']
        """
        # Use database as primary source (Nov 20, 2025 update)
        db_path = Path(".cache/gex_database.db")

        if not db_path.exists():
            logger.error(f"Database not found: {db_path}")
            # Fallback to file cache (legacy behavior)
            return self._get_trading_days_from_files(symbol, end_date, n_days)

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT date
                    FROM daily_gex_metrics
                    WHERE symbol = ? AND date <= ?
                    ORDER BY date ASC
                    """,
                    (symbol.upper(), end_date),
                )
                available_dates = [row[0] for row in cursor.fetchall()]

            # Return last N dates (inclusive of end_date)
            if len(available_dates) >= n_days:
                return available_dates[-n_days:]
            elif len(available_dates) == 0:
                # No data in database - fall back to file cache
                logger.info(f"No data in database for {symbol} {end_date}, falling back to file cache")
                return self._get_trading_days_from_files(symbol, end_date, n_days)
            else:
                logger.warning(
                    f"Insufficient trading days for {symbol} ending {end_date}: "
                    f"Expected {n_days}, found {len(available_dates)}"
                )
                return available_dates

        except Exception as e:
            logger.error(f"Database query failed: {e}, falling back to file cache")
            return self._get_trading_days_from_files(symbol, end_date, n_days)

    def _get_trading_days_from_files(self, symbol: str, end_date: str, n_days: int) -> List[str]:
        """
        Fallback method: Get trading days from file cache.

        Used when database is unavailable or query fails.
        """
        cache_dir = self.gex_cache.gex_cache_dir / symbol.upper()

        if not cache_dir.exists():
            logger.error(f"Cache directory not found: {cache_dir}")
            return []

        # Get all available dates before end_date (inclusive)
        available_dates = []
        for date_dir in sorted(cache_dir.iterdir()):
            if date_dir.is_dir():
                date_str = date_dir.name
                # Include dates up to and including end_date
                if date_str <= end_date:
                    available_dates.append(date_str)

        # Return last N dates (inclusive of end_date)
        if len(available_dates) >= n_days:
            return available_dates[-n_days:]
        else:
            logger.warning(
                f"Insufficient trading days for {symbol} ending {end_date}: "
                f"Expected {n_days}, found {len(available_dates)}"
            )
            return available_dates

    def calculate_trajectory_metrics(self, gex_sequence: List[Dict]) -> Dict:
        """Calculate trajectory summary metrics for LLM prompt.

        Computes:
        - GEX trend direction (INCREASING/DECREASING/STABLE)
        - GEX velocity (average daily change)
        - Flip point drift (movement T-4 to T+0)
        - Price drift (underlying movement)
        - Trajectory classification (accumulation/relief/reversal/persistent)

        Args:
            gex_sequence: List of 5 daily GEX summaries

        Returns:
            {
                'gex_trend': 'INCREASING' | 'DECREASING' | 'STABLE',
                'gex_velocity': float,  # Average daily change in GEX (B$/day)
                'flip_drift': float,    # Flip point movement (T-4 to T+0)
                'price_drift': float,   # Underlying price movement
                'trajectory_classification': 'accumulation' | 'relief' | 'reversal' | 'persistent'
            }

        Example:
            metrics = fetcher.calculate_trajectory_metrics(gex_sequence)
            print(f"GEX velocity: ${metrics['gex_velocity']:.2f}B per day")
            print(f"Classification: {metrics['trajectory_classification']}")
        """
        if not gex_sequence or len(gex_sequence) < 2:
            logger.warning("Cannot calculate trajectory metrics: insufficient data")
            return {
                "gex_trend": "UNKNOWN",
                "gex_velocity": 0.0,
                "flip_drift": 0.0,
                "price_drift": 0.0,
                "trajectory_classification": "unknown",
            }

        # Extract time series (convert to billions for readability)
        gex_values = [day.get("net_gex", 0) / 1e9 for day in gex_sequence]
        flip_values = [day.get("flip_point") or 0 for day in gex_sequence]  # Handle None from database
        price_values = [day.get("spot_price", 0) for day in gex_sequence]

        # Calculate changes
        gex_change = gex_values[-1] - gex_values[0]
        gex_velocity = gex_change / (len(gex_sequence) - 1)  # Avg daily change

        flip_drift = flip_values[-1] - flip_values[0]
        price_drift = price_values[-1] - price_values[0]

        # Classify trend direction
        STABLE_THRESHOLD = 0.1  # $100M per day (noise threshold)
        if abs(gex_velocity) < STABLE_THRESHOLD:
            gex_trend = "STABLE"
        elif gex_velocity > 0:
            gex_trend = "INCREASING"
        else:
            gex_trend = "DECREASING"

        # Classify trajectory type
        trajectory_type = self._classify_trajectory(gex_values)

        return {
            "gex_trend": gex_trend,
            "gex_velocity": gex_velocity,
            "flip_drift": flip_drift,
            "price_drift": price_drift,
            "trajectory_classification": trajectory_type,
        }

    def _classify_trajectory(self, gex_values: List[float]) -> str:
        """Classify 5-day GEX trajectory type.

        Classification Logic:
        1. Reversal: Sign flip (neg → pos or pos → neg)
        2. Accumulation: |GEX| magnitude increasing >20%
        3. Relief: |GEX| magnitude decreasing >20%
        4. Persistent: Stable magnitude within ±20%

        Args:
            gex_values: List of net GEX values (in billions)

        Returns:
            'accumulation' | 'relief' | 'reversal' | 'persistent'

        Examples:
            Accumulation: [-2.1, -3.2, -4.1, -4.8, -5.2] → magnitude growing
            Relief:       [-5.2, -4.1, -3.2, -2.1, -1.0] → magnitude shrinking
            Reversal:     [-3.0, -1.0, +0.5, +2.0, +3.0] → sign flip
            Persistent:   [-5.0, -4.9, -5.1, -5.2, -5.0] → stable
        """
        if not gex_values or len(gex_values) < 2:
            return "unknown"

        start_gex = gex_values[0]
        end_gex = gex_values[-1]

        # Check for sign reversal
        if (start_gex < 0 and end_gex > 0) or (start_gex > 0 and end_gex < 0):
            return "reversal"

        # Calculate magnitude change
        start_abs = abs(start_gex)
        end_abs = abs(end_gex)

        # Avoid division by zero
        if start_abs < 0.01:  # Less than $10M (negligible GEX)
            return "persistent"

        pct_change = (end_abs - start_abs) / start_abs

        # Classify by magnitude change
        ACCUMULATION_THRESHOLD = 0.20  # 20% increase
        RELIEF_THRESHOLD = -0.20  # 20% decrease

        if pct_change > ACCUMULATION_THRESHOLD:
            return "accumulation"
        elif pct_change < RELIEF_THRESHOLD:
            return "relief"
        else:
            return "persistent"

    def validate_sequence_data_quality(self, gex_sequence: List[Dict]) -> Dict[str, bool]:
        """Validate data quality of GEX sequence.

        Checks:
        - All required fields present (net_gex, flip_point, spot_price)
        - No NaN or infinite values
        - Reasonable value ranges

        Args:
            gex_sequence: List of 5 daily GEX summaries

        Returns:
            {
                'valid': bool,
                'errors': List[str]
            }

        Note: Currently basic validation. Can be extended for Paper #2 Phase 2.
        """
        errors = []

        required_fields = ["net_gex", "flip_point", "spot_price"]

        for i, day in enumerate(gex_sequence):
            day_label = day.get("obfuscated_date", f"Day {i}")

            # Check required fields
            for field in required_fields:
                if field not in day:
                    errors.append(f"{day_label}: Missing field '{field}'")
                    continue

                value = day[field]

                # Check for NaN/inf
                if value is None or (isinstance(value, float) and (value != value or abs(value) == float("inf"))):
                    errors.append(f"{day_label}: Invalid {field} value: {value}")
                    continue

            # Check reasonable ranges (sanity checks)
            if "net_gex" in day:
                net_gex = day["net_gex"]
                if abs(net_gex) > 1e12:  # > $1 trillion (unrealistic)
                    errors.append(f"{day_label}: Unrealistic net_gex: {net_gex}")

            if "spot_price" in day:
                spot = day["spot_price"]
                if spot < 0 or spot > 10000:  # SPY range check
                    errors.append(f"{day_label}: Unrealistic spot_price: {spot}")

        return {"valid": len(errors) == 0, "errors": errors}

    def get_sequential_statistics(self, symbol: str, start_date: str, end_date: str, lookback_days: int = 5) -> Dict:
        """Get statistics about sequential windows in date range.

        Useful for validation planning (how many windows available?).

        Args:
            symbol: Trading symbol
            start_date: First test date (after warmup)
            end_date: Last test date
            lookback_days: Window size

        Returns:
            {
                'total_dates': int,
                'valid_windows': int,
                'incomplete_windows': int,
                'missing_data_windows': int,
                'coverage_pct': float
            }

        Example:
            stats = fetcher.get_sequential_statistics('SPY', '2024-01-08', '2024-12-31', 5)
            print(f"Valid windows: {stats['valid_windows']}/{stats['total_dates']}")
        """
        cache_dir = self.gex_cache.gex_cache_dir / symbol.upper()

        if not cache_dir.exists():
            return {"error": f"Cache directory not found: {cache_dir}", "total_dates": 0, "valid_windows": 0}

        # Get all dates in range
        all_dates = sorted([d.name for d in cache_dir.iterdir() if d.is_dir() and start_date <= d.name <= end_date])

        valid_windows = 0
        incomplete_windows = 0
        missing_data_windows = 0

        for date in all_dates:
            result = self.get_sequential_gex(symbol, date, lookback_days)

            if result is None:
                incomplete_windows += 1
            elif not self.validate_sequence_data_quality(result["gex_sequence"])["valid"]:
                missing_data_windows += 1
            else:
                valid_windows += 1

        total_dates = len(all_dates)
        coverage_pct = (valid_windows / total_dates * 100) if total_dates > 0 else 0

        return {
            "total_dates": total_dates,
            "valid_windows": valid_windows,
            "incomplete_windows": incomplete_windows,
            "missing_data_windows": missing_data_windows,
            "coverage_pct": coverage_pct,
        }
