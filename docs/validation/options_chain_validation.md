# Options Chain Quality Validation (Issue #16)

Comprehensive data quality validation at database ingress ensures high-quality options data for GEX calculations and research.

## Overview

The `OptionsChainValidator` validates options chain data before storage in the SQLite database, filtering bad records and tracking quality scores.

## Features

### Critical Checks (Reject Records)

- **Bid ≤ Ask**: No arbitrage violations
- **Call Delta**: Must be in [0, 1]
- **Put Delta**: Must be in [-1, 0]
- **Gamma ≥ 0**: Non-negative for long options
- **Strike > 0**: Positive strike prices
- **Open Interest ≥ 0**: Non-negative OI

### Warning Checks (Flag but Store)

- **IV Range**: 1% to 500% (configurable)
- **Theta Sign**: Should be ≤ 0 for long options

### Quality Scoring (0.0 - 1.0)

Weighted scoring based on:

- **Greeks Coverage** (30%): Presence of delta, gamma, theta, vega
- **Pricing Coverage** (20%): Valid bid/ask data
- **IV Quality** (20%): IV within reasonable range
- **No Critical Issues** (30%): No critical validation failures

## Usage

### Automatic Validation (Default)

All data stored via `SQLiteOptionsManager` is automatically validated:

```python
from src.cache.sqlite_options_manager import SQLiteOptionsManager

# Validation enabled by default
manager = SQLiteOptionsManager()

# Store options chain - automatically validated
inserted = manager.store_options_chain("SPY", "2024-01-15", options_df)
# Returns number of records inserted (bad records filtered out)
```

### Manual Validation

Validate without storing:

```python
from src.validation.options_chain_validator import OptionsChainValidator

validator = OptionsChainValidator()
result = validator.validate(options_df, "SPY", "2024-01-15")

print(f"Quality score: {result.quality_score:.3f}")
print(f"Valid records: {result.valid_records}")
print(f"Rejected: {result.rejected_records}")
print(f"Passed: {result.passed}")

for issue in result.issues:
    print(f"[{issue.severity.value}] {issue.check_name}: {issue.message}")
```

### Validate and Filter

Get filtered DataFrame with only valid records:

```python
validator = OptionsChainValidator()
filtered_df, result = validator.validate_and_filter(options_df, "SPY", "2024-01-15")

# filtered_df contains only valid records
# result contains validation details
```

### Disable Validation

For raw data storage without validation:

```python
manager = SQLiteOptionsManager(enable_validation=False)
# OR
manager.store_options_chain("SPY", "2024-01-15", df, skip_validation=True)
```

## Configuration

Edit `config_defaults/data_sources_config.yaml`:

```yaml
validation:
  enabled: true

  critical:
    bid_ask_tolerance: 0.0     # bid must be <= ask
    call_delta_min: 0.0
    call_delta_max: 1.0
    put_delta_min: -1.0
    put_delta_max: 0.0
    gamma_min: 0.0
    strike_min: 0.0
    oi_min: 0

  warning:
    iv_min: 0.01               # 1%
    iv_max: 5.0                # 500%
    theta_max: 0.0
    threshold_pct: 5.0         # >5% violations = warning

  quality_weights:
    greeks_coverage: 0.30
    pricing_coverage: 0.20
    iv_quality: 0.20
    no_critical_issues: 0.30

  behavior:
    reject_on_critical: true   # Reject entire chain if critical issues
    min_quality_score: 0.5     # Minimum acceptable quality
    log_warnings: true
    store_validation_score: true
```

### Custom Configuration

Override defaults programmatically:

```python
custom_config = {
    "call_delta_min": 0.0,
    "call_delta_max": 1.0,
    "gamma_min": 0.0,
    "reject_on_critical": False,  # Store bad records with flags
}

manager = SQLiteOptionsManager(validation_config=custom_config)
```

## Validation Results

### ValidationResult Object

```python
result.symbol              # Symbol validated
result.trading_date        # Trading date validated
result.total_records       # Total records in input
result.valid_records       # Records passing validation
result.rejected_records    # Records rejected
result.flagged_records     # Records with warnings
result.quality_score       # 0.0-1.0 quality score
result.passed              # True if no critical issues
result.critical_count      # Number of critical issues
result.warning_count       # Number of warnings
result.issues              # List of ValidationIssue objects
```

### ValidationIssue Object

```python
issue.check_name           # Name of check that failed
issue.severity             # CRITICAL, WARNING, or INFO
issue.message              # Human-readable description
issue.field_name           # Field that failed (optional)
issue.field_value          # Value that failed (optional)
```

## Quality Score Tracking

Quality scores are stored in the database:

```python
# Query validation quality
progress = manager.get_collection_progress("SPY")
print(progress[['trading_date', 'validation_quality_score']])

# Database stats include quality metrics
stats = manager.get_database_stats()
```

## Testing

Run validation tests:

```bash
python scripts/validation/test_options_chain_validation.py
```

Expected output:

```text
Testing OptionsChainValidator (Issue #16)
  Test 1: Basic Validation - PASS
  Test 2: Validate and Filter - PASS
  Test 3: Good Data Only - PASS
  Test 4: Empty DataFrame - PASS
  Test 5: Convenience Function - PASS

Testing SQLite Integration
  Validation Enabled: 0 records stored (9 rejected)
  Validation Disabled: 9 records stored
  PASS: Validation correctly filtered bad records

FINAL RESULTS
  Validator tests: PASS
  SQLite integration: PASS
```

## Integration Points

### Data Collection Scripts

All collection scripts automatically benefit:

- `scripts/data_collection/collect_leveraged_etfs.py`
- `scripts/data_collection/collect_sequential_gex.py`
- `scripts/data_collection/collect_buffered_mode.py`

### Agent Tools

AutoGen tools (`src/tools/autogen_tools.py`) use validated storage:

```python
sqlite_options = SQLiteOptionsManager(enable_validation=True)
```

### API Clients

Alpha Vantage client (`src/data_sources/alpha_vantage_gex.py`) data is validated when stored.

## Troubleshooting

### All Records Rejected

Check validation logs:

```python
import logging
logging.getLogger("src.validation.options_chain_validator").setLevel(logging.DEBUG)
logging.getLogger("src.cache.sqlite_options_manager").setLevel(logging.DEBUG)
```

Common causes:

- **Bid > Ask**: Quote timing issues from API
- **Delta out of range**: Deep ITM/OTM options may have delta near bounds
- **Negative gamma**: Data corruption or API error

Solution: Check raw data quality, adjust thresholds, or use `skip_validation=True` for known-good data.

### Low Quality Scores

Quality score < 0.5 indicates:

- Missing Greeks data (delta, gamma, theta, vega)
- Missing pricing data (bid, ask)
- IV data out of reasonable range
- Some critical violations

Review data source quality and consider API upgrade if persistent.

### Performance Issues

Validation adds ~0.1ms per record overhead. For large datasets:

- Use batch inserts (already optimized in SQLiteOptionsManager)
- Consider disabling validation for known-good historical data
- Validation is thread-safe and supports concurrent operations

## Best Practices

1. **Keep Validation Enabled**: Default behavior ensures data quality
2. **Monitor Quality Scores**: Track trends in `validation_quality_score` column
3. **Review Warnings**: Warning-level issues may indicate data quality degradation
4. **Adjust Thresholds**: Tune validation config for your data source
5. **Test Changes**: Run validation tests after config changes

## Files

- **Validator**: `src/validation/options_chain_validator.py`
- **Integration**: `src/cache/sqlite_options_manager.py`
- **Config**: `config_defaults/data_sources_config.yaml`
- **Tests**: `scripts/validation/test_options_chain_validation.py`
- **This Doc**: `docs/validation/options_chain_validation.md`

## References

- **Issue #16**: [GitHub Issue](https://github.com/iAmGiG/gex-llm-patterns/issues/16)
- **Implementation Comment**: [Completion Details](https://github.com/iAmGiG/gex-llm-patterns/issues/16#issuecomment-3672182249)
