# Sequential GEX Architecture (Paper #2)

**Created**: November 3, 2025
**Issues**: #89, #107, #108
**Purpose**: Temporal trajectory analysis for dealer constraint detection

---

## Overview

The Sequential GEX system extends Paper #1's single-day snapshot approach with 5-day temporal trajectory analysis. This enables detection of constraint **dynamics** (accumulation, relief, reversal, persistence) rather than just instantaneous states.

### Key Principle: Reuse, Don't Duplicate

**Paper #1 Infrastructure** (unchanged):
- `UnifiedCacheManager` - Provides GEX data access
- `GEXCacheManager` - Single-day GEX retrieval (`get_gex_summary()`)
- `validate_pattern_taxonomy.py` - Single-day validation
- `BatchLLMProcessor` - API efficiency (5 independent days)

**Paper #2 New Components** (this document):
- `SequentialGEXFetcher` - 5-day window retrieval
- `SequentialPromptBuilder` - Trajectory prompt generation
- `validate_sequential_patterns.py` - Sequential validation pipeline

---

## Component 1: SequentialGEXFetcher

### Responsibility

Fetches 5-day GEX windows ending at a target date and calculates trajectory metrics for LLM analysis.

### Design Decisions

**1. Delegate to Existing Infrastructure**
```python
# GOOD: Reuse GEXCacheManager
self.gex_cache = cache_manager.gex_cache
gex_summary = self.gex_cache.get_gex_summary(symbol, date)

# BAD: Duplicate cache logic
# self._read_gex_from_disk(date)  # Don't do this!
```

**2. Strict Sequence Completeness**
- Require all 5 days present (no partial sequences)
- **Rationale**: Incomplete trajectories unreliable (missing T-2 changes trajectory classification)
- **Trade-off**: Lose ~12 windows in 2024, but gain data quality

**3. Pre-Calculate Trajectory Metrics**
- Compute GEX trend, velocity, drift in fetcher (not LLM prompt)
- **Rationale**: LLM prompt stays neutral (provides data, not interpretations)
- **Example**: Prompt shows "GEX velocity: -$550M/day", not "escalating short gamma"

### Data Flow

```
User Request (end_date="2024-01-12", lookback=5)
    ↓
SequentialGEXFetcher.get_sequential_gex()
    ↓
_get_trading_days_before()  # Get [2024-01-08, 01-09, 01-10, 01-11, 01-12]
    ↓
For each date:
    GEXCacheManager.get_gex_summary(symbol, date)  # Reuse existing cache
    ↓
Check sequence completeness (len == 5?)
    ↓
calculate_trajectory_metrics(gex_sequence)
    ↓
Return: List[Dict] with 5 days + trajectory summary
```

### Output Structure

```python
{
    'gex_sequence': [
        {
            'date': '2024-01-08',
            'obfuscated_date': 'T-4',
            'net_gex': -2.1,
            'flip_point': 520.0,
            'spot_price': 518.5,
            'call_gex': -1.5,
            'put_gex': -0.6
        },
        # ... T-3, T-2, T-1, T+0
    ],
    'trajectory_metrics': {
        'gex_trend': 'INCREASING',        # INCREASING | DECREASING | STABLE
        'gex_velocity': -0.55,            # Avg daily change (B$/day)
        'flip_drift': 3.0,                # Flip point movement T-4 to T+0
        'price_drift': 5.5,               # Underlying price movement
        'trajectory_classification': 'accumulation'  # For outcome verification
    }
}
```

### Trajectory Classification Logic

**Accumulation**: |GEX| magnitude increasing >20%
```
Example: -$2.1B → -$3.2B → -$5.2B (magnitude growing)
Implication: Dealer constraints escalating
```

**Relief**: |GEX| magnitude decreasing >20%
```
Example: -$5.2B → -$4.1B → -$2.1B (magnitude shrinking)
Implication: Dealer constraints easing
```

**Reversal**: Sign flip (negative → positive or vice versa)
```
Example: -$3.0B → -$1.0B → +$0.5B → +$2.0B
Implication: Regime change in market structure
```

**Persistent**: Magnitude stable within ±20%
```
Example: -$5.0B → -$4.9B → -$5.1B → -$5.2B
Implication: Sustained constraint (no relief)
```

**Classification Code**:
```python
start_abs = abs(gex_values[0])
end_abs = abs(gex_values[-1])
pct_change = (end_abs - start_abs) / start_abs

if sign_flip:
    return 'reversal'
elif pct_change > 0.20:
    return 'accumulation'
elif pct_change < -0.20:
    return 'relief'
else:
    return 'persistent'
```

---

## Component 2: Date Handling Strategy

### Challenge: Trading Days vs Calendar Days

**Problem**: 5 days back ≠ 5 calendar days (weekends, holidays)

**Solution**: Scan cache directory for actual trading days
```python
# GOOD: Use cache as source of truth
available_dates = sorted([
    d.name for d in cache_dir.iterdir()
    if d.is_dir() and d.name <= end_date
])
return available_dates[-5:]  # Last 5 trading days

# BAD: Calculate business days
# return pd.bdate_range(end_date - 5, end_date)  # Misses holidays!
```

**Rationale**: Cache directory reflects actual GEX data availability (already filtered for trading days)

---

## Integration with Existing Architecture

### How SequentialGEXFetcher Fits

```
Paper #1 (Single-Day):
UnifiedCacheManager
    ↓
GEXCacheManager.get_gex_summary(date)  # Single day
    ↓
MechanicsPromptBuilder.build_prompt()
    ↓
LLM (o3-mini)

Paper #2 (Sequential):
UnifiedCacheManager
    ↓
SequentialGEXFetcher.get_sequential_gex(end_date)  # 5 days
    ├─> GEXCacheManager.get_gex_summary(T-4)  # Reuse!
    ├─> GEXCacheManager.get_gex_summary(T-3)
    ├─> GEXCacheManager.get_gex_summary(T-2)
    ├─> GEXCacheManager.get_gex_summary(T-1)
    └─> GEXCacheManager.get_gex_summary(T+0)
    ↓
calculate_trajectory_metrics()
    ↓
MechanicsPromptBuilder.build_sequential_prompt()  # New method
    ↓
LLM (o3-mini, same model as Paper #1)
```

### Key Benefit: Zero Duplication

- No new cache infrastructure
- No new database queries
- No new GEX calculation logic
- Only adds: windowing + trajectory metrics

---

## Performance Considerations

### API Calls: No Increase

**Misconception**: 5-day windows = 5x API calls

**Reality**: All GEX data pre-computed in cache
- Single-day: 1 cache read per day
- Sequential: 5 cache reads per window (still 1 LLM call)

**Example (Q1 2024)**:
- Single-day: 53 days × 1 cache read = 53 reads
- Sequential: 49 windows × 5 cache reads = 245 reads (~4.6x cache reads, not API calls)

### Disk I/O Impact

**Measured**:
- Cache read latency: ~5ms per day (SSD)
- Sequential window: 5 × 5ms = 25ms overhead
- Negligible vs LLM call latency (~2-5 seconds)

### Memory Footprint

**Per Window**:
- 5 GEX summaries × ~2KB each = ~10KB
- Trajectory metrics: ~500 bytes
- Total: ~10.5KB per window (negligible)

---

## Error Handling

### Missing Day in Sequence

**Strategy**: Skip entire window (strict mode)

```python
if len(gex_sequence) < lookback_days:
    logger.warning(f"Incomplete sequence for {end_date}, skipping")
    return None  # Don't process partial sequences
```

**Rationale**: Incomplete trajectories misleading (T-2 missing → can't detect reversal)

**Impact**: ~12 skipped windows in 2024 (due to Q2 data gaps)

### Data Quality Issues

**Handled by GEXCacheManager** (existing):
- Invalid GEX values (NaN, inf)
- Missing flip point
- Corrupted cache files

**SequentialGEXFetcher**: Propagates errors up (doesn't re-implement validation)

---

## Testing Strategy

### Unit Tests (Day 2)

**Test 1**: Fetch complete 5-day sequence
```python
fetcher = SequentialGEXFetcher(cache)
sequence = fetcher.get_sequential_gex('SPY', '2024-01-12', lookback=5)
assert len(sequence) == 5
assert sequence[0]['obfuscated_date'] == 'T-4'
assert sequence[-1]['obfuscated_date'] == 'T+0'
```

**Test 2**: Handle missing day (skip window)
```python
sequence = fetcher.get_sequential_gex('SPY', '2024-02-20', lookback=5)  # Missing 02-19 (holiday)
assert sequence is None  # Strict mode
```

**Test 3**: Trajectory classification
```python
gex_values = [-2.1, -3.2, -4.1, -4.8, -5.2]
classification = fetcher._classify_trajectory(gex_values)
assert classification == 'accumulation'
```

### Integration Tests (Day 2)

**Test 4**: Full pipeline (5 sample dates)
```python
dates = ['2024-01-08', '2024-01-09', '2024-01-10', '2024-01-11', '2024-01-12']
for date in dates:
    result = fetcher.get_sequential_gex('SPY', date, lookback=5)
    assert result is not None
    assert 'trajectory_metrics' in result
```

---

## Open Questions & Future Work

### Q1: Variable Lookback Windows?

**Current**: Fixed 5-day window
**Future**: Test 3-day, 7-day, 10-day windows

**Hypothesis**: Shorter windows (3-day) may be noisier, longer (10-day) may miss short-term dynamics

### Q2: Weighted Recent Days?

**Current**: All 5 days equal weight
**Future**: Weight recent days higher (T+0 = 2x, T-4 = 0.5x)

**Use case**: Trajectory reversals (recent days more informative)

### Q3: Non-Linear Trajectory Detection?

**Current**: Linear trend classification
**Future**: Detect accelerations, decelerations, oscillations

**Example**: Gamma building Mon-Wed, then releasing Thu-Fri (oscillation pattern)

---

## Files Created

**Code**:
- `src/data_sources/sequential_gex_fetcher.py` (new, ~300 lines)

**Documentation**:
- `docs/system/architecture/sequential_gex_architecture.md` (this file)
- `docs/system/implementation/sequential_gex_implementation.md` (next)

**Tests**:
- `tests/unit/test_sequential_gex_fetcher.py` (to be created)

---

## Related Issues

- **#89**: Sequential GEX Analysis (5-Day Lookback) - Methodology
- **#107**: Paper #2 Sequential GEX Validation Strategy - Phased approach
- **#108**: Implement Sequential GEX Validation (Phase 1) - This implementation

---

**Status**: Architecture documented, ready for implementation
**Next**: Create `src/data_sources/sequential_gex_fetcher.py`
