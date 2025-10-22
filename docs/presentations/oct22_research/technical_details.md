# Technical Details for Oct 22 Presentation

**Accurate system specifications for diagrams and slides**

---

## LLM Configuration

### Model Selection (Cost-Optimized)

**Tool Calling**: GPT-4o-mini

- **Purpose**: Function calls, structured outputs
- **Rationale**: Cost-efficient for API interactions
- **Cost**: ~$0.15 per 1M input tokens

**Reasoning**: o3-mini

- **Purpose**: Pattern analysis, causal reasoning
- **Rationale**: Cost-efficient, chosen over o4-mini and newer models
- **Note**: Deliberately selected o3-mini for cost optimization despite newer options

**Why Not GPT-4**:

- GPT-4 mentioned in test diagrams - INCORRECT
- Actual implementation uses o3-mini for reasoning (cost savings)

---

## System Architecture (6 Stages)

### Stage 1: Options Data

- **Input**: SPY options chain (calls + puts)
- **Source**: Market data API
- **Format**: Strike prices, open interest, implied volatility

### Stage 2: GEX Calculator

- **Computes**:
  - Net GEX (gamma exposure)
  - Call GEX, Put GEX
  - Flip point (zero gamma level)
- **Units**: Dollars per 1% move

### Stage 3: Data Obfuscator

- **Removes**: Dates, tickers, event context
- **Preserves**: GEX values, spot prices (absolute)
- **Format**: "Day T+0", "Day T+1", "INDEX_1"
- **Purpose**: Prevent LLM training data memorization

### Stage 4: LLM Agent

- **Tool calling**: GPT-4o-mini
- **Reasoning**: o3-mini
- **Framework**: WHO→WHOM→WHAT causal identification
- **Output**: Pattern detection + predictions

### Stage 5: Outcome Calculator

- **Computes**:
  - Forward returns (T+1, T+3)
  - Forward extremes (max gain/loss)
  - Realized volatility
- **Purpose**: Verify predictions materialize

### Stage 6: Statistical Validator

- **Metrics**:
  - Detection rate (% days pattern detected)
  - Predictive accuracy (% predictions correct)
  - Net alpha (economic profitability)
- **Threshold**: 60% detection = "mechanical" pattern

---

## Data Specifications

### Sample Size

- **Trading days**: 242 (full 2024)
- **Patterns tested**: 3 (gamma_positioning, stock_pinning, 0dte_hedging)
- **Total tests**: 726 (242 days × 3 patterns)

### Obfuscation Details

- **Dates**: 2024-01-02 → "Day T+0"
- **Tickers**: SPY → "INDEX_1"
- **Preserved**: GEX values (exact dollar amounts)
- **Context removed**: News, events, day-of-week

---

## Key Results (For Slides)

### Primary Results (Unbiased Prompts)

- **Detection**: 71.5% average (all patterns >60% threshold)
- **Accuracy**: 91.2% (predictions materialize)
- **Statistical significance**: p < 0.001 (all patterns)

### Prompt Bias Sensitivity

- **Biased detection**: 100% (with regime labels)
- **Unbiased detection**: 71.5% (no labels)
- **Drop**: -28.5% (proves structural detection without hints)
- **Accuracy stable**: -1.0% change (patterns are real)

### Detection-Profitability Divergence

- **Detection**: Remains 84-100% (Q2-Q4 2024)
- **Alpha**: Declines +2 → -1 bps
- **Interpretation**: LLM detects structure, not profits

---

## Common Mistakes to Avoid

### ❌ WRONG

- "LLM Agent: GPT-4" (outdated, from test diagram)
- "Using latest models" (we deliberately chose o3-mini for cost)

### ✅ CORRECT

- "LLM Agent: Tool calling (GPT-4o-mini), Reasoning (o3-mini)"
- "Cost-optimized model selection: o3-mini chosen over newer options"

---

## Diagram Specifications

### For Paper (IEEE Two-Column)

- **Format**: PDF (vector)
- **Width**: 3.5 inches (single column)
- **DPI**: 300+
- **Colors**: Muted, professional

### For Presentation Slides

- **Format**: PNG
- **DPI**: 300
- **Width**: Full slide width (~10 inches)
- **Colors**: Bold, high contrast
- **Background**: Transparent preferred

---

## Pattern Definitions (Brief)

### Gamma Positioning

- **Constraint**: Dealers must maintain delta neutrality
- **Mechanism**: Negative gamma forces hedging into price moves
- **Detection**: 69.4% (unbiased)

### Stock Pinning

- **Constraint**: Gamma concentration at strike prices
- **Mechanism**: Dealers hedge to keep stock near max gamma
- **Detection**: 67.4% (unbiased)

### 0DTE Hedging

- **Constraint**: Exponential time decay on expiration day
- **Mechanism**: Rapid gamma changes force continuous hedging
- **Detection**: 77.7% (unbiased)

---

## Questions to Anticipate

**Q: Why o3-mini instead of newer models?**
A: Cost optimization. o3-mini provides sufficient reasoning capability at fraction of cost. Newer models (o4-mini, etc.) don't justify 2-3x price increase for this task.

**Q: Why not use GPT-4 for everything?**
A: GPT-4o-mini handles tool calling well at lower cost. o3-mini excels at reasoning tasks. Hybrid approach optimizes cost/performance.

**Q: How do you prevent LLM from memorizing training data?**
A: Obfuscation testing - remove all dates, tickers, events. LLM can't use "I remember SPY crashed on 2024-03-15" because it only sees "Day T+0, INDEX_1".

**Q: Why 71.5% instead of 100%?**
A: 71.5% is from unbiased prompts (no regime label hints). More academically defensible. 100% achieved with biased prompts, but proves label leakage.

**Q: What's the contribution?**
A: Novel validation methodology - obfuscation testing proves LLMs can detect structural market microstructure patterns without temporal context or training data memorization.

---

**File**: `docs/presentations/oct22_research/TECHNICAL_DETAILS.md`
**Last Updated**: October 18, 2025
**Issue**: #95
