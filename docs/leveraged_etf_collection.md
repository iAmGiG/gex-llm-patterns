# Leveraged ETF Options Collection

## Overview

Collection system for 19 leveraged/inverse ETF symbols with amplified gamma exposure patterns. These ETFs exhibit 2x-3x leveraged price movements, creating significantly larger options flows and gamma effects compared to standard ETFs.

**Date Range**: 2020-01-02 to present
**Database**: `.cache/options_historical.db` (SQLite)
**Current Size**: 18.0 GB, 43.4M records (as of 2025-12-16)

## Why Leveraged ETFs?

Leveraged ETFs are ideal for GEX research because:

- **Amplified volatility** → Higher option demand → Larger gamma exposure
- **High retail participation** → More 0DTE/1DTE options activity
- **Directional bias** → Bull/bear pairs for asymmetry analysis
- **Market structure effects** → Rebalancing flows interact with options positioning

## Scripts

### 1. Single Tier Collection

**File**: `scripts/data_collection/collect_leveraged_etfs.py`

```bash
# Tier 1 (highest liquidity)
python scripts/data_collection/collect_leveraged_etfs.py --tier 1 --sequential -y

# Tier 2 (S&P/Russell)
python scripts/data_collection/collect_leveraged_etfs.py --tier 2 --sequential -y

# Tier 3 (sector-specific)
python scripts/data_collection/collect_leveraged_etfs.py --tier 3 --sequential -y

# Check status
python scripts/data_collection/collect_leveraged_etfs.py --status
```

### 2. Auto-Queue All Tiers

**File**: `scripts/data_collection/collect_all_tiers.py`

```bash
# Run all tiers sequentially
python scripts/data_collection/collect_all_tiers.py --sequential -y

# Skip Tier 1 (if already complete)
python scripts/data_collection/collect_all_tiers.py --skip-tier1 --sequential -y

# Resume from specific date
python scripts/data_collection/collect_all_tiers.py --start 2023-01-01 --sequential -y
```

### 3. Monitor Progress

**File**: `scripts/data_collection/monitor_collection.py`

```bash
# One-time check
python scripts/data_collection/monitor_collection.py

# Watch mode (updates every 60s)
python scripts/data_collection/monitor_collection.py --watch
```

### 4. Validate Data Quality

**File**: `scripts/data_collection/validate_data_quality.py`

```bash
# All leveraged ETFs
python scripts/data_collection/validate_data_quality.py

# Specific symbols with verbose
python scripts/data_collection/validate_data_quality.py --symbols TQQQ SQQQ -v
```

## Symbol Tiers

### Tier 1: Highest Liquidity (5 symbols)

| Symbol | Name | Multiplier | Description |
|--------|------|------------|-------------|
| TQQQ | ProShares UltraPro QQQ | 3x Bull | #2 most traded ETF 2024 |
| SQQQ | ProShares UltraPro Short QQQ | 3x Bear | Nasdaq inverse |
| SOXL | Direxion Semiconductor Bull | 3x Bull | #1 most traded ETF 2024 |
| SOXS | Direxion Semiconductor Bear | 3x Bear | Semiconductor inverse |
| UVXY | ProShares Ultra VIX | 1.5x | VIX futures exposure |

### Tier 2: S&P & Russell (6 symbols)

| Symbol | Name | Multiplier | Description |
|--------|------|------------|-------------|
| SPXL | Direxion S&P 500 Bull | 3x Bull | S&P 500 long |
| SPXS | Direxion S&P 500 Bear | 3x Bear | S&P 500 inverse (37.5M volume) |
| UPRO | ProShares UltraPro S&P500 | 3x Bull | $3.9B AUM |
| SPXU | ProShares UltraPro Short S&P500 | 3x Bear | S&P 500 inverse |
| TNA | Direxion Small Cap Bull | 3x Bull | Russell 2000 long |
| TZA | Direxion Small Cap Bear | 3x Bear | Russell 2000 inverse |

### Tier 3: Sector-Specific (8 symbols)

| Symbol | Name | Multiplier | Description |
|--------|------|------------|-------------|
| FAS | Direxion Financial Bull | 3x Bull | Financials ($2.5B AUM) |
| FAZ | Direxion Financial Bear | 3x Bear | Financials inverse |
| LABU | Direxion Biotech Bull | 3x Bull | Biotech long |
| LABD | Direxion Biotech Bear | 3x Bear | Biotech inverse |
| TECL | Direxion Technology Bull | 3x Bull | Tech long |
| TECS | Direxion Technology Bear | 3x Bear | Tech inverse |
| NUGT | Direxion Gold Miners Bull | 2x Bull | Gold miners long |
| DUST | Direxion Gold Miners Bear | 2x Bear | Gold miners inverse |

## Collection Modes

### Sequential Mode (RECOMMENDED)

**Use**: `--sequential` flag
**Behavior**: Collects one symbol completely before moving to next
**Pros**: Stable, no database locks
**Cons**: Slower (~150-200 trading days/hour)

```bash
python scripts/data_collection/collect_leveraged_etfs.py --tier 1 --sequential -y
```

### Parallel Mode

**Use**: Default (no `--sequential` flag)
**Behavior**: Interleaves API calls across all symbols
**Pros**: Faster (saturates 900 calls/min quota)
**Cons**: Can cause database lock errors

### Buffered Mode

**Use**: `--buffered` flag
**Behavior**: RAM queue + async database writes
**Pros**: Fastest (decouples API from DB I/O)
**Cons**: High database lock risk, requires more RAM

## Troubleshooting

### Database Lock Errors

**Symptoms**: `database is locked` errors during collection

**Cause**: Concurrent writes from parallel/buffered modes or lingering processes

**Solution**:

```bash
# 1. Kill lingering processes (Windows)
python -c "import subprocess; subprocess.run(['wmic', 'process', 'where', \"name='python.exe'\", 'get', 'commandline'])"

# Find the PID of collection script, then:
python -c "import subprocess; subprocess.run(['taskkill', '/F', '/PID', 'XXXXX'])"

# 2. Use sequential mode
python scripts/data_collection/collect_leveraged_etfs.py --tier 1 --sequential -y
```

### Resuming Interrupted Collection

Collections are automatically resumable - just re-run the same command:

```bash
# Will skip existing dates automatically
python scripts/data_collection/collect_leveraged_etfs.py --tier 1 --sequential -y
```

## Performance Estimates

| Mode | Symbols | Trading Days | Est. Time | DB I/O |
|------|---------|--------------|-----------|--------|
| Sequential | 5 (Tier 1) | 1,500 | ~37 hrs | Stable |
| Sequential | 19 (All) | 1,500 | ~140 hrs | Stable |
| Parallel | 5 (Tier 1) | 1,500 | ~8 hrs | Lock risk |
| Buffered | 5 (Tier 1) | 1,500 | ~5 hrs | High lock risk |

**API Rate**: 900 calls/min (premium tier)
**Sequential Rate**: ~150-200 trading days/hour/symbol

## Current Progress (2025-12-16)

```text
Database: 18.0 GB, 43.4M records
Overall: 15.8% complete (4,505/28,519 symbol-days)

TIER 1:
  TQQQ: 97.1% (2020-01-02 to 2025-12-16) ✓ COMPLETE
  SQQQ: 55.8% (2020-01-02 to 2023-07-11) ← IN PROGRESS
  SOXL: 48.8% (2020-01-02 to 2023-02-06)
  SOXS: 49.7% (2020-01-02 to 2023-02-06)
  UVXY: 48.7% (2020-01-02 to 2023-02-06)

TIER 2: Not started (6 symbols)
TIER 3: Not started (8 symbols)

ETA: 2025-12-23 (sequential mode)
```

## System-Agnostic Paths

All scripts use `pathlib.Path` for Windows/Linux/HPCC compatibility:

```python
# Automatically detects project root on any OS
project_root = Path(__file__).resolve().parents[2]
db_path = project_root / ".cache" / "options_historical.db"
```

## HPCC Deployment

**SLURM Job Example**:

```bash
#!/bin/bash
#SBATCH --job-name=lev-etf-tier1
#SBATCH --time=48:00:00
#SBATCH --mem=16GB
#SBATCH --cpus-per-task=4

cd $HOME/gex-llm-patterns
python scripts/data_collection/collect_leveraged_etfs.py --tier 1 --sequential -y
```

**Multi-Tier Parallel Jobs**:

```bash
# Job 1: Tier 1
sbatch --job-name=tier1 collect_tier1.sh

# Job 2: Tier 2 (different node)
sbatch --job-name=tier2 collect_tier2.sh

# Job 3: Tier 3 (different node)
sbatch --job-name=tier3 collect_tier3.sh
```

## Database Schema

**Table**: `options_chains`

```sql
CREATE TABLE options_chains (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    trading_date TEXT,
    strike REAL,
    option_type TEXT,
    expiration TEXT,
    gamma REAL,
    delta REAL,
    theta REAL,
    vega REAL,
    volume INTEGER,
    open_interest INTEGER,
    underlying_price REAL,
    ...
);

CREATE INDEX idx_symbol_date ON options_chains(symbol, trading_date);
CREATE INDEX idx_date ON options_chains(trading_date);
```

## Next Steps

1. **Complete Tier 1**: Monitor `be18d38` task until SQQQ, SOXL, SOXS, UVXY finish
2. **Validate Tier 1**: Run `validate_data_quality.py` on completed symbols
3. **Start Tier 2**: Use `collect_leveraged_etfs.py --tier 2 --sequential -y`
4. **GEX Analysis**: Compare leveraged ETF gamma patterns vs SPY/QQQ baseline
5. **Research Findings**: Document amplified gamma effects in leveraged instruments

## References

- [Alpha Vantage Premium](https://www.alphavantage.co/premium/) - 900-1000 calls/min
- [SQLite Manager](../src/cache/sqlite_options_manager.py) - Database interface
- [Historical Collector](../src/data_sources/historical_collector.py) - Core collection logic
