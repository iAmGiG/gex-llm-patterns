# GEX-LLM Patterns Documentation

## 🚀 **PhD Research Platform**

**Latest Status** (October 11, 2025): CS PhD dissertation research platform investigating whether LLMs can identify actionable patterns in market microstructure. Currently validating consolidated `dealer_gamma_hedging` pattern across Q1-Q4 2024 data with fixed database architecture (hardcoded obfuscation removed).

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
- **[validation-data-pipeline-fix](guides/validation-data-pipeline-fix)** - Q3 corruption postmortem and database fix (Oct 11, 2025)
- **[baseline-strategy](guides/baseline-strategy)** - Trading strategy implementation

### 📊 **Technical Reference** (`reference/`)

Technical specifications and research findings:

- **[model-selection-research](reference/model-selection-research)** - O3-mini vs GPT-4o comparison
- **[token_configuration](reference/token_configuration)** - LLM token optimization strategy
- **[adaptive-consensus-technical-indicators](reference/adaptive-consensus-technical-indicators)** - Technical indicators
- **`api/`** - API documentation and specifications
- **`technical/`** - Implementation details and configurations
  - [agent-feature-audit](reference/technical/agent-feature-audit) - MarketMechanicsAgent method audit (Oct 2025)

### 🗂️ **Project Documentation** (root `docs/`)

Planning and maintenance documentation:

- **[DELETED_CODE_REFERENCE](DELETED_CODE_REFERENCE)** - Git history for removed code (data_normalization, deprecated analysis, sample_data_gex)
- **[GEX_MODULE_CONSOLIDATION_PLAN](GEX_MODULE_CONSOLIDATION_PLAN)** - Future optimization plan for LiveGEXInterface consolidation

### 🗄️ **Archive** (`archive/`)

Historical documentation and legacy components:

- **`legacy/`** - Archived code and migration documentation
- **`research/`** - Historical research and experiments
- **`agents/`** - Legacy agent implementations

## 🎯 **Current System Status (October 11, 2025)**

✅ **Pattern Consolidation** - Three patterns (gamma_positioning, stock_pinning, 0dte_hedging) consolidated into `dealer_gamma_hedging`
✅ **Database Architecture Fixed** - Removed hardcoded obfuscation (450.0) from storage layer
✅ **Obfuscation Layer Separated** - Database stores real prices, LLM analysis uses obfuscated data
✅ **Batch Processing** - Multiple dates in single LLM call (75% API cost reduction)
✅ **Enhanced Output Structure** - Outcome metrics with forward returns, velocity, grouped structure (Issue #80)
✅ **Q1 2024 Validation** - 90.38% predictive accuracy, +0.70% net alpha (53 trading days)
🔄 **Q2-Q4 2024 Validation** - In progress after database rebuild with corrected spot prices

## 🔬 **Key Research Findings**

### Validated (Q1 2024):
- **Pattern Consolidation Discovery** - Three "different" patterns are identical quantitatively (same GEX, outcomes)
- **90.38% Predictive Accuracy** - dealer_gamma_hedging pattern on 53 trading days
- **+0.70% Net Alpha** - After 5bps transaction costs (exceeds >20bps threshold)
- **100% Detection Rate** - Pattern detected on all negative GEX days

### Architecture Lessons (October 11, 2025):
- **Database Corruption Bug** - Hardcoded 450.0 obfuscation in storage layer caused 95x forward return errors
- **Separation of Concerns** - Storage layer must store REAL data; obfuscation is analysis-time only
- **Q3 2024 Corruption** - Showed impossible 42.77% daily moves (physically implausible for SPY)
- **Fix Applied** - Database builder now refuses fake prices, fetches real data from API/put-call parity

### Pending (Q2-Q4 2024):
- Database rebuild in progress with corrected spot prices
- Full-year validation to determine if pattern works consistently or needs regime filter

## 🔧 **System Requirements**

- **Python 3.8+** with required dependencies
- **Database**: SQLite for local caching
- **API Access**: Alpha Vantage Premium (with cache fallbacks)
- **LLM**: O3-mini model access for market mechanics analysis

---

## 🔧 **Known Issues**

- ⚠️ **Database Rebuild Required** - Q2-Q4 2024 database being rebuilt with corrected spot prices (Chat A working)
- ⚠️ **Q3 Validation Invalid** - Previous results showed impossible returns due to obfuscated prices in database
- ⚠️ **Q2 Incomplete** - Only June tested (17 days), Apr-May missing from cache

See `.claude/cross_chat_sync.yaml` for current status.

---

*Last Updated: October 11, 2025*
