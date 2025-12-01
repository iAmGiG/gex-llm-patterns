"""Production Research Cache for Academic Paper Reproducibility.

Two-tier architecture:
- Tier 1 (Hot): SQLite for fast lookups during research workflows
- Tier 2 (Cold): Parquet archives for immutable data lakes

Designed for Papers 1-5 with complete audit trails, experiment versioning,
and reproducibility from any git commit.

Based on AutoGen-Trader's TradingCacheManager patterns with research extensions.
"""

import json
import logging
import sqlite3
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.date_utils import get_datetime_now, now_iso, parse_date_string

logger = logging.getLogger(__name__)


class ResearchCache:
    """Production-grade cache for academic research workflows.

    Features:
    - SQLite-based hot cache for fast lookups (<100ms)
    - Parquet cold storage for strike-level data
    - Experiment versioning with git integration
    - Obfuscation tracking for unbiased validation
    - Pattern library versioning across papers
    - Complete data lineage and audit trails

    Example:
        >>> cache = ResearchCache()
        >>> # Get detections for Paper 1
        >>> detections = cache.get_detections(
        ...     symbol="SPY",
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ...     pattern_ids=["gamma_positioning"]
        ... )
        >>> # Record new experiment run
        >>> cache.record_experiment_run(
        ...     run_id="paper1_validation_v2",
        ...     config={"llm_model": "o3-mini", "threshold": 60}
        ... )
    """

    def __init__(self, db_path: str = ".cache/research_cache.db"):
        """Initialize research cache.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._write_lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Create all tables and indexes."""
        with sqlite3.connect(self.db_path) as conn:
            # ============================================================
            # MARKET DATA (adopted from AutoGen-Trader TradingCacheManager)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Asset identification
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    source TEXT NOT NULL,

                    -- OHLCV data
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL NOT NULL,
                    volume REAL,
                    vwap REAL,

                    -- Smart TTL (10yr historical, 24hr recent)
                    cached_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,

                    UNIQUE(symbol, trading_date, source)
                )
            """
            )

            # ============================================================
            # OPTIONS CHAIN (raw Polygon/Alpha Vantage data)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS options_chain (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Contract identification
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
                    expiration TEXT NOT NULL,

                    -- Pricing
                    bid REAL,
                    ask REAL,
                    last REAL,
                    volume INTEGER,
                    open_interest INTEGER,

                    -- Greeks
                    implied_volatility REAL,
                    delta REAL,
                    gamma REAL,
                    theta REAL,
                    vega REAL,
                    rho REAL,

                    -- Metadata
                    contract_symbol TEXT,
                    underlying_price REAL,
                    source TEXT NOT NULL DEFAULT 'polygon',
                    data_quality_score REAL DEFAULT 1.0,
                    cached_at TEXT NOT NULL,

                    UNIQUE(symbol, trading_date, strike, option_type, expiration, source)
                )
            """
            )

            # ============================================================
            # GEX SUMMARY (daily aggregated metrics)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gex_summary (
                    -- Identification (composite primary key)
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,

                    -- Core GEX metrics
                    total_gex REAL,
                    net_gex REAL,
                    call_gex REAL,
                    put_gex REAL,

                    -- Key levels
                    flip_point REAL,
                    max_gamma_strike REAL,

                    -- Concentration metrics
                    call_concentration REAL,
                    put_concentration REAL,
                    oi_concentration REAL,

                    -- Spot context
                    underlying_price REAL,
                    spot_to_flip_pct REAL,

                    -- Calculation metadata
                    calculation_method TEXT DEFAULT 'black_scholes_iv',
                    calculation_duration_ms INTEGER,
                    contracts_processed INTEGER,

                    -- Strike detail file reference (Parquet)
                    strike_detail_path TEXT,

                    -- Timestamps
                    calculation_timestamp TEXT NOT NULL,
                    cached_at TEXT NOT NULL,

                    PRIMARY KEY(symbol, trading_date)
                )
            """
            )

            # ============================================================
            # LLM DETECTIONS (pattern detection results)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Detection context
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    pattern_id TEXT NOT NULL,

                    -- LLM configuration
                    llm_model TEXT NOT NULL,
                    llm_temperature REAL DEFAULT 0.7,
                    prompt_version TEXT NOT NULL,
                    obfuscation_id TEXT,

                    -- Detection result
                    detected INTEGER NOT NULL,  -- 0 or 1
                    confidence INTEGER CHECK(confidence >= 0 AND confidence <= 100),

                    -- Structured output (WHO/WHOM/WHAT)
                    who TEXT,
                    whom TEXT,
                    what TEXT,
                    time_horizon TEXT,

                    -- Full reasoning chain
                    reasoning_chain TEXT,
                    raw_llm_response TEXT,

                    -- Processing metadata
                    processing_timestamp TEXT NOT NULL,
                    processing_duration_ms INTEGER,
                    token_count INTEGER,

                    -- Experiment tracking
                    experiment_run_id TEXT,

                    UNIQUE(symbol, trading_date, pattern_id, llm_model, prompt_version)
                )
            """
            )

            # ============================================================
            # VALIDATION RESULTS (outcome verification)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Link to detection
                    detection_id INTEGER NOT NULL,

                    -- Forward returns
                    t1_return REAL,
                    t3_return REAL,
                    t5_return REAL,

                    -- Risk metrics
                    max_gain REAL,
                    max_drawdown REAL,
                    realized_volatility REAL,

                    -- Materialization
                    materialized INTEGER,  -- 0 or 1
                    outcome_type TEXT CHECK(outcome_type IN ('ACCURATE', 'PARTIAL', 'MISSED', 'PENDING')),

                    -- Validation metadata
                    validation_timestamp TEXT NOT NULL,
                    validation_method TEXT DEFAULT 'forward_returns',

                    FOREIGN KEY(detection_id) REFERENCES llm_detections(id)
                )
            """
            )

            # ============================================================
            # PATTERN LIBRARY (versioned pattern definitions)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pattern_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Pattern identification
                    pattern_id TEXT NOT NULL,
                    version TEXT NOT NULL,

                    -- Definition (WHO/WHOM/WHAT structure)
                    name TEXT NOT NULL,
                    description TEXT,
                    who TEXT NOT NULL,
                    whom TEXT NOT NULL,
                    what TEXT NOT NULL,

                    -- Thresholds (JSON)
                    thresholds_json TEXT NOT NULL,

                    -- Confidence requirements
                    min_confidence INTEGER DEFAULT 60,

                    -- Versioning
                    created_date TEXT NOT NULL,
                    modified_date TEXT,
                    active INTEGER DEFAULT 1,

                    -- Paper tracking
                    used_in_papers TEXT,  -- JSON array: ["paper1", "paper2"]

                    UNIQUE(pattern_id, version)
                )
            """
            )

            # ============================================================
            # EXPERIMENT RUNS (immutable metadata for reproducibility)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Run identification
                    run_id TEXT NOT NULL UNIQUE,
                    run_name TEXT,

                    -- Git integration
                    git_commit TEXT,
                    git_branch TEXT,

                    -- Configuration (complete snapshot)
                    config_json TEXT NOT NULL,

                    -- Scope
                    symbols TEXT NOT NULL,  -- JSON array
                    date_range_start TEXT NOT NULL,
                    date_range_end TEXT NOT NULL,
                    pattern_ids TEXT NOT NULL,  -- JSON array

                    -- LLM configuration
                    llm_model TEXT NOT NULL,
                    llm_temperature REAL,
                    prompt_version TEXT NOT NULL,

                    -- Results summary
                    total_tests INTEGER,
                    total_detections INTEGER,
                    detection_rate REAL,
                    overall_accuracy REAL,

                    -- Paper tracking
                    paper_version TEXT,

                    -- Timestamps
                    created_date TEXT NOT NULL,
                    completed_date TEXT
                )
            """
            )

            # ============================================================
            # OBFUSCATION MAPPINGS (audit trail for unbiased validation)
            # ============================================================
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS obfuscation_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Identification
                    obfuscation_id TEXT NOT NULL UNIQUE,
                    schema_type TEXT NOT NULL,  -- 'relative_day', 'anonymized_ticker'

                    -- Mappings (JSON)
                    date_mapping_json TEXT,  -- {"2024-01-15": "Day T+0"}
                    symbol_mapping_json TEXT,  -- {"SPY": "INDEX_1"}

                    -- Usage tracking
                    used_in_experiments TEXT,  -- JSON array of experiment run_ids
                    used_in_papers TEXT,  -- JSON array: ["paper1"]

                    -- Timestamps
                    created_date TEXT NOT NULL
                )
            """
            )

            # ============================================================
            # INDEXES for fast lookups
            # ============================================================

            # Market data indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_symbol_date ON market_data(symbol, trading_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_expires ON market_data(expires_at)")

            # Options chain indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_options_symbol_date ON options_chain(symbol, trading_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_options_strike ON options_chain(symbol, trading_date, strike)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_options_expiration ON options_chain(expiration)")

            # GEX indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gex_symbol_date ON gex_summary(symbol, trading_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gex_flip_point ON gex_summary(symbol, flip_point)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gex_net ON gex_summary(symbol, net_gex)")

            # Detection indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detect_symbol_date ON llm_detections(symbol, trading_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detect_pattern ON llm_detections(pattern_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detect_model ON llm_detections(llm_model)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detect_experiment ON llm_detections(experiment_run_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_detect_confidence ON llm_detections(confidence)")

            # Validation indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_detection ON validation_results(detection_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_outcome ON validation_results(outcome_type)")

            # Experiment indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_paper ON experiment_runs(paper_version)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_model ON experiment_runs(llm_model)")

            conn.commit()

        self.logger.info(f"Research cache initialized: {self.db_path}")

    # ================================================================
    # MARKET DATA METHODS
    # ================================================================

    def get_market_data(
        self, symbol: str, start_date: str, end_date: str, source: str = None
    ) -> Optional[pd.DataFrame]:
        """Get cached market data for date range.

        Args:
            symbol: Ticker symbol (e.g., "SPY")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Data source filter (None = any)

        Returns:
            DataFrame with OHLCV data, or None if not found
        """
        try:
            query = """
                SELECT trading_date, open, high, low, close, volume, vwap
                FROM market_data
                WHERE symbol = ?
                  AND trading_date >= ?
                  AND trading_date <= ?
                  AND datetime(expires_at) > datetime('now')
            """
            params = [symbol.upper(), start_date, end_date]

            if source:
                query += " AND source = ?"
                params.append(source)

            query += " ORDER BY trading_date ASC"

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                return None

            df["trading_date"] = pd.to_datetime(df["trading_date"])
            df.set_index("trading_date", inplace=True)
            df.index.name = "date"

            return df

        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return None

    def set_market_data(self, symbol: str, data: pd.DataFrame, source: str, ttl_hours: int = None):
        """Cache market data with smart expiration.

        Args:
            symbol: Ticker symbol
            data: DataFrame with OHLCV columns
            source: Data source ("polygon", "alpha_vantage", etc.)
            ttl_hours: Custom TTL (None = auto-calculate)
        """
        if data.empty:
            return

        try:
            df = data.copy()

            # Ensure date column
            if isinstance(df.index, pd.DatetimeIndex):
                df.reset_index(inplace=True)
                if "index" in df.columns:
                    df.rename(columns={"index": "date"}, inplace=True)

            df["trading_date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df["symbol"] = symbol.upper()
            df["source"] = source
            df["cached_at"] = now_iso()

            # Smart expiration
            if ttl_hours:
                expires_at = get_datetime_now() + timedelta(hours=ttl_hours)
                df["expires_at"] = expires_at.isoformat()
            else:
                df["expires_at"] = df["trading_date"].apply(lambda d: self._calculate_expiration(d).isoformat())

            # Map columns to schema
            column_mapping = {
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "vwap": "vwap",
            }

            records = []
            for _, row in df.iterrows():
                record = {
                    "symbol": row["symbol"],
                    "trading_date": row["trading_date"],
                    "source": row["source"],
                    "cached_at": row["cached_at"],
                    "expires_at": row["expires_at"],
                }
                for src, dst in column_mapping.items():
                    if src in row and pd.notna(row[src]):
                        record[dst] = float(row[src])
                records.append(record)

            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    for record in records:
                        columns = ", ".join(record.keys())
                        placeholders = ", ".join(["?" for _ in record])
                        conn.execute(
                            f"INSERT OR REPLACE INTO market_data ({columns}) VALUES ({placeholders})",
                            list(record.values()),
                        )
                    conn.commit()

            self.logger.debug(f"Cached {len(records)} market data records for {symbol}")

        except Exception as e:
            self.logger.error(f"Error caching market data: {e}")

    # ================================================================
    # GEX METHODS
    # ================================================================

    def get_gex_summary(self, symbol: str, trading_date: str) -> Optional[Dict[str, Any]]:
        """Get GEX summary for a specific date.

        Args:
            symbol: Ticker symbol
            trading_date: Date (YYYY-MM-DD)

        Returns:
            Dict with GEX metrics, or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM gex_summary
                    WHERE symbol = ? AND trading_date = ?
                    """,
                    [symbol.upper(), trading_date],
                )
                row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            self.logger.error(f"Error getting GEX summary: {e}")
            return None

    def get_gex_range(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get GEX summaries for date range.

        Args:
            symbol: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with daily GEX metrics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(
                    """
                    SELECT trading_date, net_gex, total_gex, call_gex, put_gex,
                           flip_point, underlying_price, call_concentration
                    FROM gex_summary
                    WHERE symbol = ?
                      AND trading_date >= ?
                      AND trading_date <= ?
                    ORDER BY trading_date ASC
                    """,
                    conn,
                    params=[symbol.upper(), start_date, end_date],
                )

            if not df.empty:
                df["trading_date"] = pd.to_datetime(df["trading_date"])
                df.set_index("trading_date", inplace=True)

            return df

        except Exception as e:
            self.logger.error(f"Error getting GEX range: {e}")
            return pd.DataFrame()

    def set_gex_summary(self, symbol: str, trading_date: str, gex_data: Dict[str, Any], strike_df: pd.DataFrame = None):
        """Store GEX calculation with optional strike-level detail.

        Args:
            symbol: Ticker symbol
            trading_date: Date (YYYY-MM-DD)
            gex_data: Dict with GEX metrics
            strike_df: Optional strike-level breakdown (stored as Parquet)
        """
        try:
            # Store strike detail as Parquet if provided
            strike_path = None
            if strike_df is not None and not strike_df.empty:
                parquet_dir = self.db_path.parent / "gex_data" / symbol.upper() / trading_date
                parquet_dir.mkdir(parents=True, exist_ok=True)
                strike_path = parquet_dir / "gex_by_strike.parquet"
                strike_df.to_parquet(strike_path, compression="snappy")

            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO gex_summary (
                            symbol, trading_date, total_gex, net_gex, call_gex, put_gex,
                            flip_point, max_gamma_strike, call_concentration, put_concentration,
                            underlying_price, spot_to_flip_pct, calculation_method,
                            calculation_duration_ms, contracts_processed, strike_detail_path,
                            calculation_timestamp, cached_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol.upper(),
                            trading_date,
                            gex_data.get("total_gex"),
                            gex_data.get("net_gex"),
                            gex_data.get("call_gex"),
                            gex_data.get("put_gex"),
                            gex_data.get("flip_point"),
                            gex_data.get("max_gamma_strike"),
                            gex_data.get("call_concentration"),
                            gex_data.get("put_concentration"),
                            gex_data.get("underlying_price"),
                            gex_data.get("spot_to_flip_pct"),
                            gex_data.get("calculation_method", "black_scholes_iv"),
                            gex_data.get("calculation_duration_ms"),
                            gex_data.get("contracts_processed"),
                            str(strike_path) if strike_path else None,
                            gex_data.get("calculation_timestamp", now_iso()),
                            now_iso(),
                        ),
                    )
                    conn.commit()

            self.logger.debug(f"Stored GEX summary for {symbol} {trading_date}")

        except Exception as e:
            self.logger.error(f"Error storing GEX summary: {e}")

    # ================================================================
    # DETECTION METHODS
    # ================================================================

    def get_detections(
        self,
        symbol: str = None,
        start_date: str = None,
        end_date: str = None,
        pattern_ids: List[str] = None,
        llm_model: str = None,
        min_confidence: int = None,
        experiment_run_id: str = None,
    ) -> pd.DataFrame:
        """Query LLM detections with flexible filtering.

        Args:
            symbol: Filter by symbol
            start_date: Filter by date range start
            end_date: Filter by date range end
            pattern_ids: Filter by pattern IDs
            llm_model: Filter by LLM model
            min_confidence: Filter by minimum confidence
            experiment_run_id: Filter by experiment run

        Returns:
            DataFrame with detection results
        """
        try:
            query = "SELECT * FROM llm_detections WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            if start_date:
                query += " AND trading_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND trading_date <= ?"
                params.append(end_date)
            if pattern_ids:
                placeholders = ",".join(["?" for _ in pattern_ids])
                query += f" AND pattern_id IN ({placeholders})"
                params.extend(pattern_ids)
            if llm_model:
                query += " AND llm_model = ?"
                params.append(llm_model)
            if min_confidence:
                query += " AND confidence >= ?"
                params.append(min_confidence)
            if experiment_run_id:
                query += " AND experiment_run_id = ?"
                params.append(experiment_run_id)

            query += " ORDER BY trading_date ASC"

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)

            return df

        except Exception as e:
            self.logger.error(f"Error querying detections: {e}")
            return pd.DataFrame()

    def record_detection(
        self,
        symbol: str,
        trading_date: str,
        pattern_id: str,
        llm_model: str,
        prompt_version: str,
        detected: bool,
        confidence: int = None,
        structured_output: Dict[str, str] = None,
        reasoning_chain: str = None,
        raw_response: str = None,
        obfuscation_id: str = None,
        experiment_run_id: str = None,
        processing_duration_ms: int = None,
        token_count: int = None,
    ):
        """Record a single LLM detection result.

        Args:
            symbol: Ticker symbol
            trading_date: Date analyzed
            pattern_id: Pattern being detected
            llm_model: Model used (e.g., "o3-mini")
            prompt_version: Prompt template version
            detected: Whether pattern was detected
            confidence: Confidence score 0-100
            structured_output: WHO/WHOM/WHAT dict
            reasoning_chain: Full chain-of-thought
            raw_response: Raw LLM response
            obfuscation_id: Link to obfuscation mapping
            experiment_run_id: Link to experiment run
            processing_duration_ms: API call duration
            token_count: Tokens used
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO llm_detections (
                            symbol, trading_date, pattern_id, llm_model, prompt_version,
                            obfuscation_id, detected, confidence, who, whom, what, time_horizon,
                            reasoning_chain, raw_llm_response, processing_timestamp,
                            processing_duration_ms, token_count, experiment_run_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol.upper(),
                            trading_date,
                            pattern_id,
                            llm_model,
                            prompt_version,
                            obfuscation_id,
                            1 if detected else 0,
                            confidence,
                            structured_output.get("who") if structured_output else None,
                            structured_output.get("whom") if structured_output else None,
                            structured_output.get("what") if structured_output else None,
                            structured_output.get("time_horizon") if structured_output else None,
                            reasoning_chain,
                            raw_response,
                            now_iso(),
                            processing_duration_ms,
                            token_count,
                            experiment_run_id,
                        ),
                    )
                    conn.commit()

            self.logger.debug(f"Recorded detection: {symbol} {trading_date} {pattern_id}")

        except Exception as e:
            self.logger.error(f"Error recording detection: {e}")

    # ================================================================
    # VALIDATION METHODS
    # ================================================================

    def record_validation(
        self,
        detection_id: int,
        t1_return: float = None,
        t3_return: float = None,
        t5_return: float = None,
        max_gain: float = None,
        max_drawdown: float = None,
        materialized: bool = None,
        outcome_type: str = None,
    ):
        """Record validation results for a detection.

        Args:
            detection_id: ID of the detection being validated
            t1_return: T+1 forward return
            t3_return: T+3 forward return
            t5_return: T+5 forward return
            max_gain: Maximum gain in forward window
            max_drawdown: Maximum drawdown in forward window
            materialized: Whether prediction materialized
            outcome_type: 'ACCURATE', 'PARTIAL', 'MISSED', 'PENDING'
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO validation_results (
                            detection_id, t1_return, t3_return, t5_return,
                            max_gain, max_drawdown, materialized, outcome_type,
                            validation_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            detection_id,
                            t1_return,
                            t3_return,
                            t5_return,
                            max_gain,
                            max_drawdown,
                            1 if materialized else 0 if materialized is not None else None,
                            outcome_type,
                            now_iso(),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error recording validation: {e}")

    def get_validation_results(self, detection_ids: List[int] = None, outcome_type: str = None) -> pd.DataFrame:
        """Get validation results with optional filtering.

        Args:
            detection_ids: Filter by specific detection IDs
            outcome_type: Filter by outcome type

        Returns:
            DataFrame with validation results
        """
        try:
            query = """
                SELECT v.*, d.symbol, d.trading_date, d.pattern_id, d.confidence
                FROM validation_results v
                JOIN llm_detections d ON v.detection_id = d.id
                WHERE 1=1
            """
            params = []

            if detection_ids:
                placeholders = ",".join(["?" for _ in detection_ids])
                query += f" AND v.detection_id IN ({placeholders})"
                params.extend(detection_ids)
            if outcome_type:
                query += " AND v.outcome_type = ?"
                params.append(outcome_type)

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)

            return df

        except Exception as e:
            self.logger.error(f"Error getting validation results: {e}")
            return pd.DataFrame()

    # ================================================================
    # EXPERIMENT RUN METHODS
    # ================================================================

    def record_experiment_run(
        self,
        run_id: str,
        run_name: str = None,
        config: Dict[str, Any] = None,
        symbols: List[str] = None,
        date_range: Tuple[str, str] = None,
        pattern_ids: List[str] = None,
        llm_model: str = None,
        prompt_version: str = None,
        paper_version: str = None,
    ) -> str:
        """Record a new experiment run with full configuration.

        Args:
            run_id: Unique identifier for this run
            run_name: Human-readable name
            config: Complete configuration dict
            symbols: List of symbols tested
            date_range: (start_date, end_date) tuple
            pattern_ids: List of patterns tested
            llm_model: LLM model used
            prompt_version: Prompt template version
            paper_version: Which paper this run is for

        Returns:
            The run_id
        """
        try:
            # Get current git commit
            git_commit = None
            git_branch = None
            try:
                git_commit = (
                    subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
                    .decode()
                    .strip()[:8]
                )
                git_branch = (
                    subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL)
                    .decode()
                    .strip()
                )
            except Exception:
                pass

            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO experiment_runs (
                            run_id, run_name, git_commit, git_branch, config_json,
                            symbols, date_range_start, date_range_end, pattern_ids,
                            llm_model, llm_temperature, prompt_version, paper_version,
                            created_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            run_id,
                            run_name or run_id,
                            git_commit,
                            git_branch,
                            json.dumps(config or {}),
                            json.dumps(symbols or []),
                            date_range[0] if date_range else None,
                            date_range[1] if date_range else None,
                            json.dumps(pattern_ids or []),
                            llm_model,
                            config.get("llm_temperature") if config else None,
                            prompt_version,
                            paper_version,
                            now_iso(),
                        ),
                    )
                    conn.commit()

            self.logger.info(f"Recorded experiment run: {run_id}")
            return run_id

        except Exception as e:
            self.logger.error(f"Error recording experiment run: {e}")
            return run_id

    def get_experiment_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment run by ID for reproducibility.

        Args:
            run_id: The experiment run ID

        Returns:
            Dict with complete run configuration
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM experiment_runs WHERE run_id = ?", [run_id])
                row = cursor.fetchone()

            if row:
                result = dict(row)
                # Parse JSON fields
                result["config"] = json.loads(result.get("config_json") or "{}")
                result["symbols"] = json.loads(result.get("symbols") or "[]")
                result["pattern_ids"] = json.loads(result.get("pattern_ids") or "[]")
                return result
            return None

        except Exception as e:
            self.logger.error(f"Error getting experiment run: {e}")
            return None

    def update_experiment_results(
        self, run_id: str, total_tests: int, total_detections: int, detection_rate: float, overall_accuracy: float
    ):
        """Update experiment run with final results.

        Args:
            run_id: The experiment run ID
            total_tests: Total number of tests run
            total_detections: Total detections made
            detection_rate: Detection rate percentage
            overall_accuracy: Overall accuracy percentage
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        UPDATE experiment_runs
                        SET total_tests = ?, total_detections = ?,
                            detection_rate = ?, overall_accuracy = ?,
                            completed_date = ?
                        WHERE run_id = ?
                        """,
                        (total_tests, total_detections, detection_rate, overall_accuracy, now_iso(), run_id),
                    )
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error updating experiment results: {e}")

    # ================================================================
    # OBFUSCATION METHODS
    # ================================================================

    def record_obfuscation(
        self,
        obfuscation_id: str,
        schema_type: str,
        date_mapping: Dict[str, str] = None,
        symbol_mapping: Dict[str, str] = None,
        used_in_papers: List[str] = None,
    ):
        """Record obfuscation mapping for audit trail.

        Args:
            obfuscation_id: Unique identifier
            schema_type: Type of obfuscation ('relative_day', 'anonymized_ticker')
            date_mapping: Map of real dates to obfuscated dates
            symbol_mapping: Map of real symbols to obfuscated symbols
            used_in_papers: List of papers using this obfuscation
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO obfuscation_mappings (
                            obfuscation_id, schema_type, date_mapping_json,
                            symbol_mapping_json, used_in_papers, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            obfuscation_id,
                            schema_type,
                            json.dumps(date_mapping) if date_mapping else None,
                            json.dumps(symbol_mapping) if symbol_mapping else None,
                            json.dumps(used_in_papers) if used_in_papers else None,
                            now_iso(),
                        ),
                    )
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error recording obfuscation: {e}")

    def get_obfuscation(self, obfuscation_id: str) -> Optional[Dict[str, Any]]:
        """Get obfuscation mapping by ID.

        Args:
            obfuscation_id: The obfuscation ID

        Returns:
            Dict with obfuscation mappings
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM obfuscation_mappings WHERE obfuscation_id = ?", [obfuscation_id])
                row = cursor.fetchone()

            if row:
                result = dict(row)
                result["date_mapping"] = json.loads(result.get("date_mapping_json") or "{}")
                result["symbol_mapping"] = json.loads(result.get("symbol_mapping_json") or "{}")
                result["used_in_papers"] = json.loads(result.get("used_in_papers") or "[]")
                return result
            return None

        except Exception as e:
            self.logger.error(f"Error getting obfuscation: {e}")
            return None

    # ================================================================
    # PATTERN LIBRARY METHODS
    # ================================================================

    def get_pattern(self, pattern_id: str, version: str = None) -> Optional[Dict[str, Any]]:
        """Get pattern definition by ID.

        Args:
            pattern_id: Pattern identifier
            version: Specific version (None = latest active)

        Returns:
            Dict with pattern definition
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                if version:
                    cursor = conn.execute(
                        "SELECT * FROM pattern_library WHERE pattern_id = ? AND version = ?", [pattern_id, version]
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT * FROM pattern_library
                        WHERE pattern_id = ? AND active = 1
                        ORDER BY created_date DESC LIMIT 1
                        """,
                        [pattern_id],
                    )

                row = cursor.fetchone()

            if row:
                result = dict(row)
                result["thresholds"] = json.loads(result.get("thresholds_json") or "{}")
                result["used_in_papers"] = json.loads(result.get("used_in_papers") or "[]")
                return result
            return None

        except Exception as e:
            self.logger.error(f"Error getting pattern: {e}")
            return None

    def set_pattern(
        self,
        pattern_id: str,
        version: str,
        name: str,
        who: str,
        whom: str,
        what: str,
        thresholds: Dict[str, Any],
        description: str = None,
        min_confidence: int = 60,
        used_in_papers: List[str] = None,
    ):
        """Add or update pattern in library.

        Args:
            pattern_id: Pattern identifier
            version: Version string
            name: Human-readable name
            who: WHO component (causal actor)
            whom: WHOM component (affected party)
            what: WHAT component (forced action)
            thresholds: Detection thresholds dict
            description: Optional description
            min_confidence: Minimum confidence for detection
            used_in_papers: List of papers using this pattern
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO pattern_library (
                            pattern_id, version, name, description, who, whom, what,
                            thresholds_json, min_confidence, created_date, active, used_in_papers
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                        """,
                        (
                            pattern_id,
                            version,
                            name,
                            description,
                            who,
                            whom,
                            what,
                            json.dumps(thresholds),
                            min_confidence,
                            now_iso(),
                            json.dumps(used_in_papers) if used_in_papers else None,
                        ),
                    )
                    conn.commit()

        except Exception as e:
            self.logger.error(f"Error setting pattern: {e}")

    # ================================================================
    # ANALYTICS METHODS
    # ================================================================

    def get_detection_stats(self, symbol: str = None, pattern_id: str = None, llm_model: str = None) -> Dict[str, Any]:
        """Get aggregated detection statistics.

        Args:
            symbol: Filter by symbol
            pattern_id: Filter by pattern
            llm_model: Filter by model

        Returns:
            Dict with detection statistics
        """
        try:
            where_clauses = []
            params = []

            if symbol:
                where_clauses.append("d.symbol = ?")
                params.append(symbol.upper())
            if pattern_id:
                where_clauses.append("d.pattern_id = ?")
                params.append(pattern_id)
            if llm_model:
                where_clauses.append("d.llm_model = ?")
                params.append(llm_model)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            with sqlite3.connect(self.db_path) as conn:
                # Detection stats
                row = conn.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_tests,
                        SUM(d.detected) as total_detections,
                        AVG(d.confidence) as avg_confidence,
                        COUNT(DISTINCT d.trading_date) as unique_dates
                    FROM llm_detections d
                    WHERE {where_sql}
                """,
                    params,
                ).fetchone()

                total_tests = row[0] or 0
                total_detections = row[1] or 0
                avg_confidence = row[2] or 0
                unique_dates = row[3] or 0

                # Validation stats (if available)
                val_row = conn.execute(
                    f"""
                    SELECT
                        COUNT(*) as validated,
                        SUM(v.materialized) as materialized,
                        AVG(v.t1_return) as avg_t1_return,
                        AVG(v.t3_return) as avg_t3_return
                    FROM validation_results v
                    JOIN llm_detections d ON v.detection_id = d.id
                    WHERE {where_sql}
                """,
                    params,
                ).fetchone()

                validated = val_row[0] or 0
                materialized = val_row[1] or 0

            detection_rate = (total_detections / total_tests * 100) if total_tests > 0 else 0
            accuracy = (materialized / validated * 100) if validated > 0 else 0

            return {
                "total_tests": total_tests,
                "total_detections": total_detections,
                "detection_rate": round(detection_rate, 2),
                "avg_confidence": round(avg_confidence, 2),
                "unique_dates": unique_dates,
                "validated": validated,
                "materialized": materialized,
                "accuracy": round(accuracy, 2),
            }

        except Exception as e:
            self.logger.error(f"Error getting detection stats: {e}")
            return {}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get overall cache statistics.

        Returns:
            Dict with cache metrics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Count records in each table
                for table in [
                    "market_data",
                    "options_chain",
                    "gex_summary",
                    "llm_detections",
                    "validation_results",
                    "experiment_runs",
                    "pattern_library",
                ]:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    stats[f"{table}_count"] = count

                # Database size
                db_size = self.db_path.stat().st_size / (1024 * 1024)
                stats["db_size_mb"] = round(db_size, 2)

            return stats

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}

    # ================================================================
    # UTILITY METHODS
    # ================================================================

    def _calculate_expiration(self, date_str: str) -> datetime:
        """Calculate smart expiration based on data recency.

        Historical data (>2 days old): 10 years Recent data (<=2 days): 24 hours
        """
        try:
            data_date = parse_date_string(date_str)
            today = get_datetime_now().date()

            if data_date.date() < today - timedelta(days=2):
                return get_datetime_now() + timedelta(days=365 * 10)
            else:
                return get_datetime_now() + timedelta(hours=24)

        except ValueError:
            return get_datetime_now() + timedelta(hours=24)

    def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of rows deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM market_data
                    WHERE datetime(expires_at) <= datetime('now')
                """
                )
                deleted = cursor.rowcount
                conn.commit()

            if deleted > 0:
                self.logger.info(f"Cleaned up {deleted} expired cache entries")

            return deleted

        except Exception as e:
            self.logger.error(f"Error cleaning up expired cache: {e}")
            return 0

    def vacuum(self):
        """Optimize database (reclaim space after deletions)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            self.logger.info("Database optimized (VACUUM completed)")
        except Exception as e:
            self.logger.error(f"Error vacuuming database: {e}")
