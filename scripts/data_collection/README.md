# Data Collection Scripts

Scripts for gathering, managing, and processing market data.

## Scripts

### `start_historical_collection.py`

- **Purpose**: Starts historical options data collection process
- **Usage**: `python scripts/data_collection/start_historical_collection.py`
- **Features**: Command-line interface for collection parameters
- **Dependencies**: Alpha Vantage API key, cache system

### `automation/` Directory

Complete 24/7 automated data collection system:

- `automated_data_collector.py` - Main persistent collection service
- `monitor_collection.py` - Real-time progress monitoring
- `test_spx_access.py` - API access validation
- `test_polygon_collection.py` - Stock data integration testing

## Data Sources

### Alpha Vantage (Options)

- **Rate Limit**: 25 calls per day (free tier)
- **Coverage**: Historical options chains back to 2008
- **Data**: Full Greeks, bid/ask, open interest, volume

### Polygon.io (Stocks)

- **Rate Limit**: 7,200 calls per day (free tier)
- **Coverage**: Daily OHLCV data for all US stocks
- **Data**: Open, High, Low, Close, Volume

## Collection Strategy

1. **Priority**: SPY → QQQ → IWM → Major ETFs → Individual stocks
2. **Caching**: Intelligent caching prevents duplicate API calls
3. **Resume**: Collection resumes from interruptions
4. **Monitoring**: Real-time progress tracking and status checks
