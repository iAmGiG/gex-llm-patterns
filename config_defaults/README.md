# Configuration System

This directory contains centralized configuration files for the GEX LLM Patterns system.

## Current Configuration Files

- **`analysis_config.yaml`** - Core pattern detection, GEX thresholds, and statistical analysis parameters
- **`continuous_testing_config.yaml`** - Baseline comparison testing and strategy validation parameters
- **`llm_prompts.yaml`** - LLM prompt templates for pattern detection (Issue #90) and agent workflows
- **`obfuscation_patterns.yaml`** - Data obfuscation templates for anti-cheating validation
- **`pattern_library_config.yaml`** - Pattern library definitions and mechanics
- **`technical_indicators_config.yaml`** - Technical indicator calculations and adaptive consensus parameters
- **`trading_config.yaml`** - Trading system and risk management parameters

## Removed Files (Agent-Driven Evolution)

With the implementation of LLM-driven agent autonomy, several static configuration files have been removed:

- `tokenization_config.yaml` - Tokenization moved to legacy architecture
- `gex_calculation_config.yaml` - GEX calculations now handled by enhanced pattern detector
- `data_source_config.yaml` - Data sources now managed by AutoGen tools with fallbacks
- `baseline_test_config.yaml` - Testing now handled by validation scripts
- `sample_data_test_config.yaml` - Sample data testing integrated into main validation
- `technical_only_test_config.yaml` - Technical analysis integrated into main system

## Usage

### Basic Usage

```python
from src.utils.config_manager import get_config

config = get_config()
lookback_days = config.get('tokenization.gex_tokenizer.lookback_days')
```

### Agent Prompt Templates (November 2025)

The `MarketMechanicsAgent` now loads prompts from `llm_prompts.yaml` automatically:

```python
from src.agents.market_mechanics_agent import MarketMechanicsAgent

# Agent loads prompts from config_defaults/llm_prompts.yaml
agent = MarketMechanicsAgent(symbol="SPY")

# Prompts are automatically applied in:
# - agent.run_batch_experiments() -> uses agent_prompts.batch_analysis
# - agent._plan_experiment_tools() -> uses agent_prompts.experiment_planning
# - agent._analyze_experiment_results() -> uses agent_prompts.experiment_analysis
```

**Fallback Behavior**: If `llm_prompts.yaml` is missing or `agent_prompts` section is empty, the agent falls back to inline hardcoded prompts automatically with a warning log.

**Editing Prompts**: To customize agent behavior, edit `config_defaults/llm_prompts.yaml` under the `agent_prompts` section. Changes take effect on next agent initialization (no code restart required).

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
