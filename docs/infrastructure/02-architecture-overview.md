# Architecture Overview

## System Design

The GEX-LLM Pattern Analysis system is a research platform designed for CS PhD dissertation work investigating whether Large Language Models can identify actionable patterns in market microstructure data better than mechanical approaches.

## High-Level Architecture

```bash
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │────│ 2-Tier Storage  │────│ Data Pipeline   │
│                 │    │                 │    │                 │
│ • Alpha Vantage │    │ • SQLite DB     │    │ • AutoGen Tools │
│ • Polygon.io    │    │ • Cache Layer   │    │ • Rate Limiting │
│ • Options Data  │    │ • 24hr TTL      │    │ • Obfuscation   │
│ • Market Data   │    │ • Auto Fallback │    │ • Validation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ GEX Calculation │
                    │                 │
                    │ • Gamma Exposure│
                    │ • Strike-Level  │
                    │ • Flip Points   │
                    │ • Regime Class. │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Pattern Library │
                    │                 │
                    │ • 15 Patterns   │
                    │ • WHO/WHOM/WHAT │
                    │ • Success Rates │
                    │ • Validation    │
                    └─────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ LLM Integration │────│ Market Agent    │────│ A/B Validation  │
│                 │    │                 │    │                 │
│ • O3-mini       │    │ • Single Agent  │    │ • Obfuscated    │
│ • GPT-4o-mini   │    │ • Tool Calling  │    │ • Batch Tests   │
│ • Reasoning     │    │ • Experiments   │    │ • Statistics    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Research Hypothesis

**Primary Question**: Can LLM contextual reasoning about market microstructure (WHO forces WHOM to do WHAT) generate better trading signals than mechanical GEX strategies?

**Methodology**: A/B testing of baseline GEX thresholds vs LLM-enhanced pattern detection on obfuscated historical data.

## Component Interactions

### Data Flow

1. **Market Data APIs** → **2-Tier Storage** → **GEX Calculator**
2. **GEX Metrics** → **Pattern Library** → **Market Mechanics Agent**
3. **Agent** → **LLM Analysis** → **Actionable Signals** → **Validation Results**

## Key Components

### MarketMechanicsAgent (`src/agents/market_mechanics_agent.py`)

- **Purpose**: Single-agent architecture for market mechanics interpretation
- **Core Function**: Translates GEX data into WHO/WHOM/WHAT market narratives
- **LLM Integration**: Supports multiple LLM providers with fallback handling
- **Capabilities**: Tool orchestration, batch processing, experimental framework

### Agent Infrastructure (Issues #152-154)

**Tool Registry** (`src/tools/tool_registry.py`) - Branch: `issue152-tool-registry`

- Centralized tool management with agent type filtering
- AutoGen FunctionTool integration
- Tool enable/disable and validation

**Agent Factory** (`src/agents/agent_factory.py`) - Branch: `issue153-agent-factory`

- Factory pattern for centralized agent creation
- Configuration-driven defaults from YAML
- Convenience functions: `create_agent()`, `create_market_mechanics_agent()`

**Agent Bus** (`src/agents/agent_bus.py`) - Branch: `issue154-agent-communication-bus`

- Pub/sub message bus for multi-agent coordination
- Async `wait_for_result()` and `gather_results()` for parallel workflows
- Foundation for Paper 3 multi-asset analysis

### Pattern Library (`src/analysis/pattern_library.py`)

- **15 Documented Patterns**: Gamma squeeze, OPEX pin, dealer trap, etc.
- **Pattern Structure**: Setup conditions, mechanics, expected outcomes, success rates
- **Historical Validation**: Backtested success rates and sample sizes
- **LLM Prompts**: Pattern-specific prompt templates for consistent analysis

### GEX Calculator (`src/gex/gex_calculator.py`)

- **Black-Scholes Greeks**: Calculates gamma exposure for dealer positioning
- **Strike-Level Analysis**: Enhanced beyond aggregate GEX for pattern detection
- **Regime Classification**: POSITIVE/NEGATIVE gamma with high/low intensity
- **Flip Point Detection**: Critical levels where dealer hedging behavior changes

### Data Obfuscation (`src/validation/data_obfuscation.py`)

- **Date Anonymization**: "2021-01-28" → "Day T+17" format
- **Ticker Masking**: "GME" → "STOCK_G", "SPY" → "INDEX_1"
- **Context Removal**: Strips temporal references and memorizable events
- **Reversible Mapping**: Maintains consistency for result interpretation

### Validation Framework (`scripts/validation/validate_patterns.py`)

- **Historical Testing**: GME squeeze, VIX spikes, COVID events validation
- **Live Data Integration**: Uses real market data with AutoGen tools fallback
- **Database Storage**: Tracks validation results and pattern performance
- **A/B Testing**: Compares LLM vs baseline approaches systematically

## LLM Architecture

### Dual-Model Setup

- **O3-mini/O4-mini**: Primary reasoning model for pattern interpretation
- **GPT-4o-mini**: Tool calling and function execution
- **Reasoning Focus**: Complex market dynamics analysis vs simple tool operations

### Cost Optimization

- **Batch Processing**: Single LLM call analyzes multiple dates
- **Caching Strategy**: Minimize redundant API calls
- **Smart Fallbacks**: Cache → API → sample data hierarchy

## Experimental Framework

### Research Design

```python
# Baseline: Mechanical GEX thresholds
if gex_metrics['net_gex'] < -5e9:
    return {"action": "buy", "confidence": 60}

# Enhanced: LLM + Pattern context
agent = MarketMechanicsAgent()
result = agent.run_experiment("Analyze mechanics", obfuscated_date)
return result['actionable_signal']
```

### Validation Metrics

- **Win Rate**: Percentage of correct predictions
- **Confidence Calibration**: LLM confidence vs actual outcomes
- **Statistical Significance**: T-tests comparing baseline vs enhanced
- **Economic Value**: Risk-adjusted returns after transaction costs

## Production Architecture

### 2-Tier Data System

- **Tier 1**: SQLite database (`.cache/consolidated_historical.db`)
- **Tier 2**: In-memory cache with 24hr TTL
- **Performance**: 90%+ hit rate, 3-7 seconds vs 10+ minutes API calls
- **Cost Control**: Zero API costs for repeated experiments

### Error Handling

- **Graceful Degradation**: System continues with available data sources
- **Comprehensive Logging**: Debug LLM responses and data flow issues
- **Fallback Chains**: AutoGen → Cache → Sample data → Warning

### Key Dependencies

- **Cache** ← All data-dependent components
- **GEX Calculator** ← Pattern detection and agent analysis
- **Pattern Library** ← LLM Integration
- **Agent Results** ← Statistical Validation

## Directory Structure

```bash
src/
├── cache/                  # Unified caching system
│   ├── unified_cache.py   # Main cache manager
│   ├── market_data_cache.py # Market-specific caching
│   └── cache_adapter.py   # Adapter interfaces
├── data_sources/          # External data integration
│   └── alpha_vantage_gex.py # Alpha Vantage client
├── gex/                   # Gamma exposure calculations
├── utils/                 # Shared utilities
│   ├── date_utils.py      # Date/time handling
│   ├── config_manager.py  # Configuration management
│   ├── market_intelligence.py # Market analysis
│   ├── indicator_library.py # Technical indicators
│   └── reports_manager.py # Results management
└── validation/           # Research integrity
    ├── data_obfuscation.py # Remove temporal bias
    ├── date_sanitizer.py  # Date anonymization
    └── mechanics_validation_dataset.py # Historical validation
docs/legacy/              # Moved components
├── tokenization/         # Token-based LLM approach (deprecated)
├── agent_utils.py        # Legacy agent operations
├── autogen_examples.py   # Framework examples
└── advanced_greeks.py    # Complex mathematical precision
```

## Design Principles

### 1. Modularity

- Each component has clear interfaces
- Minimal coupling between modules
- Easy to test and replace individual parts

### 2. Caching-First

- All external API calls go through cache layer
- Smart expiration based on data type
- Critical for rate-limited APIs (Alpha Vantage: 75 calls/min)

### 3. Research Integrity

- Data obfuscation prevents LLM training bias
- Statistical validation ensures robustness
- Out-of-sample testing prevents overfitting

### 4. Scalability

- Designed for 4+ years of daily options data
- Efficient algorithms for pattern mining
- Optimized for academic compute environments

## Configuration Management

- **@config/ System**: Handles API keys and sensitive config (excluded from repo)
- **Environment Variables**: Fallback for standard deployment
- **Default Settings**: Sensible defaults for academic research

## Error Handling Strategy

- **Graceful Degradation**: Continue with cached data when APIs fail
- **Retry Logic**: Exponential backoff for transient failures
- **Validation Gates**: Data quality checks at each stage
- **Logging**: Comprehensive logging for debugging and analysis

## Performance Considerations

### Bottlenecks

1. **Alpha Vantage API**: 75 calls/minute rate limit
2. **GEX Calculations**: CPU-intensive for large option chains
3. **Pattern Mining**: Memory-intensive for long sequences
4. **LLM Calls**: Cost and latency considerations

### Optimizations

1. **Aggressive Caching**: 10-year TTL for historical data
2. **Batch Processing**: Group API calls efficiently
3. **Algorithmic Efficiency**: Optimized pattern mining algorithms
4. **Cost Routing**: GPT-4o-mini for most analysis, GPT-4o for high-value patterns

## Security & Privacy

- **No Sensitive Data**: Only public market data
- **API Key Protection**: Via @config/ system
- **No Network Data**: All processing local or on approved academic infrastructure
- **Research Ethics**: Academic use only, no market manipulation

---

## Navigation

**Prerequisites**: [01-project-overview.md](01-project-overview.md)
**Next**: [03-data-and-database.md](03-data-and-database.md)
**Related**: [diagrams/](diagrams/README.md) — technical system diagrams
