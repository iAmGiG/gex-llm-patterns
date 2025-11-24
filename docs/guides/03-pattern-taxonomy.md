# Pattern Taxonomy Framework

## Overview

The Pattern Taxonomy Framework distinguishes between real structural market patterns and market folklore by classifying patterns based on their underlying mechanisms and validation criteria.

## Pattern Classification

### MECHANICAL Patterns

Patterns that **MUST** occur due to dealer constraints:

- Have clear causal mechanisms
- Backed by academic research
- Dealers have no viable alternatives
- Pass obfuscation tests (work without context)

**Examples:**

- **Gamma Positioning** (Buis et al. 2024) - Delta-neutral mandates force predictable hedging
- **Stock Pinning** (Jeannin et al. 2008) - Gamma explosion at strikes creates price gravity
- **0DTE Hedging** - 40-50% SPX volume forces immediate hedging flows

### PROBABILISTIC Patterns

Patterns with statistical edge but not guaranteed:

- Have identifiable mechanisms but alternatives exist
- Show consistent success rates (>60%)
- May work without context but need validation
- Economically significant after costs

**Examples:**

- **Gamma Squeeze** - Call buying cascade (67% success)
- **Friday 3:30 PM Effects** - Final hedging window (75% success)

### NARRATIVE Patterns

Patterns that are likely market folklore:

- Lack clear causal mechanisms
- Success rates near random (50%)
- Fail obfuscation tests (need context to work)
- No economic significance after costs

### UNKNOWN Patterns

Patterns requiring further validation to classify.

## Validation Framework

### The Obfuscation Test

The critical test for pattern reality: Does it work when the LLM doesn't know:

- The specific date/time (Friday 3:30 PM)
- The ticker symbol (GME, SPY)
- The event context (OPEX, FOMC, earnings)

**Patterns that pass this test represent real structural mechanics, not narrative folklore.**

### Success Criteria

For a pattern to be validated as real:

- **Causal Mechanism**: Clear explanation of WHY it must happen
- **Out-of-Sample**: Minimum 30 samples with >60% success rate
- **Economic Significance**: >20 basis points after transaction costs
- **Persistence**: <10% annual alpha decay
- **Obfuscation Resistance**: Maintains performance without context

### Dealer State Machine

Market makers are constrained to limited actions:

```
Market Condition → Dealer Constraint → Forced Action → Observable Pattern
```

**Dealer Actions:**

- **Delta Hedge**: Buy/sell underlying (most common, required)
- **Gamma Hedge**: Trade options (expensive, limited)
- **Vega Hedge**: Trade different expirations (complex)
- **Do Nothing**: Accept risk (limited by risk management)
- **Unwind**: Close positions (liquidity dependent)

## Implementation

### Core Framework

Located in `src/validation/pattern_taxonomy.py`:

```python
from src.validation.pattern_taxonomy import PatternTaxonomy

# Initialize taxonomy
taxonomy = PatternTaxonomy()

# Classify a pattern with test results
validation = taxonomy.classify_pattern('gamma_positioning', {
    'out_of_sample': {'count': 50, 'success_rate': 0.72},
    'economic_value': 0.008,  # 80bps after costs
    'obfuscation': {'passed': True}
})

# Generate taxonomy report
report = taxonomy.generate_taxonomy_report()
```

### Integration Points

- **Obfuscation Testing**: Uses existing `data_obfuscation.py`
- **Pattern Library**: Validates patterns from `pattern_library.py`
- **Validation Framework**: Integrates with `validate_patterns.py`

## Core Patterns Focus

Based on validation, focus on **5 core patterns**:

### Tier 1: Academically Proven (3 patterns)

1. **Gamma Positioning** - Buis et al. 2024
2. **Stock Pinning/OPEX** - Jeannin et al. 2008
3. **0DTE Delta Hedging** - Recent academic papers

### Tier 2: High Conviction (2 patterns)

4. **Gamma Squeeze** - 67% success, needs obfuscation test
5. **Friday 3:30 PM Effects** - 75% success, validated timing

### Deprioritized Patterns (10 patterns)

Patterns with <55% success rates or unclear mechanisms:

- Window Dressing, Dispersion Trade, Correlation Breakdown, etc.

## Key Insights

### The State Machine Reality
>
> "Dealers are constrained to limited actions. This IS a state machine with predictable transitions. The papers confirm dealers MUST hedge when gamma exposure exceeds risk limits."

### Academic Foundation

- **Gamma effects are mechanical** - mathematically proven
- **Pinning is structural** - theoretical proof exists
- **0DTE flows are measurable** - empirical validation

### The Uncomfortable Truth Test

**If a pattern works when stripped of all context clues, it represents real structural market mechanics, not narrative folklore.**

## Usage

### For Researchers

1. Document causal mechanisms for new patterns
2. Run obfuscation tests using the framework
3. Calculate economic significance after real-world costs
4. Track degradation over time

### For Traders

1. Focus on validated mechanical patterns only
2. Ignore narrative patterns that fail validation
3. Use dealer state machine to predict forced actions
4. Monitor pattern persistence and degradation

### For Developers

1. Integrate taxonomy validation into pattern detection
2. Use framework to filter signal generation
3. Implement automated pattern validation pipeline
4. Track pattern performance metrics

## Related Documentation

- [Validation Framework](validation-framework.md) - Overall testing approach
- [Data Obfuscation](data-obfuscation.md) - Context removal techniques
- [Baseline Strategy](baseline-strategy.md) - Performance comparison methods
