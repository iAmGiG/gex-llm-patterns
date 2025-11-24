# Data Obfuscation Documentation

## Overview

The Data Obfuscation System prevents LLM training data leakage during validation by converting real market data to anonymous equivalents. This ensures unbiased testing of genuine analytical capability rather than memorized knowledge.

## Problem Statement

### Training Data Leakage Risk

When testing LLMs on famous market events:

- **"GameStop January 2021"** → LLM recognizes famous squeeze from training data
- **"COVID crash March 2020"** → LLM recalls documented market mechanics
- **"Tesla August 2020"** → LLM knows about the stock split rally

**Result**: LLM appears to perform well but is actually "cheating" using memorized knowledge rather than analyzing GEX data.

### Evidence of Leakage

Our testing revealed clear evidence:

```bash
Normal Validation (SPY March 2020):
- WHO: Retail traders
- WHAT: Dealers forced to sell at $1190 flip point
- Confidence: High detail and specific price levels

Obfuscated Validation (INDEX_1 Day T+0):
- WHO: Not identified
- WHAT: Not identified
- Confidence: 0% - no analysis possible
```

**The dramatic difference proves training data contamination.**

## Core Components

### DataObfuscator Class

**Location**: `src/validation/data_obfuscation.py`

```python
class DataObfuscator:
    """
    Obfuscates market data to prevent LLM from using training knowledge.

    Key transformations:
    - Dates: "2022-07-26" → "Day T+0", "Day T+1", etc.
    - Tickers: "SPY" → "INDEX_1", "AAPL" → "STOCK_A", etc.
    - Context: Remove market event references
    """
```

#### Key Methods

```python
def obfuscate_dates(self, date_list, base_date=None):
    """
    Convert real dates to relative timestamps.

    Example:
        Input: ["2020-03-09", "2020-03-10", "2020-03-11"]
        Output: {"2020-03-09": "Day T+0", "2020-03-10": "Day T+1", "2020-03-11": "Day T+2"}
    """

def obfuscate_tickers(self, ticker_list):
    """
    Convert real tickers to anonymous symbols.

    Example:
        Input: ["SPY", "AAPL", "MSFT"]
        Output: {"SPY": "INDEX_1", "AAPL": "STOCK_A", "MSFT": "STOCK_B"}
    """

def obfuscate_text_content(self, text) -> str:
    """
    Remove temporal and market context from text.

    Removes:
    - Specific dates and years
    - Market event references (COVID, Fed)
    - Real ticker symbols
    """
```

### Standard Mappings

```python
standard_tickers = {
    'SPY': 'INDEX_1',           # S&P 500 ETF
    'AAPL': 'STOCK_A',          # Apple
    'MSFT': 'STOCK_B',          # Microsoft
    'GOOGL': 'STOCK_C',         # Google
    'AMZN': 'STOCK_D',          # Amazon
    'NVDA': 'STOCK_E',          # Nvidia
    'META': 'STOCK_F',          # Meta
    'TSLA': 'STOCK_G',          # Tesla
    'VXX': 'VOLATILITY_INDEX'   # VIX ETF
}
```

## Obfuscation Process

### Date Transformation

Real dates are converted to relative timestamps based on the event start date:

```python
# Event: COVID crash starting March 9, 2020
original_dates = ["2020-03-09", "2020-03-10", "2020-03-11", "2020-03-12"]

obfuscated_dates = {
    "2020-03-09": "Day T+0",    # Event start (base date)
    "2020-03-10": "Day T+1",    # Day 1 after
    "2020-03-11": "Day T+2",    # Day 2 after
    "2020-03-12": "Day T+3"     # Day 3 after
}
```

### Ticker Transformation

```python
# GameStop squeeze example
original: "GME analysis for January 28, 2021"
obfuscated: "STOCK_G analysis for Day T+17"

# COVID crash example
original: "SPY during March 2020 crash"
obfuscated: "INDEX_1 during Day T+0 to T+14 period"
```

### Context Removal

```python
def obfuscate_text_content(self, text) -> str:
    """Remove temporal and market context."""

    # Temporal patterns removed:
    temporal_patterns = [
        (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', 'Period A'),
        (r'\bCOVID[-\s]19\b', 'Economic Event A'),
        (r'\bpandemic\b', 'Economic Event A'),
        (r'\b(Fed|Federal Reserve)\b', 'Central Bank'),
        (r'\b\d{4}\b', 'YEAR'),  # Remove any remaining years
    ]
```

## Integration with Validation Framework

### Automatic Obfuscation

The validation framework automatically applies obfuscation when requested:

```python
def validate_event(self, event: MechanicsEvent, obfuscate_data: bool = False) -> ValidationResult:
    """
    Validate LLM interpretation with optional data obfuscation.

    Args:
        obfuscate_data: Whether to obfuscate dates/tickers to prevent training data leakage
    """

    if obfuscate_data:
        event_for_analysis = self._apply_obfuscation(event)
        logger.info(f"Data obfuscated: {event.symbol} → {event_for_analysis.symbol}")
    else:
        event_for_analysis = event
```

### MarketMechanicsAgent Integration (Issue #81 Fix)

**IMPORTANT**: As of October 7, 2025, the `run_experiment()` method in `MarketMechanicsAgent` now supports proper obfuscation:

```python
# src/agents/market_mechanics_agent.py
def run_experiment(self,
                   experiment_description: str,
                   date: str = "2024-06-28",
                   obfuscate: bool = False) -> Dict:
    """
    Run flexible experiment based on natural language description.

    Args:
        experiment_description: Natural language experiment request
        date: Date for analysis (REAL date for data fetching)
        obfuscate: If True, strip dates/tickers from LLM prompts (anti-cheating)

    Returns:
        Experiment results with optional obfuscation metadata
    """

    if obfuscate:
        # Step 1: Obfuscate dates/tickers BEFORE LLM sees them
        obfuscator = DataObfuscator()
        date_mapping = obfuscator.obfuscate_dates([date])
        ticker_mapping = obfuscator.obfuscate_tickers([self.symbol])

        obfuscated_date = date_mapping[date]
        obfuscated_ticker = ticker_mapping[self.symbol]

        # Replace in experiment description
        experiment_description_llm = experiment_description.replace(date, obfuscated_date)
        experiment_description_llm = experiment_description_llm.replace(self.symbol, obfuscated_ticker)

        # Step 2: Use REAL date for data fetching (cache needs real dates)
        experiment_data = self._execute_tool_plan(tool_plan, date)

        # Step 3: Use OBFUSCATED description for LLM analysis
        result = self._analyze_experiment_results(experiment_description_llm, ...)

        # Step 4: Add metadata
        result['obfuscation_metadata'] = {
            'obfuscated': True,
            'real_date': date,
            'obfuscated_date': obfuscated_date,
            'real_ticker': self.symbol,
            'obfuscated_ticker': obfuscated_ticker
        }
```

**Critical Separation**:

- **LLM-facing data**: Uses obfuscated dates/tickers ("Day T+0", "INDEX_1")
- **Cache-facing data**: Uses real dates for data retrieval ("2024-01-02")

This ensures the LLM cannot use training knowledge while still accessing correct market data.

### Obfuscation Application

```python
def _apply_obfuscation(self, event: MechanicsEvent) -> MechanicsEvent:
    """Apply data obfuscation to prevent LLM training data leakage."""

    obfuscator = DataObfuscator()

    # Create date range for the event
    event_dates = pd.date_range(
        start=event.start_date,
        end=event.end_date,
        freq='D'
    ).strftime('%Y-%m-%d').tolist()

    # Obfuscate dates and ticker
    date_mapping = obfuscator.obfuscate_dates(event_dates, event.start_date)
    ticker_mapping = obfuscator.obfuscate_tickers([event.symbol])

    # Create obfuscated event
    obfuscated_event = MechanicsEvent(
        event_id=f"{event.event_id}_obfuscated",
        symbol=ticker_mapping[event.symbol],
        start_date=date_mapping[event.start_date],
        end_date=date_mapping[event.end_date],
        event_type=event.event_type,
        documented_mechanics=event.documented_mechanics,  # Keep original for scoring
        expected_llm_response=event.expected_llm_response,
        confidence_threshold=event.confidence_threshold
    )

    return obfuscated_event
```

## Date Parsing Support

### Enhanced Date Utilities

The system's date utilities were enhanced to handle obfuscated dates:

**Location**: `src/utils/date_utils.py`

```python
def parse_date_string(date_str) -> datetime.datetime:
    """
    Parse various date string formats including obfuscated dates.

    Supports:
    - Real dates: "2020-03-09", "2020-03-09 14:30:00"
    - Obfuscated dates: "Day T+0", "Day T+5", "Day T-2"
    """

    # Handle obfuscated date format
    if isinstance(date_str, str) and date_str.startswith("Day T"):
        # Extract offset from "Day T+N" or "Day T-N" format
        if "T+" in date_str:
            offset = int(date_str.split("T+")[1])
        elif "T-" in date_str:
            offset = -int(date_str.split("T-")[1])
        else:
            offset = 0

        # Use consistent base date for obfuscated dates
        base_date = datetime.datetime(2020, 1, 1)
        return base_date + datetime.timedelta(days=offset)
```

## Usage Examples

### Basic Obfuscation

```python
from src.validation.data_obfuscation import DataObfuscator

obfuscator = DataObfuscator()

# Obfuscate dates
dates = ["2021-01-25", "2021-01-26", "2021-01-27", "2021-01-28"]
date_mapping = obfuscator.obfuscate_dates(dates, "2021-01-25")
print(date_mapping)
# Output: {"2021-01-25": "Day T+0", "2021-01-26": "Day T+1", ...}

# Obfuscate tickers
tickers = ["GME", "AMC", "SPY"]
ticker_mapping = obfuscator.obfuscate_tickers(tickers)
print(ticker_mapping)
# Output: {"GME": "STOCK_G", "AMC": "STOCK_H", "SPY": "INDEX_1"}
```

### Text Obfuscation

```python
original_text = "GameStop surged on January 28, 2021 during the COVID pandemic"
obfuscated_text = obfuscator.obfuscate_text_content(original_text)
print(obfuscated_text)
# Output: "STOCK_G surged on Day T+3 during the Economic Event A"
```

### Market Data Obfuscation

```python
# Obfuscate complete DataFrame
market_data = pd.DataFrame({
    'Date': ['2021-01-25', '2021-01-26', '2021-01-27'],
    'Symbol': ['GME', 'GME', 'GME'],
    'Close': [76.79, 147.98, 347.51]
})

obfuscated_df, metadata = obfuscator.obfuscate_market_data(market_data)
print(obfuscated_df)
# Output: DataFrame with "Day T+0", "STOCK_G", etc.
```

### Validation Testing

```python
from src.validation.mechanics_validation_dataset import quick_validate_event

# Compare normal vs obfuscated
normal_result = quick_validate_event("gme_squeeze_2021", obfuscate_data=False)
obfuscated_result = quick_validate_event("gme_squeeze_2021", obfuscate_data=True)

print("Normal Analysis (may use training knowledge):")
print(f"  WHO: {normal_result.llm_response['mechanics_interpretation']['who']}")
print(f"  WHAT: {normal_result.llm_response['mechanics_interpretation']['what']}")
print(f"  Accuracy: {normal_result.accuracy_score:.1%}")

print("Obfuscated Analysis (genuine capability):")
print(f"  WHO: {obfuscated_result.llm_response['mechanics_interpretation']['who']}")
print(f"  WHAT: {obfuscated_result.llm_response['mechanics_interpretation']['what']}")
print(f"  Accuracy: {obfuscated_result.accuracy_score:.1%}")

# Calculate training data dependency
leakage = normal_result.accuracy_score - obfuscated_result.accuracy_score
print(f"Training data dependency: {leakage:.1%}")
```

## Validation Quality

### Obfuscation Quality Check

```python
def validate_obfuscation_quality(original_text, obfuscated_text):
    """Validate that obfuscation successfully removed temporal references."""

    issues = []

    # Check for remaining date patterns
    date_patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
        r'\b(January|February|March|...|December)\s+\d{1,2},?\s+\d{4}\b'
    ]

    for pattern in date_patterns:
        matches = re.findall(pattern, obfuscated_text, re.IGNORECASE)
        if matches:
            issues.append(f"Found remaining dates: {matches}")

    return {
        'validation_passed': len(issues) == 0,
        'issues_found': issues
    }
```

### Reversibility

```python
def create_reverse_mapping(self):
    """Create reverse mappings to convert obfuscated data back to original."""

    return {
        'dates': {v: k for k, v in self.date_mapping.items()},
        'tickers': {v: k for k, v in self.ticker_mapping.items()}
    }

# Save/load mappings for later analysis
def save_mappings(self, filepath):
    """Save obfuscation mappings for later reversal."""

def load_mappings(self, filepath):
    """Load previously saved obfuscation mappings."""
```

## Convenience Functions

### Quick Obfuscation

```python
# Quick date range obfuscation
def obfuscate_date_range(start_date, end_date):
    """Quick function to obfuscate a date range."""
    obfuscator = DataObfuscator()
    dates = pd.date_range(start_date, end_date, freq='D').strftime('%Y-%m-%d').tolist()
    return obfuscator.obfuscate_dates(dates, start_date)

# Quick ticker obfuscation for common symbols
def obfuscate_mag7_tickers():
    """Quick function to get MAG7 ticker obfuscation mapping."""
    obfuscator = DataObfuscator()
    mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    return obfuscator.obfuscate_tickers(mag7)
```

## Best Practices

### When to Use Obfuscation

#### ✅ **Always Use For**

- Academic research and publications
- Unbiased LLM capability assessment
- Production validation confidence
- Model comparison benchmarks
- **Pattern taxonomy validation (Issue #79)** - Required for mechanical pattern claims

#### ⚠️ **Optional For**

- Development and debugging (use normal validation for speed)
- System functionality testing
- Initial prototyping

#### ❌ **Critical Mistake (Issue #81)**

**What Happened**: Issue #79 validation claimed obfuscation testing but `run_experiment()` had no `obfuscate` parameter. The LLM received real dates/tickers, invalidating claims that patterns worked "without temporal context."

**Fix Applied**: October 7, 2025 - Added `obfuscate=True` parameter to `run_experiment()` method.

**Lesson**: Always verify obfuscation end-to-end. Don't trust flags in report generation alone - check what the LLM actually sees in prompts.

### Development Workflow

```python
# Development phase: Use normal validation
def development_testing():
    result = quick_validate_event("covid_crash_2020", obfuscate_data=False)
    # Fast iteration, debugging-friendly

# Research phase: Use obfuscated validation
def research_validation():
    result = quick_validate_event("covid_crash_2020", obfuscate_data=True)
    # Academic rigor, publication-ready

# Comparison phase: Use both
def comprehensive_analysis():
    normal = quick_validate_event("covid_crash_2020", obfuscate_data=False)
    obfuscated = quick_validate_event("covid_crash_2020", obfuscate_data=True)

    # Quantify training data influence
    training_dependency = normal.accuracy_score - obfuscated.accuracy_score

    return {
        'normal_accuracy': normal.accuracy_score,
        'obfuscated_accuracy': obfuscated.accuracy_score,
        'training_data_dependency': training_dependency
    }
```

### Result Interpretation

#### High Normal, Low Obfuscated Accuracy

- **Interpretation**: LLM heavily dependent on training data
- **Action**: Improve LLM prompts or use different model
- **Example**: Normal 85%, Obfuscated 15%

#### Similar Normal and Obfuscated Accuracy

- **Interpretation**: LLM genuinely analyzing data patterns
- **Action**: Confidence in analytical capability
- **Example**: Normal 75%, Obfuscated 70%

#### Low Both Accuracies

- **Interpretation**: LLM struggling with market mechanics
- **Action**: Enhance data quality or training approach
- **Example**: Normal 25%, Obfuscated 20%

## Implementation Details

### Memory Management

```python
class DataObfuscator:
    def __init__(self):
        self.date_mapping = {}      # Store for consistency
        self.ticker_mapping = {}    # Store for consistency
        self.reverse_mappings = {}  # For result interpretation
        self.base_date = None       # Reference point for dates
```

### Thread Safety

The obfuscator is designed for single-threaded use within validation workflows. For concurrent validation:

```python
# Create separate obfuscator instances
def concurrent_validation():
    obfuscator_1 = DataObfuscator()  # Thread 1
    obfuscator_2 = DataObfuscator()  # Thread 2

    # Each maintains independent state
```

### Performance

- **Date obfuscation**: O(n) where n = number of dates
- **Ticker obfuscation**: O(m) where m = number of tickers
- **Text obfuscation**: O(k) where k = text length
- **Memory usage**: Minimal, stores only mappings

## Troubleshooting

### Common Issues

1. **Inconsistent Mappings**
   - **Problem**: Different obfuscations for same symbol
   - **Solution**: Use same DataObfuscator instance for related operations

2. **Date Parsing Failures**
   - **Problem**: "Unable to parse date string: Day T+0"
   - **Solution**: Enhanced date_utils.py handles obfuscated dates

3. **Incomplete Obfuscation**
   - **Problem**: Real dates/tickers still visible
   - **Solution**: Use validation_quality() to check obfuscation completeness

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

obfuscator = DataObfuscator()
# Will log all transformations applied
```

---

**The Data Obfuscation System ensures that LLM validation tests genuine analytical capability rather than memorized market knowledge, providing confidence for both academic research and trading applications.**
