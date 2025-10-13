# Data Architecture for GEX-LLM Pattern Analysis

## Overview

The GEX-LLM Pattern Analysis system uses a 2-tier data system optimized for PhD research, supporting both historical backtesting and live experimental validation with cost control and obfuscation capabilities.

## 2-Tier Data System

### Architecture

```bash
Request → Tier 1 (Database) → Tier 2 (Cache) → AutoGen Tools → API → Warning
```

### Components

**Tier 1: Database Direct Access**

- **Purpose**: Fastest data access for repeated PhD experiments
- **Implementation**: Direct SQLite queries via `MarketMechanicsAgent`
- **Storage**: SQLite at `.cache/consolidated_historical.db`
- **Performance**: ~3-7 seconds vs 10+ minutes for API calls
- **Tables**: `daily_gex_metrics`, `intraday_gex_metrics`, `strike_gex_details`

**Tier 2: Cache Fallback**

- **Purpose**: Secondary storage for recently accessed data
- **Implementation**: `src/cache/unified_cache.py`
- **Storage**: In-memory + file-based caching with pickle serialization
- **TTL**: 24 hours for market data, 10 years for historical options
- **Auto-promotion**: Cache hits automatically stored in database

**Tier 3: AutoGen Tools Integration**

- **Purpose**: Intelligent data fetching with multiple source fallbacks
- **Implementation**: `src/tools/autogen_tools.py`
- **Functions**: `fetch_options_data()`, `calculate_gamma_exposure()`, `fetch_market_data()`
- **Features**: Cache-aware, API routing, cost optimization

**Tier 4: Direct API Access**

- **Purpose**: Last resort for missing data
- **APIs**: Alpha Vantage, Polygon.io, multiple providers
- **Rate Limiting**: Alpha Vantage (75 calls/minute), provider-specific limits
- **Error Handling**: Graceful degradation with warnings

### Data Flow

1. **Experiment Request**: `MarketMechanicsAgent.run_experiment()` needs data for analysis
2. **Database First**: Check SQLite for existing GEX calculations (fastest path)
3. **Cache Check**: If not in database, check unified cache for options/market data
4. **AutoGen Tools**: If cache miss, use intelligent fetching with source routing
5. **Direct API**: Last resort with rate limiting and error handling
6. **Data Obfuscation**: Apply date/ticker anonymization for LLM analysis
7. **Storage Promotion**: Store results in database for future experiments

## Performance Characteristics

### Expected Hit Rates (PhD Research Context)

- **Database Hit Rate**: High for repeated pattern validation experiments
- **Cache Hit Rate**: Moderate for recent data not yet promoted to database
- **AutoGen Tools Success**: High success rate with intelligent routing
- **Data Miss Rate**: Low (legitimate data unavailability)

### Performance Improvements

- **Significant performance gains** over direct API approaches
- **Cost optimization** for repeated PhD experiments
- **LLM batch processing** savings
- **Research reproducibility** through consistent data access

## Data Tables

### options_data

```sql
CREATE TABLE options_data (
    date TEXT,
    symbol TEXT,
    data TEXT,  -- JSON blob with full options chain
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, symbol)
);
```

### market_data

```sql
CREATE TABLE market_data (
    date TEXT,
    symbol TEXT,
    close REAL,
    volume INTEGER,
    high REAL,
    low REAL,
    open REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, symbol)
);
```

### gex_data

```sql
CREATE TABLE gex_data (
    date TEXT,
    symbol TEXT,
    net_gex REAL,
    gex_regime TEXT,
    gamma_flip REAL,
    data TEXT,  -- JSON blob with additional GEX metrics
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, symbol)
);
```

## Usage Examples

### Basic Data Fetching

```python
from src.data.two_tier_system import TwoTierDataSystem

data_system = TwoTierDataSystem()

# Fetch options data (Database → Cache → Warning)
options_data = data_system.fetch_options_data("2024-01-15", "SPY")

# Fetch market data
market_data = data_system.fetch_market_data("2024-01-15", "SPY")

# Fetch GEX data
gex_data = data_system.fetch_gex_data("2024-01-15", "SPY")
```

### Performance Monitoring

```python
# Get performance statistics
stats = data_system.get_performance_stats()
print(f"Database hit rate: {stats['database_hit_rate_pct']:.1f}%")
print(f"Data availability: {stats['data_availability_pct']:.1f}%")
```

## Integration with Continuous Framework

### Strategy Integration

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

### Batch Processing Integration

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

### Checkpoint Integration

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

## Error Handling

### Missing Data Behavior

- **Warning Logged**: Clear user notification when data unavailable
- **Graceful Degradation**: Strategy continues with available data
- **Performance Tracking**: Miss rates monitored and reported

### Database Issues

- **Auto-Creation**: Tables created automatically if missing
- **Fallback**: Cache still available if database fails
- **Recovery**: System continues operation with degraded performance

## Configuration

### Database Path

```yaml
# config_defaults/baseline_comparison_config.yaml
data_system:
  database_path: ".cache/consolidated_historical.db"
  cache_ttl: 86400  # 24 hours
  warn_on_missing: true
```

**Update (October 2025)**: The `baseline_comparison.py` analysis module no longer queries the database for pattern results. It now loads from validation YAML files at `reports/validation/pattern_taxonomy/*.yaml`. Database queries are still used for GEX metrics and market data. See `src/analysis/deprecated/README.md` for details on deprecated database-dependent analysis files.

### Performance Tuning

- **Database Location**: SSD recommended for optimal performance
- **Cache Size**: Configure based on available memory
- **Batch Size**: Optimize based on typical experiment ranges

## Monitoring and Metrics

### Key Performance Indicators

- **Database Hit Rate**: Should be >90% for mature experiments
- **Data Availability**: Should be >95% for quality date ranges
- **Cache Promotion Rate**: Measures system learning efficiency

### Alerting

- **Low Database Hit Rate**: Indicates need for data population
- **High Miss Rate**: Suggests poor date range selection
- **Performance Degradation**: Database or cache issues

This architecture provides the foundation for high-performance, reliable continuous experiments while maintaining clear user feedback about data availability.
