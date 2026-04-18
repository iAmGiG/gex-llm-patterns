# GEX-LLM Pattern Analysis Source Code

This directory contains the core modules for the GEX-LLM pattern analysis project, which uses Large Language Models to identify exploitable patterns in daily Gamma Exposure (GEX) calculations combined with price action.

## Project Structure

```
src/
├── agents/                # Market mechanics agent, data retrieval agent
├── analysis/              # Pattern analysis and baseline comparison tools
├── backtesting/           # Strategy backtesting utilities
├── cache/                 # Unified caching system for API data
├── data/                  # Market data system
├── data_sources/          # Alpha Vantage API client for options/stock data
├── gex/                   # GEX calculation modules
├── llm/                   # LLM integration (AutoGen, mechanics prompt builder)
├── tools/                 # AutoGen tool registry and data-fetch tools
├── utils/                 # General utilities (date, config, market intelligence)
└── validation/            # Data obfuscation, regime classifier, chain validator
```

## Core Modules

### `analysis/`

Pattern analysis and baseline comparison tools for validating LLM performance:

- **baseline_gex_strategy.py** - Mechanical baseline strategy (no LLM intelligence)
- **baseline_comparison.py** - Compare LLM vs baseline performance (uses validation YAMLs)
- **technical_indicator_baseline.py** - Traditional indicator baseline (MACD + RSI)
- **statistical_validator.py** - Statistical significance testing framework
- **pattern_library.py** - 15 WHO/WHOM/WHAT pattern definitions (Issue #54)
- **confidence_scorer.py** - Multi-factor confidence scoring system
- **actionable_patterns.py** - Convert patterns to trading signals
- **validated_trading_engine.py** - Production trading engine with risk management
- **deprecated/** - Database-dependent files (see Issue #82)

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
