# Legacy Documentation and Reference Code

This directory contains reference implementations and examples from previous system architectures that are no longer actively used in production but are preserved for documentation and reference purposes.

## Files

### `autogen_examples.py`

- **Purpose**: Examples of AutoGen framework implementation patterns
- **Status**: Reference only - not used in current production system
- **Contains**: Sample AutoGen agent configurations and usage patterns
- **Historical Context**: Early AutoGen experimentation before production implementation

### `agent_utils.py`

- **Purpose**: Previous system for data feeding into LLM agents
- **Status**: Superseded by modern autogen_tools.py architecture
- **Contains**: Legacy data processing utilities for agent workflows
- **Replacement**: Current system uses autogen_tools.py with Alpha Vantage API integration
- **Historical Context**: Original LLM data feeding system before API consolidation

### `advanced_greeks.py`

- **Purpose**: Advanced Greeks calculations (Vanna, Charm, Vomma, Speed, Zomma, Color)
- **Status**: Strategic decision to focus on LLM-interpretable mechanics instead
- **Contains**: Second and third-order derivatives for options pricing
- **Rationale**: Higher-order Greeks are complex for LLM interpretation; basic Gamma/Delta sufficient for market mechanics analysis
- **Historical Context**: Mathematical precision approach superseded by practical LLM-based mechanics interpretation

### `tokenization/` Directory

- **Purpose**: Token-based LLM input system for market data
- **Status**: Obsolete - replaced by natural language prompts
- **Contains**: GEXTokenizer, PriceTokenizer, EventTokenizer, SequenceBuilder, Vocabulary (1,692 lines)
- **Rationale**: Modern LLMs (O3-mini) work better with natural language descriptions than discrete tokens
- **Replacement**: Current system uses `mechanics_prompt_builder.py` for natural language prompts
- **Historical Context**: Early LLM integration approach before natural language prompt engineering matured

### `base_agent_reference.py`

- **Purpose**: Reference implementation of AutoGen-based agent architecture
- **Status**: Reference only - current system uses `base_agent.py`
- **Contains**: Comprehensive BaseAgent class with tool execution, memory management, and conversation handling (612 lines)
- **Rationale**: More complex than needed for current streamlined O3-mini architecture
- **Replacement**: Current system uses simplified `src/base_agent.py` (BaseGEXAgent)
- **Historical Context**: Earlier AutoGen integration approach with full feature set

## Migration Notes

These implementations were part of the evolution toward the current O3-mini production system:

1. **agent_utils.py** → **autogen_tools.py** (unified API approach)
2. **autogen_examples.py** → **autogen_market_mechanics.py** (production implementation)

## Current Production Architecture

The current system uses:

- `src/llm/autogen_market_mechanics.py` - O3-mini LLM integration
- `src/tools/autogen_tools.py` - Unified API tools with Alpha Vantage
- `src/agents/market_mechanics_agent.py` - Main production agent
