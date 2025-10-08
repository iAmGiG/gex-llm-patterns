# Reports Directory

This directory contains various analysis reports and experimental results organized by purpose and audience.

## Structure

```
reports/
├── validation/              # System validation and testing reports
│   ├── pattern_taxonomy/   # Pattern taxonomy validation (Issue #79, Oct 2025)
│   ├── pattern_taxonomy_DEPRECATED_ISSUE81/  # Deprecated: obfuscation bug (Oct 2025)
│   ├── mc_reports/         # Main Chat validation reports (Sep 2025)
│   └── daily_tests/        # Daily testing results and raw data
├── experiments/            # Individual experiment results (YAML format)
├── archive/               # Historical reports and deprecated analyses
│   ├── current/           # Previous active reports
│   └── archived_experiments/  # Historical development iterations
└── README.md              # This documentation
```

## Current Reports by Category

### 🔬 **Pattern Taxonomy Validation** (`validation/pattern_taxonomy/`)
**Purpose:** Issue #79 - Validate mechanical patterns using obfuscation testing

**Status:** ⏳ IN PROGRESS - Re-validating with corrected obfuscation (Issue #81 fix)

Pattern validation results testing WHO forces WHOM to do WHAT:
- **Obfuscation:** LLM receives "Day T+0" instead of "2024-01-02"
- **Test Period:** Q1 2024 (53 trading days, post-training cutoff)
- **Threshold:** ≥60% detection rate with ≥30 samples

**⚠️ IMPORTANT:** Previous results moved to `pattern_taxonomy_DEPRECATED_ISSUE81/` due to obfuscation bug discovered Oct 7, 2025. See that directory's README for details.

### 🎯 **System Validation** (`validation/mc_reports/`)
**Purpose:** Comprehensive validation for Main Chat requirements

- **`MC_COMPREHENSIVE_VALIDATION_FINAL.md`** - Complete system validation summary
- **`MC_EXECUTIVE_SUMMARY.md`** - High-level system overview and capabilities
- **`MC_TESTING_METHODOLOGY.md`** - How validation testing was conducted
- **`MC_VALIDATION_REPORT.md`** - Technical validation details and evidence
- **`MC_DAILY_0DTE_VALIDATION_*.md`** - Daily 0DTE frequency test results

### 📊 **Test Data** (`validation/daily_tests/`)
**Purpose:** Raw test datasets and detailed performance metrics

- **`mc_validation_detailed_*.json`** - Complete test datasets with signal generation data
- Daily testing logs and performance breakdowns

### 🧪 **Experiments** (`experiments/`)
**Purpose:** Individual experiment results in standardized YAML format

- **Pattern detection experiments** with obfuscated data
- **LLM analysis results** with WHO/WHOM/WHAT mechanics
- **GEX calculation validation** with real market data

### 📚 **Archive** (`archive/`)
**Purpose:** Historical research and development documentation

- **`current/`** - Previous active reports (model comparisons, configuration fixes)
- **`archived_experiments/`** - Evolution from aggregate to strike-level GEX analysis

## Report Naming Convention

- **`MC_*`** - Reports for Main Chat validation and review
- **`experiment_*`** - Individual experiment results
- **`validation_*`** - System testing and validation results
- **`archive_*`** - Historical or deprecated content

## Key Findings Summary

✅ **System Operational** - Pattern classification framework working with LLM reasoning
✅ **21 Signals/Month** - Exceeds 15-20 target for daily 0DTE opportunities
✅ **Quality Controls** - Properly filters invalid patterns to prevent false positives
✅ **Research Ready** - Can answer "What's happening?" and "Does X lead to Y?" questions

All reports use obfuscated data to prevent memorization and ensure objective analysis.
