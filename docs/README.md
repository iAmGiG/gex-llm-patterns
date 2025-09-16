# GEX-LLM Patterns Documentation

## Overview

This directory contains comprehensive documentation for the GEX-LLM Patterns trading system, which combines gamma exposure (GEX) analysis with large language model (LLM) market mechanics interpretation.

## Core Components

### [Validation Framework](validation-framework.md)
- **Mechanics Validation Dataset**: Historical market events for LLM testing
- **Data Obfuscation System**: Prevents training data leakage in validation
- **Accuracy Metrics**: Quantifies LLM market mechanics interpretation capability

### [Model Selection Research](model-selection-research.md)
- **O3-mini Production Deployment**: 90% confidence with 60% cost savings
- **Comprehensive Model Testing**: GPT-4o, O3-mini, O4-mini, GPT-5 mini comparison
- **Cost Optimization Strategy**: Hybrid architecture for maximum efficiency

### [Market Mechanics Agent](market-mechanics-agent.md)
- **Single-Agent Architecture**: Simplified pipeline for market analysis
- **AutoGen Integration**: Consistent LLM framework with sophisticated caching
- **WHO/WHOM/WHAT Analysis**: Identifies forcing parties and mechanisms

### [Data Obfuscation](data-obfuscation.md)
- **Training Data Leakage Prevention**: Ensures unbiased LLM validation
- **Date/Ticker Anonymization**: Converts real data to anonymous equivalents
- **Validation Protocol**: Normal vs obfuscated testing comparison

### [Date Utilities](date-utilities.md)
- **Centralized Date Handling**: Unified datetime operations across the system
- **Obfuscated Date Support**: Parses both real and anonymous date formats
- **Market Calendar Integration**: Business days, OPEX weeks, market hours

## Quick Start

### Installation & Setup
```bash
# Clone repository
git clone https://github.com/iAmGiG/gex-llm-patterns.git
cd gex-llm-patterns

# Install dependencies
pip install -r requirements.txt

# Configure API keys in config/config.json
cp config/config.json.example config/config.json
# Edit with your API keys
```

### Basic Usage

#### Market Mechanics Analysis
```python
from src.agents.market_mechanics_agent import MarketMechanicsAgent

# Initialize agent
agent = MarketMechanicsAgent(symbol="SPY")

# Analyze specific date
result = agent.daily_analysis("2024-01-15")
print(f"WHO: {result['mechanics_interpretation']['who']}")
print(f"WHAT: {result['mechanics_interpretation']['what']}")
```

#### Validation Testing
```python
from src.validation.mechanics_validation_dataset import quick_validate_event

# Standard academic validation (default - obfuscated for rigor)
result = quick_validate_event("covid_crash_2020")
print(f"Academic validation accuracy: {result.accuracy_score:.1%}")

# Optional: Compare with development validation to detect training data leakage
development_result = quick_validate_event("covid_crash_2020", obfuscate_data=False)
academic_result = quick_validate_event("covid_crash_2020")  # Default obfuscated

leakage = development_result.accuracy_score - academic_result.accuracy_score
print(f"Training data leakage detected: {leakage:.1%}")
```

## Architecture

### System Flow
```
Data Sources → AutoGen Tools → Market Mechanics Agent → LLM Interpretation
     ↓              ↓                   ↓                      ↓
  Cache/API   Sophisticated      GEX Calculation        WHO/WHOM/WHAT
  Fallback     Caching           + Patterns              Analysis
```

### Key Innovations

1. **Data Obfuscation for LLM Validation**
   - Prevents training data leakage
   - Ensures genuine analytical capability testing
   - Academic rigor for research applications

2. **Unified Caching with AutoGen Tools**
   - Cache → API → Sample data fallback hierarchy
   - Efficient data handling with retry logic
   - Consistent interface across all data operations

3. **Market Mechanics Focus**
   - Goes beyond price prediction to understand causality
   - Identifies forcing parties and mechanisms
   - Actionable intelligence for trading decisions

## File Structure

```
docs/
├── README.md                      # This overview
├── model-selection-research.md    # Model testing and O3-mini selection
├── validation-framework.md        # Validation system documentation
├── baseline-strategy.md           # Baseline strategy implementation
├── data-obfuscation.md           # Obfuscation system details
├── market-mechanics-agent.md     # Agent architecture and usage
├── date-utilities.md             # Date handling documentation
├── api-reference.md              # Complete API documentation
└── troubleshooting.md            # Common issues and solutions
```

## Development Status

### ✅ Production Ready
- **Model Selection**: O3-mini deployed with 90% confidence and 60% cost savings
- **Market Mechanics Agent**: Single-agent architecture with AutoGen LLM
- **Validation Framework**: 6 historical events with obfuscated testing
- **Data Obfuscation System**: Prevents training data leakage
- **Baseline Strategy**: Mechanical trading strategy for LLM comparison

### 🔄 In Development
- **Enhanced Pattern Detection**: Additional market mechanics patterns
- **Multi-Symbol Analysis**: Portfolio-level market mechanics
- **Real-Time Integration**: Live trading implementation

### 📋 Research Applications
- **Academic Validation**: Obfuscated testing for research rigor
- **LLM Benchmarking**: Compare different models and prompts
- **Market Intelligence**: Systematic WHO/WHOM/WHAT analysis

## Contributing

### Development Workflow
1. Read relevant documentation in this `docs/` directory
2. Follow the validation framework for testing new features
3. Use data obfuscation for unbiased validation
4. Update documentation when adding new components

### Testing Standards
- Use obfuscated validation for new LLM features
- Follow reports/ structure for experiment organization
- Maintain backward compatibility with existing interfaces

## Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides in this directory
- **Code Examples**: See individual component documentation

---

**Note**: This system focuses on market microstructure mechanics rather than price prediction, providing unique insights into WHO forces WHOM to do WHAT in financial markets.