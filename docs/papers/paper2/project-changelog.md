# Project Changelog

Track major architectural decisions, framework changes, and research milestones.

---

## November 2025

### Paper #2 Negative Controls Complete (Nov 4, 2025)

**What Changed**:

- Completed all 3 negative control tests (30 windows total)
- Validated v3a neutral prompt framework empirically
- Documented 60% false positive reduction with mechanical guidance
- Accepted v3a prompt for Phase 2 validation

**Results**:

- Test 1 (Prompt comparison): 80% neutral vs 100% leading (conservative calibration)
- Test 2 (Random synthetic): 20% false positives (✅ passed <30% threshold)
- Test 3 (Zero-GEX): 0% false positives (✅ passed <10% threshold)
- **Key finding**: Mechanical confidence guidance reduces FPs by 60% vs qualitative

**Methodology Contribution**:

- Novel empirical finding on LLM calibration for temporal pattern recognition
- Challenges assumption that LLM "judgment" should be unconstrained
- Provides template for rigorous negative controls in LLM research

**Impact**:

- Ready for Phase 2: Q1 2024 sequential validation (60 windows)
- Publishable methodology regardless of Phase 2 results
- Demonstrates rare empirical rigor in LLM prompt research

**Issues**: #89, #107, #108

### Documentation Reorganization (Nov 4, 2025)

**What Changed**:

- Reorganized entire `docs/` directory (103 file operations)
- Standardized all files to `kebab-case` naming
- Created `papers/adr/` for cross-paper architecture decisions
- Sequenced guides/ (02-09) and system/architecture/ (01-06)
- Archived 11 deprecated files

**Impact**:

- Clear separation of Paper #1 vs Paper #2 content
- Cross-paper ADRs document shared architecture
- Easier navigation with logical sequencing

**Files**: All `docs/` markdown files

### Paper #2 Phase 1 Complete (Nov 4, 2025)

**What Changed**:

- Implemented `SequentialGEXFetcher` (433 lines) for 5-day window retrieval
- Added neutral prompt framework to mitigate bias
- Created negative controls validation script
- Fixed 3 critical bugs (config paths, missing methods, field mismatch)

**Components Added**:

- `src/data_sources/sequential_gex_fetcher.py`
- `src/llm/mechanics_prompt_builder.py::build_sequential_prompt_neutral()`
- `scripts/validation/validate_p2_sequential_patterns.py`
- `scripts/validation/validate_p2_negative_controls.py`

**Impact**:

- Proof-of-concept: 120 windows, 100% detection, 70-85% confidence
- Framework ready for full 2024 validation
- Bias mitigation validated through neutral prompts

**Issues**: #89, #107, #108

### LLM Model Switch (Nov 3, 2025)

**What Changed**:

- Switched from GPT-4o to o4-mini reasoning model
- Updated config to use `analysis.llm.model` paths
- Validated model performance on test windows

**Rationale**:

- o4-mini optimized for reasoning tasks (dealer constraint analysis)
- Lower cost for large-scale validation
- Academic rigor (explicit reasoning chains)

**Impact**:

- All Paper #2 validation uses o4-mini
- Paper #1 used GPT-4o (submitted results unchanged)

**Issue**: #109

---

## October 2025

### Paper #1 Submitted (Oct 26, 2025)

**What Changed**:

- Submitted Paper #1 to conference/journal
- Finalized all 8 figures and 3 tables
- Completed IEEE two-column LaTeX conversion

**Results**:

- 100% detection rate (181 trading days)
- 87-98% accuracy across Q1, Q3, Q4 2024
- Net alpha declined Q1→Q4 (validates detection ≠ profit optimization)

**Issue**: #88

### Symposium Presentation (Oct 22, 2025)

**What Changed**:

- Delivered PhD symposium presentation
- Created 12 presentation-optimized figures (1920×1080, 120 DPI)
- Demonstrated obfuscation testing methodology

**Files**:

- `docs/presentations/2025-symposium.md`
- `docs/papers/paper1/figures/pres*.png` (12 files)

**Issue**: #95

### Full 2024 Validation Complete (Oct 12, 2025)

**What Changed**:

- Extended validation from Q1 to full year (Q1, Q3, Q4)
- Tested 3 patterns: gamma_positioning, stock_pinning, 0dte_hedging
- Discovered pattern consolidation (3 patterns = 1 mechanism)

**Results**:

- 181 trading days validated
- 100% detection maintained despite alpha decline
- Proves methodology detects structure, not profits

**Impact**:

- PhD contribution strengthened (no cherry-picking)
- Pattern taxonomy simplified (dealer gamma hedging)

**Issue**: #79

### Database Corruption Fix (Oct 11, 2025)

**What Changed**:

- Fixed `HistoricalGEXDatabaseBuilder` API mismatch
- GEX values corrected from 1000-4500x errors to proper magnitudes
- Rebuilt Q1 2024 database with 100% validation match

**Root Cause**:

- Old database (Oct 2) used outdated `calculate_daily_gex_metrics()`
- New code (Oct 9) uses `calculate_gex_profile()`

**Impact**:

- All downstream analysis now uses correct GEX values
- Issue #58 (baseline comparison) unblocked

**Files**: `src/data_sources/historical_gex_builder.py:631`

### OutcomeCalculator Fix (Oct 11, 2025)

**What Changed**:

- Fixed method ordering in `OutcomeCalculator._get_close_price()`
- Database lookup now Method 2 (executes first)
- Deep ITM inference demoted to Method 3 (fallback)

**Impact**:

- Forward returns corrected (was 95x errors on some days)
- Volatility analysis invalidated and rebuilt
- Q1 2024 confirmed as low-volatility period

**Files**: `src/validation/outcome_calculator.py:391-443`

**Deprecated**:

- `reports/VOLATILITY_DISCOVERY_SUMMARY.md`
- `reports/PHASE1_FAILURE_ANALYSIS.md`

### Obfuscation Bug Resolution (Oct 9, 2025)

**What Changed**:

- Added `obfuscate=True` parameter to validation pipeline
- LLM now sees "Day T+0" instead of "2024-01-02"
- LLM now sees "INDEX_1" instead of "SPY"

**Impact**:

- Methodology rigor validated
- Previous results archived (potentially influenced by temporal context)
- Fresh validation recommended for publication

**Issue**: #81

### Enhanced Output Structure (Oct 7, 2025)

**What Changed**:

- Integrated `OutcomeCalculator` for real-time outcome metrics
- Added velocity metrics (GEX day-over-day changes)
- Renamed fields: `detection_rate_pct`, `predictive_accuracy_pct`, `net_alpha_pct`
- Consolidated to single `net_gex_usd` field

**Components Added**:

- `src/validation/outcome_calculator.py` (507 lines)

**Impact**:

- Enables Issue #79 Phase 2 (full year validation)
- Outcome verification now automated

**Issue**: #80

---

## Earlier History (Pre-October 2025)

### Batch LLM Processing (Sep 2025)

**What Changed**:

- Added `run_batch_experiments()` to `MarketMechanicsAgent`
- Processes multiple dates in single LLM call
- Integrated data obfuscation

**Impact**:

- 75% API cost reduction
- Faster validation runs

**Issue**: #78

### Cache System Refactor (Sep 2025)

**What Changed**:

- Fixed dict/DataFrame confusion in `fetch_options_data()`
- Fixed GEXCalculator parameter naming (`spot_price` → `underlying_price`)
- Clarified `.cache/` (data) vs `src/cache/` (code)

**Impact**:

- Eliminated cache-related bugs
- Clear separation of concerns

**Issue**: #44

---

## Naming Conventions Evolution

### File Naming

**Before Oct 2025**:

- Mixed: `snake_case`, `PascalCase`, `ALL_CAPS`

**After Nov 2025**:

- Standard: `kebab-case` for all non-README files
- Exception: `README.md` (uppercase standard)

### Script Naming

**Before Nov 2025**:

- `validate_pattern_taxonomy.py` (unclear which paper)

**After Nov 2025**:

- `validate_p1_pattern_taxonomy.py` (Paper #1)
- `validate_p2_sequential_patterns.py` (Paper #2)

**Rationale**: See `docs/papers/adr/001-validation-script-naming.md`

### ADR Naming

**Paper #2 ADRs**:

- Before: `001_scope_boundaries.md` (underscores)
- After: `001-scope-boundaries.md` (hyphens)

**Cross-Paper ADRs**:

- Format: `###-descriptive-name.md`
- Location: `docs/papers/adr/`

---

## Architecture Evolution

### Paper #1 (Single-Day Framework)

**Core Design**:

- Single-day GEX snapshot at Day T
- Predict Day T+1 outcome
- WHO → WHOM → WHAT framework

**Components**:

- `MarketMechanicsAgent::run_experiment()`
- `build_single_day_prompt()`
- Pattern taxonomy: structural vs narrative

**Status**: ✅ Validated and submitted

### Paper #2 (Sequential Framework)

**Core Design**:

- 5-day GEX sequence (T-4 → T+0)
- Trajectory classification (accumulation, relief, reversal, persistent)
- Neutral prompt framework (bias-mitigated)

**Components**:

- `SequentialGEXFetcher`
- `build_sequential_prompt_neutral()`
- Negative controls validation

**Status**: 🔄 Phase 1 complete, Phase 2 pending

### Shared Infrastructure

**Stable Components**:

- `GEXCalculator` - Core GEX calculations
- `UnifiedCacheManager` - Caching system
- `OutcomeCalculator` - Forward returns/validation
- `DataObfuscator` - Date/ticker obfuscation
- Historical GEX database

**Extension Pattern**:

- Papers add functionality without forking
- Shared core = single source of truth for bug fixes
- Paper-specific modules clearly separated

**See**: `docs/papers/adr/002-architecture-separation.md`

---

## Future Roadmap

### Paper #3 (Cross-Asset Extension)

**Planned**:

- Multi-symbol analysis (SPY, QQQ, IWM)
- Cross-asset correlation
- Reuse sequential framework from Paper #2

**Status**: ⏸ Pending Paper #2 completion

### Repository Organization

**Current**: Single repo, extension pattern ✅

- Code reuse maximized
- Single CI/CD pipeline
- Paper #3 can build on P1 + P2

**Alternatives Considered**:

- Monorepo with subpackages (if 4+ papers)
- Git worktree (parallel development)
- Separate repos (only if fundamentally different codebases)

**Review Date**: After Paper #2 submission (Q1 2026)

---

## Deprecation Log

### Deprecated Files (Archived)

- `reports/VOLATILITY_DISCOVERY_SUMMARY.md` (Oct 11, 2025 - corrupt data)
- `reports/PHASE1_FAILURE_ANALYSIS.md` (Oct 11, 2025 - outdated analysis)
- Various Q1 2024 YAML backups (Oct 11, 2025 - corrupt outcomes)
- `docs/archive/checkpoint_oct2025_prompt_bias_investigation.md` (Oct 25, 2025 - superseded)

### Deprecated Naming

- `validate_pattern_taxonomy.py` → `validate_p1_pattern_taxonomy.py`
- `validate_all_patterns.py` → `validate_p1_all_patterns.py`
- `phd_symposium_2025.md` → `2025-symposium.md`
- `fundamentals_explained.md` → `fundamentals-explained.md`
- `technical_deep_dive.md` → `technical-deep-dive.md`

---

**Last Updated**: November 4, 2025
