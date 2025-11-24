# Raw Options Database Storage - Infrastructure Improvement

**Created**: November 22, 2025
**Status**: ✅ COMPLETE (All phases 1-5 done, November 22, 2025)
**Implementation**: Issue #147 (5 commits, 339 lines)
**Result**: 11,820,580 options migrated, 3.25 GB database

---

## Problem Statement

Currently, the system has a **dual storage architecture** that creates dependencies:

1. **Raw options data**: Stored in file cache (`.cache/gex_data/SPY/*.pickle`)
   - Temporary storage, not persistent
   - Required by `SequentialGEXFetcher` for validation scripts

2. **Calculated GEX metrics**: Stored in database (`daily_gex_metrics` table)
   - Persistent storage
   - Used for analysis and reporting

**Issue**: Validation scripts fail when file cache is cleared, even though database has all GEX calculations.

---

## Root Cause (Phase 4A Issue)

During Phase 2-3 multi-year data collection (Issue #140):

1. Fetched raw options from Alpha Vantage API → stored to file cache
2. Calculated GEX metrics from options → stored to database
3. File cache pickle files are temporary and don't persist
4. Phase 4A validation scripts need raw options to construct 30-day windows
5. **Result**: Had to re-fetch all 2021, 2022, 2025 data despite database having GEX metrics

---

## Proposed Solution

**Store BOTH raw options AND calculated GEX in database**:

### 1. Database Schema (✅ Created)

```sql
CREATE TABLE raw_options_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
    expiration DATE NOT NULL,
    bid REAL,
    ask REAL,
    last REAL,
    volume INTEGER,
    open_interest INTEGER,
    implied_volatility REAL,
    delta REAL,
    gamma REAL,
    theta REAL,
    vega REAL,
    rho REAL,
    contract_symbol TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, strike, option_type, expiration)
);
```

**Benefits**:

- Single source of truth (database)
- No dependency on file cache
- Complete audit trail of raw data
- Enables historical queries without API re-fetching

---

### 2. Collection Infrastructure Changes

**File**: `src/data_sources/historical_gex_builder.py`

**Current flow**:

```
API → file cache → GEX calculation → database (GEX only)
```

**Proposed flow**:

```
API → database (raw options) → GEX calculation → database (GEX metrics)
        ↓
    file cache (backward compat)
```

**Changes needed**:

1. Add `store_raw_options()` method to database builder
2. Insert raw options to `raw_options_chain` table after API fetch
3. Keep file cache write for backward compatibility (temporary)
4. Eventually remove file cache dependency

---

### 3. Fetcher Infrastructure Changes

**File**: `src/data_sources/sequential_gex_fetcher.py`

**Current behavior**:

```python
# Tries database first, falls back to file cache
data = self.gex_cache.get_data_from_db(symbol, date)
if data is None:
    data = self.cache.get_options_data(symbol, date)  # File cache
```

**Proposed behavior**:

```python
# Read from database only
data = self.get_raw_options_from_db(symbol, date)
if data is None:
    # Fallback to file cache (deprecated, log warning)
    logger.warning(f"Using deprecated file cache for {symbol} {date}")
    data = self.cache.get_options_data(symbol, date)
```

**Changes needed**:

1. Add `get_raw_options_from_db()` method
2. Query `raw_options_chain` table
3. Reconstruct DataFrame in same format as file cache
4. Remove file cache dependency in future version

---

## Implementation Plan

### Phase 1: Schema + Backward Compatibility (Current)

- [x] Create `raw_options_chain` table schema
- [ ] Modify `historical_gex_builder.py` to write raw options to DB
- [ ] Keep file cache writes for backward compat
- [ ] Test with single year (2021)

### Phase 2: Fetcher Update

- [ ] Add database read path to `SequentialGEXFetcher`
- [ ] Fallback to file cache with deprecation warning
- [ ] Test Phase 4A validation with database-only reads

### Phase 3: Migration

- [ ] Backfill `raw_options_chain` for existing data (2020-2025)
- [ ] Verify all validation scripts work with database reads
- [ ] Remove file cache dependency entirely

### Phase 4: Cleanup

- [ ] Remove file cache code from `GEXCacheManager`
- [ ] Update documentation
- [ ] Mark file cache as fully deprecated

---

## Estimated Effort

- **Phase 1**: 2-3 hours (modify builder, test)
- **Phase 2**: 1-2 hours (modify fetcher, test)
- **Phase 3**: 4-6 hours (backfill 1,475 days × ~5000 strikes/day)
- **Phase 4**: 1 hour (cleanup + docs)

**Total**: 8-12 hours engineering time

---

## Alternative: Keep Current Architecture

**Pros**:

- No code changes needed
- File cache works fine for 2024 data (already cached)
- Minimal engineering effort

**Cons**:

- Must re-cache data when file cache is cleared
- Duplicate storage (file cache + database)
- Fragile dependency on pickle files
- ~45 minutes to re-cache each year when needed

**Decision**: Proceed with database storage (proper solution) but use file cache workaround for Phase 4A immediate needs.

---

## Related Issues

- **Issue #140**: Multi-year regime validation (Phase 4A blocker)
- **Issue #138**: Dual GEX framework (already using database for metrics)
- **Issue #112**: Batch API implementation (works with current architecture)

---

## Current Workaround (Phase 4A)

**Temporary solution** for immediate Phase 4A needs:

1. Re-cache 2021, 2022, 2025 using `/tmp/collect_year.py`
2. Submit batch jobs once file cache is populated
3. Track database storage as future infrastructure improvement

**Status**: Re-caching in progress (November 22, 2025)

---

**Next Steps**:

1. Complete Phase 4A with file cache workaround
2. Create GitHub issue for database storage implementation
3. Schedule for post-Paper #2 submission (low priority)
