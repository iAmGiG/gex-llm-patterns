# Data and Database Architecture

## Overview

The GEX-LLM Pattern Analysis system uses a **3-tier data architecture** optimized for PhD research, supporting both historical backtesting and live experimental validation with cost control and obfuscation capabilities.

**Architecture Update (January 2026)**: System migrated from SQLite to PostgreSQL for production data storage, with new ResearchCache layer for experiment tracking and reproducibility.

---

## Part 1: Data Architecture

### 3-Tier Data System

#### Architecture

```bash
Request → Tier 1 (PostgreSQL) → Tier 2 (ResearchCache) → Tier 3 (File Cache) → AutoGen Tools → API
```

#### Components

**Tier 1: PostgreSQL Production Database**

- **Purpose**: Scalable raw options data storage for Papers 2-5
- **Implementation**: PostgreSQL 18.1 on HPCC cluster
- **Database**: `gex_options` (20.58 GB, 81.8M contracts)
- **Performance**: Thread-safe, supports 100+ concurrent writers
- **Tables**: `options_chains_partitioned` (yearly partitions 2020-2025)
- **Coverage**: 50 symbols, 6 years (2020-2025), 1,507 trading days
- **Schema**: 31 fields per contract (27 original + 4 calculated)
- **Status**: Deployed January 2-4, 2026 (Issues #194, #179, #183, #193)

**Tier 2: ResearchCache (SQLite)**

- **Purpose**: Research metadata layer for experiment tracking and reproducibility
- **Implementation**: SQLite at `.cache/research_cache.db`
- **Performance**: Fast queries for analysis and paper writing
- **Tables**: `llm_detections`, `validation_results`, `experiment_runs`, `pattern_library`, `obfuscation_mappings`, `market_data`, `options_chain`, `gex_summary`
- **Use Cases**: Store LLM detection results with chain-of-thought, track validation outcomes, link experiments to git commits
- **Status**: Deployed January 4, 2026 (Issue #169)
- **Documentation**: See `docs/infrastructure/RESEARCH_CACHE_GUIDE.md`

**Tier 3: Legacy SQLite (Deprecated)**

- **Previous Implementation**: SQLite at `.cache/consolidated_historical.db`
- **Status**: Being phased out in favor of PostgreSQL + ResearchCache
- **Tables**: `daily_gex_metrics`, `intraday_gex_metrics`, `strike_gex_details`
- **Migration**: Complete for Papers 2-5 (January 2026)

**Tier 4: File Cache (Legacy)**

- **Purpose**: Secondary storage for recently accessed data (legacy system)
- **Implementation**: `src/cache/unified_cache.py`
- **Storage**: In-memory + file-based caching with pickle serialization
- **TTL**: 24 hours for market data, 10 years for historical options
- **Status**: Still used for non-PostgreSQL data sources

**Tier 5: AutoGen Tools Integration**

- **Purpose**: Intelligent data fetching with multiple source fallbacks
- **Implementation**: `src/tools/autogen_tools.py`
- **Functions**: `fetch_options_data()`, `calculate_gamma_exposure()`, `fetch_market_data()`
- **Features**: Cache-aware, API routing, cost optimization

**Tier 6: Direct API Access**

- **Purpose**: Last resort for missing data
- **Primary API**: Alpha Vantage (options chain data, 75 calls/minute premium, 1000 calls/minute with PREMO key)
- **Secondary API**: Polygon.io (stock prices only, used for specific test cases, 5 calls/minute)
- **Rate Limiting**: Enforced per provider specifications
- **Error Handling**: Graceful degradation with warnings
- **Configuration**: API keys stored in `config/config.json` (not tracked in git)

### Data Flow (Updated January 2026)

1. **Experiment Request**: `MarketMechanicsAgent.run_experiment()` or batch validation needs data
2. **PostgreSQL First**: Check PostgreSQL for raw options data (fastest path for Papers 2-5)
3. **ResearchCache Check**: Query ResearchCache for previous LLM detections and experiment results
4. **Legacy SQLite**: Fall back to old SQLite database for historical experiments
5. **File Cache**: Check unified cache for recently accessed data not yet in database
6. **AutoGen Tools**: If cache miss, use intelligent fetching with source routing
7. **Direct API**: Last resort with rate limiting and error handling
8. **Data Obfuscation**: Apply date/ticker anonymization for LLM analysis
9. **Storage Promotion**: Store results in PostgreSQL (raw data) and ResearchCache (experiment metadata)

### Performance Characteristics

#### Expected Hit Rates (PhD Research Context)

- **Database Hit Rate**: High for repeated pattern validation experiments
- **Cache Hit Rate**: Moderate for recent data not yet promoted to database
- **AutoGen Tools Success**: High success rate with intelligent routing
- **Data Miss Rate**: Low (legitimate data unavailability)

#### Performance Improvements

- **Significant performance gains** over direct API approaches
- **Cost optimization** for repeated PhD experiments
- **LLM batch processing** savings
- **Research reproducibility** through consistent data access

### Integration with Continuous Framework

#### Strategy Integration

All strategies (`V0-V4`) use the 2-tier system automatically:

```python
class GEXStrategyV2(BaseGEXStrategy):
    def __init__(self, symbol: str = "SPY", config: Optional[Dict] = None):
        super().__init__(symbol, config)
        self.data_system = TwoTierDataSystem()

    def analyze_day(self, date: str, market_data: Dict, gex_data: Dict):
        # Data automatically fetched via 2-tier system
        # Warns user if data unavailable
        pass
```

#### Batch Processing Integration

The batch LLM processor uses the 2-tier system for efficient data preparation:

```python
from src.llm.batch_processor import BatchLLMProcessor
from src.data.two_tier_system import TwoTierDataSystem

batch_processor = BatchLLMProcessor(llm_provider)
data_system = TwoTierDataSystem()

# Prepare weekly batch with optimized data fetching
weekly_data = data_system.fetch_options_data(date_range)
batch_analysis = batch_processor.prepare_batch_analysis(weekly_data)
```

#### Checkpoint Integration

Checkpoints include data system performance metrics:

```python
checkpoint = BacktestCheckpoint(
    # ... other fields
    metadata={
        'data_performance': data_system.get_performance_stats(),
        'data_availability': f"{stats['data_availability_pct']:.1f}%"
    }
)
```

### Error Handling

#### Missing Data Behavior

- **Warning Logged**: Clear user notification when data unavailable
- **Graceful Degradation**: Strategy continues with available data
- **Performance Tracking**: Miss rates monitored and reported

#### Database Issues

- **Auto-Creation**: Tables created automatically if missing
- **Fallback**: Cache still available if database fails
- **Recovery**: System continues operation with degraded performance

### Configuration

#### Database Path

```yaml
# config_defaults/baseline_comparison_config.yaml
data_system:
  database_path: ".cache/consolidated_historical.db"
  cache_ttl: 86400  # 24 hours
  warn_on_missing: true
```

**Update (October 2025)**: The `baseline_comparison.py` analysis module no longer queries the database for pattern results. It now loads from validation YAML files at `reports/validation/pattern_taxonomy/*.yaml`. Database queries are still used for GEX metrics and market data. See `src/analysis/deprecated/README.md` for details on deprecated database-dependent analysis files.

#### Performance Tuning

- **Database Location**: SSD recommended for optimal performance
- **Cache Size**: Configure based on available memory
- **Batch Size**: Optimize based on typical experiment ranges

### Monitoring and Metrics

#### Key Performance Indicators

- **Database Hit Rate**: Should be >90% for mature experiments
- **Data Availability**: Should be >95% for quality date ranges
- **Cache Promotion Rate**: Measures system learning efficiency

#### Alerting

- **Low Database Hit Rate**: Indicates need for data population
- **High Miss Rate**: Suggests poor date range selection
- **Performance Degradation**: Database or cache issues

---

## Part 2: Database Architecture

### Current Database Location

**Path**: `.cache/consolidated_historical.db`

**Purpose**: Central storage for GEX calculations, pattern validation results, and experimental data for PhD research

**Storage**: Sufficient capacity for multi-year historical analysis with intraday support

### Location Analysis

#### Current Placement: `.cache/consolidated_historical.db`

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

#### Recommendation: Keep Current Location

**Decision**: Maintain `.cache/consolidated_historical.db`

**Rationale**:

1. **Unified Data Strategy**: All persistent data (market, options, GEX, database) in `.cache/`
2. **Existing Integration**: 2-tier system already configured for this location
3. **Backup/Recovery**: Single directory contains entire data ecosystem
4. **Development Efficiency**: Developers can `rm -rf .cache/` to reset everything
5. **Size Manageable**: Even with intraday data, modern filesystems handle this well

### Database Schema Documentation

#### Current Tables (PhD Research Context)

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
    gex_regime TEXT,              -- POSITIVE/NEGATIVE_GAMMA_HIGH/LOW
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

-- Pattern validation results (PhD research)
CREATE TABLE pattern_validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    expected_pattern TEXT NOT NULL,        -- Expected pattern from historical analysis
    detected_pattern TEXT,                -- LLM-detected pattern
    confidence REAL,                      -- LLM confidence score
    validated_at TEXT,
    data_source TEXT,                     -- 'live', 'cache', 'obfuscated'
    success BOOLEAN,                      -- Did detection match expectation
    notes TEXT
);

-- Historical pattern performance tracking
CREATE TABLE historical_pattern_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_name TEXT NOT NULL,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    entry_price REAL,
    exit_price REAL,
    return_pct REAL,
    hold_days INTEGER,
    success BOOLEAN,
    created_at TEXT,
    data_source TEXT
);
```

#### Current Intraday Schema (Issue #72 - Implemented)

```sql
-- Intraday GEX metrics (supports timestamps like '2024-06-07 15:30:00')
CREATE TABLE intraday_gex_metrics (
    symbol TEXT,
    timestamp TEXT,               -- YYYY-MM-DD HH:MM:SS format
    spot_price REAL,
    total_gex REAL,
    net_call_gex REAL,
    net_put_gex REAL,
    gamma_flip_point REAL,
    flip_ratio REAL,             -- For pin analysis
    gex_regime TEXT,             -- Regime classification
    data_quality_score REAL,
    options_count INTEGER,
    created_at TEXT,
    PRIMARY KEY (symbol, timestamp)
);

-- Intraday strike-level details (for enhanced pattern detection)
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
    gamma_concentration_pct REAL, -- For Issue #73 gamma pinning validation
    created_at TEXT,
    FOREIGN KEY (symbol, timestamp) REFERENCES intraday_gex_metrics (symbol, timestamp)
);
```

### Performance Considerations

#### Current Performance

- **Query Speed**: Optimized for research workloads
- **Index Strategy**: Primary keys on (symbol, date/timestamp)
- **Scalability**: Supports both daily and intraday analysis

#### Intraday Scaling

- **Temporal Resolution**: Supports minute-level analysis
- **Index Strategy**: Optimized for time-range queries
- **Partitioning**: Scalable design for extended historical periods

#### Optimization Strategies

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

### Integration Points

#### MarketMechanicsAgent Integration

```python
# Agent directly queries database for efficiency
class MarketMechanicsAgent:
    def _fetch_gex_from_database(self, date_str: str) -> Optional[Dict]:
        conn = sqlite3.connect("./.cache/consolidated_historical.db")
        # Support both daily and intraday queries
        is_intraday = ' ' in date_str and ':' in date_str
        table = "intraday_gex_metrics" if is_intraday else "daily_gex_metrics"
```

#### Pattern Validation Integration

```python
# Validation results stored automatically
def validate_known_events(self) -> Dict:
    conn = sqlite3.connect(self.db_path)
    # Store validation results for statistical analysis
    cursor.execute("""
        INSERT INTO pattern_validation_results
        (date, symbol, expected_pattern, detected_pattern, confidence, success)
        VALUES (?, ?, ?, ?, ?, ?)
    """, validation_data)
```

#### Backup Strategy

```bash
# Simple backup of entire data ecosystem
tar -czf backup_$(date +%Y%m%d).tar.gz .cache/

# Database-specific backup
cp .cache/consolidated_historical.db .cache/consolidated_historical.db.backup
```

#### Environment Configuration

```python
# Optional: Make database location configurable
DB_PATH = os.environ.get('GEX_DATABASE_PATH', '.cache/consolidated_historical.db')
```

### Migration Path

#### When Implementing Intraday Support (Issue #72)

1. **Preserve existing schema**: Daily tables remain unchanged
2. **Add intraday tables**: New tables for timestamp-based data
3. **Dual support**: System supports both daily and intraday queries
4. **Gradual migration**: Can move daily data to intraday format over time

#### Schema Evolution

```sql
-- Version 1.0: Daily tables (current)
-- Version 2.0: Add intraday tables (Issue #72)
-- Version 3.0: Potentially consolidate schemas
```

### Conclusion

The current database location at `.cache/consolidated_historical.db` is **optimal** for our usage pattern:

- Unified data management strategy
- Simple backup/recovery
- Development workflow efficiency
- Scales appropriately for projected growth

The location should be **maintained** as we implement intraday support in Issue #72.

---

This architecture provides the foundation for high-performance, reliable continuous experiments while maintaining clear user feedback about data availability.

---

## Navigation

**Prerequisites**: [02-architecture-overview.md](02-architecture-overview.md)
**Next**: [04-cache-and-performance.md](04-cache-and-performance.md)
**Related**: [docs/development/worktree_cache_management.md](../development/worktree_cache_management.md)
