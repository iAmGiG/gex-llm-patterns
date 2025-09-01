# Architecture Overview

## System Design

The GEX-LLM Pattern Analysis system is designed as a modular research platform that processes financial options data through multiple stages to discover patterns using Large Language Models.

## High-Level Architecture

```bash
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │────│  Cache Layer    │────│ Data Pipeline   │
│                 │    │                 │    │                 │
│ • Alpha Vantage │    │ • Historical    │    │ • Rate Limiting │
│ • SPY/SPX       │    │ • 10yr/24hr TTL │    │ • Validation    │
│ • Options Data  │    │ • Smart Expiry  │    │ • Processing    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ GEX Calculation │
                    │                 │
                    │ • Gamma Exposure│
                    │ • Flip Points   │
                    │ • Key Levels    │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Tokenization   │
                    │                 │
                    │ • Dynamic Bins  │
                    │ • Market States │
                    │ • Sequences     │
                    └─────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Pattern Mining  │────│ LLM Integration │────│   Validation    │
│                 │    │                 │    │                 │
│ • PrefixSpan    │    │ • Autogen       │    │ • Backtesting   │
│ • Significance  │    │ • GPT-4o-mini   │    │ • Statistics    │
│ • Filtering     │    │ • Multi-Agent   │    │ • Robustness    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Component Interactions

### Data Flow

1. **Alpha Vantage API** → **Cache Layer** → **GEX Calculator**
2. **GEX Results** → **Tokenizer** → **Pattern Miner**  
3. **Patterns** → **LLM Analyzer** → **Backtester** → **Validator**

### Key Dependencies

- **Cache** ← All data-dependent components
- **GEX Calculator** ← Tokenizer, Pattern Miner
- **Pattern Results** ← LLM Integration
- **All Results** ← Statistical Validation

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
├── tokenization/          # Market state tokenization
├── utils/                 # Shared utilities
│   ├── agent_utils.py     # Autogen operations
│   ├── date_utils.py      # Date/time handling
│   ├── indicator_library.py # Technical indicators
│   └── autogen_examples.py # Framework examples
└── validation/           # Research integrity
    ├── data_obfuscation.py # Remove temporal bias
    ├── date_sanitizer.py  # Date anonymization
    └── obfuscation_validator.py # Validation testing
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
