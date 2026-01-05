# Data Collection Scripts

Scripts for gathering, managing, and processing market data.

## Primary Collection Script

### `collect_leveraged_etfs.py`

Main script for collecting historical options data. Supports all collection modes.

```bash
# Tier 1 only (TQQQ, SQQQ, SOXL, SOXS, UVXY)
python scripts/data_collection/collect_leveraged_etfs.py -y

# All tiers (19 symbols)
python scripts/data_collection/collect_leveraged_etfs.py --tier all -y

# Specific tier
python scripts/data_collection/collect_leveraged_etfs.py --tier 2 -y

# Sequential mode (slower but avoids DB locks)
python scripts/data_collection/collect_leveraged_etfs.py --tier all --sequential -y

# Buffered mode (faster with more RAM)
python scripts/data_collection/collect_leveraged_etfs.py --tier all --buffered -y

# Check status
python scripts/data_collection/collect_leveraged_etfs.py --status
```

## Status & Monitoring Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_progress.py` | Quick collection progress by symbol | `python scripts/data_collection/check_progress.py` |
| `check_db_status.py` | Database health and underlying_price coverage | `python scripts/data_collection/check_db_status.py` |
| `monitor_collection.py` | Real-time progress with ETA (watch mode) | `python scripts/data_collection/monitor_collection.py --watch` |
| `validate_data_quality.py` | Data quality checks (gaps, anomalies) | `python scripts/data_collection/validate_data_quality.py -v` |

## Utility Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `backfill_underlying_prices.py` | Backfill missing underlying_price values | `python scripts/data_collection/backfill_underlying_prices.py` |
| `fetch_ohlc_alpha_vantage.py` | Fetch OHLC data for daily_gex_metrics table | `python scripts/data_collection/fetch_ohlc_alpha_vantage.py --symbol SPY` |
| `migrate_file_cache_to_db.py` | Migrate file cache to SQLite database | `python scripts/data_collection/migrate_file_cache_to_db.py --symbol SPY` |

## Legacy Script

| Script | Purpose |
|--------|---------|
| `start_historical_collection.py` | Simple collection interface (pre-SQLite) |

## Database

- **Location**: `.cache/options_historical.db`
- **Tables**: `options_chains`, `collection_progress`, `options_daily_summary`

## Leveraged ETF Tiers

| Tier | Symbols | Description |
|------|---------|-------------|
| 1 | TQQQ, SQQQ, SOXL, SOXS, UVXY | Highest liquidity |
| 2 | SPXL, SPXS, UPRO, SPXU, TNA, TZA | S&P and Russell leveraged |
| 3 | FAS, FAZ, LABU, LABD, TECL, TECS, NUGT, DUST | Sector-specific |
