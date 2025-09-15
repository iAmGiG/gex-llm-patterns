# Validation Experiments Directory

## Purpose

This directory contains results from LLM market mechanics validation experiments, testing the system's ability to correctly identify market dynamics and participant behavior.

## File Structure

### Individual Experiment Results (JSON)

```
{event_id}_{timestamp}.json - Individual validation result with full analysis
```

**Example**: `covid_crash_2020_20250914_220456.json`

### Streaming Results (JSONL)

```
validation_results_{timestamp}.jsonl - Streaming experiment log (one result per line)
```

**Example**: `validation_results_20250914_220456.jsonl`

### Summary Reports (JSON)

```
validation_summary_{timestamp}.json - Full experiment summary with statistics
```

## Experiment Types

### Normal Validation

- **File Pattern**: `{event_id}_{timestamp}.json`
- **Description**: LLM sees real dates and tickers (e.g., "SPY March 2020")
- **Purpose**: Development testing and baseline capabilities
- **Risk**: May use training data knowledge rather than genuine analysis

### Obfuscated Validation

- **File Pattern**: `{event_id}_obfuscated_{timestamp}.json`
- **Description**: LLM sees anonymous data (e.g., "INDEX_1 Day T+0")
- **Purpose**: Unbiased testing, prevents training data leakage
- **Benefit**: Validates genuine analytical capability

## Key Fields in Results

### ValidationResult Structure

```json
{
  "event_id": "covid_crash_2020",
  "llm_response": {
    "mechanics_interpretation": {
      "who": "Identified forcing party",
      "whom": "Identified forced party",
      "what": "Specific forced action",
      "confidence": 80
    }
  },
  "expected_mechanics": {
    "who": "Put hedging flows",
    "forces": "Dealers",
    "what": "Forced selling into declining market"
  },
  "accuracy_score": 0.75,
  "matches_expected": true,
  "experiment_type": "obfuscated",
  "timestamp": "2025-09-14T21:48:22.123456"
}
```

## Usage Examples

### Analyze Single Event

```python
from src.validation.mechanics_validation_dataset import quick_validate_event

# Normal validation (development)
result = quick_validate_event("covid_crash_2020", obfuscate_data=False)

# Obfuscated validation (unbiased)
result = quick_validate_event("covid_crash_2020", obfuscate_data=True)
```

### Compare Normal vs Obfuscated

```python
from src.validation.mechanics_validation_dataset import MechanicsValidationDataset

dataset = MechanicsValidationDataset()
event = dataset.get_event_by_id("covid_crash_2020")

# Run both types
normal_result = dataset.validate_event(event, obfuscate_data=False)
obfuscated_result = dataset.validate_event(event, obfuscate_data=True)

# Compare accuracy scores
print(f"Normal: {normal_result.accuracy_score:.1%}")
print(f"Obfuscated: {obfuscated_result.accuracy_score:.1%}")
```

## Historical Events Dataset

### Curated Events

1. **GameStop Squeeze** (GME, Jan 2021) - Retail → MM → Hedge Fund mechanics
2. **Tesla Gamma Rally** (TSLA, Aug 2020) - Options flow driving hedging amplification
3. **AMC Squeeze** (AMC, May 2021) - Similar retail-driven gamma mechanics
4. **COVID Crash** (SPY, Mar 2020) - Put hedging → dealer selling feedback loops
5. **OPEX Pinning** (SPY, Mar 2021) - MM actively managing to key strikes
6. **VIX Spike** (SPY, Feb 2018) - Volatility product unwinding forces

### Expected Mechanics

Each event has documented:

- **WHO**: The forcing party (retail, institutions, dealers)
- **FORCES**: The party being forced to act
- **WHAT**: The specific forced action that occurs
- **OUTCOME**: The resulting market dynamics

## Success Criteria

### Accuracy Metrics

- **80%+ Accuracy**: LLM correctly identifies market mechanics
- **Specificity**: LLM identifies WHO forces WHOM (not just "volatility increased")
- **Predictive Power**: LLM correctly anticipates forced actions
- **Pattern Recognition**: LLM connects similar mechanics across events

### Training Data Leakage Detection

Compare normal vs obfuscated validation:

- **Large Difference**: Indicates training data leakage
- **Similar Results**: Indicates genuine analytical capability
- **Obfuscated = 0%**: LLM relies entirely on memorized knowledge

## File Naming Convention

### Timestamp Format

`YYYYMMDD_HHMMSS` - ISO format for easy sorting

### Event IDs

- `gme_squeeze_2021` - GameStop gamma squeeze
- `covid_crash_2020` - COVID market crash
- `opex_pin_mar2021` - OPEX pinning dynamics
- `vix_spike_2018` - Volatility spike event

### Experiment Types

- No suffix: Normal validation
- `_obfuscated`: Data obfuscation applied

## Analysis Guidelines

### Data Quality Assessment

1. Check `accuracy_score` for quantitative performance
2. Review `matches_expected` for binary success
3. Examine `analysis_notes` for detailed comparison
4. Compare `experiment_type` results for bias detection

### Research Applications

- **Academic Papers**: Use obfuscated validation for rigor
- **Development**: Use normal validation for speed
- **Production**: Monitor both types for system health
- **Benchmarking**: Compare different LLM models/prompts

## Legacy Files

### validation_results_legacy.jsonl

Contains original validation results before restructuring. Format may differ from current structure.

---

**Note**: This validation system proves the LLM understands market microstructure mechanics, not just price patterns. By testing WHO forces WHOM to do WHAT, we validate genuine market intelligence vs superficial pattern recognition.
