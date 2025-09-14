# Scripts Directory

This directory contains all executable scripts for the GEX-LLM Patterns project, organized by purpose.

## Directory Structure

### `analysis/`
Scripts for data analysis and exploration
- `explain_options_data.py` - Analyzes and explains options data structure

### `data_collection/`
Scripts for gathering and managing data
- `start_historical_collection.py` - Starts historical data collection
- `automation/` - 24/7 automated collection system
  - `automated_data_collector.py` - Main collection service
  - `monitor_collection.py` - Progress monitoring
  - `test_spx_access.py` - API access validation
  - `test_polygon_collection.py` - Stock data testing

### `testing/`
Scripts for system validation and testing
- `test_cache_integration.py` - Cache system validation

## Usage

All scripts should be run from the project root directory:

```bash
# Analysis
python scripts/analysis/explain_options_data.py

# Data Collection
python scripts/data_collection/start_historical_collection.py
python scripts/data_collection/automation/automated_data_collector.py

# Testing
python scripts/testing/test_cache_integration.py
```

## Organization Principles

- **No scripts at root level** - All scripts must be in appropriate subfolders
- **Logical grouping** - Scripts grouped by primary purpose
- **Clear naming** - Descriptive filenames indicating functionality
- **Documentation** - Each subfolder should have clear purpose