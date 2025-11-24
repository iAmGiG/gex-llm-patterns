# ADR 002: Architecture Separation (Paper #1 vs Paper #2)

**Status**: Accepted
**Date**: November 4, 2025
**Context**: With Paper #2 introducing sequential analysis, need clear separation between single-day (P1) and temporal (P2) components to manage complexity and enable future papers.
**Decision**: Maintain shared core components with paper-specific extensions, avoiding full codebase fork.
**Consequences**: Code reuse across papers; clear boundaries for future work; some complexity in maintaining backward compatibility.

---

## Component Classification

### Shared Core (All Papers)

**Data Infrastructure**:

- `src/data_sources/alpha_vantage_gex.py` - Options data API client
- `src/data_sources/historical_gex_builder.py` - Database builder
- `src/gex/gex_calculator.py` - Core GEX calculations
- `.cache/historical_gex.db` - Historical GEX database

**Validation Framework**:

- `src/validation/outcome_calculator.py` - Forward returns, realized vol
- `src/cache/unified_cache_manager.py` - Caching system
- `src/validation/data_obfuscator.py` - Date/ticker obfuscation

**Utilities**:

- `config/config.json` - API keys, settings
- `config_defaults/analysis_config.yaml` - LLM configurations

---

### Paper #1 Specific (Single-Day Analysis)

**Core Components**:

- `src/agents/market_mechanics_agent.py::run_experiment()` - Single-day snapshot analysis
- `src/validation/pattern_taxonomy.py` - Pattern definitions (gamma_positioning, stock_pinning, 0dte_hedging)
- `scripts/validation/validate_p1_pattern_taxonomy.py` - Single-day validation script
- `scripts/validation/validate_p1_all_patterns.py` - Batch validation

**Prompt Framework**:

- `src/llm/mechanics_prompt_builder.py::build_single_day_prompt()` - Single snapshot prompt
- System prompt: `mechanics_analyst` (leading version)

**Output Format**:

- Single detection per day
- WHO → WHOM → WHAT framework
- Pattern classification: structural vs narrative

**Data Access**:

- Query: Single date from database
- Window: Day T snapshot only

**Status**: ✅ Complete, validated on 181 trading days (Q1, Q3, Q4 2024)

---

### Paper #2 Specific (Sequential/Temporal Analysis)

**Core Components**:

- `src/data_sources/sequential_gex_fetcher.py` - 5-day window retrieval (433 lines)
- `scripts/validation/validate_p2_sequential_patterns.py` - Sequential validation script
- `scripts/validation/validate_p2_negative_controls.py` - Negative controls testing

**Prompt Framework**:

- `src/llm/mechanics_prompt_builder.py::build_sequential_prompt_neutral()` - Temporal trajectory prompt
- System prompt: `mechanics_analyst_neutral` (bias-mitigated version)

**Pattern Types** (New):

- Gamma Accumulation (magnitude increasing)
- Gamma Relief (magnitude decreasing)
- Gamma Reversal (sign flip)
- Persistent Constraint (stable magnitude)

**Output Format**:

- Trajectory classification
- Temporal dynamics (T-4 → T+0)
- Confidence with null hypothesis support

**Data Access**:

- Query: 5-day sequences from database
- Window: [T-4, T-3, T-2, T-1, T+0]
- Trajectory metrics: trend, velocity, drift

**Status**: 🔄 Phase 1 complete (proof-of-concept), Phase 2 pending (full validation)

---

### Shared LLM Infrastructure (Extended for P2)

**AutoGenMarketMechanics** (`src/llm/autogen_market_mechanics.py`):

- Base class: Same for both papers
- Extension: `prompt_style` parameter added for P2
  - `prompt_style='leading'` → Paper #1 (default)
  - `prompt_style='neutral'` → Paper #2

**MechanicsPromptBuilder** (`src/llm/mechanics_prompt_builder.py`):

- P1 methods: `build_single_day_prompt()`, `parse_response()`
- P2 methods: `build_sequential_prompt()`, `build_sequential_prompt_neutral()`, `parse_sequential_response()`
- Shared: Obfuscation logic, validation helpers

---

## Architecture Decisions

### Decision 1: Extend vs Fork

**Options Considered**:

1. **Fork codebase** - Separate repos for P1 and P2
2. **Branching** - Long-lived paper-specific branches
3. **Worktree** - Multiple working trees from same repo
4. **Extension pattern** - Shared core + paper-specific modules ✅ **CHOSEN**

**Rationale for Extension Pattern**:

- ✅ Code reuse (GEX calc, data fetching, validation shared)
- ✅ Single source of truth for bug fixes
- ✅ Paper #3 can build on both P1 and P2 work
- ✅ Easier CI/CD and testing
- ❌ Some complexity in maintaining backward compatibility

### Decision 2: Validation Scripts Naming

**Convention**: `validate_p{N}_{description}.py`

**Examples**:

- `validate_p1_pattern_taxonomy.py` - Paper #1 validation
- `validate_p2_sequential_patterns.py` - Paper #2 validation
- `validate_p2_negative_controls.py` - Paper #2 controls

**See**: [001-validation-script-naming.md](001-validation-script-naming.md)

### Decision 3: Shared vs Isolated Database

**Decision**: **Shared database** with paper-agnostic schema

**Rationale**:

- Historical GEX data is identical for all papers
- Single rebuild fixes all downstream consumers
- Query optimization benefits all papers
- Paper-specific queries via different access patterns:
  - P1: `SELECT * WHERE date = ?`
  - P2: `SELECT * WHERE date BETWEEN ? AND ?`

### Decision 4: Prompt Framework Organization

**Decision**: **Single file with method dispatch**

**Structure**:

```python
# src/llm/mechanics_prompt_builder.py
class MechanicsPromptBuilder:
    # Paper #1 methods
    @staticmethod
    def build_single_day_prompt(...)

    # Paper #2 methods
    @staticmethod
    def build_sequential_prompt(...)

    @staticmethod
    def build_sequential_prompt_neutral(...)
```

**Rationale**:

- Centralized prompt logic (easier to maintain)
- Clear method naming distinguishes paper-specific logic
- Shared helpers (obfuscation, formatting) reduce duplication

---

## Future Papers (Guidance)

### Paper #3: Cross-Asset Extension

**Expected Components**:

- Reuse: All shared core (GEX calc, database, validation)
- Extend: Multi-symbol fetcher (SPY, QQQ, IWM)
- New: Cross-asset correlation analysis
- Decision: Extend `SequentialGEXFetcher` or create `MultiAssetGEXFetcher`?

**Validation Scripts**: `validate_p3_cross_asset.py`

**Prompt Framework**: Likely reuse P2 sequential prompts with multi-asset context

### Paper #4+: TBD

Follow same extension pattern:

1. Identify shared components (reuse)
2. Create paper-specific modules (extend)
3. Add validation scripts with `p{N}` prefix
4. Document decisions in cross-paper ADRs

---

## Repository Organization Options

### Current: Single Repo, Extension Pattern ✅

**Pros**:

- Code reuse maximized
- Single CI/CD pipeline
- Easier dependency management
- Paper #3 can build on P1 + P2

**Cons**:

- Some complexity in maintaining compatibility
- Larger codebase to navigate
- Potential for unintended cross-paper changes

**Verdict**: KEEP for now, revisit if complexity becomes unmanageable

### Alternative 1: Monorepo with Subpackages

```
gex-llm-patterns/
├── core/           # Shared components
├── paper1/         # P1-specific code
├── paper2/         # P2-specific code
└── paper3/         # Future papers
```

**Consideration**: Only if we have 4+ papers and clear separation is needed

### Alternative 2: Git Worktree

**Use Case**: Work on P1 and P2 simultaneously without switching branches

**Command**:

```bash
git worktree add ../paper2-worktree paper2-sequential-gex
```

**Benefits**: Parallel development, no branch switching
**Drawbacks**: More disk space, manual sync required

**Verdict**: Available if needed, not required yet

### Alternative 3: Separate Repos

**Only if**: Papers have fundamentally different codebases (e.g., P1 = Python, P2 = R)

**Current**: Not applicable (shared Python codebase)

---

## Migration Path (If Needed)

If codebase complexity grows beyond manageability:

**Phase 1**: Introduce subpackages

```bash
mkdir -p src/paper1 src/paper2 src/core
git mv src/validation/pattern_taxonomy.py src/paper1/
git mv src/data_sources/sequential_gex_fetcher.py src/paper2/
```

**Phase 2**: Separate validation directories

```bash
validation/
├── paper1/
├── paper2/
└── shared/
```

**Phase 3**: (Nuclear option) Split repos

- Extract shared core to `gex-core` library
- Create `paper1-validation`, `paper2-validation` repos
- Install `gex-core` as dependency

**Trigger**: If maintenance burden exceeds benefits of code sharing

---

## Current Status

**Implementation**: ✅ Extension pattern working well

- Paper #1: Submitted (no changes needed)
- Paper #2: Phase 1 complete, cleanly separated
- Shared components: Stable and reusable

**Recommendation**: **Keep current architecture** until Paper #3 planning

**Review Date**: After Paper #2 submission (Q1 2026)

---

## Navigation

**Related**:

- [001-validation-script-naming.md](001-validation-script-naming.md) - Script naming convention
- [../paper2/adr/006-sequential-gex-architecture.md](../paper2/adr/006-sequential-gex-architecture.md) - P2-specific architecture
**Next**: Document Paper #3 architecture decisions when planning begins
**GitHub Issues**: #89 (Paper #2), Future: #XXX (Paper #3)
