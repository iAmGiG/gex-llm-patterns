# Parallel Multi-Symbol Collection Guide

## Problem: Sequential Collection Bottleneck

The previous collection approach was **sequential** - it collected all dates for one symbol before moving to the next:

```text
SPY:  [████████████████████] 17 min
QQQ:                         [████████████████████] 17 min
IWM:                                                [████████████████████] 17 min
Total: ~51 minutes for 3 symbols
```

With 15 expanded tickers, this meant ~267 minutes (4.5 hours) to collect 1000 trading days per symbol.

## Solution: Parallel Interleaved Collection

The new **parallel** mode interleaves API calls across symbols, sharing the 900 calls/min quota:

```text
SPY date 1 → QQQ date 1 → IWM date 1 → AAPL date 1 → ... → SPY date 2 → QQQ date 2 → ...
[Single continuous stream of 900 calls/min across all symbols]
```

### Performance Improvement

| Scenario | Sequential | Parallel | Speedup |
|----------|-----------|----------|---------|
| **3 symbols** (SPY, QQQ, IWM) | ~51 min | ~17 min | **3x faster** |
| **15 symbols** (expanded) | ~267 min | ~17 min | **15.7x faster** |
| **20 symbols** (full) | ~340 min | ~17 min | **20x faster** |

**Why?** The rate limiter applies to the entire collection system, not per-symbol. Sequential wastes quota by processing one symbol at a time. Parallel keeps the 900 calls/min quota fully saturated across all symbols.

## How to Use

### 1. Continue Existing Sequential Collection (SPY only)

The current background task collecting SPY will continue running. Let it finish or check status:

```bash
python scripts/data_collection/collect_historical_sqlite.py --status
```

### 2. Start Parallel Expanded Collection (Recommended)

Once SPY is done or running in parallel, start the 15-ticker parallel collection:

```bash
# Default: expanded preset (15 tickers, 2020-present)
python scripts/data_collection/collect_parallel_expanded.py -y

# Custom tickers
python scripts/data_collection/collect_parallel_expanded.py --symbols SPY QQQ AAPL MSFT -y

# Extended date range
python scripts/data_collection/collect_parallel_expanded.py --start 2018-01-01 -y

# Check status
python scripts/data_collection/collect_parallel_expanded.py --status
```

### 3. Run Both Simultaneously (Maximum Quota Usage)

You can run BOTH scripts in the background at the same time:

```bash
# Terminal 1: Keep SPY collection running
python scripts/data_collection/collect_historical_sqlite.py -y

# Terminal 2: Start parallel expanded collection
python scripts/data_collection/collect_parallel_expanded.py -y
```

This will interleave ALL API calls (SPY + 15 expanded tickers) across the single 900 calls/min quota, maintaining roughly 17 minute completion for all tickers.

## Implementation Details

### Modified Files

**`src/data_sources/historical_collector.py`**

Added three new methods:

- `collect_multi_symbol_historical(..., parallel=True)` - Entry point with mode selection
- `_collect_multi_symbol_sequential()` - Original sequential collection
- `_collect_multi_symbol_parallel()` - New parallel interleaved collection

**Key Algorithm:**

1. Initialize iterator for each symbol's missing dates
2. Load first date for each symbol into active task queue
3. Round-robin through active symbols:
   - Fetch data for current date
   - Store results
   - Load next date for that symbol
   - Continue to next symbol
4. Remove symbol when dates exhausted
5. Continue until all symbols complete

**Rate Limiting:**

- Shared `self.call_interval = 60 / 900` (0.067 seconds)
- Applied between ALL API calls regardless of symbol
- Maintains consistent 900 calls/min across entire collection system

### New Script

**`scripts/data_collection/collect_parallel_expanded.py`**

Convenience CLI for parallel expanded ticker collection with:

- Expanded ticker preset (15 symbols)
- Custom symbol support
- Status reporting
- Time estimation with speedup calculation
- Full logging and progress tracking

## Database Structure

Both sequential and parallel modes write to the same SQLite database:

**`~/.cache/options_historical.db`**

```sql
options_chains              -- Raw contract data (symbol, date, strike, greeks, etc.)
options_daily_summary       -- Pre-calculated daily GEX
collection_progress         -- Track collection status per symbol-date
```

### Querying Results

```python
from src.cache.sqlite_options_manager import SQLiteOptionsManager

db = SQLiteOptionsManager()

# Get stats for all symbols
stats = db.get_database_stats()
print(f"Total records: {stats['total_options_records']}")
print(f"By symbol: {stats['by_symbol']}")

# Get specific symbol's data
df = db.get_options_date_range("SPY", "2024-01-01", "2024-12-31")

# Get single date's chain
chain = db.get_options_chain("SPY", "2024-01-02")
```

## Monitoring Progress

### During Collection

```bash
# Check live status while collection runs
python scripts/data_collection/collect_parallel_expanded.py --status

# Tail the log
tail -f parallel_collection.log
```

### After Completion

Collection summary saved to:

```text
.cache/collection_summary.json
```

Contains:

- Total API calls made
- Success/failure rates
- Per-symbol statistics
- Database final size
- Collection mode used

## Expanded Ticker Preset

The "expanded" preset collects 15 tickers across multiple asset classes:

**Equities** (8): SPY, QQQ, IWM, AAPL, MSFT, TSLA, VTI, DIA

**Bonds** (3): TLT, IEF, LQD

**Commodities** (2): GLD, SLV

**Volatility** (1): VXX

**Real Estate** (1): IYR

This provides comprehensive multi-asset options data for Paper 3 research.

## Troubleshooting

### Database Locked Error

If you see "database is locked", reduce concurrent background tasks:

- Run only one collection script at a time, OR
- Increase `asyncio.sleep()` intervals in the code

### Interrupted Collection

Collection is resumable - just re-run with `--skip-existing` (default):

```bash
# Re-run after interruption - picks up where it left off
python scripts/data_collection/collect_parallel_expanded.py -y
```

Collection progress is tracked in SQLite, so the system knows which dates are done.

### API Rate Limit Errors

If you hit rate limits:

- Check Alpha Vantage subscription status
- Verify API key is valid
- Premium tier should allow 900+ calls/min
- Current implementation uses 900/min buffer (well below 1000 limit)

## Next Steps

1. **Monitor current SPY collection** (`--status` command)
2. **Once SPY completes**, start parallel expanded collection
3. **Or start parallel expanded now** to interleave with SPY collection
4. **Query results** using SQLiteOptionsManager for GEX analysis
5. **Update Paper 3** research with multi-asset, multi-ticker data

## References

- [Alpha Vantage Premium Plans](https://www.alphavantage.co/premium/) - 900-1000 calls/min tier
- [Historical Collection Implementation](../src/data_sources/historical_collector.py)
- [SQLite Database Schema](../src/cache/sqlite_options_manager.py)
- [Parallel Collection CLI](../scripts/data_collection/collect_parallel_expanded.py)
