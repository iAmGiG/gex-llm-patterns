# GEX-LLM Patterns Documentation

## 🚀 **PhD Research Platform**

**Latest Status**: CS PhD dissertation research platform investigating whether LLMs can identify actionable patterns in market microstructure better than mechanical approaches. Uses O3-mini for reasoning with data obfuscation validation framework.

## 📋 **Quick Start Guide**

### For New Users

1. **Overview**: Start with [system/architecture/project_overview](system/architecture/project_overview)
2. **Agent System**: Read [CLAUDE.md](../CLAUDE) for current system status
3. **Run Experiment**: Use `scripts/orchestrate_experiment.py --experiment "analyze gamma exposure patterns" --symbol SPY --date 2024-06-28`
4. **View Results**: Check `reports/experiments/SPY-2024-06-28-gamma_analysis.yaml`

### For Developers

1. **Testing**: Read [guides/validation-framework](guides/validation-framework)
2. **Architecture**: Review [system/architecture/architecture_overview](system/architecture/architecture_overview)
3. **Validation**: Run `scripts/validation/production_cache_test.py --date 2024-06-28`

### For Researchers

1. **Latest Findings**: Check [reference/model-selection-research](reference/model-selection-research)
2. **Pattern Results**: See gamma pinning 75% success rate validation
3. **Strike Analysis**: 251 daily opportunities vs 1 aggregated signal

## 📖 **Documentation Structure**

### 🏗️ **System Documentation** (`system/`)

Core architecture and operational guides:

- **`architecture/`** - Complete system architecture
  - [project_overview](system/architecture/project_overview) - High-level system overview
  - [architecture_overview](system/architecture/architecture_overview) - Technical architecture
  - [data_architecture](system/architecture/data_architecture) - Data flow and storage
  - [database_architecture](system/architecture/database_architecture) - Database schema
  - [cache_architecture](system/architecture/cache_architecture) - Cache system design
  - [continuous_experiment_framework](system/architecture/continuous_experiment_framework) - Experimental framework
  - [intraday_implementation_complete](system/architecture/intraday_implementation_complete) - Intraday system
- **`implementation/`** - Technical implementation details
  - [actionable_patterns](system/implementation/actionable_patterns) - Trading pattern implementation

### 📚 **User Guides** (`guides/`)

How-to documentation for practical usage:

- **[validation-framework](guides/validation-framework)** - LLM validation and testing framework
- **[pattern-validation](guides/pattern-validation)** - Pattern taxonomy validation workflow (Issue #79)
- **[data-obfuscation](guides/data-obfuscation)** - Anti-cheating measures for validation
- **[baseline-strategy](guides/baseline-strategy)** - Trading strategy implementation

### 📊 **Technical Reference** (`reference/`)

Technical specifications and research findings:

- **[model-selection-research](reference/model-selection-research)** - O3-mini vs GPT-4o comparison
- **[token_configuration](reference/token_configuration)** - LLM token optimization strategy
- **[adaptive-consensus-technical-indicators](reference/adaptive-consensus-technical-indicators)** - Technical indicators
- **`api/`** - API documentation and specifications
- **`technical/`** - Implementation details and configurations
  - [agent-feature-audit](reference/technical/agent-feature-audit) - MarketMechanicsAgent method audit (Oct 2025)

### 🗄️ **Archive** (`archive/`)

Historical documentation and legacy components:

- **`legacy/`** - Archived code and migration documentation
- **`research/`** - Historical research and experiments
- **`agents/`** - Legacy agent implementations

## 🎯 **Current Production Features**

✅ **LLM-Driven Agent Autonomy** - LLM analyzes experiments and autonomously selects tools and analysis approach
✅ **Strike-Level Pattern Detection** - Enhanced from aggregate GEX analysis (251 daily opportunities vs 1 signal)
✅ **Gamma Pinning Validation** - 75% success rate on Friday 3:30 PM patterns
✅ **O3-mini LLM Integration** - 90% confidence analysis with 4000 token optimization
✅ **Complete Data Flow** - Cache→API→Live data with automatic fallbacks
✅ **Validation Framework** - Anti-cheating measures with obfuscated data
✅ **Enhanced Pattern Detection** - Compound patterns: High Probability Pin, Volume Gamma Breakout

## 🔬 **Key Research Findings**

- **90% LLM Confidence** - Production validation with real SPY options data
- **75% Gamma Pinning Success Rate** - Friday 3:30 PM validation exceeds 60% threshold
- **251 Strike-Level Opportunities** - vs 1 aggregated signal (massive improvement)
- **O3-mini Optimal Model** - Best cost/performance ratio (75% confidence, 65% cost savings)
- **Token Optimization** - 0 tokens for tools, 4000 tokens for LLM analysis only
- **LLM Agent Autonomy** - Three-stage process: LLM plans tools → executes plan → analyzes results

## 🔧 **System Requirements**

- **Python 3.8+** with required dependencies
- **Database**: SQLite for local caching
- **API Access**: Alpha Vantage Premium (with cache fallbacks)
- **LLM**: O3-mini model access for market mechanics analysis

---

*Last Updated: September 19, 2025*
