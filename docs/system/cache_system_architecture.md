# Cache System Architecture

## Overview

The GEX-LLM-Patterns project uses a multi-layer cache system for efficient data storage and retrieval. The system is designed with lazy directory creation and supports both daily and intraday data storage.

## Cache System Components

### 1. UnifiedCacheManager (`src/cache/unified_cache.py`)
**Primary cache interface for live market data storage**

**Purpose**: Stores real market data in pickle format with lazy directory creation
**Base Directory**: `.cache/`

```python
from src.cache.unified_cache import UnifiedCacheManager

cache = UnifiedCacheManager()
# Only creates .cache/ directory initially
# Subdirectories created on first use
```

**Storage Structure** (created on-demand):
```
.cache/
├── options/SPY/2024-08-01.pickle     # Options chains
├── market_data/SPY/2024-08-01.pickle # OHLCV data
├── news/earnings/2024-08-01.pickle   # News data
└── metadata/                         # Cache statistics
```

**Key Methods**:
- `store_options_data(symbol, date, df)` - Store options data
- `get_options_data(symbol, date)` - Retrieve options data
- `store_market_data(symbol, df, start_date, end_date)` - Store market data
- `get_market_data(symbol, start_date, end_date)` - Retrieve market data

### 2. GEXCacheManager (`src/cache/gex_cache_manager.py`)
**SQLite-based storage for GEX calculations and pattern analysis**

**Purpose**: Pre-computed gamma exposure storage with parquet/pickle optimization
**Database**: `.cache/consolidated_historical.db`

**Tables**:
```sql
-- Pattern validation results
CREATE TABLE pattern_validation_results (
    date TEXT, symbol TEXT, expected_pattern TEXT,
    detected_pattern TEXT, confidence REAL, success BOOLEAN
);

-- Historical pattern performance tracking
CREATE TABLE historical_pattern_performance (
    pattern_name TEXT, date TEXT, symbol TEXT,
    entry_price REAL, exit_price REAL, return_pct REAL, success BOOLEAN
);
```

**Key Methods**:
- `store_gex_calculation(symbol, date, gex_data)` - Store GEX results
- `get_gex_data(symbol, date_range)` - Retrieve GEX calculations
- `get_pattern_performance(pattern_name)` - Get pattern statistics

### 3. IntradayCacheManager (`src/cache/intraday_cache.py`)
**Timestamp-based storage for intraday analysis**

**Purpose**: 10-minute interval storage for gamma pinning validation
**Structure** (created on-demand):
```
.cache/
├── intraday_options/SPY/2024-01-17/
│   ├── 0930.json    # 9:30 AM market open
│   ├── 1530.json    # 3:30 PM gamma pin time
│   └── 1600.json    # 4:00 PM close
├── intraday_gex/SPY/2024-01-17/
│   └── [same structure]
└── intraday_market/SPY/2024-01-17/
    └── [same structure]
```

**Key Features**:
- Supports full timestamps: `2024-06-07 15:30:00`
- Configurable intervals from `analysis_config.yaml`
- Optimized for gamma pinning validation (75% success rate)

### 4. ConcurrentGEXProcessor (`src/cache/concurrent_gex_processor.py`)
**High-performance parallel processing for multi-symbol GEX calculations**

**Purpose**: Concurrent processing with ThreadPoolExecutor
**Features**:
- Multi-symbol parallel processing
- Memory-efficient batch operations
- Progress tracking and error handling
- Integrates with UnifiedCacheManager and GEXCacheManager

## Data Flow

### Live Data Collection
```python
# 1. Fetch from API/source
options_data = fetch_options_data("SPY", "2024-08-01")

# 2. Store in cache
cache.store_options_data("SPY", "2024-08-01", options_data)
# Creates: .cache/options/SPY/2024-08-01.pickle

# 3. Calculate GEX
gex_data = calculate_gamma_exposure(options_data)

# 4. Store GEX results
gex_cache.store_gex_calculation("SPY", "2024-08-01", gex_data)
# Stores in: .cache/consolidated_historical.db
```

### Pattern Validation
```python
# 1. Historical event validation
validator = PatternLibraryValidator()

# 2. Fetch cached or live data
market_data = validator._get_market_data_live("2021-01-27", "GME")

# 3. Detect patterns
patterns = validator._detect_patterns_from_data(market_data, date, symbol)

# 4. Store validation results
# Automatically stored in consolidated_historical.db
```

## Current Usage Patterns

### 1. Validation Framework (`scripts/validation/validate_patterns.py`)
- Uses UnifiedCacheManager for live data caching
- Stores validation results in consolidated_historical.db
- Lazy directory creation (only creates what's needed)

### 2. Market Data System (`src/data/market_data_system.py`)
- Uses both UnifiedCacheManager and IntradayCacheManager
- Handles both daily and intraday data flows

### 3. MarketMechanicsAgent (`src/agents/market_mechanics_agent.py`)
- Primary consumer of cached data
- Integrates all cache layers for comprehensive analysis

## Configuration

**Cache configuration** in `config_defaults/analysis_config.yaml`:
```yaml
cache_settings:
  base_directory: ".cache"
  options_format: "pickle"  # or "parquet"
  intraday_intervals: [930, 1000, 1430, 1530, 1600]
  retention_days: 90
```

## Performance Optimizations

### 1. Lazy Directory Creation
- Directories only created when data is actually stored
- Eliminates unused empty directories
- Faster initialization

### 2. Format Selection
- Pickle: Fast serialization for DataFrames
- Parquet: Efficient columnar storage (with pyarrow)
- SQLite: Structured data with SQL querying

### 3. Concurrent Processing
- ThreadPoolExecutor for parallel GEX calculations
- Memory-efficient batch operations
- Progress tracking for long-running operations

## Storage Sizes (Typical)

```bash
.cache/
├── consolidated_historical.db        # 16K (pattern results)
├── options/SPY/2024-08-01.pickle    # ~2MB (full options chain)
├── market_data/SPY/2024-08.pickle   # ~50KB (monthly OHLCV)
└── intraday_gex/SPY/2024-08-01/     # ~100KB/interval
```

## Integration Points

**Used by**:
- `scripts/validation/validate_patterns.py` - Pattern validation
- `src/agents/market_mechanics_agent.py` - Primary analysis
- `src/data/market_data_system.py` - Data pipeline
- `scripts/data_collection/automation/automated_data_collector.py` - Data collection
- `src/tools/autogen_tools.py` - AutoGen integration

**Dependencies**:
- `src/utils/date_utils.py` - Date handling
- `src/utils/config_manager.py` - Configuration
- `pandas`, `sqlite3`, `pathlib` - Core dependencies

## Best Practices

### 1. Use Lazy Loading
```python
# Good - only creates directories when storing data
cache = UnifiedCacheManager()
cache.store_options_data("SPY", "2024-08-01", df)

# Avoid - don't pre-create unused directories
```

### 2. Check Cache Before API Calls
```python
# Always check cache first
cached_data = cache.get_options_data("SPY", "2024-08-01")
if cached_data is None:
    # Only fetch from API if not cached
    fresh_data = api.fetch_options("SPY", "2024-08-01")
    cache.store_options_data("SPY", "2024-08-01", fresh_data)
```

### 3. Use Appropriate Cache Layer
- **UnifiedCacheManager**: Live market data (options, stocks, news)
- **GEXCacheManager**: Computed GEX results and pattern analysis
- **IntradayCacheManager**: Timestamp-specific data for gamma pinning

## Troubleshooting

### Empty Directories Created
**Issue**: `.cache/options/`, `.cache/market_data/` created but empty
**Solution**: Directories are created lazily - they'll populate when data is stored

### Import Errors
**Issue**: `ModuleNotFoundError: No module named 'cache'`
**Solution**: Use absolute imports: `from src.cache.unified_cache import UnifiedCacheManager`

### Database Locked
**Issue**: SQLite database locked during concurrent access
**Solution**: GEXCacheManager handles concurrent access automatically

## Migration Notes

From previous cache system:
- ✅ Eliminated 7 empty directories created on initialization
- ✅ Optimized imports (removed unused pandas from intraday_cache.py)
- ✅ All 4 cache files verified as actively used
- ✅ Lazy directory creation implemented
- ✅ Consolidated documentation updated