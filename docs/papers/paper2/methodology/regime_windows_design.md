# Paper #2: 30-Day Regime Windows - Design Document

**Date**: November 5, 2025
**Status**: Design Phase
**Related Issues**: #89, #107

---

## Executive Summary

**Pivot Decision**: Moving from 5-day trajectory analysis (98-100% detection) to 30-day regime windows (30-50% expected detection).

**Rationale**:
- 5-day windows detect daily hedging flows (always present, not research-worthy)
- 30-day windows detect persistent regimes (sometimes present, meaningful structure)

**Research Question**:
> "Can LLMs identify persistent market regimes from dealer gamma positioning, and how did 0DTE proliferation (2020→2024) change regime persistence?"

---

## Methodology Design

### Regime Classification Framework

#### Definition: Persistent Regime

A **persistent regime** is a 30-day window where dealer gamma constraints remain stable:
- **Persistent Positive**: >70% of days (21+/30) have positive net GEX
- **Persistent Negative**: >70% of days (21+/30) have negative net GEX

#### Non-Regimes (Rejected Patterns)

- **Transitional**: Frequent GEX sign flips, no dominant direction
- **Low Conviction**: Consistent but weak magnitude (<$5B average)

### Regime Metrics

```python
def calculate_regime_metrics(gex_data_30d):
    """
    Calculate 30-day regime characteristics.

    Args:
        gex_data_30d: List of 30 daily GEX observations

    Returns:
        dict with regime metrics
    """
    # Sign persistence
    positive_days = sum(1 for d in gex_data_30d if d['net_gex'] > 0)
    negative_days = 30 - positive_days
    persistence_pct = max(positive_days, negative_days) / 30 * 100

    # Magnitude metrics
    avg_magnitude = np.mean([abs(d['net_gex']) for d in gex_data_30d])
    min_magnitude = min([abs(d['net_gex']) for d in gex_data_30d])
    max_magnitude = max([abs(d['net_gex']) for d in gex_data_30d])

    # Stability metrics
    gex_std = np.std([d['net_gex'] for d in gex_data_30d])
    coefficient_of_variation = gex_std / avg_magnitude if avg_magnitude > 0 else 0

    # Sign flips (regime transitions)
    sign_flips = sum(1 for i in range(1, 30)
                     if np.sign(gex_data_30d[i]['net_gex']) !=
                        np.sign(gex_data_30d[i-1]['net_gex']))

    return {
        'positive_days': positive_days,
        'negative_days': negative_days,
        'persistence_pct': persistence_pct,
        'avg_magnitude': avg_magnitude,
        'min_magnitude': min_magnitude,
        'max_magnitude': max_magnitude,
        'std_magnitude': gex_std,
        'coefficient_of_variation': coefficient_of_variation,
        'sign_flips': sign_flips,
        'regime_type': classify_regime(positive_days, negative_days, avg_magnitude)
    }


def classify_regime(positive_days, negative_days, avg_magnitude):
    """
    Classify regime type based on persistence and magnitude.
    """
    # Persistence threshold
    PERSISTENCE_THRESHOLD = 21  # 70% of 30 days
    MAGNITUDE_THRESHOLD = 5e9   # $5B

    if positive_days >= PERSISTENCE_THRESHOLD:
        if avg_magnitude >= MAGNITUDE_THRESHOLD:
            return "persistent_positive"
        else:
            return "low_conviction_positive"

    elif negative_days >= PERSISTENCE_THRESHOLD:
        if avg_magnitude >= MAGNITUDE_THRESHOLD:
            return "persistent_negative"
        else:
            return "low_conviction_negative"

    else:
        return "transitional"
```

---

## LLM Prompt Design

### Regime Detection Prompt (v1 Draft)

```
You are a market structure analyst specializing in dealer gamma positioning regimes.

TASK: Analyze this 30-day period and determine if it represents a PERSISTENT regime.

30-DAY GEX DATA:
{30 days of obfuscated GEX data with Day T-29 through Day T+0}

REGIME CLASSIFICATION CRITERIA:

1. PERSISTENT POSITIVE REGIME (Detect):
   - >70% of days (21+/30) have positive net GEX
   - Average magnitude >$5B
   - Dealers are long gamma, forced to sell into strength

2. PERSISTENT NEGATIVE REGIME (Detect):
   - >70% of days (21+/30) have negative net GEX
   - Average magnitude >$5B
   - Dealers are short gamma, forced to buy into weakness

3. TRANSITIONAL (Reject):
   - Frequent sign flips between positive/negative
   - No dominant regime direction
   - Market in regime change period

4. LOW CONVICTION (Reject):
   - Consistent sign but weak magnitude (<$5B avg)
   - Insufficient constraint to create persistent flows

ANALYSIS QUESTIONS:

1. What percentage of days show the same GEX sign?
2. What is the average GEX magnitude?
3. How many sign flips occurred across 30 days?
4. Does this represent a PERSISTENT regime or should it be rejected?

OUTPUT FORMAT (JSON):
{
    "regime_detected": true/false,
    "regime_type": "persistent_positive|persistent_negative|transitional|low_conviction",
    "positive_days": <count>,
    "negative_days": <count>,
    "avg_magnitude_billions": <value>,
    "sign_flips": <count>,
    "confidence": 0-100,
    "reasoning": "Why this is/isn't a persistent regime"
}

CONFIDENCE CALIBRATION:
- 90-100: Very persistent (25+ days same sign, >$10B avg, <2 flips)
- 70-89: Moderately persistent (21-24 days same sign, $5-10B avg, 2-4 flips)
- 50-69: Borderline (18-20 days same sign, $3-5B avg, 5-7 flips)
- 0-49: Not persistent (reject)
```

---

## Implementation Plan

### Step 1: Modify SequentialGEXFetcher

**Current**: Fetches 5-day windows (T-4 through T+0)
**New**: Fetch 30-day windows (T-29 through T+0)

**Changes Needed**:

```python
# src/data_sources/sequential_gex_fetcher.py

class SequentialGEXFetcher:
    def __init__(self, window_size: int = 30, ...):  # Changed from 5
        """
        Fetches sequential GEX windows for regime analysis.

        Args:
            window_size: Number of days in regime window (default 30)
        """
        self.window_size = window_size
        # ... rest of init

    def fetch_regime_window(self, end_date: str) -> Optional[List[Dict]]:
        """
        Fetch 30-day GEX sequence ending on end_date.

        Returns None if insufficient data (need 30+ trading days before end_date).
        """
        # Get 30 trading days before (and including) end_date
        trading_days = self._get_trading_days_before(
            symbol=self.symbol,
            end_date=end_date,
            n_days=self.window_size
        )

        if len(trading_days) < self.window_size:
            logger.warning(f"Insufficient data for 30-day window ending {end_date}")
            return None

        # Fetch GEX for all 30 days
        gex_sequence = []
        for day in trading_days:
            gex_data = self._fetch_single_day_gex(day)
            if gex_data is None:
                logger.warning(f"Missing GEX data for {day}")
                return None
            gex_sequence.append(gex_data)

        return gex_sequence
```

### Step 2: Create RegimeClassifier Module

**New file**: `src/validation/regime_classifier.py`

```python
"""
Regime classification for 30-day GEX windows.
Replaces 5-day trajectory analysis.
"""

import numpy as np
from typing import Dict, List, Optional


class RegimeClassifier:
    """
    Classifies 30-day GEX windows into regime types.
    """

    # Thresholds
    PERSISTENCE_THRESHOLD = 0.70  # 70% of days same sign
    MAGNITUDE_THRESHOLD = 5e9     # $5B average GEX
    MAX_SIGN_FLIPS = 5            # Max flips for persistent regime

    def __init__(self):
        pass

    def classify_window(self, gex_sequence: List[Dict]) -> Dict:
        """
        Classify 30-day GEX window into regime type.

        Args:
            gex_sequence: List of 30 daily GEX observations

        Returns:
            Classification dict with regime metrics
        """
        if len(gex_sequence) != 30:
            raise ValueError(f"Expected 30 days, got {len(gex_sequence)}")

        # Calculate metrics
        metrics = self._calculate_metrics(gex_sequence)

        # Classify regime
        regime_type = self._classify_regime_type(metrics)

        return {
            'regime_type': regime_type,
            'metrics': metrics,
            'is_persistent': regime_type in ['persistent_positive', 'persistent_negative']
        }

    def _calculate_metrics(self, gex_sequence: List[Dict]) -> Dict:
        """Calculate regime metrics from 30-day sequence."""

        gex_values = [d['net_gex'] for d in gex_sequence]

        positive_days = sum(1 for v in gex_values if v > 0)
        negative_days = 30 - positive_days

        avg_magnitude = np.mean([abs(v) for v in gex_values])
        gex_std = np.std(gex_values)

        # Count sign flips
        sign_flips = sum(
            1 for i in range(1, 30)
            if np.sign(gex_values[i]) != np.sign(gex_values[i-1])
        )

        return {
            'positive_days': positive_days,
            'negative_days': negative_days,
            'persistence_pct': max(positive_days, negative_days) / 30 * 100,
            'avg_magnitude': avg_magnitude,
            'std_magnitude': gex_std,
            'sign_flips': sign_flips
        }

    def _classify_regime_type(self, metrics: Dict) -> str:
        """Determine regime type from metrics."""

        pos_days = metrics['positive_days']
        neg_days = metrics['negative_days']
        avg_mag = metrics['avg_magnitude']
        flips = metrics['sign_flips']

        # Check for persistent positive
        if pos_days >= 21 and avg_mag >= self.MAGNITUDE_THRESHOLD and flips <= self.MAX_SIGN_FLIPS:
            return "persistent_positive"

        # Check for persistent negative
        if neg_days >= 21 and avg_mag >= self.MAGNITUDE_THRESHOLD and flips <= self.MAX_SIGN_FLIPS:
            return "persistent_negative"

        # Check for low conviction
        if (pos_days >= 21 or neg_days >= 21) and avg_mag < self.MAGNITUDE_THRESHOLD:
            return "low_conviction"

        # Otherwise transitional
        return "transitional"
```

### Step 3: Update Validation Script

**Modify**: `scripts/validation/validate_sequential_patterns.py`

```python
# Change imports
from src.validation.regime_classifier import RegimeClassifier

# Update validator init
class SequentialPatternValidator:
    def __init__(
        self,
        symbol: str = "SPY",
        window_size: int = 30,  # Changed from 5
        calculate_outcomes: bool = True
    ):
        self.symbol = symbol
        self.window_size = window_size

        # Initialize components
        self.gex_fetcher = SequentialGEXFetcher(
            symbol=symbol,
            window_size=window_size
        )
        self.regime_classifier = RegimeClassifier()
        # ...

# Update validation loop
def validate_regime_windows(self, dates, ...):
    """Validate 30-day regime windows."""

    for end_date in dates:
        # Fetch 30-day window
        gex_sequence = self.gex_fetcher.fetch_regime_window(end_date)

        if gex_sequence is None:
            logger.warning(f"Skipping {end_date} - insufficient data")
            continue

        # Pre-classify regime (deterministic)
        regime_classification = self.regime_classifier.classify_window(gex_sequence)

        # Build LLM prompt with 30-day data
        prompt = self.prompt_builder.build_regime_prompt(
            gex_sequence=gex_sequence,
            end_date=end_date
        )

        # Get LLM classification
        llm_response = self.llm_agent.analyze_regime(prompt)

        # Compare LLM vs deterministic classification
        detection = {
            'end_date': end_date,
            'deterministic_regime': regime_classification['regime_type'],
            'llm_regime': llm_response['regime_type'],
            'llm_confidence': llm_response['confidence'],
            'agreement': regime_classification['regime_type'] == llm_response['regime_type'],
            'metrics': regime_classification['metrics']
        }

        detections.append(detection)
```

---

## Expected Outcomes

### Q1 2024 (Phase 1 Quick Validation)

**Dataset**: 61 trading days (Jan 2 - Mar 29, 2024)
**Potential 30-day windows**: 32 windows (each day can be end of window)

**Expected regime classification**:
- Persistent negative: 1-2 windows (Q1 had strong negative GEX)
- Transitional: 20-25 windows (regime stability varies)
- Low conviction: 5-10 windows (weaker periods)

**Expected LLM detection rate**: 60-80% (LLM detects 1-2 persistent regimes)

### Full 2024 (Phase 2)

**Dataset**: 252 trading days
**Potential 30-day windows**: ~223 windows

**Expected regime classification**:
- Persistent regimes: 4-8 windows
- Transitional: 150-180 windows
- Low conviction: 30-50 windows

**Expected LLM detection rate**: 30-50%

### 2020 Comparison (Phase 3)

**Dataset**: 252 trading days (pre-0DTE era)
**Expected regime classification**:
- Persistent regimes: 2-4 windows (weaker constraints)
- Transitional: 180-200 windows
- Low conviction: 40-60 windows

**Expected LLM detection rate**: 20-30% (lower than 2024)

**Hypothesis**: 0DTE proliferation → stronger regime persistence

---

## Success Criteria

### Methodology Validation

1. **Selectivity**: Detection rate 30-50% (not 98-100%)
2. **Regime Discrimination**: LLM agrees with deterministic classifier 70%+ of the time
3. **Temporal Evolution**: 2024 detection > 2020 detection (0DTE effect)
4. **Negative Controls**: All pass (shuffled <20%, transitions <10%)

### Research Contribution

**Novel Finding**:
> "LLM-based regime analysis identifies persistent dealer gamma constraints (30-day stability >70%) with 30-50% selectivity, distinguishing structural regimes from transitional periods. 0DTE option proliferation (2020→2024) increased regime persistence by XX% (p<0.05)."

**Sets up Paper #3**:
- Regime boundaries identified (30-day windows)
- Cross-asset sector rotation analysis
- Regime transition signals

---

## Timeline

**Week 1 (Nov 4-8)**: Implementation
- Modify SequentialGEXFetcher for 30-day windows
- Create RegimeClassifier module
- Design regime detection prompt
- Update validation script

**Week 2 (Nov 11-15)**: Phase 1 + Phase 2
- Q1 2024 quick validation
- Full 2024 validation
- Initial results analysis

**Week 3 (Nov 18-22)**: Phase 3
- 2020 validation
- 0DTE proliferation analysis
- Statistical comparison (2020 vs 2024)

**Week 4 (Nov 25-29)**: Negative Controls
- Shuffled regime windows
- Synthetic transitions
- Low-magnitude persistent windows

**Week 5 (Dec 2-6)**: Paper Writing
- Methodology section
- Results section
- Discussion (0DTE effect)

---

## Files to Create/Modify

### New Files
- `src/validation/regime_classifier.py` - Regime classification logic
- `docs/papers/paper2/methodology/regime_windows_design.md` - This document
- `docs/papers/paper2/prompts/regime_detection_v1.md` - LLM prompt

### Modified Files
- `src/data_sources/sequential_gex_fetcher.py` - Support 30-day windows
- `scripts/validation/validate_sequential_patterns.py` - Regime validation
- `src/llm/mechanics_prompt_builder.py` - Add regime prompt builder

### Configuration
- `config_defaults/analysis_config.yaml` - Add regime thresholds

---

## Risk Mitigation

### Risk 1: Detection rate still too high (>70%)

**Mitigation**: Increase persistence threshold to 80% (24/30 days)

### Risk 2: Detection rate too low (<15%)

**Mitigation**: Decrease persistence threshold to 60% (18/30 days)

### Risk 3: 2020 ≈ 2024 detection (no 0DTE effect)

**Mitigation**: Alternative hypothesis - regime persistence independent of 0DTE volume

### Risk 4: Negative controls fail

**Mitigation**: Re-calibrate prompt confidence thresholds

---

## Next Steps (Immediate)

1. ✅ Create this design document
2. Create RegimeClassifier module
3. Modify SequentialGEXFetcher for 30-day windows
4. Design regime detection prompt (v1)
5. Run Phase 1 quick validation (Q1 2024)

**Priority**: HIGH - Core methodology for Paper #2

Date: November 5, 2025
