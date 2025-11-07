# Analysis Scripts

Scripts for data analysis, exploration, and understanding.

## Scripts

### `explain_options_data.py`

- **Purpose**: Analyzes and explains the structure of collected options data
- **Usage**: `python scripts/analysis/explain_options_data.py`
- **Output**: Detailed breakdown of options contracts, strikes, expirations, and Greeks
- **Dependencies**: Requires cached options data from Alpha Vantage

## Adding New Analysis Scripts

When adding new analysis scripts to this directory:

1. **Naming**: Use descriptive names like `analyze_gex_patterns.py`
2. **Documentation**: Include docstring explaining purpose and usage
3. **Dependencies**: Document required data sources and packages
4. **Output**: Clearly specify what the script produces
