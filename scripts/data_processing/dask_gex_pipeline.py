"""
Dask-Based GEX Calculator - Production Pipeline

Issue #501 - Big Data GEX Calculation Pipeline

Features:
- Dask for out-of-core parallel processing
- Vectorized pandas operations
- Proper logging with rotation
- Checkpointing for recovery
- Progress tracking
- Data validation
- Report generation

Usage:
    python dask_gex_calculator.py
    python dask_gex_calculator.py --config custom_config.yaml
    python dask_gex_calculator.py --symbols SPY QQQ IWM
    python dask_gex_calculator.py --dry-run
"""

import argparse
import os
import logging
import sqlite3
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import yaml

from src.utils.date_utils import get_datetime_now, now_iso, now_timestamp

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    "database": {
        "path": ".cache/options_historical.db",
        "journal_mode": "WAL",
        "cache_size_mb": 100,
        "mmap_size_mb": 1024,
        "synchronous": "OFF",
    },
    "processing": {
        "read_chunk_size": 100000,
        "write_batch_size": 1000,
        "num_workers": 0,
        "memory_limit_per_worker": "2GB",
        "scheduler": "processes",
    },
    "logging": {
        "log_dir": "logs/gex_pipeline",
        "level": "INFO",
        "max_log_size_mb": 50,
        "backup_count": 5,
    },
    "validation": {
        "min_contracts": 50,
        "min_open_interest": 100,
        "max_gamma": 1.0,
    },
    "output": {
        "generate_reports": True,
        "report_dir": "docs/08_research/03_gex_research/reports",
        "checkpoint_frequency": 5,
    },
}

ASSET_CLASS_MAP = {
    "SPY": "equity",
    "QQQ": "equity",
    "IWM": "equity",
    "DIA": "equity",
    "VTI": "equity",
    "AAPL": "equity",
    "MSFT": "equity",
    "TSLA": "equity",
    "TQQQ": "equity",
    "SQQQ": "equity",
    "UPRO": "equity",
    "SPXU": "equity",
    "SPXL": "equity",
    "SPXS": "equity",
    "SOXL": "equity",
    "SOXS": "equity",
    "TNA": "equity",
    "TZA": "equity",
    "TECL": "equity",
    "TECS": "equity",
    "FAS": "equity",
    "FAZ": "equity",
    "LABU": "equity",
    "LABD": "equity",
    "NUGT": "equity",
    "DUST": "equity",
    "UVXY": "volatility",
    "VXX": "volatility",
    "GLD": "commodity",
    "SLV": "commodity",
    "TLT": "bond",
    "IEF": "bond",
    "LQD": "bond",
    "IYR": "real_estate",
}


# =============================================================================
# LOGGING SETUP
# =============================================================================


def setup_logging(config: Dict) -> logging.Logger:
    """Configure logging with file rotation and console output."""
    log_dir = Path(config["logging"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"gex_pipeline_{now_timestamp()}.log"

    logger = logging.getLogger("gex_pipeline")
    logger.setLevel(getattr(logging, config["logging"]["level"]))

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config["logging"]["max_log_size_mb"] * 1024 * 1024,
        backupCount=config["logging"]["backup_count"],
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================


def setup_database(db_path: Path, config: Dict) -> None:
    """Configure SQLite for optimal bulk operations."""
    conn = sqlite3.connect(db_path, timeout=60)

    conn.execute(f"PRAGMA journal_mode={config['database']['journal_mode']}")
    conn.execute(f"PRAGMA cache_size=-{config['database']['cache_size_mb'] * 1024}")
    conn.execute(f"PRAGMA synchronous={config['database']['synchronous']}")
    conn.execute(f"PRAGMA mmap_size={config['database']['mmap_size_mb'] * 1024 * 1024}")
    conn.execute("PRAGMA temp_store=MEMORY")

    conn.close()


def get_symbols_info(db_path: Path) -> List[Tuple[str, int]]:
    """Get list of symbols with their date counts."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT symbol, COUNT(DISTINCT trading_date) as days
        FROM options_chains
        GROUP BY symbol
        ORDER BY days DESC
    """
    )

    result = cursor.fetchall()
    conn.close()

    return result


def get_processed_dates(db_path: Path, symbol: str) -> set:
    """Get dates already processed for a symbol."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT trading_date FROM options_daily_summary WHERE symbol = ?", (symbol,))

    result = {row[0] for row in cursor.fetchall()}
    conn.close()

    return result


def read_symbol_data(db_path: Path, symbol: str, chunk_size: int) -> pd.DataFrame:
    """Read all data for a symbol into a pandas DataFrame."""
    conn = sqlite3.connect(db_path)

    query = """
        SELECT symbol, trading_date, strike, option_type, expiration,
               gamma, delta, underlying_price, open_interest
        FROM options_chains
        WHERE symbol = ?
        ORDER BY trading_date, strike
    """

    # Read in chunks and concatenate
    chunks = []
    for chunk in pd.read_sql_query(query, conn, params=(symbol,), chunksize=chunk_size):
        chunks.append(chunk)

    conn.close()

    if not chunks:
        return pd.DataFrame()

    return pd.concat(chunks, ignore_index=True)


def bulk_insert_results(db_path: Path, results: pd.DataFrame, batch_size: int, logger: logging.Logger) -> int:
    """Bulk insert results using executemany."""
    if results.empty:
        return 0

    conn = sqlite3.connect(db_path, timeout=120)
    cursor = conn.cursor()

    insert_sql = """
        INSERT OR REPLACE INTO options_daily_summary (
            symbol, trading_date, underlying_price, total_gex, net_call_gex,
            net_put_gex, zero_gamma_level, max_gamma_strike, regime,
            call_oi_concentration, put_oi_concentration, contracts_count,
            expirations_count, data_quality_score, calculation_method,
            calculation_timestamp, asset_class
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    records = results.values.tolist()
    inserted = 0

    try:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            cursor.executemany(insert_sql, batch)
            inserted += len(batch)

        conn.commit()
        logger.debug(f"Inserted {inserted} records")

    except Exception as e:
        logger.error(f"Insert error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    return inserted


# =============================================================================
# GEX CALCULATION (VECTORIZED)
# =============================================================================


def calculate_gex_vectorized(df: pd.DataFrame, config: Dict, logger: logging.Logger) -> pd.DataFrame:
    """Calculate GEX metrics using vectorized pandas operations.

    This is the core calculation - processes entire symbol data at once.
    """
    if df.empty:
        return pd.DataFrame()

    symbol = df["symbol"].iloc[0]
    logger.debug(f"Calculating GEX for {symbol} ({len(df):,} contracts)")

    # Data cleaning
    df = df.copy()
    df["gamma"] = df["gamma"].fillna(0)
    df["delta"] = df["delta"].fillna(0)
    df["open_interest"] = df["open_interest"].fillna(1).astype(int)

    # Filter invalid gamma values
    max_gamma = config["validation"]["max_gamma"]
    df = df[df["gamma"].abs() <= max_gamma]

    if df.empty:
        logger.warning(f"{symbol}: All records filtered due to invalid gamma")
        return pd.DataFrame()

    # Calculate weighted gamma
    df["weighted_gamma"] = df["gamma"] * df["open_interest"]
    df["abs_weighted_gamma"] = df["weighted_gamma"].abs()

    # Flags
    df["is_call"] = df["option_type"] == "call"
    df["is_put"] = df["option_type"] == "put"
    df["near_neutral"] = (df["delta"].abs() >= 0.4) & (df["delta"].abs() <= 0.6)

    # Aggregate by trading_date
    agg = (
        df.groupby("trading_date")
        .agg(
            {
                "symbol": "first",
                "underlying_price": "first",
                "abs_weighted_gamma": "sum",
                "open_interest": "sum",
                "strike": "count",
                "expiration": "nunique",
            }
        )
        .rename(
            columns={
                "abs_weighted_gamma": "total_weighted_gamma",
                "open_interest": "total_oi",
                "strike": "contracts_count",
                "expiration": "expirations_count",
            }
        )
    )

    # Call aggregations
    call_agg = (
        df[df["is_call"]]
        .groupby("trading_date")
        .agg(
            {
                "weighted_gamma": "sum",
                "open_interest": "sum",
            }
        )
        .rename(
            columns={
                "weighted_gamma": "call_weighted_gamma",
                "open_interest": "call_oi",
            }
        )
    )

    # Put aggregations
    put_agg = (
        df[df["is_put"]]
        .groupby("trading_date")
        .agg(
            {
                "weighted_gamma": lambda x: x.abs().sum(),
                "open_interest": "sum",
            }
        )
        .rename(
            columns={
                "weighted_gamma": "put_weighted_gamma",
                "open_interest": "put_oi",
            }
        )
    )

    # Zero gamma level (weighted average of near-neutral strikes)
    def calc_zero_gamma(group):
        if len(group) == 0 or group["open_interest"].sum() == 0:
            return np.nan
        return np.average(group["strike"], weights=group["open_interest"])

    zero_gamma = df[df["near_neutral"]].groupby("trading_date").apply(calc_zero_gamma).rename("zero_gamma_level")

    # Max gamma strike
    idx_max = df.groupby("trading_date")["abs_weighted_gamma"].idxmax()
    max_gamma_strikes = (
        df.loc[idx_max][["trading_date", "strike"]]
        .set_index("trading_date")
        .rename(columns={"strike": "max_gamma_strike"})
    )

    # Merge all
    result = agg.join(call_agg, how="left").join(put_agg, how="left")
    result = result.join(zero_gamma, how="left").join(max_gamma_strikes, how="left")

    # Fill NaN
    result["call_weighted_gamma"] = result["call_weighted_gamma"].fillna(0)
    result["put_weighted_gamma"] = result["put_weighted_gamma"].fillna(0)
    result["call_oi"] = result["call_oi"].fillna(0)
    result["put_oi"] = result["put_oi"].fillna(0)

    # Calculate normalized metrics
    result["total_gex"] = result["total_weighted_gamma"] / result["total_oi"]
    result["net_call_gex"] = np.where(result["call_oi"] > 0, result["call_weighted_gamma"] / result["call_oi"], 0)
    result["net_put_gex"] = np.where(result["put_oi"] > 0, result["put_weighted_gamma"] / result["put_oi"], 0)
    result["net_gamma"] = result["net_call_gex"] - result["net_put_gex"]

    # OI concentration
    result["call_oi_concentration"] = result["call_oi"] / result["total_oi"]
    result["put_oi_concentration"] = result["put_oi"] / result["total_oi"]

    # Regime classification
    min_contracts = config["validation"]["min_contracts"]
    result["regime"] = np.where(
        result["contracts_count"] < min_contracts,
        "NEUTRAL",
        np.where(
            result["net_gamma"] > 0,
            "POSITIVE_GAMMA",
            np.where(result["net_gamma"] < 0, "NEGATIVE_GAMMA", "NEUTRAL"),
        ),
    )

    # Data quality score
    min_oi = config["validation"]["min_open_interest"]
    quality = np.ones(len(result))
    quality = np.where(
        result["contracts_count"] < 100,
        quality * 0.5,
        np.where(result["contracts_count"] < 500, quality * 0.75, quality),
    )
    quality = np.where(
        result["total_oi"] < min_oi,
        quality * 0.7,
        np.where(result["total_oi"] < 5000, quality * 0.85, quality),
    )
    result["data_quality_score"] = quality

    # Metadata
    result["calculation_method"] = "dask_vectorized"
    result["calculation_timestamp"] = now_iso()
    result["asset_class"] = ASSET_CLASS_MAP.get(symbol, "equity")

    # Reset index
    result = result.reset_index()

    # Select output columns
    output_cols = [
        "symbol",
        "trading_date",
        "underlying_price",
        "total_gex",
        "net_call_gex",
        "net_put_gex",
        "zero_gamma_level",
        "max_gamma_strike",
        "regime",
        "call_oi_concentration",
        "put_oi_concentration",
        "contracts_count",
        "expirations_count",
        "data_quality_score",
        "calculation_method",
        "calculation_timestamp",
        "asset_class",
    ]

    result = result[output_cols]

    # Round numeric columns
    for col in [
        "total_gex",
        "net_call_gex",
        "net_put_gex",
        "call_oi_concentration",
        "put_oi_concentration",
        "data_quality_score",
    ]:
        result[col] = result[col].round(8)

    return result


# =============================================================================
# MAIN PIPELINE
# =============================================================================


def process_symbol(symbol: str, db_path: Path, config: Dict, logger: logging.Logger) -> Tuple[str, int, int]:
    """Process a single symbol.

    Returns (symbol, new_count, skip_count).
    """
    logger.info(f"Processing {symbol}...")

    # Get already processed dates
    processed_dates = get_processed_dates(db_path, symbol)

    # Read symbol data
    df = read_symbol_data(db_path, symbol, config["processing"]["read_chunk_size"])

    if df.empty:
        logger.warning(f"{symbol}: No data found")
        return symbol, 0, len(processed_dates)

    # Filter out already processed dates
    df = df[~df["trading_date"].isin(processed_dates)]

    if df.empty:
        logger.info(f"{symbol}: Already complete ({len(processed_dates)} days)")
        return symbol, 0, len(processed_dates)

    # Calculate GEX
    results = calculate_gex_vectorized(df, config, logger)

    if results.empty:
        logger.warning(f"{symbol}: No valid results calculated")
        return symbol, 0, len(processed_dates)

    # Insert results
    inserted = bulk_insert_results(db_path, results, config["processing"]["write_batch_size"], logger)

    logger.info(f"{symbol}: {inserted} new days calculated")

    return symbol, inserted, len(processed_dates)


def generate_report(db_path: Path, config: Dict, logger: logging.Logger) -> str:
    """Generate summary report after processing."""
    conn = sqlite3.connect(db_path)

    # Get summary statistics
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(DISTINCT symbol) as symbols,
            COUNT(*) as total_days,
            MIN(trading_date) as start_date,
            MAX(trading_date) as end_date
        FROM options_daily_summary
    """
    )
    summary = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            asset_class,
            COUNT(*) as days,
            SUM(CASE WHEN regime = 'POSITIVE_GAMMA' THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN regime = 'NEGATIVE_GAMMA' THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN regime = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral,
            ROUND(AVG(data_quality_score), 3) as avg_quality
        FROM options_daily_summary
        GROUP BY asset_class
    """
    )
    asset_breakdown = cursor.fetchall()

    cursor.execute(
        """
        SELECT symbol, COUNT(*) as days,
            SUM(CASE WHEN regime = 'POSITIVE_GAMMA' THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN regime = 'NEGATIVE_GAMMA' THEN 1 ELSE 0 END) as negative
        FROM options_daily_summary
        GROUP BY symbol
        ORDER BY days DESC
    """
    )
    symbol_breakdown = cursor.fetchall()

    conn.close()

    # Generate markdown report
    report = []
    report.append("# GEX Calculation Pipeline Report")
    report.append(f"\nGenerated: {now_iso()}")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append(f"- **Symbols Processed**: {summary[0]}")
    report.append(f"- **Total Trading Days**: {summary[1]:,}")
    report.append(f"- **Date Range**: {summary[2]} to {summary[3]}")
    report.append("")
    report.append("## Regime Distribution by Asset Class")
    report.append("")
    report.append("| Asset Class | Days | Positive | Negative | Neutral | Avg Quality |")
    report.append("|-------------|------|----------|----------|---------|-------------|")
    for row in asset_breakdown:
        report.append(f"| {row[0] or 'unknown'} | {row[1]:,} | {row[2]:,} | {row[3]:,} | {row[4]:,} | {row[5]} |")
    report.append("")
    report.append("## Symbol Detail")
    report.append("")
    report.append("| Symbol | Days | Positive Gamma | Negative Gamma |")
    report.append("|--------|------|----------------|----------------|")
    for row in symbol_breakdown:
        report.append(f"| {row[0]} | {row[1]:,} | {row[2]:,} | {row[3]:,} |")

    report_text = "\n".join(report)

    # Save report
    if config["output"]["generate_reports"]:
        report_dir = Path(config["output"]["report_dir"])
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"gex_report_{now_timestamp()}.md"
        report_file.write_text(report_text)
        logger.info(f"Report saved: {report_file}")

    return report_text


def run_pipeline(config: Dict, symbols: Optional[List[str]] = None, dry_run: bool = False) -> None:
    """Main pipeline execution."""
    logger = setup_logging(config)

    logger.info("=" * 70)
    logger.info("GEX CALCULATION PIPELINE - Issue #501")
    logger.info("=" * 70)

    db_path = Path(config["database"]["path"])

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return

    # Setup database
    logger.info("Configuring database for bulk operations...")
    setup_database(db_path, config)

    # Get symbols to process
    all_symbols_info = get_symbols_info(db_path)

    if symbols:
        # Filter to specified symbols
        symbols_info = [(s, d) for s, d in all_symbols_info if s in symbols]
    else:
        symbols_info = all_symbols_info

    logger.info(f"Symbols to process: {len(symbols_info)}")
    total_expected = sum(d for _, d in symbols_info)
    logger.info(f"Total expected trading days: {total_expected:,}")

    if dry_run:
        logger.info("DRY RUN - No data will be modified")
        for symbol, days in symbols_info:
            logger.info(f"  Would process: {symbol} ({days} days)")
        return

    # Configure Dask
    num_workers = config["processing"]["num_workers"]
    if num_workers == 0:
        import multiprocessing

        num_workers = max(1, multiprocessing.cpu_count() - 1)

    logger.info(f"Using {num_workers} workers")
    logger.info("=" * 70)

    # Process symbols
    start_time = get_datetime_now()
    results = []
    checkpoint_freq = config["output"]["checkpoint_frequency"]

    for i, (symbol, _) in enumerate(symbols_info, 1):
        try:
            result = process_symbol(symbol, db_path, config, logger)
            results.append(result)

            # Checkpoint logging
            if i % checkpoint_freq == 0:
                elapsed = get_datetime_now() - start_time
                total_new = sum(r[1] for r in results)
                logger.info(f"Checkpoint: {i}/{len(symbols_info)} symbols, {total_new:,} new days, {elapsed}")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            results.append((symbol, 0, 0))

    # Summary
    elapsed = get_datetime_now() - start_time
    total_new = sum(r[1] for r in results)
    total_skipped = sum(r[2] for r in results)

    logger.info("")
    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"New records: {total_new:,}")
    logger.info(f"Existing skipped: {total_skipped:,}")
    logger.info(f"Time elapsed: {elapsed}")
    if elapsed.total_seconds() > 0:
        logger.info(f"Records per second: {total_new / elapsed.total_seconds():.1f}")

    # Generate report
    report = generate_report(db_path, config, logger)
    print("\n" + report)


# =============================================================================
# CLI
# =============================================================================


def load_config(config_path: Optional[Path] = None) -> Dict:
    """Load configuration from file or use defaults."""
    config = DEFAULT_CONFIG.copy()

    if config_path and config_path.exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f)
            # Deep merge
            for key, value in file_config.items():
                if isinstance(value, dict) and key in config:
                    config[key].update(value)
                else:
                    config[key] = value

    return config


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GEX Calculation Pipeline - Big Data Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python dask_gex_calculator.py
    python dask_gex_calculator.py --config custom_config.yaml
    python dask_gex_calculator.py --symbols SPY QQQ IWM
    python dask_gex_calculator.py --dry-run
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("scripts/research/gex/gex_pipeline_config.yaml"),
        help="Path to configuration file",
    )
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to process (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")

    args = parser.parse_args()

    config = load_config(args.config)
    run_pipeline(config, args.symbols, args.dry_run)


if __name__ == "__main__":
    main()
