# Data Pipeline Documentation

## Overview

The data pipeline manages the collection, caching, and preprocessing of financial market data from multiple sources: Alpha Vantage API for options data, FRED API for economic indicators, with a focus on SPY/SPX options chains and Fed context for enhanced GEX calculations.

## Pipeline Architecture

```bash
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Alpha Vantage  │────│  Rate Limiter   │────│   Cache Layer   │
│   API (Premium) │    │ 75 calls/min    │    │  Smart Expiry   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
┌─────────────────┐                                     │
│   FRED API      │────┬─────────────────────────────────┘
│ (Fed Indicators)│    │
└─────────────────┘    │
         │              │
         └──────────────┼─────────────────────────────────┐
                        │                                 │
                ┌───────▼─────────┐                       │
                │  Data Validator │                       │
                │   & Processor   │                       │
                └─────────────────┘                       │
                        │                                 │
                ┌───────▼─────────┐                       │
                │   GEX Engine    │◄──────────────────────┘
                │  + Fed Context  │
                └─────────────────┘
                        │
                ┌───────▼─────────┐
                │ Enhanced Market │
                │ Data + Patterns │
                └─────────────────┘
```

## Alpha Vantage Integration

### Client Configuration

The `AlphaVantageGEXClient` is specifically designed for GEX analysis needs:

```python
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.cache import UnifiedCacheManager

# Initialize with caching
cache_manager = UnifiedCacheManager()
client = AlphaVantageGEXClient(cache_manager=cache_manager)
```

### API Key Management

Uses the `@config/` system for secure API key management:

```python
# Keys loaded via ConfigLoader (excluded from repository)
from config.config_loader import ConfigLoader

config_loader = ConfigLoader()
api_key = config_loader.get("ALPHA_VANTAGE_KEY")
```

### Rate Limiting Strategy

#### API Tier Requirements

- **Free Tier**: 25 calls per day (insufficient for research needs)
- **Entry Premium Tier**: 75 calls per minute (recommended for this project)
- **Historical Options**: Requires premium subscription for options chain data
- **Current Setup**: Designed for entry premium tier (75 calls/min)

#### Rate Limit Implementation

```python
class RateLimiter:
    def __init__(self, calls_per_minute=75):
        self.calls_per_minute = calls_per_minute
        self.call_timestamps = []
        
    def check_rate_limit(self) -> bool:
        """Check if within rate limits, update timestamps"""
        from src.utils.date_utils import now_iso
        from datetime import datetime
        now = datetime.now()
        
        # Remove calls older than 1 minute
        self.call_timestamps = [
            ts for ts in self.call_timestamps 
            if now - ts < timedelta(minutes=1)
        ]
        
        if len(self.call_timestamps) >= self.calls_per_minute:
            logger.warning("Rate limit approached, using cache only")
            return False
            
        self.call_timestamps.append(now)
        return True
```

## Caching Strategy

### Cache Architecture

The unified cache system provides intelligent data management:

```python
class UnifiedCacheManager:
    def __init__(self, base_dir=".cache"):
        self.market_dir = base_dir / "market_data"
        self.metadata_dir = base_dir / "metadata"
```

### Cache Expiration Logic

Smart expiration based on data recency:

```python
def calculate_expiration(self, start_date: str, end_date: str) -> datetime:
    """
    Historical data (>2 days old): 10 years expiration
    Recent data (≤2 days): 24 hours expiration  
    """
    from src.utils.date_utils import parse_date_string, today_str
    from datetime import datetime, timedelta
    end_dt = parse_date_string(end_date)
    today = datetime.now().date()
    
    if end_dt.date() < today - timedelta(days=2):
        return datetime.now() + timedelta(days=365 * 10)  # 10 years
    else:
        return datetime.now() + timedelta(hours=24)  # 24 hours
```

### Cache Hit Optimization

```python
# Always check cache first
cached_data = cache.get_market_data(symbol, start_date, end_date, "daily_stock")
if cached_data is not None:
    logger.info(f"Cache hit for {symbol}")
    return cached_data

# Only make API call if cache miss
api_data = fetch_from_api(symbol, start_date, end_date)
cache.set_market_data(symbol, start_date, end_date, "daily_stock", api_data)
```

## Fed Data Integration

### FRED API Configuration

```python
from src.data_sources.fed_data_integration import FedDataIntegration

fed = FedDataIntegration()  # Auto-loads FREDAPI key from config
context = fed.get_full_context(pd.Timestamp('2024-01-19'))
```

### Economic Indicators Tracked

- **DFF**: Effective Federal Funds Rate
- **DFEDTARU/DFEDTARL**: Fed Funds Target Rates (Upper/Lower)
- **VIXCLS**: VIX Volatility Index
- **BAMLH0A0HYM2**: High Yield Credit Spreads
- **T10Y2Y**: 10Y-2Y Treasury Yield Curve
- **DEXUSEU**: USD/EUR Exchange Rate

### Fed Data Caching

```bash
.cache/fed_data/
├── fomc_calendar.pkl      # FOMC meeting dates and decisions
├── fed_indicators.pkl     # Daily economic indicators
└── fed_analysis/
    └── reports/           # Generated analysis reports
```

### Market Stress Calculation

```python
stress_metrics = fed.calculate_market_stress(date)
# Returns: VIX regime, yield curve inversion, credit stress, composite score
```

## Data Collection Workflow

### 1. Underlying Stock Data Collection

```python
def collect_underlying_data(symbol: str, start_date: str, end_date: str):
    """Collect daily OHLCV data for underlying asset"""
    
    client = AlphaVantageGEXClient()
    
    # Process date range 
    processed_start, processed_end = get_processed_date_range(start_date, end_date)
    
    # Fetch with caching and rate limiting
    data = client.fetch_underlying_data(symbol, processed_start, processed_end)
    
    # Validate and normalize
    validated_data = validate_ohlcv_data(data)
    normalized_data = normalize_market_data(validated_data)
    
    return normalized_data
```

### 2. Options Chain Data Collection

**Note**: Requires Alpha Vantage Premium subscription

```python
def collect_options_data(symbol: str, expiration_date: str):
    """Collect options chain for specific expiration"""
    
    # This requires premium Alpha Vantage subscription
    options_data = client.fetch_options_chain(symbol, expiration_date)
    
    if options_data.empty:
        logger.warning(f"No options data for {symbol} {expiration_date}")
        # Fallback to alternative data source or historical data
        return get_fallback_options_data(symbol, expiration_date)
    
    return process_options_chain(options_data)
```

## Data Validation

### Quality Checks

```python
class DataValidator:
    def validate_ohlcv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate OHLCV data integrity"""
        
        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing columns: {missing_cols}")
        
        # Validate price relationships
        invalid_ohlc = df[(df['high'] < df['low']) | 
                         (df['high'] < df['open']) | 
                         (df['high'] < df['close']) |
                         (df['low'] > df['open']) | 
                         (df['low'] > df['close'])]
        
        if not invalid_ohlc.empty:
            logger.warning(f"Found {len(invalid_ohlc)} invalid OHLC relationships")
            df = self.fix_ohlc_relationships(df)
        
        return df
    
    def validate_options_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate options chain data"""
        
        # Check for negative values where inappropriate
        if (df['call_volume'] < 0).any() or (df['put_volume'] < 0).any():
            raise ValueError("Negative volume values found")
            
        # Validate strike price ordering
        if not df['strike'].is_monotonic_increasing:
            logger.warning("Strike prices not in ascending order")
            df = df.sort_values('strike')
        
        return df
```

### Data Completeness Monitoring

```python
def generate_data_quality_report(data: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive data quality report"""
    
    return {
        'total_records': len(data),
        'date_range': (data.index.min(), data.index.max()),
        'missing_data_pct': data.isnull().sum().sum() / data.size * 100,
        'duplicate_records': data.duplicated().sum(),
        'outlier_detection': detect_statistical_outliers(data),
        'data_gaps': identify_missing_trading_days(data),
        'quality_score': calculate_quality_score(data)
    }
```

## Data Processing Pipeline

### 1. Raw Data Ingestion

```python
def ingest_raw_data(source: str, symbol: str, date_range: Tuple[str, str]) -> pd.DataFrame:
    """Ingest raw data from specified source"""
    
    if source == 'alpha_vantage':
        return alpha_vantage_ingestion(symbol, date_range)
    elif source == 'cached':
        return cache_ingestion(symbol, date_range)
    else:
        raise ValueError(f"Unknown data source: {source}")
```

### 2. Data Normalization

```python
def normalize_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize market data to standard format"""
    
    # Standardize column names
    df = standardize_column_names(df)
    
    # Handle timezone localization
    df = localize_df(df, get_default_timezone())
    
    # Calculate derived fields
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
    
    # Sort by date (newest first for consistency)
    df = df.sort_index(ascending=False)
    
    return df
```

### 3. Data Enhancement

```python
def enhance_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators and market context"""
    
    from src.utils.indicator_library import TechnicalIndicators
    indicators = TechnicalIndicators()
    
    # Add technical indicators
    df['sma_20'] = indicators.sma(df['close'], 20)
    df['rsi'] = indicators.rsi(df['close'], 14)
    df['vix_proxy'] = calculate_vix_proxy(df)
    
    # Add market context
    df['days_to_opex'] = calculate_days_to_opex(df.index)
    df['days_since_fomc'] = calculate_days_since_fomc(df.index)
    df['earnings_week'] = identify_earnings_weeks(df.index)
    
    return df
```

## Error Handling and Recovery

### Graceful Degradation

```python
def fetch_with_fallback(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch data with graceful fallback options"""
    
    try:
        # Primary: Fresh API data
        return client.fetch_underlying_data(symbol, start_date, end_date)
        
    except RateLimitExceeded:
        logger.warning("Rate limit exceeded, using cached data")
        cached = cache.get_market_data(symbol, start_date, end_date, "daily_stock") 
        if cached is not None:
            return cached
        else:
            raise DataUnavailableError("No cached data available")
            
    except APIError as e:
        logger.error(f"API error: {e}")
        # Fallback to alternative data source
        return fetch_alternative_source(symbol, start_date, end_date)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise DataPipelineError(f"Failed to fetch data for {symbol}")
```

### Retry Logic

```python
def fetch_with_retry(func, max_retries=3, backoff_factor=2):
    """Execute function with exponential backoff retry"""
    
    for attempt in range(max_retries):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = backoff_factor ** attempt
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
            time.sleep(wait_time)
```

## Performance Optimization

### Batch Processing

```python
def batch_collect_data(symbols: List[str], date_ranges: List[Tuple[str, str]]) -> Dict[str, pd.DataFrame]:
    """Collect data for multiple symbols efficiently"""
    
    results = {}
    rate_limiter = RateLimiter()
    
    for symbol in symbols:
        for start_date, end_date in date_ranges:
            # Respect rate limits
            if not rate_limiter.check_rate_limit():
                time.sleep(60)  # Wait for rate limit reset
            
            # Check cache first to avoid unnecessary API calls
            cached = cache.get_market_data(symbol, start_date, end_date, "daily_stock")
            if cached is not None:
                results[f"{symbol}_{start_date}_{end_date}"] = cached
                continue
            
            # Fetch fresh data
            data = client.fetch_underlying_data(symbol, start_date, end_date)
            results[f"{symbol}_{start_date}_{end_date}"] = data
            
    return results
```

### Memory Management

```python
def process_large_datasets(data_chunks: Iterator[pd.DataFrame]) -> pd.DataFrame:
    """Process large datasets in chunks to manage memory"""
    
    processed_chunks = []
    
    for chunk in data_chunks:
        # Process chunk
        normalized_chunk = normalize_market_data(chunk)
        validated_chunk = validate_ohlcv_data(normalized_chunk)
        
        # Store processed chunk
        processed_chunks.append(validated_chunk)
        
        # Clear memory if needed
        if len(processed_chunks) > 10:
            # Combine and save intermediate results
            intermediate_result = pd.concat(processed_chunks)
            save_intermediate_result(intermediate_result)
            processed_chunks = []
    
    # Combine final results
    return pd.concat(processed_chunks) if processed_chunks else pd.DataFrame()
```

## Monitoring and Logging

### Pipeline Metrics

```python
class PipelineMonitor:
    def __init__(self):
        self.metrics = {
            'api_calls_made': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'data_validation_errors': 0,
            'processing_time': []
        }
    
    def log_api_call(self, endpoint: str, response_time: float):
        self.metrics['api_calls_made'] += 1
        self.metrics['processing_time'].append(response_time)
        
    def log_cache_result(self, hit: bool):
        if hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
    
    def generate_report(self) -> Dict[str, Any]:
        return {
            'cache_hit_rate': self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses']),
            'avg_response_time': np.mean(self.metrics['processing_time']),
            'total_api_calls': self.metrics['api_calls_made'],
            'error_rate': self.metrics['data_validation_errors'] / self.metrics['api_calls_made']
        }
```

### Alert System

```python
def check_pipeline_health():
    """Monitor pipeline health and send alerts"""
    
    monitor = PipelineMonitor()
    report = monitor.generate_report()
    
    # Check cache hit rate
    if report['cache_hit_rate'] < 0.8:
        logger.warning(f"Low cache hit rate: {report['cache_hit_rate']:.2%}")
    
    # Check API response times
    if report['avg_response_time'] > 5.0:
        logger.warning(f"High API response time: {report['avg_response_time']:.2f}s")
    
    # Check error rates  
    if report['error_rate'] > 0.1:
        logger.error(f"High error rate: {report['error_rate']:.2%}")
```

## Configuration

### Pipeline Settings

```python
# @config/data_pipeline.json
{
    "alpha_vantage": {
        "rate_limit": 75,
        "timeout": 30,
        "retry_attempts": 3,
        "backoff_factor": 2
    },
    "cache": {
        "base_directory": ".cache",
        "historical_ttl_years": 10,
        "recent_ttl_hours": 24,
        "max_cache_size_gb": 10
    },
    "validation": {
        "strict_mode": true,
        "auto_fix_errors": true,
        "outlier_threshold": 3
    }
}
```

This data pipeline provides the foundation for reliable, efficient data collection that supports the GEX-LLM analysis workflow while respecting API limitations and ensuring data quality.
