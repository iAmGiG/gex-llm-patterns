# Validation Framework Documentation

## Overview

The Validation Framework provides systematic testing of LLM market mechanics interpretation capability using historical market events. It includes data obfuscation to prevent training data leakage and ensure unbiased validation.

## Core Components

### MechanicsValidationDataset

**Location**: `src/validation/mechanics_validation_dataset.py`

The main orchestrator for historical market event validation testing.

```python
class MechanicsValidationDataset:
    """
    Curated dataset of historical market mechanics events for LLM validation.

    Features:
    - 6 curated historical events (GME squeeze, COVID crash, etc.)
    - Normal vs obfuscated validation modes
    - Accuracy scoring against expected mechanics
    - Results saved to reports/validation_experiments/
    """
```

#### Key Methods

```python
# Validate single event
def validate_event(self, event: MechanicsEvent, use_cached_data: bool = True, obfuscate_data: bool = False) -> ValidationResult:
    """
    Args:
        event: Historical market event to analyze
        use_cached_data: Use cached data for faster processing
        obfuscate_data: Apply data obfuscation to prevent training data leakage

    Returns:
        ValidationResult with LLM analysis and accuracy assessment
    """

# Process all events
def run_full_validation(self, use_cached_data: bool = True) -> Dict[str, Any]:
    """Run validation against all curated events"""

# Get specific event
def get_event_by_id(self, event_id: str) -> Optional[MechanicsEvent]:
    """Retrieve event by ID (e.g., 'covid_crash_2020')"""
```

#### Convenience Functions

```python
# Quick single event testing
def quick_validate_event(event_id: str, use_cache: bool = True, obfuscate_data: bool = False) -> ValidationResult:
    """
    One-line validation testing

    Example:
        result = quick_validate_event("covid_crash_2020", obfuscate_data=True)
    """
```

## Historical Events Dataset

### Curated Events

1. **GameStop Squeeze (GME)** - January 2021
   - **Event ID**: `gme_squeeze_2021`
   - **Type**: `gamma_squeeze`
   - **Expected Mechanics**: Retail → Market Makers → Hedge Funds forced covering
   - **Date Range**: 2021-01-11 to 2021-01-28

2. **Tesla Gamma Rally (TSLA)** - August 2020
   - **Event ID**: `tsla_gamma_2020`
   - **Type**: `gamma_squeeze`
   - **Expected Mechanics**: Options flow driving hedging amplification
   - **Date Range**: 2020-08-11 to 2020-08-28

3. **AMC Squeeze (AMC)** - May 2021
   - **Event ID**: `amc_squeeze_2021`
   - **Type**: `gamma_squeeze`
   - **Expected Mechanics**: Similar retail-driven gamma mechanics as GME
   - **Date Range**: 2021-05-24 to 2021-06-02

4. **COVID Crash (SPY)** - March 2020
   - **Event ID**: `covid_crash_2020`
   - **Type**: `crash_rehedging`
   - **Expected Mechanics**: Put hedging → dealer selling feedback loops
   - **Date Range**: 2020-03-09 to 2020-03-23

5. **OPEX Pinning (SPY)** - March 2021
   - **Event ID**: `opex_pin_mar2021`
   - **Type**: `opex_pinning`
   - **Expected Mechanics**: Market makers actively managing to key strikes
   - **Date Range**: 2021-03-15 to 2021-03-19

6. **VIX Spike (SPY)** - February 2018
   - **Event ID**: `vix_spike_2018`
   - **Type**: `volatility_unwind`
   - **Expected Mechanics**: Volatility product unwinding forces systematic selling
   - **Date Range**: 2018-02-02 to 2018-02-09

### Event Structure

```python
@dataclass
class MechanicsEvent:
    event_id: str                           # Unique identifier
    symbol: str                             # Trading symbol (SPY, GME, etc.)
    start_date: str                         # Start date (YYYY-MM-DD)
    end_date: str                           # End date (YYYY-MM-DD)
    event_type: str                         # Event category
    documented_mechanics: Dict[str, str]    # Expected WHO/WHOM/WHAT mechanics
    expected_llm_response: str              # Expected LLM interpretation
    confidence_threshold: float = 0.75      # Minimum confidence for success
    data_availability: Optional[Dict] = None # Data tracking metadata
```

## Validation Protocol

### Academic Validation (Default)

**Purpose**: Unbiased testing, prevents training data leakage
**Benefit**: Validates genuine analytical capability
**Usage**: Default behavior - no parameter needed

```python
# Standard academic validation (obfuscated by default)
result = quick_validate_event("covid_crash_2020")
# LLM input: "INDEX_1 Day T+0" - must analyze raw GEX data
```

### Development Validation (Debugging Only)

**Purpose**: Rapid development and debugging
**Risk**: May use training data knowledge
**Usage**: `obfuscate_data=False` (not recommended for research)

```python
# Development/debugging only - NOT for research
result = quick_validate_event("covid_crash_2020", obfuscate_data=False)
# LLM input: "SPY March 2020" - may recognize famous COVID crash
```

### Data Obfuscation Process

1. **Date Transformation**: "2020-03-09" → "Day T+0"
2. **Ticker Transformation**: "SPY" → "INDEX_1", "GME" → "STOCK_G"
3. **Context Removal**: Remove temporal references (COVID, Fed events, years)
4. **Reversible Mapping**: Maintain mappings for result interpretation

## Accuracy Scoring

### Scoring Methodology

```python
def _score_llm_response(self, llm_analysis: Dict, expected_mechanics: Dict, expected_response: str) -> tuple[float, bool]:
    """
    Score LLM response against expected market mechanics.

    Scoring Components (25% each):
    1. WHO identification accuracy
    2. WHOM identification accuracy
    3. WHAT identification accuracy
    4. Confidence level (≥70% threshold)

    Returns:
        (accuracy_score, matches_expected) tuple
        - accuracy_score: 0.0-1.0 float
        - matches_expected: Boolean (≥60% threshold)
    """
```

### Success Criteria

- **80%+ Accuracy**: LLM correctly identifies market mechanics
- **Specificity**: Identifies WHO forces WHOM (not just "volatility increased")
- **Predictive Power**: Correctly anticipates forced actions
- **Pattern Recognition**: Connects similar mechanics across events

### Training Data Leakage Detection

Compare normal vs obfuscated validation:

- **Large Difference**: Indicates training data leakage
- **Similar Results**: Indicates genuine analytical capability
- **Obfuscated = 0%**: LLM relies entirely on memorized knowledge

## Results Organization

### File Structure

Results saved to `reports/validation_experiments/`:

```
validation_experiments/
├── README.md                                    # Usage documentation
├── covid_crash_2020_20250914_220456.json      # Individual result (JSON)
├── validation_results_20250914_220456.jsonl   # Streaming results (JSONL)
├── validation_summary_20250914_220456.json    # Full experiment summary
└── validation_results_legacy.jsonl            # Historical results
```

### Result Structure

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
  "validation_framework_version": "1.0",
  "timestamp": "2025-09-14T21:48:22.123456"
}
```

## Usage Examples

### Basic Validation

```python
from src.validation.mechanics_validation_dataset import quick_validate_event

# Standard academic validation (default - obfuscated)
result = quick_validate_event("covid_crash_2020")
print(f"Academic validation accuracy: {result.accuracy_score:.1%}")

# Compare with development validation to detect training data leakage
development = quick_validate_event("covid_crash_2020", obfuscate_data=False)
academic = quick_validate_event("covid_crash_2020")  # Default obfuscated

print(f"Development accuracy: {development.accuracy_score:.1%}")
print(f"Academic accuracy: {academic.accuracy_score:.1%}")

# Difference indicates training data leakage
leakage = development.accuracy_score - academic.accuracy_score
print(f"Training data leakage detected: {leakage:.1%}")
```

### Full Dataset Validation

```python
from src.validation.mechanics_validation_dataset import MechanicsValidationDataset

dataset = MechanicsValidationDataset()

# Run all events with academic rigor (default - obfuscated)
summary = dataset.run_full_validation()

print(f"Academic validation - Overall accuracy: {summary['avg_accuracy']:.1%}")
print(f"Events matching expected mechanics: {summary['match_rate']:.1%}")
print(f"Total events tested: {summary['total_events']}")

# Optional: Compare with development validation to assess training data dependency
dev_summary = dataset.run_full_validation(obfuscate_data=False)
print(f"Development validation accuracy: {dev_summary['avg_accuracy']:.1%}")
print(f"Training data dependency: {dev_summary['avg_accuracy'] - summary['avg_accuracy']:.1%}")
```

### Compare Different LLM Models

```python
# Test with different LLM providers
from src.agents.market_mechanics_agent import MarketMechanicsAgent

# Test Model A
agent_a = MarketMechanicsAgent(llm_provider=model_a)
dataset_a = MechanicsValidationDataset()
dataset_a.agent = agent_a
results_a = dataset_a.run_full_validation()

# Test Model B
agent_b = MarketMechanicsAgent(llm_provider=model_b)
dataset_b = MechanicsValidationDataset()
dataset_b.agent = agent_b
results_b = dataset_b.run_full_validation()

# Compare performance
print(f"Model A accuracy: {results_a['avg_accuracy']:.1%}")
print(f"Model B accuracy: {results_b['avg_accuracy']:.1%}")
```

## Integration with Market Mechanics Agent

The validation framework integrates with the Market Mechanics Agent to test LLM interpretation:

```python
# Internal validation workflow
def _analyze_event_period(self, event: MechanicsEvent) -> Dict[str, Any]:
    """Analyze event period using MarketMechanicsAgent."""

    # Set agent to analyze event symbol
    self.agent.symbol = event.symbol

    # Parse analysis date (handles obfuscated dates)
    analysis_date = parse_date_string(event.start_date)

    # Get LLM analysis
    analysis_result = self.agent.daily_analysis(analysis_date)

    return analysis_result
```

## Best Practices

### Academic/Research Phase (Default)

- Use obfuscated validation (default behavior) for rigor
- Ensures genuine analytical capability testing
- Prevents training data contamination criticism
- Suitable for publication and peer review

### Development Phase (When Needed)

- Use development validation (`obfuscate_data=False`) sparingly
- Only for system debugging and rapid iteration
- Not recommended for research or performance claims
- Always compare with academic validation

### Production Phase

- Primarily use academic validation for system confidence
- Monitor performance with obfuscated data over time
- Optional: Track development vs academic performance gap
- Use academic results for business decisions

## Troubleshooting

### Common Issues

1. **Date Parsing Errors**
   - **Symptom**: "Unable to parse date string: Day T+0"
   - **Solution**: Enhanced `parse_date_string()` in `date_utils.py` handles obfuscated dates

2. **No LLM Response**
   - **Symptom**: `{"error": "No LLM interpretation generated"}`
   - **Solution**: Check LLM initialization and API keys

3. **Low Accuracy Scores**
   - **Expected**: Obfuscated validation typically shows lower scores
   - **Analysis**: Compare normal vs obfuscated to identify training data dependency

4. **Missing Historical Data**
   - **Symptom**: Warnings about missing options data
   - **Expected**: Historical data often unavailable, system falls back to sample data

### Data Availability

The framework handles missing historical data gracefully:

- **Primary**: Fetch from cache/API
- **Fallback**: Use sample data for testing
- **Result**: Validation framework functionality maintained regardless

## Research Applications

### Academic Validation

- Use obfuscated validation for publication
- Prevents criticism of training data contamination
- Demonstrates genuine analytical capability

### LLM Benchmarking

- Compare different models systematically
- Quantify improvements in market mechanics understanding
- Track progress over time

### Market Intelligence Research

- Validate WHO/WHOM/WHAT framework effectiveness
- Study different types of market mechanics
- Build confidence in trading applications

---

**The validation framework ensures the LLM understands market microstructure mechanics rather than memorizing famous market events, providing confidence for both research and trading applications.**
