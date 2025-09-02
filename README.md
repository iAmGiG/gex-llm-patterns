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

- **Historical Period**: 2020-2024 (4+ years of options data)
- **Instruments**: SPY/SPX options chains and underlying price data
- **Data Source**: Alpha Vantage Historical Options API
- **Key Metrics**: Daily GEX calculations, gamma flip points, volatility skew
- **Market Events**: FOMC meetings, OpEx, earnings, major volatility events

## Architecture

```bash
src/
├── cache/                  # Unified caching system (10yr historical, 24hr recent)
├── data_sources/          # Alpha Vantage client (entry premium: 75 calls/min)
├── gex/                   # GEX calculation engine (Black-Scholes, flip points)
├── tokenization/          # Dynamic tokenizer for LLM sequence generation
├── utils/                 # Agent utilities, indicators, Autogen examples
└── validation/           # Data obfuscation for unbiased LLM testing
```

## Development Phases

### Phase 1: Data Infrastructure ⏳

- **Issues #1-3**: Alpha Vantage integration, caching, data pipeline
- **Goal**: Reliable SPY/SPX options chain collection with rate limiting

### Phase 2: GEX Calculation Engine ⏳  

- **Issues #4**: Gamma exposure calculations, flip point detection
- **Goal**: Daily GEX metrics and key market levels

### Phase 3: Tokenization System ⏳

- **Issues #5**: Dynamic tokenization of market states for LLM input
- **Goal**: Optimized sequences for GPT-4o-mini/GPT-4o analysis

### Phase 4: Pattern Mining & LLM Integration ⏳

- **Issues #6-7**: Sequential pattern mining, Autogen multi-agent analysis
- **Goal**: Discovered patterns with mechanical explanations

### Phase 5: Validation & Analysis ⏳

- **Issues #8-9, #11**: Backtesting, statistical validation, research documentation
- **Goal**: Statistically significant, out-of-sample validated results

## Getting Started

### Prerequisites

- Python 3.10+
- Alpha Vantage API key (entry premium tier recommended - 75 calls/min)
- OpenAI API key for GPT-4o-mini/GPT-4o
- Conda environment with Autogen dependencies

### Installation

```bash
# Clone the repository
git clone https://github.com/iAmGiG/gex-llm-patterns.git
cd gex-llm-patterns

# Set up configuration (uses @config/ loader, excluded from repo)
# Add your API keys to the @config/ system

# Install dependencies
pip install -r requirements.txt  # To be created

# Verify setup
python -c "from src.cache import UnifiedCacheManager; print('Setup OK')"
```

### Quick Start

```python
# Initialize Alpha Vantage client with caching
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.cache import UnifiedCacheManager

cache = UnifiedCacheManager()
client = AlphaVantageGEXClient(cache_manager=cache)

# Fetch underlying data for GEX calculations
spy_data = client.fetch_underlying_data("SPY", "2020-01-01", "2024-12-31")
print(f"Retrieved {len(spy_data)} days of SPY data")
```

## Project Status

- ✅ **Codebase Foundation**: Clean architecture with caching and data obfuscation
- ✅ **Issue Planning**: 11 detailed issues with technical specifications  
- ✅ **GitHub Integration**: Project board, labels, automated tracking
- ⏳ **Data Pipeline**: Alpha Vantage client implementation
- ⏳ **GEX Engine**: Gamma calculation and flip point detection
- ⏳ **Pattern Mining**: LLM integration via Autogen framework

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[Project Overview](docs/architecture/project_overview.md)**: Complete research vision, current status, and development roadmap
- **[Implementation Status](docs/technical/implementation_status.md)**: Technical guide showing what's built and what's next
- **[Architecture Overview](docs/architecture/architecture_overview.md)**: System design and component interactions
- **[Agent Framework](docs/agents/agent_framework.md)**: Autogen multi-agent setup and workflows  
- **[Data Pipeline](docs/technical/data_pipeline.md)**: Alpha Vantage integration, caching, and processing
- **[GEX Calculations](docs/technical/gex_calculations.md)**: Mathematical GEX framework
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
