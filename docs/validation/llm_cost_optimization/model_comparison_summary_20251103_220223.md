# LLM Cost Optimization Test Results (Issue #109)

**Date**: 2025-11-03 22:02:23

**Test Configuration**:
- Ground Truth: gamma_positioning_SPY_2024Q1.yaml
- Sample Size: 10 dates
- Models: GPT-4o, o3-mini, GPT-5 mini

## Results Summary

| Model | Detection Rate | Match Rate | Errors | Total Cost | Avg Cost/Query |
|-------|----------------|------------|--------|------------|----------------|
| gpt-4o | 0/10 (0.0%) | 0/0 (0.0%) | 10 | $0.000000 | $0.000000 |
| o3-mini | 0/10 (0.0%) | 0/0 (0.0%) | 10 | $0.000000 | $0.000000 |
| gpt-5-mini | 0/10 (0.0%) | 0/0 (0.0%) | 10 | $0.000000 | $0.000000 |

## Cost Comparison

### gpt-4o
- Avg cost per query: $0.000000
- vs GPT-4o: 0.0% more expensive

### o3-mini
- Avg cost per query: $0.000000
- vs GPT-4o: 0.0% more expensive

### gpt-5-mini
- Avg cost per query: $0.000000
- vs GPT-4o: 0.0% more expensive

## Detailed Results

### gpt-4o

- ❌ 2024-02-26: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-06: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-20: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-19: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-01-18: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-15: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-01-22: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-13: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-22: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-04: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'

### o3-mini

- ❌ 2024-02-26: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-06: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-20: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-19: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-01-18: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-15: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-01-22: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-13: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-22: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-04: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'

### gpt-5-mini

- ❌ 2024-02-26: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-06: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-20: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-19: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-01-18: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-15: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-01-22: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-13: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-02-22: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'
- ❌ 2024-03-04: ERROR - MarketMechanicsAgent.__init__() got an unexpected keyword argument 'model'

