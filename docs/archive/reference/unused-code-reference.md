# Unused Code Reference

**Last Updated**: October 12, 2025
**Maintained By**: Code Review Process (Issue #63)

This document tracks unused/orphaned code in the codebase that may be candidates for removal or archiving.

## Purpose

During code reviews, we sometimes discover code that:

- Was part of earlier experiments
- Has been superseded by better implementations
- Is not imported or used anywhere in the codebase

Rather than immediately deleting potentially useful code, we document it here for informed decision-making.

---

## `src/strategies/` - Unused Strategy Framework

**Status**: ✅ **REMOVED** - Deleted October 12, 2025
**Date Identified**: October 12, 2025
**Total Lines**: 799 lines (removed)
**Last Modified**: September 18, 2023
**Removal Commit**: Part of Issue #63 code review

### What It Is

An abstract base class framework for implementing versioned GEX trading strategies (V0-V4):

**Files**:

1. [src/strategies/base_gex_strategy.py](../src/strategies/base_gex_strategy.py) (293 lines)
   - Abstract base class `BaseGEXStrategy`
   - Dataclasses: `GEXSignal`, `StrategyMetrics`
   - Interface methods: `analyze_day()`, `prepare_batch_data()`, `backtest()`

2. [src/strategies/gex_strategy_v0.py](../src/strategies/gex_strategy_v0.py) (96 lines)
   - Basic implementation of `BaseGEXStrategy`
   - Version identifier: "V0"
   - Simple negative GEX trading logic

3. [src/strategies/gex_strategy_v2.py](../src/strategies/gex_strategy_v2.py) (410 lines)
   - Advanced implementation of `BaseGEXStrategy`
   - Version identifier: "V2"
   - More sophisticated GEX analysis

### Why It's Unused

**The actual baseline comparison (Issue #58) uses a completely different implementation:**

**Active Code**: [src/analysis/baseline_gex_strategy.py](../src/analysis/baseline_gex_strategy.py) (492 lines)

- Used by: [scripts/baseline_comparison/run_baseline_comparison.py](../scripts/baseline_comparison/run_baseline_comparison.py)
- Implements proper baseline strategies for Issue #58
- Loads configuration from `config_defaults/trading_config.yaml`
- Actually called by production scripts

### Verification

```bash
# Search for any imports of strategies module
grep -r "from.*strategies.*import\|import.*strategies" \
  --include="*.py" src/ scripts/

# Result: No imports found (except within strategies/ folder itself)
```

The `BaseGEXStrategy` class name appears only in:

- [src/analysis/baseline_gex_strategy.py](../src/analysis/baseline_gex_strategy.py) - but as `BaselineGEXStrategy` (different class)

### History

Based on file timestamps (Sept 18, 2023), this appears to be an **early experiment** for a "continuous experiment framework" that was **superseded** by the cleaner implementation in `src/analysis/baseline_gex_strategy.py`.

The abstract base class approach (V0-V4 versioning) was likely intended for A/B testing multiple strategy versions, but the project pivoted to:

1. **Issue #79**: LLM-based pattern detection (not mechanical strategies)
2. **Issue #58**: Simple baseline comparison (doesn't need abstract framework)

### Options

#### Option 1: Archive (Recommended)

Move to `docs/archive/unused_strategies/` with:

- All three files
- README explaining why it was superseded
- Link to this document

**Pros**:

- Preserves historical context
- Can be referenced if needed
- Removes clutter from active codebase

**Cons**:

- None (git history still preserves everything)

#### Option 2: Delete

Simply remove the folder and files.

**Pros**:

- Cleaner codebase
- Less confusion for new developers
- Git history preserves everything if needed later

**Cons**:

- Less immediately accessible if context is needed

#### Option 3: Keep As-Is

Leave the code in place.

**Pros**:

- No action needed
- Might be useful someday

**Cons**:

- ⚠️ Creates confusion (developers may think it's active code)
- ⚠️ Adds maintenance burden (linting, imports, etc.)
- ⚠️ Clutters codebase

### Decision Made

**✅ Option 2: Delete - COMPLETED October 12, 2025**

**Rationale**:

- Completely unused (verified no imports anywhere)
- Superseded by cleaner implementation in `src/analysis/baseline_gex_strategy.py`
- Git history preserves all code if needed later
- Reduces codebase clutter and confusion
- Part of Issue #63 code review cleanup

**What was removed**:

- `src/strategies/base_gex_strategy.py` (293 lines)
- `src/strategies/gex_strategy_v0.py` (96 lines)
- `src/strategies/gex_strategy_v2.py` (410 lines)
- **Total**: 799 lines removed

**Recovery if needed**: Code is preserved in git history at commit prior to Issue #63 completion.

---

## Decision Process

Before removing or archiving code:

1. **✅ Verify it's unused** - No imports anywhere in codebase
2. **✅ Check git history** - Understand why it was created
3. **✅ Identify replacement** - Find what superseded it (if applicable)
4. **✅ Document decision** - Add to this file
5. **✅ Archive or remove** - Based on historical value

## Archive Commands

```bash
# Create archive directory
mkdir -p docs/archive/unused_strategies

# Move files
mv src/strategies/*.py docs/archive/unused_strategies/

# Create README in archive
cat > docs/archive/unused_strategies/README.md << 'EOF'
# Unused Strategies - Archived Oct 12, 2025

**Original Location**: `src/strategies/`
**Reason for Archival**: Superseded by `src/analysis/baseline_gex_strategy.py`
**See**: [docs/UNUSED_CODE_REFERENCE.md](../../UNUSED_CODE_REFERENCE.md)

This code was part of an early experiment for versioned strategy testing
that was superseded when the project pivoted to LLM-based pattern detection.
EOF

# Remove empty directory
rmdir src/strategies
```

---

## Notes

- This document is **living documentation** - update as code is reviewed
- Always check git history before removing code
- Preserve context for future developers
- When in doubt, archive rather than delete
