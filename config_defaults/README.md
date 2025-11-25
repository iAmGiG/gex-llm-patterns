# Configuration System

This directory contains centralized configuration files for the GEX LLM Patterns system.

## Current Configuration Files

- **`agent_config.yaml`** - Agent LLM settings, timeouts, and multi-agent configuration (Issue #151)
- **`analysis_config.yaml`** - Core pattern detection, GEX thresholds, and statistical analysis parameters
- **`continuous_testing_config.yaml`** - Baseline comparison testing and strategy validation parameters
- **`data_sources_config.yaml`** - API timeouts, rate limits, and data source settings (Issue #151)
- **`llm_prompts.yaml`** - LLM prompt templates for pattern detection (Issue #90) and agent workflows
- **`obfuscation_patterns.yaml`** - Data obfuscation templates for anti-cheating validation
- **`pattern_library_config.yaml`** - Pattern library definitions and mechanics
- **`technical_indicators_config.yaml`** - Technical indicator calculations and adaptive consensus parameters
- **`tool_registry_config.yaml`** - Tool registry settings and agent tool assignments (Issue #152)
- **`trading_config.yaml`** - Trading system and risk management parameters
- **`agent_factory_config.yaml`** - Agent factory pattern configuration (Issue #153)
- **`agent_bus_config.yaml`** - Agent communication bus configuration (Issue #154)

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

### Agent Factory Pattern (Issue #153)

Use the `AgentFactory` for centralized agent creation:

```python
from src.agents import (
    AgentFactory, AgentType,
    create_agent, create_market_mechanics_agent
)

# Create via factory
factory = AgentFactory()
instance = factory.create(AgentType.MARKET_MECHANICS, symbol='SPY')

# Or use convenience functions
instance = create_market_mechanics_agent(symbol='SPY')

# Access the actual agent
agent = instance.agent
```

**Configuration**: Edit `agent_factory_config.yaml` to customize:

- Default model and temperature per agent type
- Tool assignments
- Agent-specific extra configuration

### Agent Communication Bus (Issue #154)

Use the `AgentBus` for multi-agent coordination:

```python
import asyncio
from src.agents import (
    AgentBus, EventType, AgentMessage,
    get_agent_bus, create_message, publish_result
)

# Get singleton bus
bus = get_agent_bus()

# Subscribe to events
def on_gex_calculated(msg: AgentMessage):
    print(f"GEX ready: {msg.payload}")

bus.subscribe("my_agent", EventType.GEX_CALCULATED, on_gex_calculated)

# Publish results
async def publish_gex():
    await publish_result(
        source_agent="spy_agent",
        event_type=EventType.GEX_CALCULATED,
        payload={"symbol": "SPY", "net_gex": 5000000}
    )

# Wait for results from other agents
async def wait_for_data():
    result = await bus.wait_for_result("spy_agent", EventType.GEX_CALCULATED)
    return result.payload

# Gather multiple results
async def gather_all():
    results = await bus.gather_results([
        ("spy_agent", EventType.GEX_CALCULATED),
        ("qqq_agent", EventType.GEX_CALCULATED),
    ])
    return results
```

**Configuration**: Edit `agent_bus_config.yaml` to customize:

- Message history limits
- Default timeouts
- Event type definitions
- Default subscriptions

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

### Issue #151 Updates (November 2025)

- `src/base_agent.py` - Model, temperature, timeout, max_tokens from `agent_config.yaml`
- `src/cache/concurrent_gex_processor.py` - max_workers, timeout from `data_sources_config.yaml`
- `src/data_sources/alpha_vantage_gex.py` - Request timeout, rate limits from `data_sources_config.yaml`

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
