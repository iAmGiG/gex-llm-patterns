# Bug Report: Zero GEX Values in Batch Validation

**Date**: November 22, 2025
**Severity**: Critical
**Status**: Root cause identified, fix pending

## Summary

Batch validation reads $0.00B for all GEX values despite correct file cache data containing values like -$17.87B.

## Reproduction

1. Export database GEX data to file cache (has `total_gex` field)
2. Run batch validation with file cache fallback
3. LLM receives $0.00B for all 30 days in window

## Root Cause

**File**: `src/cache/gex_cache_manager.py:274-278`

```python
# Add compatibility aliases for legacy file cache data
# File cache (2020) has 'net_gex' but prompt builder expects 'net_gex_usd'
# Database (2024) already adds this alias in the query mapping above
if 'net_gex' in data and 'net_gex_usd' not in data:
    data['net_gex_usd'] = data['net_gex']
```

**Problem Flow**:

1. File cache exported from database has this structure:

   ```json
   {
     "total_gex": -17867256434.204144,
     "net_call_gex": -9884526457.990332,
     "net_put_gex": -7982729976.213814,
     ...
   }
   ```

2. Code checks `if 'net_gex' in data` → **FALSE** (file has `total_gex`)

3. No `net_gex_usd` alias created

4. Prompt builder (`src/llm/mechanics_prompt_builder.py:387`) expects:

   ```python
   net_gex_b = day['net_gex_usd'] / 1e9
   ```

5. KeyError or default to 0 → LLM sees $0.00B

## Evidence

**File Cache Data** (`.cache/gex_data/SPY/2021-01-06/gex_summary.json`):

```json
{
  "total_gex": -17867256434.204144,
  ...
}
```

**Batch Input** (`batch_regime_20251122_164817.jsonl`):

```
Day T-29: +0.00B
Day T-28: +0.00B
...
(all 30 days show $0.00B)
```

**Validation Output**:

```
Window 2021-01-06:
  avg_magnitude_billions: 0.0
  positive_days: 0
  negative_days: 0
  Detection: False (magnitude fails $5B threshold)
```

## Why 2025 Worked

Batch `69223088f1688190be0e398337285cb1` (2025) achieved 100% detection because:

- 2025 data exists in database `gex_database.db`
- Database query path (lines 217-259) correctly maps `total_gex → net_gex_usd`
- File cache fallback never triggered

## Impact

**Affected Batches** (2021-2023 with file cache fallback):

- `batch_69222fa2df488190a68fa4c2b75a5776` (2021: 0.0% detection)
- `batch_69222ffaa6408190a14701dccc39b425` (2022: 0.0% detection)
- `batch_69223048df5481908bba882d0a2f1ac5` (2023: 0.0% detection)

**Total Cost Wasted**: $11.26 (750 windows × $0.015/window)

## Proposed Fix

**File**: `src/cache/gex_cache_manager.py:274-285`

```python
# Add compatibility aliases for file cache data
# File cache may have 'total_gex' (database export) or 'net_gex' (legacy)
# Prompt builder expects 'net_gex_usd'
if 'net_gex_usd' not in data:
    if 'net_gex' in data:
        data['net_gex_usd'] = data['net_gex']
    elif 'total_gex' in data:
        data['net_gex_usd'] = data['total_gex']
        # Also create net_gex alias for consistency
        data['net_gex'] = data['total_gex']
```

**Alternative Fix**: Update export script to write `net_gex` instead of `total_gex`

## Database Field Mapping

**Database** (`daily_gex_metrics` table):

- `total_gex` = Net gamma exposure (sum of calls + puts)

**File Cache** (should have):

- `total_gex` OR `net_gex` = Same value as database `total_gex`
- `net_gex_usd` = Alias for prompt builder compatibility

**Code Expectation**:

- Prompt builder: `net_gex_usd` (line 387)
- Database query: Maps `total_gex → net_gex_usd` (line 241)
- File cache: Currently missing this mapping for `total_gex`

## Testing Plan

1. Apply fix to `gex_cache_manager.py`
2. Test with 2021-01-06 window:

   ```python
   fetcher.get_sequential_gex('SPY', '2021-01-06')
   # Should return net_gex_usd = -17867256434.204144
   ```

3. Resubmit 2021-2023 batches
4. Verify detection rates are non-zero with proper GEX magnitudes

## Related Issues

- Issue #140: Multi-year validation (affected by this bug)
- Export script: `/tmp/export_gex_to_file_cache.py` (generates `total_gex`)
- Database schema: `total_gex` is canonical field name
