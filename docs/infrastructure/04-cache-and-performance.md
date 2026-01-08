# Cache System and Performance Optimization

## Overview

The GEX-LLM Pattern Analysis system uses a multi-layer cache system optimized for PhD research data storage and retrieval. The system supports both daily and intraday data storage with lazy directory creation for efficiency, combined with token optimization strategies for cost-efficient LLM usage.

---

## Part 1: Cache System Architecture

### Cache System Components

#### 1. UnifiedCacheManager (`src/cache/unified_cache.py`)

Primary cache interface for live market data storage.

**Purpose**: Stores real market data in pickle format with lazy directory creation
**Base Directory**: `.cache/`

```python
from src.cache.unified_cache import UnifiedCacheManager

cache = UnifiedCacheManager()
# Only creates .cache/ directory initially
# Subdirectories created on first use
```

**Storage Structure** (created on-demand):

```bash
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

#### 2. GEXCacheManager (`src/cache/gex_cache_manager.py`)

SQLite-based storage for GEX calculations and pattern analysis.

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

#### 3. IntradayCacheManager (`src/cache/intraday_cache.py`)

Timestamp-based storage for intraday analysis.

**Purpose**: 10-minute interval storage for gamma pinning validation
**Structure** (created on-demand):

```bash
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
- Optimized for gamma pinning validation research

#### 4. ConcurrentGEXProcessor (`src/cache/concurrent_gex_processor.py`)

High-performance parallel processing for multi-symbol GEX calculations.

**Purpose**: Concurrent processing with ThreadPoolExecutor
**Features**:

- Multi-symbol parallel processing
- Memory-efficient batch operations
- Progress tracking and error handling
- Integrates with UnifiedCacheManager and GEXCacheManager
- **Adaptive worker count**: Auto-calculates optimal threads based on CPU cores (2-8 range)

### Data Flow

#### Live Data Collection

```python
# 1. Fetch from API/source
options_data = fetch_options_data("SPY", "2024-08-01")

# 2. Store in SQLite (Issue #180: primary options storage)
from src.cache.sqlite_options_manager import SQLiteOptionsManager
sqlite_options = SQLiteOptionsManager()
sqlite_options.store_options_chain("SPY", "2024-08-01", options_data)
# Stores in: .cache/consolidated_historical.db

# 3. Calculate GEX
gex_data = calculate_gamma_exposure(options_data)

# 4. Store GEX results
gex_cache.store_gex_calculation("SPY", "2024-08-01", gex_data)
# Stores in: .cache/consolidated_historical.db
```

#### Pattern Validation

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

### Current Usage Patterns

#### 1. Validation Framework (`scripts/validation/validate_patterns.py`)

- Uses UnifiedCacheManager for live data caching
- Stores validation results in consolidated_historical.db
- Lazy directory creation (only creates what's needed)

#### 2. Market Data System (`src/data/market_data_system.py`)

- Uses both UnifiedCacheManager and IntradayCacheManager
- Handles both daily and intraday data flows

#### 3. MarketMechanicsAgent (`src/agents/market_mechanics_agent.py`)

- Primary consumer of cached data
- Integrates all cache layers for comprehensive analysis

### Configuration

**Cache configuration** in `config_defaults/analysis_config.yaml`:

```yaml
cache_settings:
  base_directory: ".cache"
  options_format: "pickle"  # or "parquet"
  intraday_intervals: [930, 1000, 1430, 1530, 1600]
  retention_days: 90
```

### Performance Optimizations

#### 1. Lazy Directory Creation

- Directories only created when data is actually stored
- Eliminates unused empty directories
- Faster initialization

#### 2. Format Selection

- Pickle: Fast serialization for DataFrames
- Parquet: Efficient columnar storage (with pyarrow)
- SQLite: Structured data with SQL querying

#### 3. Concurrent Processing

- ThreadPoolExecutor for parallel GEX calculations
- Memory-efficient batch operations
- Progress tracking for long-running operations
- **Adaptive worker count**: `max(2, min(8, cpu_count - 1))` (Issue #155)

#### 4. Rate Limiting (Issue #155)

- O(1) rate limiting using `collections.deque` with maxlen
- Replaces O(n) list scan for API rate limit checking
- Applied to Alpha Vantage client (`src/data_sources/alpha_vantage_gex.py`)

#### 5. Thread-Safe Configuration (Issue #155)

- ConfigManager uses double-check locking pattern
- Thread-safe singleton initialization
- Prevents multiple config file loads in concurrent scenarios

### Storage Structure

```bash
.cache/
├── consolidated_historical.db        # Pattern validation results
├── options/SPY/2024-08-01.pickle    # Full options chains
├── market_data/SPY/2024-08.pickle   # OHLCV market data
└── intraday_gex/SPY/2024-08-01/     # Intraday GEX calculations
```

### Integration Points

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

### Best Practices

#### 1. Use SQLite for Options Data (Issue #180)

```python
# Primary storage - use SQLiteOptionsManager directly
from src.cache.sqlite_options_manager import SQLiteOptionsManager
sqlite_options = SQLiteOptionsManager()
sqlite_options.store_options_chain("SPY", "2024-08-01", df)
```

#### 2. Check Cache Before API Calls

```python
# Always check SQLite first (Issue #180: primary options storage)
from src.cache.sqlite_options_manager import SQLiteOptionsManager
sqlite_options = SQLiteOptionsManager()
cached_data = sqlite_options.get_options_chain("SPY", "2024-08-01")
if cached_data is None or cached_data.empty:
    # Only fetch from API if not cached
    fresh_data = api.fetch_options("SPY", "2024-08-01")
    sqlite_options.store_options_chain("SPY", "2024-08-01", fresh_data)
```

#### 3. Use Appropriate Cache Layer

- **SQLiteOptionsManager**: Options chain data (primary storage - Issue #180)
- **UnifiedCacheManager**: Market data (stocks, news) - NOT for options
- **GEXCacheManager**: Computed GEX results and pattern analysis
- **IntradayCacheManager**: Timestamp-specific data for gamma pinning

### Troubleshooting

#### Empty Directories Created

**Issue**: `.cache/options/`, `.cache/market_data/` created but empty
**Solution**: Directories are created lazily - they'll populate when data is stored

#### Import Errors

**Issue**: `ModuleNotFoundError: No module named 'cache'`
**Solution**: Use absolute imports: `from src.cache.unified_cache import UnifiedCacheManager`

#### Database Locked

**Issue**: SQLite database locked during concurrent access
**Solution**: GEXCacheManager handles concurrent access automatically

### Migration Notes

From previous cache system:

- ✅ Eliminated 7 empty directories created on initialization
- ✅ Optimized imports (removed unused pandas from intraday_cache.py)
- ✅ All 4 cache files verified as actively used
- ✅ Lazy directory creation implemented
- ✅ Consolidated documentation updated

---

## Part 2: Token Configuration and Cost Optimization

### Overview

The GEX-LLM system uses a hybrid approach with different token configurations for different components, separating data operations (zero tokens) from LLM reasoning (optimized tokens).

### Architecture

#### AutoGen Tools (NO LLM TOKENS)

**Location**: `src/tools/autogen_tools.py`
**Type**: Direct Python function calls
**Token Usage**: Zero - these are not LLM calls

**Functions**:

- `fetch_options_data()` - Direct cache/API data retrieval
- `calculate_gamma_exposure()` - Mathematical GEX calculations
- `fetch_market_data()` - Direct market data API calls

**Key Point**: These tools run as pure Python functions. No LLM involvement, no token costs.

#### Market Mechanics Analysis (LLM REASONING)

**Location**: `src/llm/autogen_market_mechanics.py`
**Type**: O3-mini/O4-mini for reasoning, GPT-4o-mini for tool calls
**Token Limit**: 4000 tokens for analysis

**Configuration**:

```python
# For O3-mini models
client_params["max_completion_tokens"] = 4000

# For standard models (if used)
client_params["max_tokens"] = 4000
```

**Usage**: Complex market mechanics interpretation requiring detailed reasoning.

### Token Usage by Component

| Component | Model | Token Limit | Purpose |
|-----------|-------|-------------|---------|
| AutoGen Tools | None | 0 | Direct function calls |
| Market Analysis | O3-mini/O4-mini | 4000 | Pattern reasoning |
| Tool Calling | GPT-4o-mini | Minimal | Function execution |
| Data Fetching | None | 0 | Cache/API calls |
| GEX Calculation | None | 0 | Mathematical operations |

### Cost Optimization

#### High Efficiency Design

- **Tool Calls**: Zero tokens (direct Python functions)
- **Data Processing**: Zero tokens (local calculations)
- **LLM Usage**: Only for complex market interpretation
- **Token Cost**: ~4000 tokens per analysis (not per tool call)

#### Example Flow

```bash
1. fetch_options_data() → 0 tokens (cache hit)
2. calculate_gamma_exposure() → 0 tokens (math)
3. Market mechanics analysis → 4000 tokens (O3-mini)
Total: 4000 tokens for complete analysis
```

### Failed Test Handling

#### Token Limit Errors

**Detection**: System detects "max_tokens" errors in LLM responses
**Action**: Mark test as `failed_retry_needed`
**Resolution**: Increased token limits from 1000 → 4000

#### Error Categories

- `token_limit`: LLM hit token limit, needs retry
- `llm_failure`: Other LLM errors
- `invalid_response`: Null confidence/direction

### Configuration Files

#### LLM Configuration

**File**: `src/llm/autogen_market_mechanics.py`
**Key Setting**: `analysis_tokens = 4000`

#### Tool Configuration

**File**: `src/tools/autogen_tools.py`
**Key Point**: No token configuration needed (direct function calls)

### Best Practices

1. **Separate Concerns**: Tools do data/math, LLM does reasoning
2. **Token Efficiency**: Only use LLM for complex interpretation
3. **Error Handling**: Detect and retry token limit failures
4. **Cost Control**: High token limits only for analysis, not tools

### Validation

**Test**: `scripts/validation/production_cache_test.py`
**Result**: ✅ 90% confidence analysis with 4000 tokens
**Performance**: ~4000 tokens per complete market analysis

---

## Part 3: ResearchCache for Experiment Tracking

### Overview

ResearchCache provides a structured way to store and query LLM detection results, validation outcomes, and experiment runs with git versioning for reproducibility.

**Location**: `src/cache/research_cache.py`

### Quick Start

```python
from src.cache.research_cache import ResearchCache

# Initialize
cache = ResearchCache()

# Store a detection
detection_id = cache.store_detection(
    symbol="SPY",
    trading_date="2024-01-15",
    pattern_id="regime_30day",
    model_name="o4-mini",
    confidence_score=85.0,
    chain_of_thought="Analysis shows...",
    detected=True
)

# Query detections
detections = cache.get_detections(
    symbol="SPY",
    start_date="2024-01-01",
    end_date="2024-12-31",
    pattern_ids=["regime_30day"]
)

# Record experiment
cache.record_experiment_run(
    run_id="my_experiment_v1",
    description="Testing new regime criteria",
    config={"threshold": 70, "window": 30}
)
```

### Common Queries

```python
from src.cache.research_cache_queries import (
    get_detection_stats_by_year,
    compare_detections_by_confidence,
    get_experiment_history
)

# Detection statistics by year
stats = get_detection_stats_by_year()
for year, data in stats.items():
    print(f"{year}: {data['detection_rate']:.1f}% ({data['detected']}/{data['total']})")

# Compare high vs low confidence
comparison = compare_detections_by_confidence(threshold=80.0)
print(f"Above 80%: {comparison['above']['rate']:.1f}%")
print(f"Below 80%: {comparison['below']['rate']:.1f}%")

# Experiment history
experiments = get_experiment_history("paper2")
for exp in experiments:
    print(f"{exp['run_id']}: {exp['description']}")
```

### Database Schema

| Table | Purpose |
|-------|---------|
| `llm_detections` | Pattern detection results with chain-of-thought |
| `experiment_runs` | Tracks runs with git commit hash for reproducibility |
| `validation_results` | Outcome verification (T+1, T+3, T+5 returns) |

### Best Practices

1. **Always record experiment runs** before generating detections
2. **Use git commit hashes** for reproducibility
3. **Store chain-of-thought** for reviewer transparency
4. **Keep YAML backups** for human review
5. **Query by year/pattern** for performance

### Troubleshooting

**Database locked?** ResearchCache uses `threading.Lock()` for safety. Wait and retry.

**Missing detections?** Check date format (`YYYY-MM-DD`), verify `pattern_id` matches exactly.

### Scaling for Papers 3-5

ResearchCache scales across all papers:

- Paper 3: Multi-symbol detections
- Paper 4: Graph neural network results
- Paper 5: Real-time detection tracking

---

## Summary

The combined cache and performance architecture provides:

- **Multi-layer caching**: Lazy directory creation, format optimization, concurrent processing
- **Zero-token operations**: Data fetching and GEX calculations run locally
- **Optimized LLM usage**: 4000 tokens only for complex market reasoning
- **Cost efficiency**: Significant savings through intelligent separation of concerns
- **Scalability**: Handles multi-year, multi-symbol, intraday data efficiently

---

## Navigation

**Prerequisites**: [03-data-and-database.md](03-data-and-database.md)
**Next**: [05-llm-integration.md](05-llm-integration.md)
**Related**: [docs/development/worktree_cache_management.md](../development/worktree_cache_management.md)
