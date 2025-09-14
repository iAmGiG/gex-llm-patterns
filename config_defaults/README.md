# Configuration System

This directory contains centralized configuration files for the GEX LLM Patterns system.

## Configuration Files

- **`tokenization_config.yaml`** - GEX tokenizer, sequence builder, and price tokenizer parameters
- **`analysis_config.yaml`** - Statistical analysis and confidence scoring parameters
- **`gex_calculation_config.yaml`** - GEX calculations and pattern detection parameters
- **`data_source_config.yaml`** - API clients and data collection parameters
- **`trading_config.yaml`** - Trading system and risk management parameters

## Usage

### Basic Usage

```python
from src.utils.config_manager import get_config

config = get_config()
lookback_days = config.get('tokenization.gex_tokenizer.lookback_days')
```

### In Class Constructors

```python
from src.utils.config_manager import get_config

class MyClass:
    def __init__(self, parameter=None):
        config = get_config()
        self.parameter = parameter or config.get('section.subsection.parameter', default_value)
```

## Environment Overrides

Configuration values can be overridden using environment variables:

```bash
# Override tokenization.gex_tokenizer.lookback_days
export TOKENIZATION_GEX_TOKENIZER_LOOKBACK_DAYS=500

# Override analysis.confidence_scorer.min_sample_size
export ANALYSIS_CONFIDENCE_SCORER_MIN_SAMPLE_SIZE=30
```

## Updated Classes

The following classes now use the configuration system:

### High Priority (Fully Updated)

- `src/tokenization/gex_tokenizer.py` - 4+ parameters from config
- `src/tokenization/sequence_builder.py` - 6+ parameters from config
- `src/analysis/confidence_scorer.py` - 10+ parameters from config

### Medium Priority (Partially Updated)

- `src/gex/gex_calculator.py` - Risk-free rate from config
- `src/data_sources/polygon_client.py` - Rate limiting from config

## Benefits

1. **Environment Flexibility** - Different parameters for dev/test/prod
2. **A/B Testing** - Easy parameter experimentation without code changes
3. **Consistency** - Shared parameters across components (e.g., lookback periods)
4. **Maintainability** - Central location for all system constants
5. **Backward Compatibility** - Direct parameter passing still works

## Configuration Key Format

Use dot notation: `section.subsection.parameter`

Examples:

- `tokenization.gex_tokenizer.lookback_days`
- `analysis.confidence_scorer.base_lookback_days`
- `gex_calculation.gex_calculator.risk_free_rate`
