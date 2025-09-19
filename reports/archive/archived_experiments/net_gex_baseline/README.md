# Archived: Net GEX Baseline Experiment

## Why Archived

The net GEX baseline experiment using aggregate GEX values was too simplistic and generated meaningless results:

- **Fundamental Flaw**: Only used 1 aggregate GEX number instead of 7,950+ individual options contracts
- **Poor Signal Generation**: Both mechanical and LLM strategies produced only 1 trade per quarter
- **Missed Opportunities**: Ignored 251 major strike-level trading opportunities per day
- **No Real Differentiation**: LLM and mechanical strategies produced identical results

## Key Discovery Leading to Better Approach

The experiment revealed a critical insight: **We need strike-level analysis, not aggregate GEX**.

### What We Found in the Data

- 7,950+ individual options contracts with rich signal potential
- 412K+ volume contracts at specific strikes
- 353:1 put/call ratios indicating extreme sentiment
- Gamma concentrations at specific price levels
- Clear dealer positioning at individual strikes

### Next Generation Approach

The continuous experiment framework now focuses on:

**V2: Strike-Level GEX Discovery**

- Individual strike analysis instead of aggregate
- High-volume strike detection (>100K contracts)
- Gamma concentration mapping
- Extreme imbalance detection (>10:1 ratios)
- Target: 20+ high-quality signals per month

This archive preserves the learning but shifts focus to the real opportunity in strike-level options analysis.

## Files Archived

- `mechvsllm_SPY_2024Q1.json` - Q1 2024 net GEX comparison results (removed - sparse data with no meaningful insights)
