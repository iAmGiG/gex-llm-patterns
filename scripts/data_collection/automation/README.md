# Automated Data Collection System

This directory contains the automated data collection infrastructure for the GEX-LLM Patterns project.

## Components

### Core Collection System
- `automated_data_collector.py` - Main 24/7 collection service
- `monitor_collection.py` - Real-time progress monitoring
- `test_spx_access.py` - API access validation
- `test_polygon_collection.py` - Stock data integration testing

## Usage

### Start Collection System
```bash
# From project root
python scripts/data_collection/automation/automated_data_collector.py
```

### Monitor Progress
```bash
python scripts/data_collection/automation/monitor_collection.py
```

### Test API Access
```bash
python scripts/data_collection/automation/test_spx_access.py
python scripts/data_collection/automation/test_polygon_collection.py
```

## System Features

- **Persistent Sessions**: Survives disconnection using screen/tmux
- **Rate Limiting**: Respects API limits (Alpha Vantage: 25/day, Polygon: 7,200/day)
- **Smart Prioritization**: SPY → Major ETFs → Individual stocks
- **Resume Capability**: Continues from interruptions
- **Auto-GEX Calculation**: Processes data as it arrives

## Data Collection Timeline

- **Options**: ~152 days for 15-year complete dataset
- **Stocks**: Days to weeks for comprehensive coverage
- **Current Rate**: 25 trading days per calendar day (options)

## Dependencies

- Alpha Vantage API key (configured in config/config.json)
- Polygon.io API key (configured in config/config.json)
- Python packages: requests, pandas, asyncio

## Monitoring

The system creates progress files and logs in the `.cache` directory:
- `automated_collection_progress.json` - Collection state
- `automated_collection.log` - Activity logs