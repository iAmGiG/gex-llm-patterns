# Tools and Utilities Documentation

## Overview

The `src/utils/` directory contains shared utilities and tools that support the GEX-LLM analysis pipeline. These modules provide common functionality used across multiple components.

## Core Utilities

### Agent Utils (`agent_utils.py`) - LEGACY

**Status**: Moved to `docs/legacy/` - superseded by modern autogen_tools.py architecture

Previously provided utilities for Autogen agent operations and configuration management.

#### Key Functions

```python
def load_agent_config(config_path: str) -> Dict[str, Any]:
    """Load agent configuration from JSON file"""
    
def QueryParser:
    """Parse natural language queries for agent processing"""
    
def DataProcessor:
    """Process and format data for agent consumption"""
```

#### Usage Example

```python
# LEGACY: # LEGACY: from src.utils.agent_utils import load_agent_config
# Current: Use src/tools/autogen_tools.py, DataProcessor
# Current: Use src/tools/autogen_tools.py for modern agent functionality

# Load agent configuration
config = load_agent_config('config/agents.json')

# Process data for agents
processor = DataProcessor()
formatted_data = processor.format_for_agent(raw_market_data)
```

### Date Utils (`date_utils.py`)

Provides timezone-aware date processing specifically designed for financial market data. **Consolidated datetime module** - all datetime operations across the project should use these utilities to reduce library imports and ensure consistency.

#### Core DateTime Functions (Consolidated)

```python
# Timestamp generation functions
def now_iso() -> str:
    """Get current timestamp as ISO string (replaces datetime.now().isoformat())"""
    
def now_timestamp() -> str:
    """Get current timestamp for filenames/IDs (replaces datetime.now().strftime())"""
    
def today_str() -> str:
    """Get today's date as YYYY-MM-DD string (replaces datetime.now().strftime('%Y-%m-%d'))"""

# Date parsing and formatting
def parse_date_string(date_str: str) -> datetime:
    """Parse various date string formats (replaces datetime.strptime())"""
    
def format_for_filename(dt: datetime = None) -> str:
    """Format datetime for filenames (no special characters)"""
```

#### Market Data Functions

```python
def get_default_timezone() -> timezone:
    """Get default timezone for market data (US/Eastern)"""

def process_date_param(date_str: str) -> str:
    """Process date parameters from various formats"""
    # Supports: "2024-01-15", "-30d", "today", etc.

def get_processed_date_range(start: str, end: str) -> Tuple[str, str]:
    """Get processed date range with timezone handling"""

def localize_df(df: pd.DataFrame, tz: timezone) -> pd.DataFrame:
    """Localize DataFrame index to specified timezone"""

# Business day utilities
def add_business_days(date_str: str, days: int) -> str:
    """Add business days to a date string"""
    
def is_business_day(date_str: str) -> bool:
    """Check if a date is a business day"""
    
def date_range_trading_days(start_date: str, end_date: str) -> list:
    """Generate list of trading days between dates"""
```

#### Usage Example

```python
from src.utils.date_utils import (
    now_iso, now_timestamp, today_str, parse_date_string,
    get_processed_date_range, localize_df
)

# Use consolidated datetime functions (preferred over datetime imports)
timestamp = now_iso()          # "2025-09-11T15:31:22.396607"
filename_ts = now_timestamp()  # "20250911_153122"
current_date = today_str()     # "2025-09-11"

# Parse date strings consistently
parsed_date = parse_date_string("2024-01-15")

# Process flexible date inputs
start, end = get_processed_date_range("-30d", "today")

# Localize market data to Eastern timezone
df = localize_df(market_data, get_default_timezone())
```

### Indicator Library (`indicator_library.py`)

Technical analysis indicators that complement GEX calculations.

#### Available Indicators

```python
class TechnicalIndicators:
    def sma(self, data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        
    def ema(self, data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        
    def rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        
    def bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2):
        """Bollinger Bands"""
        
    def macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD Indicator"""
        
    def atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
        """Average True Range"""
```

#### Usage Example

```python
from src.utils.indicator_library import TechnicalIndicators

indicators = TechnicalIndicators()

# Calculate RSI for SPY data
rsi = indicators.rsi(spy_data['close'], period=14)

# Calculate Bollinger Bands
upper, middle, lower = indicators.bollinger_bands(spy_data['close'])

# Combine with GEX data for enhanced analysis
combined_signals = combine_gex_and_technical(gex_data, rsi, upper, lower)
```

### Data Normalizer (`data_normalizer.py`)

Preprocesses and normalizes market data for consistent analysis.

#### Key Functions

```python
class DataNormalizer:
    def normalize_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize OHLCV data to standard format"""
        
    def handle_missing_data(self, df: pd.DataFrame, method: str = 'forward_fill') -> pd.DataFrame:
        """Handle missing data points"""
        
    def detect_outliers(self, series: pd.Series, method: str = 'iqr') -> pd.Series:
        """Detect outliers using various methods"""
        
    def winsorize(self, series: pd.Series, limits: Tuple[float, float] = (0.01, 0.01)) -> pd.Series:
        """Winsorize extreme values"""
        
    def standardize_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate standardized returns"""
```

#### Usage Example

```python
from src.utils.data_normalizer import DataNormalizer

normalizer = DataNormalizer()

# Normalize raw market data
clean_data = normalizer.normalize_ohlcv(raw_data)

# Handle missing data points
complete_data = normalizer.handle_missing_data(clean_data, method='linear_interpolate')

# Remove outliers before analysis
filtered_data = normalizer.winsorize(complete_data['returns'], limits=(0.005, 0.005))
```

### Autogen Examples (`autogen_examples.py`) - LEGACY

**Status**: Moved to `docs/legacy/` - reference implementations preserved for documentation

Previously contained reference implementations and examples for the Autogen framework integration.

#### Reference Patterns

```python
# Multi-agent conversation setup
def create_analysis_conversation():
    """Example multi-agent conversation for pattern analysis"""

# Tool integration patterns  
def setup_market_analysis_tools():
    """Setup tools for market data analysis agents"""

# Cost optimization examples
def implement_cost_routing():
    """Example cost-based model routing"""
```

## Validation Utilities

Located in `src/validation/`, these utilities ensure research integrity and prevent bias.

### Data Obfuscation (`data_obfuscation.py`)

Removes temporal and ticker references to prevent LLM training data leakage.

#### Key Classes

```python
class DataObfuscator:
    def __init__(self):
        self.date_mapping = {}
        self.ticker_mapping = {}
        
    def obfuscate_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert dates to relative format (Day T+0, T+1, etc.)"""
        
    def obfuscate_tickers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert tickers to generic names (INDEX_1, STOCK_A, etc.)"""
        
    def remove_context_clues(self, text: str) -> str:
        """Remove market event references and contextual clues"""
        
    def create_reverse_mapping(self) -> Dict:
        """Create mapping to restore original data"""
```

#### Usage Example

```python
from src.validation.data_obfuscation import DataObfuscator

obfuscator = DataObfuscator()

# Obfuscate data for LLM testing
obfuscated_data = obfuscator.obfuscate_dataframe(market_data)
reverse_mapping = obfuscator.create_reverse_mapping()

# Test LLM without temporal bias
llm_results = test_pattern_analysis(obfuscated_data)

# Restore original context for interpretation
final_results = restore_context(llm_results, reverse_mapping)
```

### Date Sanitizer (`date_sanitizer.py`)

Sanitizes date information for unbiased backtesting.

#### Key Functions

```python
def sanitize_backtest_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove specific date information that could bias results"""
    
def create_anonymous_timeline(df: pd.DataFrame) -> pd.DataFrame:  
    """Create anonymous timeline preserving market dynamics"""
    
def preserve_market_structure(df: pd.DataFrame) -> pd.DataFrame:
    """Maintain market microstructure while removing calendar effects"""
```

### Obfuscation Validator (`obfuscation_validator.py`)

Validates the effectiveness of data obfuscation techniques.

#### Validation Tests

```python
class ObfuscationValidator:
    def test_temporal_leakage(self, original: pd.DataFrame, obfuscated: pd.DataFrame) -> Dict:
        """Test for temporal information leakage"""
        
    def test_ticker_anonymity(self, original: pd.DataFrame, obfuscated: pd.DataFrame) -> Dict:
        """Validate ticker anonymization effectiveness"""
        
    def test_pattern_preservation(self, original: pd.DataFrame, obfuscated: pd.DataFrame) -> Dict:
        """Ensure important patterns are preserved during obfuscation"""
```

## Usage Patterns

### Common Workflow

```python
# 1. Load and normalize data
from src.utils.data_normalizer import DataNormalizer
from src.utils.date_utils import get_processed_date_range

normalizer = DataNormalizer()
start_date, end_date = get_processed_date_range("-1y", "today")

# 2. Calculate technical indicators
from src.utils.indicator_library import TechnicalIndicators
indicators = TechnicalIndicators()
rsi = indicators.rsi(price_data['close'])

# 3. Obfuscate for LLM testing
from src.validation.data_obfuscation import DataObfuscator
obfuscator = DataObfuscator()
clean_data = obfuscator.obfuscate_dataframe(combined_data)

# 4. Configure agents
# LEGACY: from src.utils.agent_utils import load_agent_config
# Current: Use src/tools/autogen_tools.py
agent_config = load_agent_config('research_agents.json')
```

### Integration with Main Pipeline

```python
# These utilities integrate with main components:
# - GEX Calculator uses date_utils for timezone handling
# - Tokenizer uses data_normalizer for preprocessing  
# - Pattern Miner uses indicator_library for feature engineering
# - LLM Integration uses autogen_tools.py for modern configuration
# - All components use validation tools for research integrity
```

## Configuration and Setup

### Environment Variables

```bash
# Set timezone for market data
MARKET_TIMEZONE=US/Eastern

# Agent configuration paths
AGENT_CONFIG_PATH=@config/agents.json

# Validation settings
OBFUSCATION_ENABLED=true
VALIDATION_STRICT_MODE=true
```

### Dependencies

- pandas: Data manipulation
- numpy: Numerical operations  
- pytz: Timezone handling
- autogen-core: Agent framework
- scipy: Statistical functions

## Best Practices

1. **Always use date_utils** for any date/time operations - **NEVER import datetime directly**
   - Use `now_iso()`, `now_timestamp()`, `today_str()` instead of `datetime.now()`
   - Use `parse_date_string()` instead of `datetime.strptime()`
   - This reduces library imports and ensures consistency across the project
2. **Normalize data** before feeding to any analysis component
3. **Obfuscate data** before LLM testing to ensure research integrity
4. **Validate obfuscation** effectiveness regularly
5. **Use autogen_tools.py** for modern agent configuration and API integration
6. **Combine technical indicators** with GEX analysis for richer insights

## Testing

Each utility module includes comprehensive unit tests:

```bash
# Run utility tests
python -m pytest src/utils/tests/
python -m pytest src/validation/tests/

# Test specific modules
python -m pytest src/utils/tests/test_date_utils.py
python -m pytest src/validation/tests/test_obfuscation.py
```
