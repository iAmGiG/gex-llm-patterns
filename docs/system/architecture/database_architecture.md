# Database Architecture Documentation

## Current Database Location

**Path**: `.cache/consolidated_historical.db`

**Current Size**: 36KB (as of latest analysis)

## Location Analysis

### Current Placement: `.cache/consolidated_historical.db`

**Advantages**:

- ✅ **Consistent with cache strategy**: Database is alongside other cached data
- ✅ **Unified data location**: All persistent data in `.cache/` directory
- ✅ **Gitignore compatibility**: `.cache/` already excluded from version control
- ✅ **Backup simplicity**: Single directory to backup all data
- ✅ **Development workflow**: Easy to clean/reset entire cache including database

**Disadvantages**:

- ⚠️ **Semantic confusion**: Database is permanent storage, not traditional "cache"
- ⚠️ **Size concerns**: Will grow significantly with intraday data
- ⚠️ **Performance**: Not optimized for database workloads (depending on filesystem)

### Alternative Locations Considered

#### Option 1: Project Root (`./consolidated_historical.db`)

**Pros**: Clear importance, not mistaken for temporary cache
**Cons**: Clutters project root, mixed with code files

#### Option 2: Data Directory (`./data/consolidated_historical.db`)

**Pros**: Semantic clarity, separate from cache
**Cons**: Creates another directory to manage, splits data locations

#### Option 3: Database Directory (`./database/consolidated_historical.db`)

**Pros**: Very clear purpose, database-specific optimizations
**Cons**: Over-engineering for single database file

## Recommendation: Keep Current Location

**Decision**: Maintain `.cache/consolidated_historical.db`

**Rationale**:

1. **Unified Data Strategy**: All persistent data (market, options, GEX, database) in `.cache/`
2. **Existing Integration**: 2-tier system already configured for this location
3. **Backup/Recovery**: Single directory contains entire data ecosystem
4. **Development Efficiency**: Developers can `rm -rf .cache/` to reset everything
5. **Size Manageable**: Even with intraday data, modern filesystems handle this well

## Database Schema Documentation

### Current Tables

```sql
-- Main GEX aggregations (daily level)
CREATE TABLE daily_gex_metrics (
    symbol TEXT,
    date TEXT,                    -- YYYY-MM-DD format
    spot_price REAL,
    total_gex REAL,
    net_call_gex REAL,
    net_put_gex REAL,
    gamma_flip_point REAL,
    flip_ratio REAL,
    gex_regime TEXT,
    data_quality_score REAL,
    options_count INTEGER,
    created_at TEXT,
    PRIMARY KEY (symbol, date)
);

-- Strike-level GEX details (daily level)
CREATE TABLE strike_gex_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,           -- YYYY-MM-DD format
    strike REAL NOT NULL,
    call_gex REAL,
    put_gex REAL,
    net_gex REAL,
    call_oi INTEGER,
    put_oi INTEGER,
    distance_from_spot REAL,
    created_at TEXT,
    FOREIGN KEY (symbol, date) REFERENCES daily_gex_metrics (symbol, date)
);

-- Pattern detection results
CREATE TABLE pattern_detections (
    [schema not fully documented]
);

-- Federal Reserve context data
CREATE TABLE fed_context (
    [schema not fully documented]
);
```

## Future Intraday Schema (Issue #72)

### Proposed Intraday Tables

```sql
-- Intraday GEX metrics (15-minute intervals)
CREATE TABLE intraday_gex_metrics (
    symbol TEXT,
    timestamp TEXT,               -- YYYY-MM-DD HH:MM:SS format
    spot_price REAL,
    total_gex REAL,
    net_call_gex REAL,
    net_put_gex REAL,
    gamma_flip_point REAL,
    gex_regime TEXT,
    options_count INTEGER,
    created_at TEXT,
    PRIMARY KEY (symbol, timestamp)
);

-- Intraday strike-level details
CREATE TABLE intraday_strike_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,     -- YYYY-MM-DD HH:MM:SS format
    strike REAL NOT NULL,
    call_gex REAL,
    put_gex REAL,
    net_gex REAL,
    call_oi INTEGER,
    put_oi INTEGER,
    distance_from_spot REAL,
    created_at TEXT,
    FOREIGN KEY (symbol, timestamp) REFERENCES intraday_gex_metrics (symbol, timestamp)
);
```

## Performance Considerations

### Current Performance

- **Size**: 36KB for daily data across multiple symbols
- **Query Speed**: Subsecond for daily aggregations
- **Index Strategy**: Primary keys on (symbol, date)

### Intraday Scaling

- **15-min intervals**: ~26× size increase per symbol
- **Expected size**: ~1MB for single symbol, full year intraday
- **Index needs**: (symbol, timestamp), time-range queries
- **Partitioning**: Consider monthly tables for very large datasets

### Optimization Strategies

```sql
-- Indexes for intraday queries
CREATE INDEX idx_intraday_symbol_time ON intraday_gex_metrics(symbol, timestamp);
CREATE INDEX idx_intraday_date_range ON intraday_gex_metrics(symbol, DATE(timestamp));

-- Views for common queries
CREATE VIEW friday_330pm AS
SELECT * FROM intraday_gex_metrics
WHERE strftime('%w', timestamp) = '5'  -- Friday
  AND TIME(timestamp) = '15:30:00';    -- 3:30 PM
```

## Integration Points

### 2-Tier Data System

```python
# Database path already configured
class TwoTierDataSystem:
    def __init__(self, db_path: str = ".cache/consolidated_historical.db"):
        self.db_path = Path(db_path)
```

### Backup Strategy

```bash
# Simple backup of entire data ecosystem
tar -czf backup_$(date +%Y%m%d).tar.gz .cache/

# Database-specific backup
cp .cache/consolidated_historical.db .cache/consolidated_historical.db.backup
```

### Environment Configuration

```python
# Optional: Make database location configurable
DB_PATH = os.environ.get('GEX_DATABASE_PATH', '.cache/consolidated_historical.db')
```

## Migration Path

### When Implementing Intraday Support (Issue #72)

1. **Preserve existing schema**: Daily tables remain unchanged
2. **Add intraday tables**: New tables for timestamp-based data
3. **Dual support**: System supports both daily and intraday queries
4. **Gradual migration**: Can move daily data to intraday format over time

### Schema Evolution

```sql
-- Version 1.0: Daily tables (current)
-- Version 2.0: Add intraday tables (Issue #72)
-- Version 3.0: Potentially consolidate schemas
```

## Conclusion

The current database location at `.cache/consolidated_historical.db` is **optimal** for our usage pattern:

- Unified data management strategy
- Simple backup/recovery
- Development workflow efficiency
- Scales appropriately for projected growth

The location should be **maintained** as we implement intraday support in Issue #72.
