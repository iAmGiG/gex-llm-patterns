# GEX-LLM Pattern Analysis

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Overview

This research project uses Large Language Models to identify exploitable patterns in daily Gamma Exposure (GEX) calculations combined with price action, detecting when dealer hedging constraints create predictable market movements.

The experiment feeds tokenized sequences of options-derived metrics (GEX levels, gamma flip points, volatility skew) and price data from Alpha Vantage's historical options API into GPT-4o-mini/GPT-4o via Microsoft's Autogen framework to discover multi-timeframe patterns that traditional single-indicator models miss.

## Research Hypothesis

**Can LLMs identify patterns in dealer hedging constraints through GEX analysis that provide exploitable trading opportunities?**

We hypothesize that:

1. **Dealer gamma hedging** creates predictable market movements during certain conditions
2. **Multi-timeframe GEX patterns** contain information not captured by traditional indicators  
3. **LLMs can discover** these patterns through sequence analysis of tokenized market states
4. **Discovered patterns** will show statistical significance and out-of-sample performance

## Data Scope

- **Historical Period**: 2008-present (15+ years of options data via automated collection)
- **Instruments**: SPY, QQQ, IWM, DIA, TLT, GLD options chains + underlying price data
- **Data Sources**: Alpha Vantage Premium (options) + Polygon.io (stocks) + FRED (Fed data)
- **Collection Rate**: 75/min (options), 7,200/day (stocks), daily (Fed indicators)
- **Current Status**: LLM-driven agent autonomy operational with YAML reporting and data obfuscation
- **Key Metrics**: Enhanced GEX (3 metrics), gamma flip points, dealer hedging mechanics, WHO/WHOM/WHAT analysis
- **Market Events**: FOMC meetings, OpEx, earnings, major volatility events with context weighting

## Architecture

```bash
src/
├── data_sources/          # API clients (Alpha Vantage + Polygon.io + Fed/FOMC)
│   ├── alpha_vantage_gex.py      # Premium options API client
│   ├── polygon_client.py         # Stock data integration  
│   ├── fed_data_integration.py   # FOMC/Fed economic context
│   └── historical_gex_builder.py # Production database builder
├── scripts/
│   ├── data_collection/   # 24/7 automated collection system
│   │   └── automation/    # Persistent collection services  
│   ├── analysis/          # Data analysis and exploration
│   └── testing/           # System validation and QA
├── cache/                 # Unified caching system (auto-expanding)
├── gex/                   # GEX calculation engine (Black-Scholes, flip points)
├── agents/               # AutoGen 0.7.4 multi-agent framework
├── utils/                # Consolidated datetime utilities (20+ files)
├── tokenization/         # Dynamic tokenizer for LLM sequence generation
└── validation/          # Data obfuscation for unbiased LLM testing
```

## Development Phases

### Phase 1: Data Infrastructure ✅

- **Status**: Complete - 24/7 automated collection system operational
- **Achievement**: 87,000+ options contracts, persistent collection, API rate management
- **Data Sources**: Alpha Vantage (options) + Polygon.io (stocks) + Fed/FOMC data fully integrated
- **New**: Fed economic context integration with FOMC calendar and market stress indicators

### Phase 2: GEX Calculation Engine ✅  

- **Status**: Complete - Full Greeks calculations with advanced derivatives
- **Achievement**: Black-Scholes engine, flip point detection, comprehensive validation
- **Features**: Second/third-order Greeks, GEX caching, auto-calculation pipeline
- **New**: Historical GEX database builder with production-grade features (concurrency, resume, validation)

### Phase 3: Agent Framework ✅

- **Status**: Complete - AutoGen 0.7.4 multi-agent system operational  
- **Achievement**: Agent communication, tool integration, workflow automation
- **Capabilities**: Data retrieval, GEX calculation, pattern analysis agents
- **New**: Consolidated datetime utilities across 20+ files for consistent time handling

### Phase 4: Pattern Mining & LLM Integration ⏳

- **Status**: Ready for implementation with real data
- **Next**: Sequential pattern mining, GPT-4o analysis of collected data
- **Goal**: Discovered patterns with mechanical explanations

### Phase 5: Validation & Analysis ⏳

- **Status**: Framework prepared, awaiting pattern discovery
- **Goal**: Statistically significant, out-of-sample validated results

## Getting Started

### Prerequisites

- Python 3.10+
- Alpha Vantage API key (free tier: 25 calls/day, or premium: 75 calls/min)
- Polygon.io API key (free tier: 7,200 calls/day)
- OpenAI API key for GPT-4o-mini/GPT-4o (for pattern analysis)
- Linux/Unix environment for persistent collection sessions

### Installation

```bash
# Clone the repository
git clone https://github.com/iAmGiG/gex-llm-patterns.git
cd gex-llm-patterns

# Set up configuration (add API keys to config/config.json)
# {
#   "ALPHA_VANTAGE_KEY": "your_alpha_vantage_key",
#   "POLYGON_IO": "your_polygon_key", 
#   "OPEN_AI_KEY": "your_openai_key"
# }

# Install dependencies
pip install requests pandas asyncio

# Verify setup
python -c "from src.cache.unified_cache import UnifiedCacheManager; print('Setup OK')"
```

### Quick Start

#### 1. Start Automated Data Collection
```bash
# Start persistent collection (runs 24/7)
python scripts/data_collection/automation/automated_data_collector.py

# Monitor progress  
python scripts/data_collection/automation/monitor_collection.py
```

#### 2. Analyze Collected Data
```python
from src.cache.unified_cache import UnifiedCacheManager

cache = UnifiedCacheManager()
summary = cache.get_options_cache_summary()

print(f"Options data: {summary['total_contracts']:,} contracts")
print(f"Symbols: {list(summary['tickers'].keys())}")
```

#### 3. Explore Options Data Structure  
```bash
python scripts/analysis/explain_options_data.py
```

## Current Status

- ✅ **Data Infrastructure**: 24/7 automated collection system operational  
- ✅ **Real Data**: 87,000+ live options contracts cached and growing
- ✅ **API Integration**: Alpha Vantage + Polygon.io + Fed/FOMC data fully integrated
- ✅ **GEX Engine**: Complete Black-Scholes implementation with advanced Greeks
- ✅ **Agent Framework**: AutoGen 0.7.4 multi-agent system ready
- ✅ **Fed Integration**: FOMC calendar, economic indicators, market stress analysis
- ✅ **Historical Database**: Production-ready GEX database builder with enterprise features
- ✅ **Code Quality**: Consolidated datetime utilities, comprehensive code review applied
- ✅ **Organized Codebase**: Clean scripts structure, comprehensive testing
- ⏳ **Pattern Discovery**: Ready for LLM analysis of collected data with Fed context
- ⏳ **Research Phase**: Statistical validation and backtesting framework

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[Project Overview](docs/architecture/project_overview.md)**: Complete research vision, current status, and development roadmap
- **[Implementation Status](docs/technical/implementation_status.md)**: Technical guide showing what's built and what's next
- **[Architecture Overview](docs/architecture/architecture_overview.md)**: System design and component interactions
- **[Agent Framework](docs/agents/agent_framework.md)**: Autogen multi-agent setup and workflows  
- **[Data Pipeline](docs/technical/data_pipeline.md)**: Alpha Vantage integration, caching, and processing
- **[GEX Calculations](docs/technical/gex_calculations.md)**: Mathematical GEX framework
- **[Fed Integration Summary](docs/technical/fed_integration_summary.md)**: FOMC/Fed data integration system
- **[Historical GEX Database](docs/technical/historical_gex_database_implementation.md)**: Production database builder
- **[Tools and Utils](docs/technical/tools_and_utils.md)**: Consolidated utilities and datetime handling
- **[Research Methodology](docs/research/research_methodology.md)**: Statistical validation and testing approach
- **[Documentation Guidelines](docs/README.md)**: How to organize and format project documentation

## Contributing

This is an academic research project. Contributions are welcome, particularly:

- **Data Quality**: Improving options data validation and cleaning
- **GEX Calculations**: Enhancing gamma exposure calculation accuracy
- **Pattern Mining**: Advanced sequential pattern algorithms
- **Statistical Validation**: Robust testing frameworks
- **Documentation**: Research methodology and findings

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

**Note**: The current AGPL v3 license ensures open source compliance but may be restrictive for future commercial applications. Consider transitioning to a more flexible license (MIT, Apache 2.0, or dual licensing) to maintain control over future academic and commercial opportunities.

## Research Ethics

- **No Market Manipulation**: All research is for academic purposes
- **Data Privacy**: Uses publicly available market data only  
- **Transparency**: All methodology and code are open source
- **Risk Disclaimer**: Past performance does not guarantee future results

## Contact

For questions about this research, please open an issue on GitHub or refer to the project documentation in `@docs/`.

---

*This research explores the intersection of market microstructure, gamma exposure calculations, and modern AI techniques for pattern discovery in financial markets.*
