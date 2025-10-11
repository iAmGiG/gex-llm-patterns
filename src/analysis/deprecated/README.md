# Deprecated Analysis Files

These files have been deprecated due to dependencies on an old database schema that no longer exists in the current system.

## Deprecation Reason

The current system stores pattern validation results in YAML files (`reports/validation/pattern_taxonomy/*.yaml`), not in a database. These files assume:
- `pattern_detections` table (doesn't exist)
- `fed_context` table (doesn't exist)
- `daily_gex_metrics` table (may exist but structure changed)

## Deprecated Files

### 1. pattern_analyzer.py (191 lines, 3 SQL queries)
**Purpose**: Simple pattern analyzer using database queries

**Issues**:
- Lines 34-72: Queries `pattern_detections` table
- Assumes old schema with confidence scoring in database
- Not integrated with current validation framework

**Replacement**: Use validation YAML files directly or `baseline_comparison.py`

### 2. trading_rules_generator.py (272 lines, 1 SQL query)
**Purpose**: Generate trading rules from pattern statistics

**Issues**:
- Lines 27-51: Queries `pattern_detections` and `fed_context` tables
- Line 118-202: LLM prompt generation not integrated with current agent
- Assumes patterns stored in database

**Replacement**: Use `validated_trading_engine.py` with Issue #79 validation results

### 3. pattern_probability_mapper.py (361 lines, 1 SQL query)
**Purpose**: Analyze historical patterns and calculate probabilities

**Issues**:
- Lines 279-308: Placeholder methods with incomplete implementation
- Lines 286-307: Simplified SQL assumes old schema
- Line 38: Warning suppression suggests performance issues

**Replacement**: Use `statistical_validator.py` and validation YAML files

## Migration Path

If you need functionality from these files:

1. **Pattern Analysis**: Use `baseline_comparison.py._load_validation_results()` to load from YAML
2. **Trading Rules**: Update `validated_trading_engine.py` with dynamic values from Issue #79
3. **Probability Mapping**: Use `statistical_validator.py` with validation results

## Date Deprecated

October 11, 2025 (Issue #82)

## Related Issues

- #82 - Refactor src/analysis/ folder
- #79 - Pattern Taxonomy Validation (provides YAML format)
- #58 - Baseline Comparison (now uses YAML)
