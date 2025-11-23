# Infrastructure Grooming Audit

**Date**: November 22, 2025
**Auditor**: Chat A
**Scope**: Configuration management, prompt templates, database/cache architecture
**Status**: In Progress

---

## Executive Summary

This audit identifies hardcoded values, prompts, and architectural issues that should be externalized to configuration files for better maintainability, testing, and collaboration.

### Key Findings

1. ✅ **Agent prompts already in config** - `llm_prompts.yaml` contains agent workflow prompts
2. ❌ **Paper #2 regime prompt hardcoded** - Critical 500-line prompt embedded in code
3. ⚠️ **Regime classifier thresholds hardcoded** - Core Paper #2 criteria not configurable
4. ✅ **Database/cache architecture sound** - Dual-layer system working correctly
5. ⚠️ **Worktree cache divergence** - Known issue causing sync problems

---

## 1. Prompt Template Analysis

### 1.1 Already Externalized ✅

**File**: `config_defaults/llm_prompts.yaml`

Existing prompt templates (all properly configured):

- `standard` - Pattern detection with regime labels (Paper #1)
- `unbiased` - No regime labels for bias testing (Issue #90)
- `reasoning` - Chain-of-thought for o3-mini (advanced validation)
- **`rich_reasoning`** - NEW (Issue #146, added by Chat C) - Alpha divergence analysis

Agent workflow prompts (lines 363-491):

- `batch_analysis` - Multi-day comparative analysis
- `experiment_planning` - Autonomous tool selection
- `experiment_analysis` - Result interpretation

**Status**: Well-structured, follows convention, no action needed.

### 1.2 Hardcoded Prompts Requiring Extraction ❌

#### Issue #1: Paper #2 Regime Detection Prompt

**Location**: `src/llm/mechanics_prompt_builder.py:393-500` (108 lines)

**Current Implementation**:

```python
@staticmethod
def build_regime_prompt(gex_sequence: List[Dict], end_date: str = None) -> str:
    """Build regime detection prompt for 30-day GEX window analysis (Paper #2)."""

    # ... GEX formatting ...

    prompt = f"""You are a market structure analyst specializing in dealer gamma positioning regimes.

TASK: Analyze this 30-day period and determine if it represents a PERSISTENT regime...

## 30-DAY GEX DATA
{gex_data_table}

## REGIME CLASSIFICATION FRAMEWORK

### PERSISTENT REGIMES (Detect These)

**1. PERSISTENT POSITIVE REGIME**
- Definition: Dealers are LONG gamma, forced to sell into strength
- Criteria:
  * >70% of days (21+/30) have positive net GEX
  * Average magnitude >$5B
  * ≤5 sign flips across 30 days
  * Stable directional constraint

**Mechanism**: When dealers hold long gamma:
- Price rises → Dealers MUST sell shares (rebalance)
...
[continues for ~100 lines]
"""
```

**Why This Is Critical**:

- **Paper #2 core methodology** - This prompt defines the entire validation approach
- **Not version controlled separately** - Changes require code commits
- **Cannot A/B test** - Can't compare prompt variants without code changes
- **Hard to review** - Embedded in Python file, not standalone document
- **Collaboration friction** - Chat B/C can't easily edit prompts without touching code

**Impact**: HIGH - This is the foundation of Paper #2's 1,418-window validation

**Recommendation**: Extract to `llm_prompts.yaml` under new section `paper2_regime_detection`

**Proposed Structure**:

```yaml
# Paper #2 Regime Detection Prompts
paper2_prompts:

  regime_classification:
    name: "30-Day Regime Classification (Paper #2)"
    description: "Persistent regime detection from dealer gamma constraints"

    header: |
      You are a market structure analyst specializing in dealer gamma positioning regimes.

      TASK: Analyze this 30-day period and determine if it represents a PERSISTENT regime
      where dealer constraints create forced, directional flows.

    data_section:
      title: "30-DAY GEX DATA"
      format: "{date_label}: {sign}{net_gex_b:.2f}B"

    framework_section:
      title: "REGIME CLASSIFICATION FRAMEWORK"

      persistent_positive:
        definition: "Dealers are LONG gamma, forced to sell into strength"
        criteria:
          - ">70% of days (21+/30) have positive net GEX"
          - "Average magnitude >$5B"
          - "≤5 sign flips across 30 days"
          - "Stable directional constraint"
        mechanism: |
          When dealers hold long gamma:
          - Price rises → Dealers MUST sell shares (rebalance)
          - Price falls → Dealers MUST buy shares (rebalance)
          - Creates dampening, mean-reverting flows
          - Constraint is STRUCTURAL (dealers cannot avoid)

      persistent_negative:
        definition: "Dealers are SHORT gamma, forced to buy into strength"
        criteria:
          - ">70% of days (21+/30) have negative net GEX"
          - "Average magnitude >$5B"
          - "≤5 sign flips across 30 days"
          - "Stable directional constraint"
        mechanism: |
          When dealers hold short gamma:
          - Price rises → Dealers MUST buy shares (chase)
          - Price falls → Dealers MUST sell shares (chase)
          - Creates amplifying, momentum flows
          - Constraint is STRUCTURAL (dealers cannot avoid)

      transitional:
        definition: "Frequent sign flips between positive/negative GEX"
        rejection_reason: "No persistent constraint. Dealers face mixed conditions daily."

      low_conviction:
        definition: "Consistent sign BUT weak magnitude (<$5B average)"
        rejection_reason: "Insufficient constraint to create persistent forced flows"

    response_format:
      format: "json"
      required_fields:
        - "regime_detected"  # persistent_positive, persistent_negative, transitional, low_conviction
        - "confidence"  # 0-100
        - "reasoning"  # Brief explanation
        - "days_analysis"  # Breakdown by criteria
```

**Implementation Plan**:

1. Add `paper2_prompts` section to `llm_prompts.yaml`
2. Create prompt loader in `MechanicsPromptBuilder`
3. Update `build_regime_prompt()` to use config
4. Add fallback to hardcoded prompt (backward compatibility)
5. Test with existing batch results (verify identical prompts)

**Effort**: 2-3 hours
**Risk**: Low (fallback ensures no breakage)
**Benefit**: High (enables prompt iteration without code changes)

---

#### Issue #2: Pattern Detection Prompt

**Location**: `src/llm/mechanics_prompt_builder.py:199-220` (22 lines)

**Current Implementation**:

```python
prompt = f"""{gex_section}

{flow_section}

{context_section}

QUESTION: Analyze the market mechanics using the WHO forces WHOM to do WHAT framework.

WHO: Identify the key market participant taking action (retail traders, institutions, dealers, etc.)
WHOM: Identify who is being forced to respond (dealers, market makers, other participants)
WHAT: Describe the specific forced action (buy/sell, hedge, rebalance)
...
"""
```

**Why Less Critical**:

- Paper #1 already uses `llm_prompts.yaml` templates (standard/unbiased/reasoning)
- This is a **fallback/legacy** prompt for direct API calls
- Most validation now uses configured templates

**Recommendation**: LOW PRIORITY - Document as legacy, migrate callers to configured templates

**Effort**: 1 hour
**Risk**: Very Low
**Benefit**: Consistency (all prompts in one place)

---

## 2. Hardcoded Configuration Values

### 2.1 Regime Classifier Thresholds ⚠️

**Location**: `src/validation/regime_classifier.py:62-67`

**Current Implementation**:

```python
class RegimeClassifier:
    # Classification thresholds
    PERSISTENCE_THRESHOLD = 0.70  # 70% of days (21/30) same sign
    MAGNITUDE_THRESHOLD = 5e9     # $5B average GEX
    MAX_SIGN_FLIPS = 5            # Max flips for persistent regime
    LOW_CONVICTION_MAG = 3e9      # $3B (below this is too weak)
```

**Why This Matters**:

- **Paper #2 core methodology** - These thresholds define what counts as "persistent"
- **Cannot A/B test** - Can't test 60% vs 70% persistence without code changes
- **Sensitivity analysis impossible** - Reviewers may ask "what if threshold was X?"
- **Not documented separately** - Thresholds embedded in code

**Current Flexibility**: Constructor allows overrides, but defaults are hardcoded

**Recommendation**: Move defaults to config file

**Proposed Addition** to `config_defaults/analysis_config.yaml`:

```yaml
# Paper #2 Regime Classification
regime_classification:
  persistence_threshold: 0.70      # 70% of days same sign (21/30)
  magnitude_threshold: 5000000000  # $5B average GEX
  max_sign_flips: 5                # Max flips for persistent regime
  low_conviction_threshold: 3000000000  # $3B weak magnitude cutoff

  # Window parameters
  window_size: 30  # Days in regime window

  # Rationale (for documentation)
  rationale:
    persistence: "70% ensures dominant regime (21/30 days)"
    magnitude: "$5B threshold from Paper #1 detection rates"
    sign_flips: "≤5 flips allows minor volatility while maintaining regime"
```

**Implementation**:

```python
from src.utils.config_manager import get_config

class RegimeClassifier:
    def __init__(self, persistence_threshold=None, magnitude_threshold=None, max_sign_flips=None):
        config = get_config()

        self.persistence_threshold = persistence_threshold or config.get(
            'regime_classification.persistence_threshold', 0.70
        )
        self.magnitude_threshold = magnitude_threshold or config.get(
            'regime_classification.magnitude_threshold', 5e9
        )
        self.max_sign_flips = max_sign_flips or config.get(
            'regime_classification.max_sign_flips', 5
        )
```

**Effort**: 30 minutes
**Risk**: Very Low (maintains backward compatibility)
**Benefit**: Medium (enables sensitivity analysis)

---

### 2.2 Other Hardcoded Values (Lower Priority)

**Pattern Library Success Rates** (`src/analysis/pattern_library.py`):

- Lines 137-850: Hardcoded success rates for 15+ patterns
- Example: `success_rate=0.67, false_positive_rate=0.15`
- **Status**: OK for now (empirically derived, not tunable parameters)
- **Future**: Could move to `pattern_library_config.yaml` for historical tracking

**Sequential GEX Fetcher Defaults** (`src/data_sources/sequential_gex_fetcher.py`):

- Line 45: `window_size=30` (default for Paper #2)
- Line 49: `window_size=5` (default for Paper #1)
- **Status**: OK (example code in docstrings)

**Validation Confidence Thresholds** (`src/validation/mechanics_validation_dataset.py`):

- Lines 122-207: Multiple `confidence_threshold` values (0.7-0.8)
- **Status**: Test dataset configuration, low priority

---

## 3. Database and Cache Architecture Review

### 3.1 Current Architecture ✅ (Updated Issue #147, Nov 22, 2025)

**Database-First Architecture** (as of Nov 22, 2025):

1. **SQLite Database** (`.cache/consolidated_historical.db`) - **Primary Source**
   - Table: `daily_gex_metrics` (GEX summaries, 1,475 rows)
   - Table: `strike_gex_details` (per-strike GEX, 573,649 rows)
   - Table: `raw_options_chain` (**NEW** - Issue #147, 11,820,580 rows)
   - Purpose: Single source of truth, queryable, persistent
   - Size: 3.25 GB (up from 55 MB pre-Issue #147)

2. **File Cache** (`.cache/gex_data/SPY/YYYY-MM-DD/`) - **DEPRECATED**
   - Purpose: Legacy backward compatibility only
   - Status: Deprecated as of Issue #147
   - Managed by: `GEXCacheManager`, `UnifiedCacheManager`
   - Schema: Flexible (JSON/pickle)

**Schema** (`daily_gex_metrics`):

```sql
CREATE TABLE daily_gex_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    spot_price REAL,
    total_gex REAL,
    net_call_gex REAL,
    net_put_gex REAL,
    gamma_flip_point REAL,
    flip_ratio REAL,
    gex_regime TEXT,
    data_quality_score INTEGER,
    options_count INTEGER,
    validation_status TEXT DEFAULT 'valid',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    gex_oi REAL,
    gex_volume REAL,
    activity_ratio REAL,
    economic_regime TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, date)
);
```

**Indexes**:

- `idx_daily_gex_symbol_date` - Primary lookup
- `idx_daily_gex_date` - Temporal queries

**Schema** (`raw_options_chain`) - **NEW Issue #147**:

```sql
CREATE TABLE raw_options_chain (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
    expiration DATE NOT NULL,
    bid REAL, ask REAL, last REAL,
    volume INTEGER, open_interest INTEGER,
    implied_volatility REAL,
    delta REAL, gamma REAL, theta REAL, vega REAL, rho REAL,
    contract_symbol TEXT,
    underlying_price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, strike, option_type, expiration)
);
```

**Indexes**:

- `idx_raw_options_symbol_date` - Primary lookup (fast 30-day window retrieval)
- `idx_raw_options_expiration` - Expiration-based queries
- `idx_raw_options_strike` - Strike-based queries

**Data Volume**: 11,820,580 rows (1,294 trading days × ~9,000 options/day avg)

**Cache Manager Index** (`gex_cache_index.sqlite`) - **DEPRECATED**:

```sql
CREATE TABLE gex_cache_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    trading_date TEXT NOT NULL,
    calculation_timestamp TEXT NOT NULL,
    data_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    total_gex REAL,
    net_gex REAL,
    flip_point REAL,
    underlying_price REAL,
    contracts_processed INTEGER,
    calculation_duration_ms INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, trading_date, data_type)
);
```

**Assessment**: ✅ **Architecture significantly improved (Issue #147)**

- **Single source of truth**: Database now stores raw options (not just GEX summaries)
- **No file cache dependency**: Validation scripts work database-only
- **Persistent storage**: Raw options survive file cache clearing
- **Queryable history**: Can reconstruct any date's GEX from raw options
- **Indexes optimized**: Fast 30-day window retrieval for Paper #2
- **Schema accommodates growth**: Recent additions: OHLCV (Issue #144), raw_options_chain (Issue #147)

---

### 3.2 Known Issues and Mitigations

#### Issue #3: Field Name Aliasing (FIXED Nov 22, 2025) ✅

**Root Cause** (discovered during Phase 4A):

- Database exports have `total_gex` field
- File cache may have `net_gex` (legacy) or `total_gex` (export)
- Prompt builder expects `net_gex_usd`
- Original code only created alias for `net_gex` → `net_gex_usd`

**Symptom**: All GEX values read as $0.00B in batch validation

**Fix**: `src/cache/gex_cache_manager.py:274-284` (commit 268ba7f)

```python
# Add compatibility aliases for file cache data
if 'net_gex_usd' not in data:
    if 'net_gex' in data:
        data['net_gex_usd'] = data['net_gex']
    elif 'total_gex' in data:  # NEW - handle database export
        data['net_gex_usd'] = data['total_gex']
        data['net_gex'] = data['total_gex']  # Consistency alias
```

**Status**: ✅ Fixed and tested, committed to main repo

**Recommendation**: Add unit tests to prevent regression

---

#### Issue #4: Worktree Cache Divergence ⚠️

**Problem** (discovered during Phase 4A):

- Git worktrees (e.g., `gex-llm-patterns-issue140`) have separate `.cache/` directories
- Not symlinked to main repo cache
- Changes in one worktree don't propagate to others
- User noted: "between having 2 agents share that mem, I'm sure something is getting updated out of sync"

**Impact**:

- Initial Issue #140 batch submissions failed (343 days vs 1297 expected)
- Worktree had incomplete cache
- Required manual rsync from main repo

**Current Mitigation**:

- Manual copy: `rsync -av .cache/gex_data/ ../gex-llm-patterns-issue140/.cache/gex_data/`
- Database file can be symlinked (single source of truth)
- File cache must be copied (git worktree limitation)

**Recommendation**: Document in developer guide

**Proposed**: `docs/development/worktree_cache_management.md`

```markdown
# Git Worktree Cache Management

## Problem

Git worktrees create separate `.cache/` directories, leading to:
- Incomplete data in new worktrees
- Changes not propagating between branches
- Wasted API calls fetching duplicate data

## Solution

### Option 1: Symlink Database (Recommended)

```bash
# In worktree
rm -rf .cache/consolidated_historical.db
ln -s /path/to/main/repo/.cache/consolidated_historical.db .cache/consolidated_historical.db
```

**Pros**: Single source of truth, instant sync
**Cons**: Database writes affect all worktrees (use with caution)

### Option 2: Sync File Cache (Safe)

```bash
# From main repo
rsync -av .cache/gex_data/ ../gex-llm-patterns-issue140/.cache/gex_data/
```

**Pros**: Isolated changes, safe for parallel work
**Cons**: Manual sync required, data duplication

### Option 3: Environment Variable Override

```bash
# In worktree .env
CACHE_DIR=/path/to/main/repo/.cache
```

**Pros**: Automatic sync
**Cons**: Requires code support (not yet implemented)

## Best Practice

For read-only work (validation, testing): **Symlink database**
For data collection (new years): **Sync file cache**
For development (schema changes): **Separate caches**

```

**Effort**: 1 hour (documentation)
**Risk**: None (documentation only)
**Benefit**: Prevents future confusion

---

## 4. Architecture Decisions Review

### 4.1 Why Paper #2 Doesn't Use Agent System ✅

**Question**: "When we started paper 2 we didn't go the route of paper 1 using the agent system. which is fine it it wasn't needed. But why exactly?"

**Answer**:

Paper #1 (Agent System):
```

User Request → Agent → Pattern Library → LLM (multi-turn) → Agent Tools → Result

```
- Multi-step reasoning (detect → explain → validate)
- Tool orchestration (fetch data, calculate GEX, detect patterns)
- Pattern library integration (8+ pattern types)
- Conversation state management

Paper #2 (Direct Batch API):
```

GEX Sequence → Prompt Template → LLM (single-shot) → JSON Result

```
- Single classification task ("Is this persistent?")
- All data pre-loaded in prompt
- No tool calls needed
- Stateless (1,418 independent windows)

**Architectural Decision**: CORRECT ✅

**Rationale**:
1. **No over-engineering** - Agents add complexity only when needed
2. **Cost efficiency** - Batch API = 50% cheaper ($0.015 vs $0.030 per window)
3. **Deterministic** - Same prompt every time (no agent state variations)
4. **Scalable** - Async processing (agent would block terminal for hours)

**The prompt IS the agent** - Paper #2's 108-line prompt template contains:
- Task definition
- Classification framework
- Mechanism explanations
- Output schema

This is equivalent to a "single-turn agent" - no conversation state needed.

**Comparison**:
| Feature | Paper #1 | Paper #2 |
|---------|----------|----------|
| Task Type | Pattern detection (complex) | Regime classification (binary) |
| Reasoning | Multi-turn dialogue | Single-shot classification |
| Tools | AutoGen (fetch, calc, detect) | None (data in prompt) |
| State | Conversation context | Stateless |
| Cost | $0.030/window | $0.015/window |
| Latency | Sync (blocking) | Async (batch) |
| Appropriate? | ✅ Yes | ✅ Yes |

**Status**: No changes needed - architecture matches task complexity

---

## 5. Recommendations Summary

### High Priority (Do Now)

1. **Extract Paper #2 Regime Prompt** to `llm_prompts.yaml`
   - Effort: 2-3 hours
   - Impact: Enables prompt iteration without code changes
   - Risk: Low (fallback preserves compatibility)

2. **Move Regime Classifier Thresholds** to `analysis_config.yaml`
   - Effort: 30 minutes
   - Impact: Enables sensitivity analysis
   - Risk: Very Low

### Medium Priority (Next Sprint)

3. **Document Worktree Cache Management**
   - Effort: 1 hour
   - Impact: Prevents future sync issues
   - Risk: None

4. **Add Unit Tests** for field aliasing
   - Effort: 2 hours
   - Impact: Prevents regression of Issue #3
   - Risk: None

### Low Priority (Future)

5. **Migrate Pattern Detection Prompt** (legacy fallback)
   - Effort: 1 hour
   - Impact: Consistency
   - Risk: Very Low

6. **Pattern Library Config Migration**
   - Effort: 4 hours
   - Impact: Historical tracking
   - Risk: Low

---

## 6. Action Plan

### Phase 1: Critical Extractions (This Session)

- [ ] Add `paper2_prompts` section to `llm_prompts.yaml`
- [ ] Add `regime_classification` section to `analysis_config.yaml`
- [ ] Update `MechanicsPromptBuilder.build_regime_prompt()` to use config
- [ ] Update `RegimeClassifier.__init__()` to use config
- [ ] Test with existing batch results (verify identical behavior)

### Phase 2: Documentation (Next Session)

- [ ] Create `docs/development/worktree_cache_management.md`
- [ ] Add unit tests for field aliasing
- [ ] Update `config_defaults/README.md` with Paper #2 sections

### Phase 3: Code Review (Future)

- [ ] Audit remaining hardcoded values in `src/`
- [ ] Review all `TODO` and `FIXME` comments
- [ ] Consolidate duplicate logic

---

## 7. Current Status Notes

**Git Branch**: `paper1-issue144-p-hacking`

**Unstaged Changes**:
- `config_defaults/llm_prompts.yaml` - Chat C added `rich_reasoning` template (Issue #146)
- `docs/papers/paper1/journal_version/05_Results.tex` - Results updates
- `docs/papers/paper2/validation_complete_summary.md` - Phase 4A summary

**Untracked Files**:
- Issue #146 analysis files (keyword analysis, reasoning extraction)
- Issue #144 verification scripts

**Recommendation**:
1. Commit Chat C's `rich_reasoning` prompt changes first (clean separation)
2. Then commit infrastructure grooming changes
3. Keep Paper #1 and Paper #2 work separated

---

**Next Steps**: Awaiting user direction on which recommendations to implement.
