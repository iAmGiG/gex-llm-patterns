# Reports Directory

This directory contains validation reports and historical archives.

> **Note:** This README captures directory state as of October 2025. For the latest validation results see the published papers ([Paper 1 — IEEE BigData 2025](../docs/papers/paper1/), [Paper 2 — AIAI 2026 accepted / JRFM under review](../docs/papers/paper2/)).

## Structure (October 11, 2025)

```
reports/
├── validation/              # System validation and testing reports
│   ├── pattern_taxonomy/   # Pattern taxonomy validation (Issue #79, Oct 2025)
│   ├── pattern_taxonomy_DEPRECATED_ISSUE81/  # Deprecated: obfuscation bug (Oct 2025)
│   └── daily_tests/        # Daily testing results and raw data
├── archive/               # Historical reports and deprecated analyses
│   └── archived_experiments/  # Historical development iterations
└── README.md              # This documentation
```

**Note**: All validation YAML files are gitignored and generated locally. Corrupt Q1-Q3 YAMLs (based on 450.0 database) deleted Oct 11, 2025 - will be regenerated with corrected database.

## Current Status (October 11, 2025)

### 🔬 **Pattern Taxonomy Validation** (`validation/pattern_taxonomy/`)

**Purpose:** Issue #79 - Validate `dealer_gamma_hedging` pattern across Q1-Q4 2024

**Status:** 🔄 RE-VALIDATING - Database rebuilt with REAL prices (no more 450.0!)

**Critical Fix Applied:**

- **Problem**: Database stored obfuscated 450.0 prices → corrupt forward returns (42.77% Q3 max)
- **Fix**: `historical_gex_builder.py` now uses put-call parity + API, refuses fake prices
- **Impact**: All Q1-Q3 validation YAMLs deleted (corrupt), regenerating with corrected database

**Validation Framework:**

- **Obfuscation:** LLM receives "Day T+0" instead of real dates
- **Pattern**: `dealer_gamma_hedging` (consolidated from 3 patterns)
- **Test Period**: Q1-Q4 2024 (198 dates with real spot prices)
- **Threshold:** ≥60% detection rate with ≥30 samples

**Background Jobs Running:**

- Q1 2024: Re-validation with corrected database
- Q2 2024: Partial (Jun only, Apr-May missing from cache)
- Q3 2024: Re-validation in progress
- Q4 2024: Pending data collection completion

### 📚 **Archive** (`archive/`)

Historical reports and deprecated analyses:

- **`archived_experiments/`** - Evolution from aggregate to strike-level GEX analysis

### ⚠️ **Deprecated** (`validation/pattern_taxonomy_DEPRECATED_ISSUE81/`)

Previous validation results (obfuscation bug discovered Oct 7, 2025). See that directory's README for details.

---

## Key Findings (Q1 2024 - Validated)

✅ **Pattern Consolidation** - Three patterns (gamma_positioning, stock_pinning, 0dte_hedging) are identical
✅ **90.38% Predictive Accuracy** - dealer_gamma_hedging pattern on 53 trading days
✅ **+0.70% Net Alpha** - After 5bps transaction costs
✅ **100% Detection Rate** - Pattern detected on all negative GEX days

## Data Quality Issues Resolved

❌ **Database Corruption (Fixed Oct 11, 2025)** - Hardcoded 450.0 obfuscation stored permanently

- **Impact**: Q3 showed impossible 42.77% daily moves (SPY doesn't move that much!)
- **Root Cause**: Storage layer violated separation of concerns (obfuscation should be analysis-only)
- **Fix**: Database rebuilt with real prices using put-call parity estimation
- **See**: `docs/guides/database-corruption-fix-status.md` for full postmortem

---

*All reports use obfuscated data at analysis time to prevent LLM memorization. Database now stores REAL market data only.*
