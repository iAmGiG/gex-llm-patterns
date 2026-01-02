"""PostgreSQL Options Manager for gex-llm-patterns

Replaces SQLite with PostgreSQL for better concurrency and scalability.
Maintains same interface as SQLiteOptionsManager for drop-in replacement.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


class PostgreSQLOptionsManager:
    """PostgreSQL-based options data manager with partitioning and connection pooling"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "cregan1",
        database: str = "gex_options",
        password: Optional[str] = None,
    ):
        """Initialize PostgreSQL connection

        Args:
            host: PostgreSQL host (default: localhost)
            port: PostgreSQL port (default: 5432)
            user: PostgreSQL user (default: cregan1)
            database: Database name (default: gex_options)
            password: Password (default: None for trust authentication)
        """
        self.host = host
        self.port = port
        self.user = user
        self.database = database
        self.password = password

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Compatibility property for code expecting db_path
        self.db_path = Path(".cache")  # Use .cache directory for summary files

        # Initialize connection
        self._connect()

    def _connect(self):
        """Establish PostgreSQL connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                database=self.database,
                password=self.password,
            )
            self.conn.autocommit = False  # Use transactions
            self.logger.info(f"Connected to PostgreSQL: {self.user}@{self.host}:{self.port}/{self.database}")
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def store_options_chain(
        self,
        symbol: str,
        trading_date: str,
        options_df: pd.DataFrame,
        asset_class: str = "equity",
        data_source: str = "alpha_vantage",
        underlying_price: float = None,
    ) -> bool:
        """Store options chain in PostgreSQL

        Args:
            symbol: Ticker symbol
            trading_date: Trading date (YYYY-MM-DD)
            options_df: DataFrame with options data
            asset_class: Asset class (default: equity)
            data_source: Data source (default: alpha_vantage)

        Returns:
            True if successful, False otherwise
        """
        if options_df.empty:
            self.logger.warning(f"Empty DataFrame for {symbol} {trading_date}")
            return False

        try:
            cursor = self.conn.cursor()

            # Prepare batch insert data
            records = []
            for _, row in options_df.iterrows():
                records.append((
                    symbol,
                    asset_class,
                    trading_date,
                    float(row.get('strike', 0)),
                    row.get('option_type', 'call'),
                    row.get('expiration', trading_date),
                    float(row.get('bid', 0)) if pd.notna(row.get('bid')) else None,
                    float(row.get('ask', 0)) if pd.notna(row.get('ask')) else None,
                    float(row.get('last', 0)) if pd.notna(row.get('last')) else None,
                    float(row.get('mark', 0)) if pd.notna(row.get('mark')) else None,
                    int(row.get('bid_size', 0)) if pd.notna(row.get('bid_size')) else None,
                    int(row.get('ask_size', 0)) if pd.notna(row.get('ask_size')) else None,
                    int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
                    int(row.get('open_interest', 0)) if pd.notna(row.get('open_interest')) else None,
                    float(row.get('delta', 0)) if pd.notna(row.get('delta')) else None,
                    float(row.get('gamma', 0)) if pd.notna(row.get('gamma')) else None,
                    float(row.get('theta', 0)) if pd.notna(row.get('theta')) else None,
                    float(row.get('vega', 0)) if pd.notna(row.get('vega')) else None,
                    float(row.get('rho', 0)) if pd.notna(row.get('rho')) else None,
                    float(row.get('implied_volatility', 0)) if pd.notna(row.get('implied_volatility')) else None,
                    float(row.get('underlying_price', 0)) if pd.notna(row.get('underlying_price')) else None,
                    float(row.get('mid_price', 0)) if pd.notna(row.get('mid_price')) else None,
                    float(row.get('bid_ask_spread', 0)) if pd.notna(row.get('bid_ask_spread')) else None,
                    data_source,
                    1.0,  # data_quality_score
                ))

            # Bulk insert with conflict handling
            insert_query = """
                INSERT INTO options_chains_partitioned (
                    symbol, asset_class, trading_date, strike, option_type, expiration,
                    bid, ask, last, mark, bid_size, ask_size,
                    volume, open_interest,
                    delta, gamma, theta, vega, rho, implied_volatility,
                    underlying_price, mid_price, bid_ask_spread,
                    data_source, data_quality_score
                ) VALUES %s
                ON CONFLICT (symbol, trading_date, strike, option_type, expiration) DO NOTHING
            """
            execute_values(cursor, insert_query, records, page_size=1000)
            self.conn.commit()

            self.logger.info(f"Stored {len(records)} options contracts for {symbol} {trading_date}")
            cursor.close()
            return True

        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error storing options chain for {symbol} {trading_date}: {e}")
            return False

    def has_options_data(self, symbol: str, trading_date: str) -> bool:
        """Check if options data exists for symbol and date"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT 1 FROM options_chains_partitioned WHERE symbol = %s AND trading_date = %s LIMIT 1"
            cursor.execute(query, (symbol, trading_date))
            exists = cursor.fetchone() is not None
            cursor.close()
            return exists
        except Exception as e:
            # Don't log every check as error, just return False
            return False

    def retrieve_options_chain(
        self,
        symbol: str,
        trading_date: str
    ) -> Optional[pd.DataFrame]:
        """Retrieve options chain from PostgreSQL

        Args:
            symbol: Ticker symbol
            trading_date: Trading date (YYYY-MM-DD)

        Returns:
            DataFrame with options data or None if not found
        """
        try:
            query = """
                SELECT * FROM options_chains_partitioned
                WHERE symbol = %s AND trading_date = %s
                ORDER BY strike, option_type, expiration
            """
            df = pd.read_sql_query(query, self.conn, params=(symbol, trading_date))

            if df.empty:
                self.logger.warning(f"No options data found for {symbol} {trading_date}")
                return None

            return df

        except Exception as e:
            self.logger.error(f"Error retrieving options chain: {e}")
            return None

    def get_missing_dates(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """Get list of dates that are missing from the database"""
        try:
            # Generate expected trading dates (weekdays)
            start = pd.Timestamp(start_date)
            end = pd.Timestamp(end_date)
            expected_dates = [d.strftime('%Y-%m-%d') for d in pd.bdate_range(start, end)]

            # Get existing dates
            query = "SELECT DISTINCT trading_date::text FROM options_chains_partitioned WHERE symbol = %s AND trading_date >= %s AND trading_date <= %s"
            df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))
            existing_dates = set(df['trading_date'].values) if not df.empty else set()

            return [d for d in expected_dates if d not in existing_dates]
        except Exception as e:
            self.logger.error(f"Error getting missing dates: {e}")
            # Return all dates on error to be safe (will re-check individually)
            return [d.strftime('%Y-%m-%d') for d in pd.bdate_range(pd.Timestamp(start_date), pd.Timestamp(end_date))]

    def update_progress(
        self,
        symbol: str,
        trading_date: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update collection progress tracking

        Args:
            symbol: Ticker symbol
            trading_date: Trading date
            status: Status (pending, in_progress, completed, failed)
            error_message: Optional error message

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()

            insert_query = """
                INSERT INTO collection_progress (symbol, trading_date, status, error_message, attempts, last_attempt)
                VALUES (%s, %s, %s, %s, 1, %s)
                ON CONFLICT (symbol, trading_date) DO UPDATE SET
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    attempts = collection_progress.attempts + 1,
                    last_attempt = EXCLUDED.last_attempt,
                    completed_at = CASE WHEN EXCLUDED.status = 'completed' THEN CURRENT_TIMESTAMP ELSE NULL END
            """
            cursor.execute(insert_query, (symbol, trading_date, status, error_message, datetime.now()))
            self.conn.commit()
            cursor.close()
            return True

        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error updating progress: {e}")
            return False

    def get_collection_progress(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """Get collection progress as DataFrame"""
        try:
            query = "SELECT * FROM collection_progress"
            params = ()
            if symbol:
                query += " WHERE symbol = %s"
                params = (symbol,)
            return pd.read_sql_query(query, self.conn, params=params)
        except Exception:
            return pd.DataFrame()

    def get_collection_status(self, symbol: Optional[str] = None) -> Dict:
        """Get collection status statistics

        Args:
            symbol: Optional symbol filter

        Returns:
            Dictionary with status counts
        """
        try:
            cursor = self.conn.cursor()

            if symbol:
                query = """
                    SELECT status, COUNT(*) as count
                    FROM collection_progress
                    WHERE symbol = %s
                    GROUP BY status
                """
                cursor.execute(query, (symbol,))
            else:
                query = """
                    SELECT status, COUNT(*) as count
                    FROM collection_progress
                    GROUP BY status
                """
                cursor.execute(query)

            results = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.close()
            return results

        except Exception as e:
            self.logger.error(f"Error getting collection status: {e}")
            return {}

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            cursor = self.conn.cursor()
            # Estimate row count from metadata (fast)
            cursor.execute("SELECT reltuples::bigint FROM pg_class WHERE relname = 'options_chains_partitioned'")
            res = cursor.fetchone()
            count = res[0] if res else 0

            cursor.execute("SELECT pg_database_size(%s)", (self.database,))
            size = cursor.fetchone()[0]
            cursor.close()

            return {
                "total_options_records": int(count) if count else 0,
                "db_size_mb": size / (1024 * 1024) if size else 0
            }
        except Exception:
            return {}

    def close(self):
        """Close PostgreSQL connection"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            self.logger.info("PostgreSQL connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
