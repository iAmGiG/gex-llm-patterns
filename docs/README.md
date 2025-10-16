# GEX-LLM Patterns Documentation

## 🚀 **PhD Research Platform**

**Latest Status** (October 12, 2025): CS PhD dissertation research platform investigating whether LLMs can understand market microstructure mechanics (WHY and WHEN patterns exist). **MAJOR MILESTONE**: Successfully validated LLM methodology across 3 pattern types throughout full 2024 year (181 trading days), proving LLMs can detect structural patterns without memorization.

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
- **[gex-metrics-explained](guides/gex-metrics-explained)** - Why we use net GEX and metric choice justification (Oct 16, 2025)
- **[validation-data-pipeline-fix](guides/validation-data-pipeline-fix)** - Q3 corruption postmortem and database fix (Oct 11, 2025)
- **[baseline-strategy](guides/baseline-strategy)** - Trading strategy implementation
- **[report-manager-consolidation](guides/report-manager-consolidation)** - Report manager consolidation (Issue #63, Oct 12, 2025)

### 📊 **Technical Reference** (`reference/`)

Technical specifications, research findings, and code reference documentation:

- **[model-selection-research](reference/model-selection-research)** - O3-mini vs GPT-4o comparison
- **[token-configuration](reference/token-configuration)** - LLM token optimization strategy
- **[adaptive-consensus-technical-indicators](reference/adaptive-consensus-technical-indicators)** - Technical indicators
- **[deleted-code-reference](reference/deleted-code-reference)** - Git history for removed code (data_normalization, deprecated analysis, sample_data_gex)
- **[unused-code-reference](reference/unused-code-reference)** - Orphaned/unused code tracking (src/strategies/, Oct 12, 2025)
- **[gex-module-consolidation-plan](reference/gex-module-consolidation-plan)** - Future optimization plan for LiveGEXInterface consolidation
- **`api/`** - API documentation and specifications
- **`technical/`** - Implementation details and configurations
  - [agent-feature-audit](reference/technical/agent-feature-audit) - MarketMechanicsAgent method audit (Oct 2025)

### 🗄️ **Archive** (`archive/`)

Historical documentation and legacy components:

- **[multipattern_validation_2024](archive/multipattern_validation_2024)** - Full 2024 multi-pattern validation analysis (Oct 2025)
- **`legacy/`** - Archived code and migration documentation
- **`research/`** - Historical research and experiments
- **`agents/`** - Legacy agent implementations

## 🎯 **Current System Status (October 12, 2025)**

✅ **Full 2024 Multi-Pattern Validation COMPLETE** - 181 trading days across Q1, Q3, Q4 2024
✅ **Research Question Answered** - LLMs can detect structural market microstructure patterns without memorization
✅ **100% Detection Rate** - Maintained across all 9 quarter-pattern combinations
✅ **87-98% Predictive Accuracy** - Maintained across all quarters and pattern types
✅ **Obfuscation Testing Passes** - All patterns MECHANICAL (work without temporal context)
✅ **Cross-Pattern Generalization** - Same methodology works for gamma_positioning, stock_pinning, 0dte_hedging
✅ **Regime Robustness** - Detection/accuracy stable across varying market conditions
📝 **Ready for PhD Paper #1** - Sufficient evidence for methodology validation paper

## 🔬 **Key Research Findings**

### Research Success (Full 2024)

**Core Research Question**: "Can LLMs identify and interpret market microstructure patterns (WHY/WHEN) without memorization?"

**Answer**: **YES** ✅

**Evidence**:

- **100% detection** across 181 trading days, 3 pattern types, 3 quarters
- **87-98% predictive accuracy** - predictions materialize regardless of profitability
- **Passes obfuscation testing** - works without temporal context
- **Cross-pattern generalization** - same methodology detects different constraint types
- **Regime robustness** - detection/accuracy stable across varying market conditions

### Full Year Results Table

| Pattern | Quarter | Detection | Accuracy | Sample |
|---------|---------|-----------|----------|--------|
| gamma_positioning | Q1 | 100% | 96.2% | 53 |
| gamma_positioning | Q3 | 100% | 98.4% | 64 |
| gamma_positioning | Q4 | 100% | 98.4% | 64 |
| stock_pinning | Q1 | 100% | 86.5% | 53 |
| stock_pinning | Q3 | 100% | 92.2% | 64 |
| stock_pinning | Q4 | 100% | 92.1% | 64 |
| 0dte_hedging | Q1 | 100% | 90.4% | 53 |
| 0dte_hedging | Q3 | 100% | 92.2% | 64 |
| 0dte_hedging | Q4 | 100% | 88.9% | 64 |

### Key Insights

**1. Pattern Consolidation Discovery**: Three tested patterns are narrative variations of one underlying mechanism - dealer gamma hedging constraints. LLM correctly identifies the same structural mechanic across different framings.

**2. Detection ≠ Profitability**: Detection and accuracy remain stable while profitability varies across quarters. This proves the LLM detects structural mechanisms, not just profitable patterns.

**3. Methodology Validation**: Obfuscation testing proves LLMs can reason about market microstructure mechanics (WHY patterns exist, WHEN they're mechanical) without memorizing training data.

### Technical Lessons (October 2025)

- **Database Architecture** - Storage layer must store real data; obfuscation is analysis-time only
- **Coverage Validation** - Must verify ≥80% data completeness to prevent selection bias (Issue #84)
- **Outcome Calculation** - Database lookup must execute before fallback inference methods

## 🔧 **System Requirements**

- **Python 3.8+** with required dependencies
- **Database**: SQLite for local caching
- **API Access**: Alpha Vantage Premium (with cache fallbacks)
- **LLM**: O3-mini model access for market mechanics analysis

---

## 📚 **Key Documentation**

- **[multipattern_validation_2024.md](archive/multipattern_validation_2024.md)** - Comprehensive analysis of full 2024 multi-pattern validation with research framing
- **[CLAUDE.md](../CLAUDE.md)** - Current system status and next steps
- **[todo.md](../todo.md)** - Task tracking and completed milestones

## 📊 **Validation Reports**

All validation results stored in `reports/validation/pattern_taxonomy/`:

- `gamma_positioning_SPY_2024Q*.yaml` (Q1, Q3, Q4)
- `stock_pinning_SPY_2024Q*.yaml` (Q1, Q3, Q4)
- `0dte_hedging_SPY_2024Q*.yaml` (Q1, Q3, Q4)

## 🔧 **Known Limitations**

- ⚠️ **Q2 2024 Data Gap** - Only June data collected (27% coverage, insufficient for validation)
  - Q2 results not included in full year analysis
  - Q1, Q3, Q4 provide sufficient evidence (181 trading days)

---

*Last Updated: October 12, 2025*
