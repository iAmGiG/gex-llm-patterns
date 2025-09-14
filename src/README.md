# GEX-LLM Pattern Analysis Source Code

This directory contains the core modules for the GEX-LLM pattern analysis project, which uses Large Language Models to identify exploitable patterns in daily Gamma Exposure (GEX) calculations combined with price action.

## Project Structure

```
src/
├── cache/                  # Unified caching system for API data
├── data_sources/          # Alpha Vantage API client for options/stock data
├── gex/                   # GEX calculation modules (to be implemented)
├── tokenization/          # LLM sequence generation (to be implemented)
├── utils/                 # General utilities (date, agent operations)
└── validation/           # Data obfuscation and validation tools
```

## Core Modules

### `cache/`
Unified caching system optimized for financial data:
- **UnifiedCacheManager** - Consistent caching interface for all data sources
- Smart expiration: 10 years for historical data, 24 hours for recent data
- Critical for Alpha Vantage free tier rate limits (75 calls/min)

### `data_sources/alpha_vantage_gex.py`
Alpha Vantage API client specialized for GEX calculations:
- **AlphaVantageGEXClient** - Rate-limited client for SPY/SPX data
- Options chain retrieval (requires premium tier)
- Underlying stock data with intelligent caching
- Uses `@config/` loader for API key management

### `utils/`
General utilities adapted from previous project:
- **agent_utils.py** - Autogen agent configuration and operations
- **date_utils.py** - Timezone-aware date processing for market data

### `validation/`
Tools for LLM research integrity:
- **data_obfuscation.py** - Remove temporal/ticker references to prevent training data leakage
- **date_sanitizer.py** - Sanitize dates for unbiased backtesting
- **obfuscation_validator.py** - Validate obfuscation effectiveness

## Removed Components
The following were removed from the original RH2MAS project as not relevant to GEX analysis:
- News data sources and Google Search tools
- Sentiment analysis modules
- VXX volatility tools
- Polygon.io integration (focusing on Alpha Vantage)

## Usage

```python
# Initialize Alpha Vantage client with caching
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.cache import UnifiedCacheManager

cache = UnifiedCacheManager()
client = AlphaVantageGEXClient(cache_manager=cache)

# Fetch underlying data for GEX calculations
spy_data = client.fetch_underlying_data("SPY", "2020-01-01", "2024-12-31")

# Data validation and obfuscation for LLM testing
from src.validation.data_obfuscation import DataObfuscator
obfuscator = DataObfuscator()
clean_data = obfuscator.obfuscate_dataframe(spy_data)
```

## Research Context
This codebase supports research into whether LLMs can identify patterns in dealer hedging constraints through GEX analysis, feeding tokenized sequences of options-derived metrics into GPT-4o-mini/GPT-4o via Microsoft's Autogen framework.
