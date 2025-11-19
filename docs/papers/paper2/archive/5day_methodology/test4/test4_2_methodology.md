# Test 4: Methodology - Low-GEX Negative Control

**Date**: November 5, 2025
**Approach**: Real historical data (pre-0DTE era)
**Dataset**: 2020 full year (257 5-day windows)

---

## Objective

Validate LLM can discriminate pattern strength by comparing detection rates between weak (2020) and strong (2024) GEX regimes.

**Test Hypothesis**: If methodology is sound, detection rate should be significantly lower on 2020 data (weak GEX) compared to Q1 2024 (strong GEX).

---

## Data Preparation

### Step 1: Historical Options Data Collection

**Script**: `scripts/validation/negative_controls/fetch_2020_options.py`

**Method**: HistoricalOptionsCollector (cache + API fallback)

**Why needed**: HistoricalGEXDatabaseBuilder only checks cache, never falls back to API

```bash
python scripts/validation/negative_controls/fetch_2020_options.py
```

**Result**:

- 250 trading days fetched from Alpha Vantage Premium API
- Cached to `.cache/` for subsequent processing
- Duration: ~15 minutes

---

### Step 2: GEX Calculation

**Script**: `scripts/validation/negative_controls/process_2020_gex_simple.py`

**Method**: Direct GEX calculation bypassing broken HistoricalGEXDatabaseBuilder

**Process**:

1. Iterate through cached 2020 options data
2. Infer spot price from deep ITM call options
3. Calculate GEX using GEXCalculator
4. Insert directly into database

```bash
PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH \
python scripts/validation/negative_controls/process_2020_gex_simple.py
```

**Result**:

- 252 trading days processed
- Added to `.cache/consolidated_historical.db` (does not replace 2024 data)
- Duration: ~4 minutes

**2020 GEX Summary**:

- Avg: $2.85B (only **11%** of 2024's $26.06B)
- Range: $0.01B - $11.23B
- Avg SPY Price: $321.47

---

### Step 3: Cache Structure Export

**Script**: `scripts/validation/negative_controls/export_db_to_cache_v2.py`

**Why needed**: SequentialGEXFetcher expects directory structure with JSON files, not flat database queries

**Required format**:

```
.cache/gex_data/SPY/YYYY-MM-DD/
  ├── gex_summary.json  (GEX metrics)
  └── metadata.json     (timestamp, file references)
```

```bash
PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH \
python scripts/validation/negative_controls/export_db_to_cache_v2.py
```

**Result**:

- 252 date directories created
- Duration: ~5 seconds

---

## Window Selection Strategy

### Options Considered

| Option | Sample Size | Runtime | Coverage | Rationale |
|--------|-------------|---------|----------|-----------|
| A: Full Year | 257 windows | ~1 hour | Complete | Comprehensive, no bias |
| B: Stratified | 60 windows | ~30 min | Balanced | Tests all GEX ranges |
| C: Very Low GEX | 42 windows | ~20 min | Conservative | Strongest discrimination test |
| D: Smoke Test | 20 windows | ~10 min | Quick | Initial validation only |

### Selected: Option A (Full Year)

**Rationale**:

1. **Comprehensive**: Tests all GEX strengths ($0.01-11.23B)
2. **No filtering bias**: Avoids cherry-picking windows
3. **Statistical power**: 257 windows provides robust sample
4. **Simplicity**: No max-gex-threshold parameter needed
5. **User guidance**: "Simpler is better"

**2020 Window Distribution** (estimated):

- < $1B (Very Low): ~42 windows (16%)
- $1-2B (Low): ~77 windows (30%)
- $2-3B (Medium-Low): ~34 windows (13%)
- $3-5B (Medium): ~48 windows (19%)
- ≥ $5B (High): ~47 windows (18%)
- Missing data: ~9 windows (3%)

**Note**: Even "High" 2020 windows ($5-11B) are weaker than 2024 minimum ($8.16B).

---

## Test 4 Validation Execution

### Configuration

**Script**: `scripts/validation/validate_sequential_patterns.py` (main validation, not in negative_controls/)

```bash
PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH \
python scripts/validation/validate_sequential_patterns.py \
  --symbol SPY \
  --start-date 2020-01-08 \
  --end-date 2020-12-31 \
  --lookback 5 \
  --confidence 60.0 \
  --batch-size 10 \
  --output reports/validation/test4_negative_control/test4_2020_full_year.yaml
```

**Parameters**:

- **Windows**: 257 5-day windows (full 2020 year after initial lookback)
- **LLM Model**: o4-mini (reasoning model, same as Q1 2024)
- **Batch Size**: 10 windows per batch (26 batches total)
- **Confidence Threshold**: 60.0% (same as Q1 2024)
- **Obfuscation**: Enabled (Day T+0, INDEX_1 format)
- **Prompt Version**: v3a (neutral, mechanical guidance)

### Execution Timeline

- **Start**: 2025-11-05 16:19 UTC
- **End**: 2025-11-05 17:16 UTC
- **Duration**: 57 minutes (13.3 sec/window avg)
- **Batches**: 26 batches of 10 windows each
- **Log**: `/tmp/test4_2020_full_run.log`

---

## Pass/Fail Criteria

### Original Hypothesis

**Pass Criteria** (proves discrimination):

- Detection rate < 50% on 2020 data
- Ideally < 30% for very weak windows (< $1B)
- Clear gradient: lower GEX → lower detection rate

**Fail Criteria** (suggests "yes machine"):

- Detection rate > 70% on 2020 data
- No correlation between GEX strength and detection
- Uniform high detection across all GEX ranges

**Actual Result**: 98.4% detection (see Results & Analysis document)

---

## Comparison to Q1 2024

### Test Configuration (Identical)

| Parameter | Q1 2024 | 2020 Full Year |
|-----------|---------|----------------|
| LLM Model | o4-mini | o4-mini |
| Lookback Days | 5 | 5 |
| Confidence Threshold | 60.0% | 60.0% |
| Obfuscation | Enabled | Enabled |
| Prompt Version | v3a neutral | v3a neutral |
| Batch Size | 10 | 10 |

### Dataset Characteristics (Different)

| Metric | Q1 2024 | 2020 Full Year | Ratio |
|--------|---------|----------------|-------|
| Trading Days | 61 | 257 | 4.2x |
| Windows | 61 | 257 | 4.2x |
| Avg GEX | $13.95B | $2.85B | **0.20x** |
| Min GEX | $8.16B | $0.01B | **0.001x** |
| Max GEX | $38.57B | $11.23B | 0.29x |
| Era | 0DTE | Pre-0DTE | - |

**Key difference**: 2020 has **5x lower average GEX** and **800x lower minimum GEX**.

---

## Technical Issues Encountered

### Bug #1: HistoricalGEXDatabaseBuilder Cache-Only Operation

**Location**: `src/data_sources/historical_gex_builder.py`

**Problem**: Builder only calls `cache.get_options_data()`, never uses collector with API fallback

**Impact**: Cannot fetch historical data beyond cached dates

**Workaround**: Created `fetch_2020_options.py` using HistoricalOptionsCollector directly

---

### Bug #2: Resume Logic Assumes Forward-Only Building

**Location**: `src/data_sources/historical_gex_builder.py` (resume logic)

**Problem**: Filters out all dates before `max(existing dates)`, assumes chronological forward building

**Impact**: Cannot backfill historical data (skips all 2020 when 2024 data exists)

**Workaround**: Created `process_2020_gex_simple.py` with direct GEX calculation

---

### Cache Structure Requirements

**Discovery**: SequentialGEXFetcher expects **directories** not files

**Key code** (`src/data_sources/sequential_gex_fetcher.py:169-182`):

```python
for date_dir in sorted(cache_dir.iterdir()):
    if date_dir.is_dir():  # <-- EXPECTS DIRECTORIES
        date_str = date_dir.name
        if date_str <= end_date:
            available_dates.append(date_str)
```

**Initial mistake**: Created flat `.parquet` files → Fetcher found 0 trading days

**Solution**: Export to proper structure:

```
.cache/gex_data/SPY/2020-01-02/
  ├── gex_summary.json
  └── metadata.json
```

---

## Database State After Test 4

**`.cache/consolidated_historical.db`**:

- **2020**: 252 trading days (avg $2.85B GEX)
- **2024**: 86 trading days (avg $26.06B GEX)
- **Total**: 338 days of historical GEX data

**Cache Structure** (`.cache/gex_data/SPY/`):

- **2020**: 252 date directories
- **2024**: 86 date directories
- **Format**: `YYYY-MM-DD/gex_summary.json` + `metadata.json`

---

## Scripts Created

All organized in `scripts/validation/negative_controls/`:

| Script | Purpose | Status |
|--------|---------|--------|
| `fetch_2020_options.py` | Fetch historical options data | ✅ Works |
| `process_2020_gex_simple.py` | Calculate GEX from cached options | ✅ Works |
| `export_db_to_cache_v2.py` | Export to cache directory structure | ✅ Works |
| `build_2019_2020_test4.py` | Original builder attempt | ❌ DEPRECATED |

**DEPRECATED**: `build_2019_2020_test4.py` kept for reference (documents builder bugs)

---

## Validation Log

**Full log**: `/tmp/test4_2020_full_run.log`

**Contains**:

- LLM prompts for all 257 windows
- Detection results with confidence scores
- WHO/WHOM/WHAT for each detected pattern
- Trajectory classifications
- Outcome metrics (T+1 returns, etc.)

**Size**: ~15 MB (257 windows × 15-50 KB per window)

---

## Next Steps

See Results & Analysis document for:

- Detection rate statistics
- Three possible interpretations
- Stratified GEX analysis plan
- Impact on Paper #2 and Phase 2 decision

---

**Date**: November 5, 2025
