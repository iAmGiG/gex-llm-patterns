# Test 4: Technical Appendix

**Date**: November 5, 2025

---

## Data Quality Summary

### 2020 GEX Dataset

**Coverage**: 252 trading days (full year 2020)

| Metric | Value |
|--------|-------|
| Trading Days | 252 |
| Avg GEX | $2.85B |
| Median GEX | $2.51B |
| Min GEX | $0.01B |
| Max GEX | $11.23B |
| Std Dev | $2.17B |
| Avg SPY Price | $321.47 |

**Quality Metrics**:

- Data quality score: 100 (all days)
- Failed fetches: 0
- Processing errors: 0
- Avg options per day: ~8,500 contracts

### 2024 GEX Dataset (For Comparison)

**Coverage**: 86 trading days

| Metric | Value |
|--------|-------|
| Trading Days | 86 |
| Avg GEX | $26.06B |
| Median GEX | $24.18B |
| Min GEX | $8.16B |
| Max GEX | $38.57B |
| Std Dev | $7.89B |
| Avg SPY Price | $515.27 |

**GEX Regime Comparison**:

- 2020 Avg is **11%** of 2024 Avg ($2.85B vs $26.06B)
- 2020 Max is **29%** of 2024 Max ($11.23B vs $38.57B)
- 2020 Min is **0.1%** of 2024 Min ($0.01B vs $8.16B)

---

## HistoricalGEXDatabaseBuilder Bugs

### Bug #1: Cache-Only Operation

**Location**: `src/data_sources/historical_gex_builder.py`

**Problem**: Builder calls `self.cache.get_options_data()` directly instead of using HistoricalOptionsCollector with API fallback.

**Code**:

```python
# Current (broken):
options_data = self.cache.get_options_data(symbol, trade_date)
if options_data is None:
    # No API fallback - just skips date
    continue

# Should be (like HistoricalOptionsCollector):
options_data = await self.collector.collect_single_date(symbol, trade_date)
# Collector handles cache check + API fallback automatically
```

**Impact**: Cannot fetch historical data beyond cached dates

**Workaround**: Created `fetch_2020_options.py` using HistoricalOptionsCollector directly

---

### Bug #2: Resume Logic Assumes Forward-Only Building

**Location**: `src/data_sources/historical_gex_builder.py` (resume logic)

**Problem**: Resume point is set to `max(existing dates)` and filters out all dates before it.

**Code**:

```python
# Gets latest date in database
resume_date = self._get_resume_point(symbol)  # Returns "2024-12-11"

# Filters trading dates
valid_dates = [d for d in all_dates if d >= resume_date]
# Result: Skips ALL 2020 dates because they're < "2024-12-11"
```

**Assumption**: Builder assumes chronological forward-only operation (building from 2020→2024)

**Reality**: We need to backfill historical data (adding 2020 when 2024 already exists)

**Impact**: Cannot backfill historical periods when later data exists

**Workaround**: Created `process_2020_gex_simple.py` with direct iteration (no resume logic)

---

## Cache Structure Requirements

### SequentialGEXFetcher Expectations

**Location**: `src/data_sources/sequential_gex_fetcher.py:169-182`

**Code**:

```python
def _get_trading_days_before(self, symbol: str, end_date: str, n_days: int):
    cache_dir = self.gex_cache.gex_cache_dir / symbol.upper()

    available_dates = []
    for date_dir in sorted(cache_dir.iterdir()):
        if date_dir.is_dir():  # ← EXPECTS DIRECTORIES
            date_str = date_dir.name
            if date_str <= end_date:
                available_dates.append(date_str)

    return available_dates[-n_days:]
```

**Key requirement**: `date_dir.is_dir()` check means it scans for **directories** not files.

### Required Directory Structure

```
.cache/gex_data/SPY/
├── 2020-01-02/
│   ├── gex_summary.json
│   └── metadata.json
├── 2020-01-03/
│   ├── gex_summary.json
│   └── metadata.json
...
├── 2024-01-02/
│   ├── gex_summary.json
│   └── metadata.json
...
```

### gex_summary.json Format

```json
{
  "symbol": "SPY",
  "trading_date": "2020-01-02",
  "spot_price": 325.465,
  "total_gex": 8911189842.121225,
  "call_gex": 2675715057.473225,
  "put_gex": -11586904899.594448,
  "net_gex": 8911189842.121225,
  "gex_by_strike": {}
}
```

### metadata.json Format

```json
{
  "symbol": "SPY",
  "trading_date": "2020-01-02",
  "stored_timestamp": "2025-11-05T15:56:42.123456",
  "files": {
    "summary": "gex_data/SPY/2020-01-02/gex_summary.json",
    "strike_detail": null,
    "expiry_breakdown": null
  }
}
```

### Initial Mistake

Created flat parquet files:

```
.cache/gex_summary_2020-01-02.parquet
.cache/gex_summary_2020-01-03.parquet
...
```

**Result**: SequentialGEXFetcher found "0 trading dates to process"

**Fix**: Rewrote `export_db_to_cache_v2.py` to create proper directory structure

---

## Validation Log Structure

### Log File

**Location**: `/tmp/test4_2020_full_run.log`

**Size**: ~15 MB (257 windows × ~60 KB per window)

**Contains** (per window):

1. LLM prompt (system + user messages)
2. LLM response (JSON with WHO/WHOM/WHAT/confidence)
3. Trajectory classification
4. GEX sequence (5 days of values)
5. Outcome metrics (T+1 return, volatility, etc.)
6. Detection verdict

### Sample Log Entry

```
INFO - [42/257] Processing window ending 2020-02-18...
INFO - Fetching 5-day GEX sequence ending 2020-02-18
INFO - GEX sequence:
  Day T-4 (2020-02-12): $4.52B, flip $0.00, spot $334.22
  Day T-3 (2020-02-13): $3.89B, flip $0.00, spot $333.70
  Day T-2 (2020-02-14): $5.11B, flip $0.00, spot $335.18
  Day T-1 (2020-02-18): $4.37B, flip $0.00, spot $337.28
  Day T+0 (2020-02-19): $3.94B, flip $0.00, spot $338.53

INFO - Trajectory: STABLE (velocity -$0.14B/day)
INFO - Sending to LLM (o4-mini)...
INFO - ✅ DETECTED: 70% confidence
INFO -    WHO: Institutional vol sellers
INFO -    WHOM: Dealers
INFO -    WHAT: Continuous delta-hedging to maintain neutral exposure
INFO -    TRAJECTORY: persistent (STABLE)
INFO -    OUTCOME: +0.34% T+1 return
```

### Extracting Stratification Data

To perform stratified GEX analysis:

```bash
# Extract window date, 5-day avg GEX, detected status, confidence
grep -A 10 "Processing window ending" /tmp/test4_2020_full_run.log | \
grep -E "(ending|Day T|DETECTED|Low confidence)" | \
# Parse and calculate avg GEX per window
# Group by GEX range
# Calculate detection rate per range
```

**Script needed**: `scripts/analysis/stratify_test4_results.py` (not yet created)

---

## Scripts Reference

All organized in `scripts/validation/negative_controls/`:

### fetch_2020_options.py

**Purpose**: Fetch 2020 historical options data from Alpha Vantage API

**Usage**:

```bash
python scripts/validation/negative_controls/fetch_2020_options.py
```

**Key components**:

- Uses HistoricalOptionsCollector (proper API fallback)
- Rate limiting: 900 calls/min (under 1000/min Premium limit)
- Caches to `.cache/` for reuse
- Progress logging every 10 days

**Output**: 250 days of options data cached

---

### process_2020_gex_simple.py

**Purpose**: Calculate GEX from cached options and insert into database

**Usage**:

```bash
PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH \
python scripts/validation/negative_controls/process_2020_gex_simple.py
```

**Key components**:

- Bypasses broken HistoricalGEXDatabaseBuilder
- Direct iteration over cached options
- Infers spot price from deep ITM calls (delta > 0.95)
- Uses GEXCalculator.calculate_gex_profile()
- Directly inserts into daily_gex_metrics table

**Processing rate**: ~1 day/second (~4 minutes for 252 days)

**Database**: Adds to `.cache/consolidated_historical.db` (does not replace)

---

### export_db_to_cache_v2.py

**Purpose**: Export database GEX to cache directory structure

**Usage**:

```bash
PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH \
python scripts/validation/negative_controls/export_db_to_cache_v2.py
```

**Key components**:

- Queries database for 2020 daily_gex_metrics
- Creates date directories for each trading day
- Generates gex_summary.json (GEX data)
- Generates metadata.json (timestamp, file refs)
- Required for SequentialGEXFetcher compatibility

**Output**: 252 date directories in `.cache/gex_data/SPY/`

**Processing rate**: ~5 seconds total

---

### build_2019_2020_test4.py (DEPRECATED)

**Purpose**: Original attempt to use HistoricalGEXDatabaseBuilder

**Status**: ❌ FAILED - Kept for reference

**Issues encountered**:

1. Builder only checks cache (no API fallback)
2. Resume logic skips historical dates
3. 2019 data unavailable from Alpha Vantage

**Replaced by**: Separate fetch + process + export scripts

---

## Database Schema

### daily_gex_metrics Table

```sql
CREATE TABLE daily_gex_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    spot_price REAL NOT NULL,
    total_gex REAL NOT NULL,
    net_call_gex REAL,
    net_put_gex REAL,
    gex_regime TEXT,
    options_count INTEGER,
    data_quality_score INTEGER,
    UNIQUE(symbol, date)
);
```

**Key columns**:

- `total_gex`: Net GEX (call GEX + put GEX, with signs)
- `net_call_gex`: Call-only GEX (negative if dealers short gamma)
- `net_put_gex`: Put-only GEX (positive if dealers long gamma)
- `gex_regime`: 'positive_gamma' or 'negative_gamma'
- `data_quality_score`: 0-100 (100 = complete data)

### Query 2020 Data

```sql
SELECT
    date,
    total_gex / 1e9 as gex_billions,
    spot_price,
    options_count
FROM daily_gex_metrics
WHERE date LIKE '2020-%'
ORDER BY date;
```

### Comparison Query

```sql
SELECT
    strftime('%Y', date) as year,
    COUNT(*) as days,
    ROUND(AVG(ABS(total_gex)) / 1e9, 2) as avg_gex_b,
    ROUND(MIN(ABS(total_gex)) / 1e9, 2) as min_gex_b,
    ROUND(MAX(ABS(total_gex)) / 1e9, 2) as max_gex_b
FROM daily_gex_metrics
GROUP BY strftime('%Y', date);
```

---

## API Usage

### Alpha Vantage Premium

**Tier**: Premium (1000 calls/min)

**Usage for Test 4**:

- Options fetching: 250 API calls (~15 minutes)
- Cost: ~$0 (within monthly quota)

**Rate limiting**:

```python
rate_limit_per_minute=900  # Stay under 1000/min
```

### OpenAI o4-mini

**Model**: `o4-mini-2025-04-16` (reasoning model)

**Usage for Test 4**:

- 257 windows × 1 API call = 257 calls
- Avg tokens per call: ~1,800 (650 prompt + 1,150 completion)
- Total tokens: ~463K tokens
- Estimated cost: ~$1.40 (at $3/M tokens)

**Batch processing**: 10 windows per batch (26 batches total)

---

## Timeline Summary

| Phase | Start | End | Duration |
|-------|-------|-----|----------|
| Data fetch | 14:00 | 14:15 | 15 min |
| GEX calculation | 14:15 | 14:19 | 4 min |
| Cache export | 14:19 | 14:19 | <1 min |
| Cache debugging | 15:00 | 16:00 | 1 hour |
| Validation | 16:19 | 17:16 | 57 min |
| Results analysis | 17:16 | 17:20 | 4 min |
| **Total** | **14:00** | **17:20** | **~3.3 hours** |

**Note**: Cache debugging took longest (discovering SequentialGEXFetcher expects directories)

---

## Files Generated

### Scripts (Kept)

- `scripts/validation/negative_controls/fetch_2020_options.py`
- `scripts/validation/negative_controls/process_2020_gex_simple.py`
- `scripts/validation/negative_controls/export_db_to_cache_v2.py`
- `scripts/validation/negative_controls/build_2019_2020_test4.py` (deprecated)
- `scripts/validation/negative_controls/README.md`

### Logs (Temporary)

- `/tmp/fetch_2020.log` - Options fetch log
- `/tmp/process_2020_v2.log` - GEX processing log
- `/tmp/export_cache_v2.log` - Cache export log
- `/tmp/test4_2020_full_run.log` - Validation log (15 MB)

### Documentation (Consolidated)

- `/tmp/test4_1_executive_summary.md` - High-level findings
- `/tmp/test4_2_methodology.md` - How Test 4 was executed
- `/tmp/test4_3_results_analysis.md` - Results and interpretations
- `/tmp/test4_4_technical_appendix.md` - This file

### Database/Cache

- `.cache/consolidated_historical.db` - 338 days (2020 + 2024)
- `.cache/gex_data/SPY/YYYY-MM-DD/` - 338 date directories

---

**Date**: November 5, 2025
