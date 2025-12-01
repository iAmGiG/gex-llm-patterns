# 4. Experimental Setup

**Reference**: See `full_year_2024_validation.md` for complete validation details

---

## 4.1 Data Sources and Coverage

### 4.1.1 Options Data

**Source**: [Specify data provider - Polygon, Alpha Vantage, etc.]
**Asset**: SPY (S&P 500 ETF) options
**Period**: Full year 2024 (January 2 - December 31)
**Trading Days**: 252 expected, 242 available (96% coverage)

**Data Quality**:

- All contracts with complete bid/ask/OI/IV data
- Strike range: Typical ±10% from spot
- Expirations: All available tenors
- Updates: End-of-day snapshots

### 4.1.2 Coverage Validation (Issue #84)

**Requirement**: ≥80% of expected trading days
**Achieved**: 242/252 days (96% coverage) ✅
**Purpose**: Prevents selection bias from incomplete data

---

## 4.2 Pattern Definitions

### 4.2.1 Pattern 1: gamma_positioning

**Academic Literature**: [Citations needed - dealer gamma hedging]

**Structural Constraint**:

- Dealers with net negative gamma must hedge delta changes
- Regulatory requirement: Maintain delta neutrality
- Result: Pro-cyclical hedging (amplifies volatility)

**Rule-Based Detection Criteria**:

```
IF Net GEX < -$2B AND
   |Spot - Flip Point| < 2% AND
   Call Gamma Concentration > 70%
THEN gamma_positioning conditions present
```

**WHO→WHOM→WHAT**:

- WHO: Dealers with negative gamma exposure
- WHOM: Directional traders
- WHAT: Forced to sell rallies, buy dips (amplify volatility)

### 4.2.2 Pattern 2: stock_pinning

**Academic Literature**: [Citations needed - options pinning]

**Structural Constraint**:

- Heavy OI at strike creates delta hedging flow
- Dealers must adjust hedges as price approaches strike
- Result: Price gravitates toward high-OI strike (pinning effect)

**Rule-Based Detection Criteria**:

```
IF OI Concentration at Strike > 80% AND
   |Spot - Strike| < 1% AND
   Days to Expiration < 5
THEN stock_pinning conditions present
```

**WHO→WHOM→WHAT**:

- WHO: Dealers hedging concentrated gamma at strike
- WHOM: Market participants trading near strike
- WHAT: Hedging flow pins price to strike level

### 4.2.3 Pattern 3: 0dte_hedging

**Academic Literature**: [Citations needed - 0DTE options effects]

**Structural Constraint**:

- Same-day expiration creates extreme gamma concentration
- Time decay accelerates exponentially in final hours
- Result: Forced rapid rehedging by dealers

**Rule-Based Detection Criteria**:

```
IF Days to Expiration == 0 AND
   Net GEX magnitude > $3B AND
   Gamma concentration > 75%
THEN 0dte_hedging conditions present
```

**WHO→WHOM→WHAT**:

- WHO: Dealers with 0DTE gamma exposure
- WHOM: Intraday traders
- WHAT: Forced rapid hedging creates intraday volatility

---

## 4.3 Prompt Template Configurations

### 4.3.1 Standard Template (Biased)

**File**: `config_defaults/llm_prompts.yaml` → `standard`

**Characteristics**:

- Includes regime labels ("NEGATIVE_GAMMA", "POSITIVE_GAMMA")
- Shows pattern hints from rule-based detection
- Leading questions ("What patterns do you see?")
- Cannot respond "no pattern detected"

**Use Case**: Baseline validation, upper bound performance

### 4.3.2 Unbiased Template (Primary)

**File**: `config_defaults/llm_prompts.yaml` → `unbiased`

**Characteristics**:

- Raw GEX values only (no classification)
- No pattern hints
- Neutral questions ("Do you detect any mechanics?")
- Allows null hypothesis ("no pattern detected" with confidence 0)

**Use Case**: Academic validation, primary results (Option A)

---

## 4.4 Validation Pipeline Implementation

### 4.4.1 System Architecture

**Component 1: Data Fetcher**

- Load options chain from cache (`cache/options/SPY/YYYY-MM-DD.pickle`)
- Extract spot price, strikes, OI, IV, Greeks

**Component 2: GEX Calculator**

- Calculate net GEX, call/put gamma, flip point
- Compute concentration metrics
- Output: GEX profile for date

**Component 3: Data Obfuscator**

- Convert dates → "Day T+N"
- Convert tickers → "INDEX_1"
- Remove contextual references
- Output: Obfuscated GEX data

**Component 4: LLM Agent** (MarketMechanicsAgent)

- Build prompt from template configuration
- Call LLM with structured output schema
- Extract: WHO, WHOM, WHAT, confidence, time_horizon
- Output: Detection result

**Component 5: Outcome Calculator**

- Fetch T+1, T+3 forward prices
- Calculate forward returns
- Measure realized volatility
- Verify prediction materialization
- Output: Outcome metrics

### 4.4.2 Batch Processing

**Efficiency Optimization**:

- Process 10 dates per LLM API call (75% cost reduction)
- Maintains obfuscation (all dates presented as "Day T+N")
- Single structured response with all detections

**Implementation**: `MarketMechanicsAgent.run_batch_experiments()`

---

## 4.5 Validation Metrics

### 4.5.1 Detection Metrics

**Detection Rate**:

```
Detection Rate = (Days with Confidence ≥60%) / Total Days Tested
```

**Threshold**: ≥60% for MECHANICAL classification

**Statistical Significance**: 95% confidence intervals using binomial proportion

### 4.5.2 Accuracy Metrics

**Predictive Accuracy**:

```
Accuracy = (Predictions Materialized) / Total Detections
```

**Materialization Criteria** (rule-based):

- Pattern predicts volatility → Realized vol T+1 > baseline
- Pattern predicts directionality → Forward return matches prediction
- Pattern predicts mean reversion → Price returns to level

### 4.5.3 Economic Metrics

**Net Alpha** (informational, not validation criterion):

```
Net Alpha = Mean(Forward Returns) - Transaction Costs (5 bps)
```

**Note**: Economic profitability is NOT required for pattern validation (we test understanding, not trading edge)

---

## 4.6 Reproducibility

### 4.6.1 Command Structure

**Single Pattern Validation**:

```bash
python scripts/validation/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-12-31 \
  --prompt-template unbiased \
  --confidence 60.0 \
  --with-outcomes
```

**Output**: `reports/validation/pattern_taxonomy/gamma_positioning_SPY_2024_unbiased.yaml`

### 4.6.2 Code Availability

**Repository**: [To be shared upon publication]
**Key Files**:

- `src/agents/market_mechanics_agent.py` - LLM interface
- `src/validation/data_obfuscation.py` - Obfuscation logic
- `src/validation/outcome_calculator.py` - Forward return calculation
- `config_defaults/llm_prompts.yaml` - Prompt templates

---

**Status**: Experimental setup section template complete
**Word Count Target**: 1500-2000 words
**Next**: Expand with specific implementation details
