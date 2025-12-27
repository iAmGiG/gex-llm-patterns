# GEX-LLM Pattern Analysis: LLM Structural Reasoning in Financial Markets

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Paper 1](https://img.shields.io/badge/Paper%201-Submitted-success.svg)](https://github.com/iAmGiG/gex-llm-patterns/issues/88)
[![Research](https://img.shields.io/badge/Research-PhD%20Project-purple.svg)](docs/papers/research_roadmap.md)

[![Detection Rate](https://img.shields.io/badge/Detection%20Rate-71.5%25%20Unbiased-orange.svg)](docs/presentations/phd_symposium_2025.md)
[![Accuracy](https://img.shields.io/badge/Predictive%20Accuracy-90.9%25-green.svg)](docs/presentations/phd_symposium_2025.md)
[![Documentation](https://img.shields.io/badge/docs-130%2B%20files-informational.svg)](docs/)

[![OpenAI](https://img.shields.io/badge/LLM-OpenAI%20O3--mini-412991.svg)](https://openai.com/)
[![AutoGen](https://img.shields.io/badge/Framework-AutoGen%200.7-00A36C.svg)](https://github.com/microsoft/autogen)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![Alpha Vantage](https://img.shields.io/badge/Data-Alpha%20Vantage%20Premium-0066CC.svg)](https://www.alphavantage.co/)
[![Matplotlib](https://img.shields.io/badge/Viz-Matplotlib-11557c.svg)](https://matplotlib.org/)
[![Graphviz](https://img.shields.io/badge/Diagrams-Graphviz-2C3E50.svg)](https://graphviz.org/)

[![Agent Factory](https://img.shields.io/badge/Pattern-Agent%20Factory-9B59B6.svg)](#architecture)
[![Agent Bus](https://img.shields.io/badge/Pattern-Pub%2FSub%20Bus-E67E22.svg)](#architecture)
[![Tool Registry](https://img.shields.io/badge/Pattern-Tool%20Registry-3498DB.svg)](#architecture)
[![Config System](https://img.shields.io/badge/Config-YAML%20Centralized-2ECC71.svg)](config_defaults/)

---

## Table of Contents

- [Overview](#overview)
- [Key Results](#key-results)
- [Quick Links](#quick-links)
- [Research Roadmap](#research-roadmap)
- [Project Status](#project-status-november-2025)
- [Getting Started](#getting-started)
- [Documentation](#documentation)

---

## Key Results

> **Main Finding**: LLMs can detect structural market constraints without temporal context

| Metric | Unbiased (Conservative) | Biased (Sensitive) |
|--------|------------------------|-------------------|
| **Detection Rate** | 71.5% | 100% |
| **Predictive Accuracy** | 90.9% | 87-98% |
| **Test Coverage** | 242 days (2024) | 181 days (Q1,Q3,Q4) |
| **Obfuscation** | Full (no dates/tickers) | Full (no dates/tickers) |
| **Pattern Types** | 3 validated | 3 validated |

**Significance**: Detection remains stable (71-100%) while profitability varies (+70bps to -1bps), proving LLM detects **structural mechanics**, not profitable anomalies.

---

## Quick Links

| Category | Link | Description |
|----------|------|-------------|
| **Research** | [Research Roadmap](docs/papers/research_roadmap.md) | Multi-paper strategy (Phase 1-3) |
| **Presentation** | [PhD Symposium 2025](docs/presentations/phd_symposium_2025.md) | Complete presentation guide |
| **Fundamentals** | [Concepts Explained](docs/presentations/fundamentals_explained.md) | Non-technical introduction |
| **Implementation** | [Technical Deep Dive](docs/presentations/technical_deep_dive.md) | Code walkthrough |
| **Validation** | [Pattern Taxonomy](reports/validation/pattern_taxonomy/) | Full 2024 test results |
| **Issues** | [GitHub Issues](https://github.com/iAmGiG/gex-llm-patterns/issues) | Active development tracker |

---

## Research Roadmap

```text
Phase 1: Methodology Validation [COMPLETE]
├─ Obfuscation testing framework
├─ 15 pattern library (WHO->WHOM->WHAT)
├─ Full 2024 validation (252 days, 3 patterns)
├─ Symposium presentation delivered
└─ Paper #1 submitted to IEEE LLM-Finance 2025

Phase 2: Temporal Dynamics [IN PROGRESS]
├─ Sequential GEX (5-day lookback)
├─ Constraint trajectory detection
└─ Target: Q1 2026 journal submission

Phase 3: Cross-Asset Generalization [PLANNED]
├─ Individual equities (AAPL, TSLA, NVDA, etc.)
├─ Index vs single-name comparison
└─ Target: Q2 2026 journal submission

Future: Discovery & Applications [CONCEPTUAL]
├─ Pattern discovery (unsupervised)
├─ Comparative LLM analysis
└─ Real-time monitoring systems
```

---

## Overview

**Academic Research**: PhD project investigating whether Large Language Models can detect and reason about structural constraints in financial markets without memorizing training data.

**Core Innovation**: Obfuscation testing framework that validates LLM structural understanding by removing all temporal and contextual information (dates, tickers, events) before analysis.

**Research Question**: Can LLMs identify mechanical patterns driven by dealer hedging constraints (WHO forces WHOM to do WHAT) using only gamma exposure metrics?

**Answer**: **YES** - Validated with two testing approaches:

- **Conservative (Unbiased)**: 71.5% detection rate, 91.2% predictive accuracy across 242 trading days (full 2024, 96% coverage*) using fully obfuscated data with no regime labels
- **Conservative (Unbiased)**: 71.5% detection rate, 90.9% predictive accuracy across 242 trading days (full 2024, 96% coverage*) using fully obfuscated data with no regime labels
- **Sensitive (Biased)**: 100% detection rate, 87-98% predictive accuracy across 181 trading days (Q1+Q3+Q4**) using pattern-specific prompts with regime labels

Both approaches prove LLM detects structural dealer constraints even when temporal context is removed.

*Q2 excluded due to insufficient data coverage (~27% availability) - remaining quarters represent full 2024 validation coverage

## Project Status (November 2025)

### Completed

- **Pattern Library**: 15 comprehensive market mechanics patterns with WHO->WHOM->WHAT framework
- **Validation Framework**: Complete obfuscation testing system for historical validation
- **Data Infrastructure**: Historical GEX database (corrected Oct 2025), options data cache, automated collection
- **LLM Integration**: O3-mini deployment with structured reasoning prompts
- **Obfuscation System**: Date/ticker anonymization with 35x performance optimization
- **Documentation**: 130+ markdown files covering methodology, implementation, and findings
- **Full 2024 Validation**: 252 trading days (100% coverage) tested with unbiased prompts
- **Quarterly Validation**: 181 trading days (Q1, Q3, Q4) tested with pattern-specific prompts
- **Prompt Bias Analysis**: Biased vs unbiased prompt comparison complete
- **Symposium Presentation**: PhD symposium delivered (October 2025)
- **Paper #1 Submitted**: IEEE LLM-Finance 2025 workshop (submitted Oct 26, 2025) - [Workshop](https://intelligentfinance.github.io/IEEE-LLM-finance-2025/index.html) | [Host Conference](https://conferences.cis.um.edu.mo/ieeebigdata2025/)
- **Agent Infrastructure** (November 2025):
  - Agent Factory Pattern - centralized agent creation with YAML config
  - Agent Communication Bus - async pub/sub messaging for multi-agent coordination
  - Tool Registry - AutoGen 0.7 compatible tool management
  - Performance Optimizations - O(1) rate limiting, adaptive thread pools, thread-safe singletons
  - Configuration Extraction - all hardcoded values moved to `config_defaults/`

### In Progress

- **Paper #1 Review**: Awaiting reviews from IEEE LLM-Finance 2025 (4-6 weeks)
- **Individual Equities**: Extending validation to AAPL, TSLA, NVDA, JPM, XOM (Issue #87)
- **Sequential GEX**: 5-day lookback analysis for temporal constraint detection (Issue #89)

### Deferred

- **Multi-Year Validation**: 2023/2025 out-of-sample testing for regime robustness (future work)
- **Advanced Figures**: Causal network diagram, statistical power analysis (journal submission)

See [GitHub Issues](https://github.com/iAmGiG/gex-llm-patterns/issues) for detailed roadmap.

## Research Contributions

### 1. Novel Validation Methodology

**Obfuscation Testing Framework**:

- Remove dates -> "Day T+0", "Day T+1"
- Remove tickers -> "INDEX_1", "STOCK_G"
- Remove events -> No FOMC, earnings, COVID references
- **Result**: Forces LLM to reason from pure mechanics, not memorize training data

**Applications**: Can be applied to any domain requiring validation of LLM structural understanding (medical diagnosis, supply chain, engineering systems).

### 2. Market Microstructure Pattern Detection

**15 Documented Patterns** implementing dealer hedging constraints:

- Gamma Squeeze, Stock Pinning, 0DTE Hedging
- OPEX Pin, Volatility Suppression/Squeeze
- Delta Hedging Cascade, Liquidity Vacuum
- FOMC Positioning, Earnings Straddle
- Quarter-End Rebalancing, Window Dressing
- Dealer Trap, Correlation Breakdown
- Momentum Ignition, Dispersion Trade

Each pattern documented with:

- Setup conditions, mechanics description
- WHO (actor), WHOM (counterparty), WHAT (forced action)
- Historical examples, success metrics
- LLM prompts, identification criteria

### 3. Empirical Evidence for LLM Structural Reasoning

**Key Finding**: Detection does not equal Profitability

| Quarter | Biased Detection | Unbiased Detection | Predictive Accuracy | Net Alpha | Interpretation |
|---------|------------------|--------------------|--------------------|-----------|----------------|
| Q1 2024 | 100% (53 days) | 69.4% | 96.2% | +70 bps | Profitable regime |
| Q2 2024 | 100% (61 days) | *Not tested* | 91.7% | +16 bps | Moderate profitability |
| Q3 2024 | 100% (64 days) | 71.5% | 98.4% | +4 bps | Barely profitable |
| Q4 2024 | 100% (64 days) | 71.5% | 98.4% | -1 bps | Unprofitable |
| **Full 2024** | **100%** (181 days) | **71.5%** (242 days) | **90.9%** | **+22 bps** | **Average across year** |

**Significance**: Proves LLM detects **structural mechanics** (which remain constant at 71-100% depending on prompt) rather than fitting to profitable anomalies (which vary by regime from +70 to -1 bps).

### 4. Pattern Taxonomy

**MECHANICAL vs. NARRATIVE classification**:

- **MECHANICAL**: Pattern exists due to structural constraints (passes obfuscation test >=60% detection)
- **NARRATIVE**: Pattern requires context/memorization (fails obfuscation test <60% detection)

**Validated**: All three tested patterns (gamma positioning, stock pinning, 0DTE hedging) achieved 100% detection -> MECHANICAL classification.

## Architecture

```bash
gex-llm-patterns/
├── src/
│   ├── agents/                    # LLM market mechanics agent (single-agent design)
│   │   └── market_mechanics_agent.py    # Core reasoning engine
│   ├── analysis/                  # Pattern library & validation
│   │   ├── pattern_library.py            # 15 documented patterns
│   │   ├── baseline_comparison.py        # Statistical baselines
│   │   └── outcome_calculator.py         # Objective outcome verification
│   ├── gex/                       # Gamma exposure calculations
│   │   ├── gex_calculator.py             # Black-Scholes GEX engine
│   │   └── enhanced_pattern_detector.py  # Pattern matching
│   ├── llm/                       # LLM integration
│   │   ├── autogen_market_mechanics.py   # O3-mini interface
│   │   └── mechanics_prompt_builder.py   # Structured prompts
│   ├── validation/                # Obfuscation & testing
│   │   ├── data_obfuscation.py           # Date/ticker anonymization
│   │   ├── pattern_taxonomy.py           # MECHANICAL/NARRATIVE classification
│   │   └── outcome_calculator.py         # Forward return verification
│   ├── data_sources/              # Data collection
│   │   ├── historical_gex_builder.py     # SQLite database builder
│   │   ├── alpha_vantage_gex.py          # Options API client
│   │   └── polygon_client.py             # Stock data client
│   └── utils/                     # Core utilities
│       ├── date_utils.py                 # Obfuscated date handling
│       ├── config_manager.py             # Configuration system
│       └── reports_manager.py            # YAML report generation
├── scripts/
│   ├── validation/                # Validation pipeline (26 scripts)
│   │   ├── paper1/                       # Paper #1 validation (17 scripts, 01-17)
│   │   ├── paper2/                       # Paper #2 validation (7 scripts, 01-07)
│   │   └── shared/                       # Cross-paper utilities
│   ├── database/                  # Database management
│   │   └── rebuild_gex_database.py       # Historical GEX builder
│   ├── experiments/               # Experiment orchestration
│   │   └── checkpoint_manager.py         # Resumable backtesting
│   └── analysis/                  # Analysis tools
│       └── gamma_pinning_validator.py    # Pattern-specific validation
├── docs/
│   ├── presentations/             # PhD symposium, papers
│   │   ├── phd_symposium_2025.md         # Full presentation guide
│   │   ├── fundamentals_explained.md     # Non-technical explanation
│   │   └── technical_deep_dive.md        # Implementation details
│   ├── system/                    # System documentation
│   │   └── SYSTEM_FLOW_SIMPLE.md         # Methodology flowcharts
│   └── guides/                    # Implementation guides
│       └── validation-framework.md       # Validation usage guide
└── config_defaults/               # Configuration templates
    ├── analysis_config.yaml              # Pattern thresholds
    └── pattern_library_config.yaml       # Pattern-specific settings
```

## Key Modules

### Pattern Detection Pipeline

```python
# Example: Single-day pattern detection with obfuscation
from src.agents.market_mechanics_agent import MarketMechanicsAgent
from src.validation.data_obfuscation import DataObfuscator

# Initialize agent
agent = MarketMechanicsAgent()
obfuscator = DataObfuscator()

# Fetch and obfuscate data
gex_data = agent.fetch_gex_data(symbol="SPY", date="2024-01-05")
obfuscated_data = obfuscator.obfuscate(gex_data)
# Result: date="Day T+0", symbol="INDEX_1"

# LLM analysis (no temporal context)
detection = agent.detect_pattern(obfuscated_data)
# Returns: {
#   'pattern': 'gamma_positioning',
#   'who': 'Dealers with negative gamma',
#   'whom': 'Market participants',
#   'what': 'Force dealers to amplify volatility',
#   'confidence': 0.85
# }

# Verify outcome (forward returns)
outcome = calculate_outcome(date="2024-01-05", horizon=1)
# Returns: {
#   'forward_1d_return_pct': 0.49,
#   'prediction_materialized': True
# }
```

### Full Validation Run

```bash
# Validate pattern across full quarter with obfuscation
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --with-outcomes

# Output: reports/validation/pattern_taxonomy/gamma_positioning_SPY_2024Q1.yaml
# Contains:
# - Test metadata (dates, coverage, thresholds)
# - Performance metrics (detection rate, accuracy, alpha)
# - Obfuscation test verdict (MECHANICAL/NARRATIVE)
# - All daily detection results with outcomes
```

## Getting Started

### Prerequisites

- Python 3.10+
- OpenAI API key (for O3-mini LLM)
- Polygon.io API key (for options/stock data)
- HPCC access (for full historical validation) OR local development

### Installation

```bash
# Clone repository
git clone https://github.com/iAmGiG/gex-llm-patterns.git
cd gex-llm-patterns

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp config_defaults/config.json config/config.json
# Edit config/config.json with your API keys:
# {
#   "OPEN_AI_KEY": "your_openai_key",
#   "POLYGON_IO": "your_polygon_key"
# }

# Verify setup
python -c "from src.analysis.pattern_library import PatternLibrary; print('Setup OK')"
```

### Quick Start: Pattern Library

```python
from src.analysis.pattern_library import PatternLibrary

# Load pattern library
library = PatternLibrary()

# List all patterns
for name, pattern in library.patterns.items():
    print(f"{name}: {pattern.success_metrics.success_rate:.0%} success rate")

# Get specific pattern
gamma_squeeze = library.get_pattern('gamma_squeeze')
print(gamma_squeeze.mechanics_description)
# Output: "Call buying forces dealers to buy shares as price rises,
#          creating positive feedback loop"

# Generate LLM prompt for pattern
prompt = library.generate_llm_prompt(
    pattern_name='gamma_squeeze',
    prompt_type='identification',
    context_data={'net_gex': -8.5, 'strikes': '565-570'}
)
```

### Quick Start: Pattern Validation

```bash
# Test single pattern (local development)
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --date 2024-01-05

# Full quarter validation (requires HPCC or extensive local cache)
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --with-outcomes

# Batch validation across multiple patterns
python scripts/validation/paper1/03_validate_all_patterns.py \
  --patterns gamma_positioning stock_pinning 0dte_hedging \
  --start-date 2024-01-02 \
  --end-date 2024-03-29
```

## Documentation

Comprehensive documentation available in `docs/`:

### Research & Presentations

- **[PhD Symposium 2025](docs/presentations/phd_symposium_2025.md)**: Complete presentation with methodology, results, Q&A
- **[Fundamentals Explained](docs/presentations/fundamentals_explained.md)**: Non-technical introduction to concepts
- **[Technical Deep Dive](docs/presentations/technical_deep_dive.md)**: Implementation details and code walkthrough

### System Documentation

- **[System Flow Guide](docs/SYSTEM_FLOW_SIMPLE.md)**: Visual methodology flowcharts
- **[Validation Framework](docs/guides/validation-framework.md)**: How to run pattern validations
- **[Pattern Library Guide](docs/guides/pattern-library-guide.md)**: Using the 15-pattern library

## Research Papers (In Progress)

### Paper #1: Workshop Submission (Due Oct 26, 2025)

**Title**: "Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing"

**Venue**: [IEEE LLM-Finance 2025](https://intelligentfinance.github.io/IEEE-LLM-finance-2025/call.html) (workshop at [IEEE BigData 2025](https://conferences.cis.um.edu.mo/ieeebigdata2025/), Macau)

**Contribution**: Novel obfuscation testing framework for validating LLM structural reasoning

**Status**: Draft complete (10 pages, IEEE format), under advisor review ([Issue #88](https://github.com/iAmGiG/gex-llm-patterns/issues/88))

**Key Results**: 71.5% unbiased detection rate and 90.9% predictive accuracy across 242 trading days (full 2024)

### Paper #2: Sequential GEX Analysis

**Title**: TBD - Temporal dynamics of dealer constraints

**Contribution**: 5-day lookback analysis shows LLM reasoning about constraint trajectories (accumulation, relief, reversal, persistence)

**Status**: Methodology design ([Issue #89](https://github.com/iAmGiG/gex-llm-patterns/issues/89))

### Paper #3: Cross-Asset Generalization

**Title**: TBD - Individual equity pattern detection

**Contribution**: Extending validation to individual equities (AAPL, TSLA, NVDA, JPM, XOM) to demonstrate cross-asset generalization

**Status**: Planned (Q2 2026)

---

**Detailed Roadmap**: See [`docs/papers/research_roadmap.md`](docs/papers/research_roadmap.md) for complete multi-paper plan, timelines, and future work (Papers #4+)

## Current Research Focus

### Active GitHub Issues

- **[Issue #88](https://github.com/iAmGiG/gex-llm-patterns/issues/88)**: Paper #1 submission (draft under advisor review, Oct 26 deadline)
- **[Issue #87](https://github.com/iAmGiG/gex-llm-patterns/issues/87)**: Individual equities extension (AAPL, TSLA, NVDA, JPM, XOM)
- **[Issue #89](https://github.com/iAmGiG/gex-llm-patterns/issues/89)**: Sequential GEX analysis (5-day lookback for temporal dynamics)

### Recently Closed

- **[Issue #96](https://github.com/iAmGiG/gex-llm-patterns/issues/96)**: DataObfuscator optimization (35x performance improvement)
- **[Issue #97](https://github.com/iAmGiG/gex-llm-patterns/issues/97)**: Performance benchmarks documentation
- **[Issue #91-93](https://github.com/iAmGiG/gex-llm-patterns/issues/)**: All 8 must-have paper figures complete
- **[Issue #79](https://github.com/iAmGiG/gex-llm-patterns/issues/79)**: Pattern taxonomy validation (full 2024 complete)
- **[Issue #80](https://github.com/iAmGiG/gex-llm-patterns/issues/80)**: Outcome calculator integration
- **[Issue #81](https://github.com/iAmGiG/gex-llm-patterns/issues/81)**: Obfuscation bug fix

### Key Findings

1. **LLMs can detect structural constraints** - 71.5% detection rate (unbiased) to 100% (biased) with obfuscated data across 242 days, proving detection without temporal memorization
2. **Detection does not equal Profitability** - Detection remains stable (71-100%) while economic outcomes vary (+70bps to -1bps), proving LLM detects structural mechanics not profitable anomalies
3. **Obfuscation testing works** - All tested patterns passed >=60% threshold for MECHANICAL classification, even with fully unbiased prompts (no regime labels)
4. **Cross-pattern generalization** - Same methodology detects gamma positioning (69.4%), stock pinning (67.4%), and 0DTE hedging (77.7%) - three manifestations of dealer constraints
5. **Prompt bias quantified** - Adding regime labels increases detection from 71.5% to 100% (+28.5%), but accuracy remains stable (91-92%), demonstrating robust pattern materialization

## Contributing

This is an active PhD research project. Contributions welcome in:

- **Pattern Discovery**: Identifying new dealer hedging patterns
- **Validation Testing**: Running validations on different time periods/symbols
- **LLM Experimentation**: Testing different models (GPT-4o-mini, GPT-o3-mini, etc.)
- **Cross-Domain Application**: Applying obfuscation testing to other domains
- **Documentation**: Improving guides and examples

Please open an issue before starting major work.

## Research Ethics & Disclaimers

- **Academic Research**: All results for academic publication, not trading advice
- **No Market Manipulation**: Uses publicly available data only
- **Transparency**: Methodology and code are open source
- **Risk Disclaimer**: Past performance (detection rates, accuracy) does not guarantee future results
- **Not Financial Advice**: This research demonstrates LLM capabilities, not profitable trading strategies

## License

This project is licensed under the GNU Affero General Public License v3.0 - see [LICENSE](LICENSE) for details.

**Future License Consideration**: AGPL v3 ensures open source compliance but may restrict commercial applications. Consider transitioning to MIT or dual licensing for academic/commercial flexibility.

## Citation

If you use this methodology or code in your research, please cite:

```bibtex
@misc{gex-llm-patterns-2025,
  author = {Chris Regan},
  title = {Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/iAmGiG/gex-llm-patterns}
}
```

## Contact

**Researcher**: PhD Candidate, Computer Science
**Project**: LLM Structural Reasoning in Market Microstructure
**Code**: <https://github.com/iAmGiG/gex-llm-patterns>
**Issues**: <https://github.com/iAmGiG/gex-llm-patterns/issues>

---

**Last Updated**: November 2025
**Project Status**: Full 2024 validation complete (242 days), Paper #1 submitted, agent infrastructure deployed
**Next Milestone**: Paper #1 reviews, Paper #2 sequential GEX analysis, individual equities extension

*This research explores the intersection of large language models, market microstructure, and validation methodology for testing AI structural reasoning capabilities.*
