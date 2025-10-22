# 3. Methodology

**Reference**: See `methodology_clarifications.md` for detailed technical Q&A

---

## 3.1 Terminology and Definitions

### Core Concepts

**Dealer Constraint Patterns**:
We test **dealer constraint patterns** - recurring market structures that arise when regulatory requirements (delta neutrality mandate) or risk limits (gamma exposure thresholds) force dealers into predictable hedging behavior.

**Precise Hierarchy**:

1. **Constraint** (causal mechanism): Regulatory/risk requirement forcing behavior
   - Example: Delta neutrality mandate, margin requirements, position limits

2. **Pattern** (recurring structure): Observable market state created when constraint binds
   - Example: Net negative gamma + spot near flip point → dealers must hedge directionally

3. **Rule-based detection** (identification method): Deterministic thresholds identifying when structural conditions exist
   - Example: IF (Net GEX < -$2B AND |spot - flip_point| < 2%) THEN conditions present

**Negative Gamma Regime** (formal definition):
Market state where dealers hold net short gamma exposure. To maintain delta neutrality (regulatory requirement), dealers must trade in the same direction as price moves: sell into rallies (as delta increases) and buy into dips (as delta decreases). This forced hedging behavior amplifies price volatility and creates directional momentum.

Mathematical expression:

```
Net Dealer Gamma = Σ(Call Gamma × OI × multiplier) - Σ(Put Gamma × OI × multiplier)

If Net Gamma < 0:
  - Price ↑ → Dealer delta more positive → Must sell to rehedge
  - Price ↓ → Dealer delta more negative → Must buy to rehedge
  - Result: Volatility amplification (pro-cyclical hedging)
```

**Structural Regime vs Sentiment**:

- **Market Regime** (structural, observable): Gamma positioning state, volatility level, measurable from options data
- **Market Sentiment** (psychological, unobservable): Participant beliefs (bullish/bearish), cannot be directly measured

This work detects structural market regimes (dealer gamma positioning), not participant sentiment. The distinction is critical: regimes are observable from options market data (gamma exposure, strike distribution), while sentiment represents unobservable trader beliefs.

---

## 3.2 Pattern Taxonomy: Three-Level Classification

### Type 1: Structural Constraint Patterns ← **WE TEST ONLY THIS**

Patterns where dealer behavior is forced by:

- Regulatory requirements (delta neutrality, position limits)
- Risk limits (gamma exposure, margin requirements)
- Physical constraints (time decay, settlement mechanics)

**Characteristics**:

- Clear causal mechanism (WHO forces WHOM to do WHAT)
- Predictable under specific conditions
- Cannot be avoided by constrained agents
- Observable in market data (GEX, OI distribution)

**Examples**:

- `gamma_positioning`: Negative gamma forces directional hedging
- `stock_pinning`: OI concentration at strikes creates hedging flow
- `0dte_hedging`: Same-day expiration forces accelerated hedging

### Type 2: Statistical Regularities

Empirical patterns without established causal mechanisms:

- Correlations in historical data
- Seasonal effects without explanation
- Volume anomalies without structural driver

**Why We Exclude**: Risk of data mining, no causal validation

### Type 3: Narrative Explanations

Post-hoc storytelling without empirical validation:

- "Markets always rally in December" (selection bias)
- "Friday 3:30 PM squeeze" (requires temporal context)
- Context-dependent patterns (not mechanical)

**Why We Exclude**: Circular reasoning, not testable with obfuscation

**Methodological Choice**:
We exclusively test Type 1 patterns (structural constraint patterns) where dealer behavior is forced by regulatory requirements or risk limits. We explicitly exclude statistical anomalies without causal mechanisms (Type 2) and narrative explanations without empirical validation (Type 3).

---

## 3.3 Obfuscation Testing Framework

### 3.3.1 Motivation

**The Training Data Leakage Problem**:
LLMs trained on vast corpora may have encountered descriptions of famous market events:

- "GameStop January 2021 squeeze"
- "COVID crash March 2020 volatility"
- "Fed rate hikes 2022-2023"

Without obfuscation, LLM could recall these narratives rather than reason from market structure.

**Our Solution**:
Strip all temporal and contextual information, forcing LLM to reason from quantitative market structure (GEX values, strike relationships) alone.

### 3.3.2 Obfuscation Transformations

**PRESERVED** (quantitative structure):

- ✅ GEX values (Net GEX, Call GEX, Put GEX) - absolute dollar values
- ✅ Spot prices - absolute prices preserved (not normalized)
- ✅ Strike relationships (distance to flip point, concentration levels)
- ✅ Open interest distribution (concentration percentages)
- ✅ Volatility metrics (realized vol, IV)

**REMOVED** (temporal/contextual):

- ❌ Real dates → "Day T+0", "Day T+1", etc.
- ❌ Real tickers → "INDEX_1" (SPY), "STOCK_A" (AAPL), etc.
- ❌ Calendar references (months, years, day of week)
- ❌ Event references (COVID, Fed, specific market events)
- ❌ Economic context (recession, recovery, rate changes)

**Table 1: Obfuscation Transformations**

| Data Type | Original Example | Obfuscated Example | Purpose |
|-----------|-----------------|-------------------|---------|
| Date | 2024-01-05 | Day T+0 | Remove temporal context |
| Ticker | SPY | INDEX_1 | Remove identity hints |
| Price | $552.10 | $552.10 | Preserve structure |
| GEX | -$5.2B | -$5.2B | Preserve magnitude |
| Event | "Fed meeting" | [removed] | Remove narrative context |

**Temporal Relationships**:
Date obfuscation converts 'YYYY-MM-DD' to 'Day T+N' format, preserving sequential ordering while removing calendar context. This prevents LLM from using day-of-week patterns (e.g., Friday expiration effects) or seasonal regularities, while maintaining the ability to observe multi-day pattern development.

**Key Implication**:
LLM cannot use Friday 3:30 PM effects, monthly expiration patterns, or seasonal trends (all require calendar knowledge). Must reason from GEX structure alone.

---

## 3.4 WHO→WHOM→WHAT Causal Identification Framework

### Framework Definition

We require LLM to explicitly identify causal chains:

- **WHO**: Constrained agent (dealers with gamma exposure)
- **WHOM**: Counterparty affected (directional traders, market makers)
- **WHAT**: Specific action constraint requires (sell rallies, buy dips, hedge flow)

**This tests causal reasoning**, not correlational pattern recognition.

**Example Output**:

```
WHO: "Dealers with negative gamma exposure"
WHOM: "Market participants"
WHAT: "Force dealers to sell into rallies and buy dips, amplifying volatility"
CONFIDENCE: 85%
TIME_HORIZON: "1-3 days"
```

**Why This Matters**:

- Tests understanding of *mechanisms* (causal)
- Not just pattern recognition (correlational)
- Requires identifying agency and forced actions
- Structured output enables systematic validation

---

## 3.5 Detection Methodology

### 3.5.1 Confidence Threshold

**Mechanical Classification Threshold: 60%**

**Justification**:

1. **Statistical**: Binomial test with n=50 days, p=0.5 (random) → 60% is ~1.4 standard deviations above chance
2. **Practical**: 60% implies pattern detectable on majority of days (not rare anomaly)
3. **Conservative**: Higher than 50% (chance) but lower than 80% (very strong signal)

We classify patterns as **MECHANICAL** if detection rate ≥60% and sample size ≥30 days. This threshold represents ~1.4 standard deviations above random detection (50%), balancing statistical rigor with practical significance. Patterns detected on <60% of days are classified as NARRATIVE (context-dependent) rather than structural.

### 3.5.2 Confidence Score Calibration

**Source**: Raw LLM output (GPT-4 structured output)
**Calibration**: NOT post-processed - using model's self-assessed confidence

**Acknowledged Limitation**:
LLM confidence scores may not be well-calibrated (known limitation of GPT-4 series). We address this by:

1. Using a conservative threshold (60%)
2. Measuring prediction accuracy independently
3. Comparing results across different prompt configurations (biased vs unbiased)

**For Methods Section**:
Confidence scores (0-100%) are extracted from LLM structured output without post-processing. We do not calibrate or adjust these scores, instead using a fixed threshold (60%) to classify detections. Future work could assess confidence calibration by comparing stated confidence to prediction accuracy.

---

## 3.6 Prompt Template Configurations (Issue #90)

### 3.6.1 The Prompt Bias Discovery

**Problem Identified**: Original validation showed LLM regime labels ("NEGATIVE_GAMMA") and pattern hints in prompts - essentially revealing the answer.

**Impact**: Detection rate 100% with regime labels, 71.5% without (28.5% inflation)

### 3.6.2 Template Comparison

**Biased Prompt (Standard Template)**:

```
Day T+0
  Net GEX: -$32,905,699,168
  Regime: NEGATIVE_GAMMA                    ← Shows the answer!
  Patterns Detected: gamma_positioning      ← Shows the pattern!
  Questions: "What patterns do you see?"    ← Leading question
```

**Characteristics**:

- Shows regime classification ("NEGATIVE_GAMMA" / "POSITIVE_GAMMA")
- Includes pattern hints from rule-based detection
- Leading questions presume patterns exist
- Cannot respond "no pattern detected"

**Unbiased Prompt (New Template)**:

```
Day T+0
  Net GEX: -$32,905,699,168 (raw value, unclassified)
  Zero-gamma level: $485.00
  Questions: "Do you detect any mechanics? (Yes/No)"  ← Neutral
```

**Characteristics**:

- Raw GEX values only (no classification labels)
- No pattern hints from rule-based system
- Neutral questions allow null hypothesis
- Can respond "no pattern detected" with confidence 0

### 3.6.3 Methodological Decision (Option A)

**Primary Results**: Unbiased prompts (71.5% detection, 91.2% accuracy)
**Sensitivity Analysis**: Biased prompts (100% detection, 91-94% accuracy)

**Rationale**:

- Unbiased results prove structural detection without label leakage
- 71.5% is conservative, defensible lower bound
- 100% biased result shows upper bound with contextual hints
- Ablation study demonstrates methodological rigor

---

## 3.7 Outcome Verification

### Independent Validation

**Prediction Materialization Check**:
For each detected pattern, we calculate:

1. **Forward returns** (T+1, T+3 price movements)
2. **Realized volatility** (did volatility amplify as predicted?)
3. **Directional consistency** (did price move as mechanism suggests?)

**Rule-based Verification**:
Materialization is determined algorithmically (not subjectively):

- Pattern predicts volatility amplification → measure realized vol T+1
- Pattern predicts directional pressure → measure forward return
- Pattern predicts mean reversion → measure price return to level

**Key Metrics**:

- **Detection Rate**: % of days where pattern detected (confidence ≥60%)
- **Predictive Accuracy**: % of detections where prediction materialized
- **Net Alpha**: Average forward return - transaction costs (5 bps)

---

## 3.8 Validation Criteria

### Pattern Classification Thresholds

**MECHANICAL Pattern** (structural constraint):

- Detection rate ≥60% with obfuscation
- Sample size ≥30 days (statistical significance)
- Predictive accuracy ≥60% (predictions materialize)

**NARRATIVE Pattern** (context-dependent):

- Detection rate <60% with obfuscation
- OR: Requires temporal context (fails obfuscation test)
- OR: No consistent causal mechanism

**Data Coverage Requirement**:
≥80% of expected trading days (prevents selection bias - Issue #84)

---

## 3.9 Scope and Limitations

### What This Work Tests

**Pattern Validation** (recognition of pre-defined constraints):

- Tests LLM ability to recognize dealer constraint patterns with known causal mechanisms
- Each pattern has established academic literature documenting underlying constraint
- Validates understanding, not discovery

**NOT Pattern Discovery** (unsupervised mining):

- We do not test unsupervised pattern discovery
- Different research question (data mining vs understanding)

### Acknowledged Limitations

1. **Confidence Calibration**: Raw LLM confidence may not be well-calibrated
   - Mitigated by: Conservative threshold, independent accuracy measurement

2. **Pattern Validation Scope**: Tests recognition, not discovery
   - Defensible: Each pattern has academic literature support

3. **Single Asset Class**: SPY options only (US equity index)
   - Future work: Multi-asset validation (individual stocks, commodities, FX)

4. **Single LLM Architecture**: GPT-4 series
   - Future work: Compare reasoning models (o3-mini), open-source LLMs

---

**Status**: Methodology section template complete
**Word Count Target**: 2500-3000 words
**Next**: Section 4 (Experimental Setup) - describe data, patterns, validation pipeline
