# LLM Cost Optimization Test Results (Issue #109)

**Date**: 2025-11-03 22:03:30

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

- ❌ 2024-02-08: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-27: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-26: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-11: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-28: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-25: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-22: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-01-16: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-14: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-04: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'

### o3-mini

- ❌ 2024-02-08: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-27: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-26: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-11: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-28: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-25: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-22: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-01-16: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-14: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-04: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'

### gpt-5-mini

- ❌ 2024-02-08: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-27: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-26: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-11: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-28: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-25: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-02-22: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-01-16: ERROR - MarketMechanicsAgent.run_experiment() got an unexpected keyword argument 'symbol'
- ❌ 2024-03-14: ERROR - [Errno 32] Broken pipe
- ❌ 2024-03-04: ERROR - [Errno 32] Broken pipe

