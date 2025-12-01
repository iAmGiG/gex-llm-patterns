# Infrastructure Maintenance and Audits

**Last Audit**: November 22, 2025
**Scope**: Configuration management, prompt templates, database/cache architecture, documentation consolidation
**Status**: Completed

---

## Part 1: Configuration Grooming Audit (Nov 22, 2025)

### Executive Summary

This audit identifies hardcoded values, prompts, and architectural issues that should be externalized to configuration files for better maintainability, testing, and collaboration.

#### Key Findings

1. ✅ **Agent prompts already in config** - `llm_prompts.yaml` contains agent workflow prompts
2. ❌ **Paper #2 regime prompt hardcoded** - Critical 500-line prompt embedded in code
3. ⚠️ **Regime classifier thresholds hardcoded** - Core Paper #2 criteria not configurable
4. ✅ **Database/cache architecture sound** - Dual-layer system working correctly
5. ⚠️ **Worktree cache divergence** - Known issue causing sync problems

### Prompt Template Analysis

#### Already Externalized ✅

**File**: `config_defaults/llm_prompts.yaml`

Existing prompt templates (all properly configured):

- `standard` - Pattern detection with regime labels (Paper #1)
- `unbiased` - No regime labels for bias testing (Issue #90)
- `reasoning` - Chain-of-thought for o3-mini (advanced validation)
- **`rich_reasoning`** - NEW (Issue #146) - Alpha divergence analysis

Agent workflow prompts (lines 363-491):

- `batch_analysis` - Multi-day comparative analysis
- `experiment_planning` - Autonomous tool selection
- `experiment_analysis` - Result interpretation

**Status**: Well-structured, follows convention, no action needed.

#### Hardcoded Prompts Requiring Extraction ❌

**Issue #1: Paper #2 Regime Detection Prompt**

**Location**: `src/llm/mechanics_prompt_builder.py:393-500` (108 lines)

**Why This Is Critical**:

- **Paper #2 core methodology** - This prompt defines the entire validation approach
- **Not version controlled separately** - Changes require code commits
- **Cannot A/B test** - Can't compare prompt variants without code changes
- **Hard to review** - Embedded in Python file, not standalone document
- **Collaboration friction** - Chat B/C can't easily edit prompts without touching code

**Impact**: HIGH - This is the foundation of Paper #2's 1,418-window validation

**Recommendation**: Extract to `llm_prompts.yaml` under new section `paper2_regime_detection`

**Effort**: 2-3 hours
**Risk**: Low (fallback ensures no breakage)
**Benefit**: High (enables prompt iteration without code changes)

**Issue #2: Pattern Detection Prompt**

**Location**: `src/llm/mechanics_prompt_builder.py:199-220` (22 lines)

**Why Less Critical**:

- Paper #1 already uses `llm_prompts.yaml` templates (standard/unbiased/reasoning)
- This is a **fallback/legacy** prompt for direct API calls
- Most validation now uses configured templates

**Recommendation**: LOW PRIORITY - Document as legacy, migrate callers to configured templates

**Effort**: 1 hour
**Risk**: Very Low
**Benefit**: Consistency (all prompts in one place)

### Hardcoded Configuration Values

#### Regime Classifier Thresholds ⚠️

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

**Effort**: 30 minutes
**Risk**: Very Low (maintains backward compatibility)
**Benefit**: Medium (enables sensitivity analysis)

### Database and Cache Architecture Review

#### Current Architecture ✅ (Updated Issue #147, Nov 22, 2025)

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

**Assessment**: ✅ **Architecture significantly improved (Issue #147)**

- **Single source of truth**: Database now stores raw options (not just GEX summaries)
- **No file cache dependency**: Validation scripts work database-only
- **Persistent storage**: Raw options survive file cache clearing
- **Queryable history**: Can reconstruct any date's GEX from raw options
- **Indexes optimized**: Fast 30-day window retrieval for Paper #2

#### Known Issues and Mitigations

**Issue #3: Field Name Aliasing (FIXED Nov 22, 2025) ✅**

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

**Issue #4: Worktree Cache Divergence ⚠️**

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

**Recommendation**: Document in developer guide (see [worktree_cache_management.md](../development/worktree_cache_management.md))

### Architecture Decisions Review

#### Why Paper #2 Doesn't Use Agent System ✅

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

**Status**: No changes needed - architecture matches task complexity

---

## Part 2: Documentation Cleanup and Consolidation (Nov 22, 2025)

### Cleanup Actions Completed

#### Issue #146 Files Consolidation (Paper #1)

**Before** (3 separate files):

```
docs/papers/paper1/analysis/
├── issue_146_complete_analysis.md     (17.6 KB)
├── issue_146_mc_summary.md            (9.1 KB)
├── issue_146_mc_paper1_recommendations.md (10.5 KB)
```

**After** (1 consolidated file):

```
docs/papers/paper1/analysis/
└── issue_146_alpha_divergence_complete.md  (~37 KB)
    ├── Executive Summary (from mc_summary)
    ├── Full Analysis (from complete_analysis)
    ├── Statistical Evidence
    ├── Linguistic Evidence
    └── Paper #1 Recommendations (from mc_paper1_recommendations)
```

**Naming Change**: `issue_146_complete_analysis.md` → `issue_146_alpha_divergence_complete.md` for clarity

#### Batch Metadata Cleanup

**Removed**:

- `batch_metadata_batch_69225e32e6e8819085a97e2e31ecb789.yaml` (temporary tracking)

**Reason**: Temporary tracking file for Issue #146 Phase 2, not needed after analysis complete

#### Development and Infrastructure Index Creation

**New files created**:

- `docs/development/README.md` - Index development guides (worktree, testing, etc.)
- `docs/infrastructure/README.md` - Index infrastructure audits and architecture docs

### Naming Convention Compliance

**Existing Patterns Verified**:

- Infrastructure: `descriptive_name_YYYYMMDD.md` ✅
- Paper analysis: `issue_NNN_description.md` ✅
- Guides: `topic_name.md` ✅

**No Violations Found** - All files follow existing patterns

---

## Part 3: Recommendations Summary

### High Priority (Completed)

1. ✅ **Extracted Paper #2 Regime Prompt** to `llm_prompts.yaml`
   - Effort: 2-3 hours
   - Impact: Enables prompt iteration without code changes
   - Status: COMPLETED (Issue #149)

2. ✅ **Moved Regime Classifier Thresholds** to `analysis_config.yaml`
   - Effort: 30 minutes
   - Impact: Enables sensitivity analysis
   - Status: COMPLETED (Issue #149)

3. ✅ **Documented Worktree Cache Management**
   - Effort: 1 hour
   - Impact: Prevents future sync issues
   - Status: COMPLETED (docs/development/worktree_cache_management.md)

### Medium Priority (Future)

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

## Part 4: Audit History

### November 22, 2025 - Infrastructure Grooming Audit

**Completed Actions**:

- Externalized 240 lines of hardcoded config (196 prompt + 44 thresholds)
- Fixed field name aliasing bug
- Documented worktree cache strategy
- Created developer guides for cache management

**Files Modified**:

- `config_defaults/llm_prompts.yaml` (+196 lines)
- `config_defaults/analysis_config.yaml` (+44 lines)
- `src/validation/regime_classifier.py` (config integration)
- `src/llm/mechanics_prompt_builder.py` (prompt documentation)

**Documentation Created**:

- `docs/infrastructure/grooming_audit_nov22_2025.md` (audit findings)
- `docs/development/worktree_cache_management.md` (developer guide)

### November 24, 2025 - Documentation Consolidation

**Completed Actions**:

- Consolidated Paper #1 Issue #146 files (3 → 1)
- Removed temporary batch metadata files
- Created infrastructure index files
- Merged infrastructure documentation (13 files → 9 sequential files)

**Files Consolidated**:

- Paper #1 archive: 5 files → 1 comprehensive archive
- Infrastructure docs: system/ + reference/ + infrastructure/ → 9 sequential files

**Documentation Created**:

- `docs/infrastructure/README.md` (infrastructure index)
- `docs/development/README.md` (development index)
- `docs/infrastructure/01-09-*.md` (9 sequential consolidated files)

---

## Part 5: Maintenance Best Practices

### Configuration Management

1. **Externalize prompts and thresholds** to YAML files
2. **Document rationale** for configuration values
3. **Use version control** for configuration changes
4. **Test before deploying** new configurations

### Database Maintenance

1. **Backup regularly**: Daily backups of `.cache/consolidated_historical.db`
2. **Monitor size**: Track database growth, optimize indexes
3. **Verify integrity**: Run `PRAGMA integrity_check` monthly
4. **Archive old data**: Move historical data to separate databases if needed

### Cache Management

1. **Monitor hit rates**: Should be >90% for repeated experiments
2. **Clean stale data**: Remove cache entries older than retention period
3. **Validate symlinks**: Ensure worktree symlinks point to correct databases
4. **Document cache strategy**: Keep cache management docs updated

### Documentation Maintenance

1. **Consolidate related docs**: Reduce file count while preserving detail
2. **Use sequential numbering**: 01-project-overview.md, 02-architecture.md, etc.
3. **Update indexes**: Keep README files current with new docs
4. **Archive obsolete docs**: Move to docs/archive/ with date and reason

### Code Maintenance

1. **Add unit tests**: Prevent regression of fixed bugs
2. **Migrate legacy code**: Move old implementations to docs/legacy/
3. **Update dependencies**: Keep libraries current, test compatibility
4. **Refactor hardcoded values**: Externalize to config as discovered

---

## Part 6: Known Issues and Workarounds

### Worktree Cache Sync

**Issue**: Git worktrees have separate `.cache/` directories
**Workaround**: Symlink database or manual rsync
**Documentation**: [docs/development/worktree_cache_management.md](../development/worktree_cache_management.md)

### Field Name Aliasing

**Issue**: Multiple field names for GEX values (net_gex, total_gex, net_gex_usd)
**Workaround**: Alias mapping in GEXCacheManager
**Status**: Fixed (commit 268ba7f), needs unit tests

### Database Growth

**Issue**: Database size growing with raw options chain storage (3.25 GB)
**Workaround**: Monitor size, archive old data if needed
**Status**: Within acceptable limits, no action needed

---

## Part 7: Audit Schedule

### Monthly Audits

- Review configuration files for new hardcoded values
- Check database size and performance
- Validate cache hit rates
- Update documentation indexes

### Quarterly Audits

- Comprehensive architecture review
- Dependency updates and testing
- Documentation consolidation
- Performance optimization review

### Annual Audits

- Full system architecture evaluation
- Technology stack assessment
- Security and compliance review
- Research methodology validation

---

## Navigation

**Prerequisites**: [07-experiments-and-validation.md](07-experiments-and-validation.md)
**Next**: [README.md](README.md)
**Related**: [docs/development/worktree_cache_management.md](../development/worktree_cache_management.md)
