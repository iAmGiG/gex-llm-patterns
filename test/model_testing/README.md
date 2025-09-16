# Model Testing Scripts

This directory contains one-off testing scripts used during model selection research (Issue #62).

## Scripts

### Final Production Tests
- `test_o3_mini_final.py` - Final O3-mini validation test (75% confidence)
- `test_o4_mini_final.py` - Final O4-mini validation test (failed)
- `test_gpt5_mini.py` - GPT-5 mini testing script

### Development/Debug Scripts
- `simple_model_test.py` - Simple prompt testing across models
- `debug_gpt5_mini.py` - Debug GPT-5 mini basic functionality
- `debug_reasoning_models.py` - Debug O3/O4 raw responses
- `reasoning_model_test.py` - Chain-of-thought prompt testing
- `final_reasoning_test.py` - Final reasoning model validation

## Results

See `/reports/working_model_results/` for the actual test outputs and analysis.

## Usage

These scripts were used for one-time model evaluation and may be useful for:
- Re-testing models with different prompts
- Validating new model releases
- Debugging API compatibility issues
- Comparing model performance

**Note**: These are research/testing scripts, not production code. For production model usage, see `/src/llm/autogen_market_mechanics.py`.