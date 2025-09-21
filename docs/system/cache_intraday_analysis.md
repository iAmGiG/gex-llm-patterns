# Cache System & Intraday Support Analysis

> **NOTE**: This document has been superseded by [cache_system_architecture.md](cache_system_architecture.md) which provides current implementation details.

## Current Cache Structure (Updated 2025-09-21)

The cache system uses lazy directory creation and consolidated SQLite storage:

```bash
.cache/
├── consolidated_historical.db        # Pattern validation & performance results
├── options/SPY/YYYY-MM-DD.pickle    # Created on-demand when storing options data
├── market_data/SPY/YYYY-MM-DD.pickle # Created on-demand when storing market data
├── news/category/YYYY-MM-DD.pickle   # Created on-demand when storing news data
├── metadata/                         # Created on-demand for cache statistics
├── intraday_options/SPY/DATE/TIME.json # Created on-demand for intraday storage
├── intraday_gex/SPY/DATE/TIME.json     # Created on-demand for intraday storage
└── intraday_market/SPY/DATE/TIME.json  # Created on-demand for intraday storage
```

**Key Changes**:
- ✅ Lazy directory creation (no empty directories)
- ✅ Consolidated database for pattern results
- ✅ Intraday timestamp support implemented
- ✅ All cache components verified as actively used

## Intraday Support Analysis

### Current Status: INTRADAY TIMESTAMP SUPPORT IMPLEMENTED ✅

**Update 2025-09-21**: Intraday support has been fully implemented:
- ✅ Timestamp format support: `2024-06-07 15:30:00`
- ✅ Gamma pinning validation: 75% success rate at Friday 3:30 PM
- ✅ IntradayCacheManager with 10-minute intervals
- ✅ Production-ready intraday storage system

### Previous Analysis: DATE-LEVEL Granularity (Historical)

**Cache System**:

- Files organized by DATE (YYYY-MM-DD)
- No timestamp suffixes in filenames
- GEX data stored as daily summaries
- Options data stored as end-of-day snapshots

**Database Schema**:

```sql
-- Current schema uses TEXT date fields, not timestamps
CREATE TABLE daily_gex_metrics (
    date TEXT,  -- Just date, no time
    symbol TEXT,
    ...
);

CREATE TABLE strike_gex_details (
    date TEXT,  -- Just date, no time
    symbol TEXT,
    strike REAL,
    ...
);
```

## Alpha Vantage Historical Options

**API Capabilities**:

- `HISTORICAL_OPTIONS` endpoint available
- Returns end-of-day data only (not intraday)
- Includes full Greeks (delta, gamma, theta, vega, rho)
- Requires premium API key for historical data
- Free tier: 25 requests/day (not sufficient for validation)

**Simple Python Test**:

```python
import requests

# Test Alpha Vantage historical options
response = requests.get('https://www.alphavantage.co/query', params={
    'function': 'HISTORICAL_OPTIONS',
    'symbol': 'SPY',
    'date': '2024-01-05',  # Friday
    'apikey': 'YOUR_KEY'
})

# Returns: Full options chain with Greeks for that date
```

## Storage Implications for Intraday

### Current Storage (Date-Level)

- 1 entry per trading day
- ~252 entries per year per symbol
- Database size: ~36MB for multiple symbols

### Intraday Storage Requirements

- **15-minute intervals**: 26 entries per day (6.5 hours × 4)
- **5-minute intervals**: 78 entries per day
- **1-minute intervals**: 390 entries per day

**Storage Impact**:

- 15-min: 26× increase (6,552 entries/year)
- 5-min: 78× increase (19,656 entries/year)
- 1-min: 390× increase (98,280 entries/year)

## Implementation Changes Needed for Intraday

### 1. Database Schema Updates

```sql
-- Add timestamp columns
ALTER TABLE daily_gex_metrics
ADD COLUMN timestamp TEXT;  -- ISO format: 2024-01-17 15:30:00

-- Or create new intraday tables
CREATE TABLE intraday_gex_metrics (
    symbol TEXT,
    timestamp TEXT,  -- Full timestamp
    spot_price REAL,
    total_gex REAL,
    ...
    PRIMARY KEY (symbol, timestamp)
);
```

### 2. Cache Structure Updates

```bash
cache/gex_data/SYMBOL/DATE/
├── 0930.json   # 9:30 AM snapshot
├── 1000.json   # 10:00 AM
├── 1030.json   # 10:30 AM
├── 1500.json   # 3:00 PM
├── 1530.json   # 3:30 PM (key time for gamma pin)
└── 1600.json   # 4:00 PM close
```

### 3. Date Utils Enhancement

```python
from src.utils.date_utils import parse_date_string

# Already supports datetime parsing
# Just need to use timestamp format
timestamp = "2024-01-17 15:30:00"
dt = parse_date_string(timestamp)  # Works
```

## Manual Validation Approach

Given current limitations:

### Option 1: Use Existing Daily Data

```python
# Query existing database for Fridays
SELECT date, spot_price, gamma_flip_point
FROM daily_gex_metrics
WHERE symbol = 'SPY'
  AND strftime('%w', date) = '5'  -- Fridays
  AND date >= '2024-01-01';
```

### Option 2: Populate Historical Data First

```python
# Use scripts to populate database with historical data
# Then run validation on populated data
python scripts/testing/populate_historical_cache.py --symbol SPY --start 2024-01-01
```

### Option 3: Real-Time Collection During Market Hours

```python
# Collect intraday data during market hours
# Store with timestamps for future analysis
# Requires running during market hours (9:30 AM - 4:00 PM ET)
```

## Recommendation

For the gamma pinning validation experiment:

1. **Current System**: Can do daily-level validation (end-of-day Friday prices vs max gamma strikes)
2. **For 3:30 PM Validation**: Need to enhance storage with timestamps
3. **Alpha Vantage**: Provides historical data but requires premium key and only EOD
4. **Best Approach**: Use existing daily data first, then enhance for intraday if results promising

The cache system has good depth (fed, news, options, market, gex, patterns) but currently lacks intraday granularity. Adding timestamp support would be straightforward but would significantly increase storage requirements.
