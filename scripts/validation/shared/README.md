# Shared Validation Utilities

**Purpose**: Cross-paper utilities for data management and testing

---

## Scripts

### `export_db_to_cache.py`

**Purpose**: Export historical GEX database to cached format for faster access

**Usage**:

```bash
python scripts/validation/shared/export_db_to_cache.py \
  --start-date 2024-01-02 \
  --end-date 2024-12-31 \
  --output .cache/historical_gex_2024.pkl
```

**Key Features**:

- Converts SQLite database to pickle cache
- Reduces API calls during validation runs
- Speeds up multi-pattern testing
- Maintains data integrity checks

**Used By**: Both Paper #1 and Paper #2 validation workflows

---

### `production_cache_test.py`

**Purpose**: Validate cache integrity and performance

**Usage**:

```bash
python scripts/validation/shared/production_cache_test.py \
  --date 2024-01-02 \
  --symbol SPY
```

**Key Features**:

- Tests cache hit rates
- Validates data consistency (cache vs database vs API)
- Measures read/write performance
- Detects cache corruption

**Use Cases**:

- After database rebuilds
- Before major validation runs
- Troubleshooting data quality issues

---

## Dependencies

**Python Modules**:

- `src.cache.unified_cache` - Cache management system
- `src.data_sources.historical_gex_builder` - Database builder

**Data Sources**:

- Historical GEX database (`.cache/consolidated_historical.db`)
- Cached pickle files (`.cache/*.pkl`)
