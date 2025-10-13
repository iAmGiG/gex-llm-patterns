# Token Configuration Strategy

## Overview

The GEX-LLM system uses a hybrid approach with different token configurations for different components.

## Architecture

### AutoGen Tools (NO LLM TOKENS)

**Location**: `src/tools/autogen_tools.py`
**Type**: Direct Python function calls
**Token Usage**: Zero - these are not LLM calls

**Functions**:

- `fetch_options_data()` - Direct cache/API data retrieval
- `calculate_gamma_exposure()` - Mathematical GEX calculations
- `fetch_market_data()` - Direct market data API calls

**Key Point**: These tools run as pure Python functions. No LLM involvement, no token costs.

### Market Mechanics Analysis (LLM REASONING)

**Location**: `src/llm/autogen_market_mechanics.py`
**Type**: O3-mini/O4-mini for reasoning, GPT-4o-mini for tool calls
**Token Limit**: 4000 tokens for analysis

**Configuration**:

```python
# For O3-mini models
client_params["max_completion_tokens"] = 4000

# For standard models (if used)
client_params["max_tokens"] = 4000
```

**Usage**: Complex market mechanics interpretation requiring detailed reasoning.

## Token Usage by Component

| Component | Model | Token Limit | Purpose |
|-----------|-------|-------------|---------|
| AutoGen Tools | None | 0 | Direct function calls |
| Market Analysis | O3-mini/O4-mini | 4000 | Pattern reasoning |
| Tool Calling | GPT-4o-mini | Minimal | Function execution |
| Data Fetching | None | 0 | Cache/API calls |
| GEX Calculation | None | 0 | Mathematical operations |

## Cost Optimization

### High Efficiency Design

- **Tool Calls**: Zero tokens (direct Python functions)
- **Data Processing**: Zero tokens (local calculations)
- **LLM Usage**: Only for complex market interpretation
- **Token Cost**: ~4000 tokens per analysis (not per tool call)

### Example Flow

```bash
1. fetch_options_data() → 0 tokens (cache hit)
2. calculate_gamma_exposure() → 0 tokens (math)
3. Market mechanics analysis → 4000 tokens (O3-mini)
Total: 4000 tokens for complete analysis
```

## Failed Test Handling

### Token Limit Errors

**Detection**: System detects "max_tokens" errors in LLM responses
**Action**: Mark test as `failed_retry_needed`
**Resolution**: Increased token limits from 1000 → 4000

### Error Categories

- `token_limit`: LLM hit token limit, needs retry
- `llm_failure`: Other LLM errors
- `invalid_response`: Null confidence/direction

## Configuration Files

### LLM Configuration

**File**: `src/llm/autogen_market_mechanics.py`
**Key Setting**: `analysis_tokens = 4000`

### Tool Configuration

**File**: `src/tools/autogen_tools.py`
**Key Point**: No token configuration needed (direct function calls)

## Best Practices

1. **Separate Concerns**: Tools do data/math, LLM does reasoning
2. **Token Efficiency**: Only use LLM for complex interpretation
3. **Error Handling**: Detect and retry token limit failures
4. **Cost Control**: High token limits only for analysis, not tools

## Validation

**Test**: `scripts/validation/production_cache_test.py`
**Result**: ✅ 90% confidence analysis with 4000 tokens
**Performance**: ~4000 tokens per complete market analysis
