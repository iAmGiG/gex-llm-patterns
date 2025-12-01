# 2. Background and Related Work

## 2.1 LLMs in Financial Markets

[DRAFT NEEDED]

**Literature to Cover**:

- Financial text analysis and sentiment (BERT, GPT applications)
- Price prediction using LLMs
- Trading strategy generation
- Risk management and portfolio optimization

**Gap to Emphasize**:
Most existing work focuses on *performance* (prediction accuracy) without testing *understanding* (causal reasoning about mechanisms)

**Key Citations Needed**:

- [ ] Recent LLM finance surveys
- [ ] GPT-4 financial applications
- [ ] Limitations of training data leakage

---

## 2.2 Market Microstructure: Dealer Constraints

[DRAFT NEEDED]

**Core Theory**:

- Dealer delta neutrality requirements (regulatory mandate)
- Gamma exposure and hedging flow
- Options market making and inventory management

**Established Patterns** (Type 1 - Structural Constraints):

### 2.2.1 Gamma Positioning

**Literature**: [Citations needed - dealer gamma hedging papers]

- Negative gamma regime forces pro-cyclical hedging
- Amplifies volatility through forced buying/selling
- Well-documented in market microstructure literature

### 2.2.2 Stock Pinning

**Literature**: [Citations needed - options expiration pinning]

- OI concentration at strikes creates hedging pressure
- Dealers hedge delta → price gravitates toward high OI strikes
- Strongest near expiration (time decay accelerates)

### 2.2.3 0DTE Hedging

**Literature**: [Citations needed - same-day expiration effects]

- Same-day expiration creates forced rebalancing
- Gamma exposure extremely concentrated
- Recent phenomenon (0DTE volume explosion 2022-2024)

---

## 2.3 Pattern Validation Methodologies

[DRAFT NEEDED]

**Existing Approaches**:

1. **Historical Backtesting**: Test rules on historical data
   - Problem: Data mining bias, overfitting

2. **Expert Validation**: Human traders assess patterns
   - Problem: Subjective, not scalable, experience-dependent

3. **Academic Studies**: Rigorous econometric testing
   - Problem: Requires large samples, specific hypotheses

**Our Contribution**:
Obfuscation testing framework - automated, rigorous, prevents memorization

---

## 2.4 Positioning Our Contribution

[DRAFT NEEDED]

**What Makes This Work Novel**:

1. **First LLM market microstructure validation**: No prior work tests LLM understanding of dealer constraints

2. **Obfuscation testing framework**: Novel methodology preventing training data leakage

3. **Prompt bias discovery**: First to identify and quantify regime label inflation (100% → 71%)

4. **Multi-pattern generalization**: Tests across 3 constraint types (not single pattern)

**Table: Comparison to Prior Work**

| Approach | Tests Understanding? | Prevents Memorization? | Multi-Pattern? | Causal Framework? |
|----------|---------------------|----------------------|----------------|-------------------|
| Traditional Backtest | ❌ No | ❌ No | ✅ Yes | ❌ No |
| Expert Validation | ⚠️ Subjective | ✅ Yes | ✅ Yes | ⚠️ Implicit |
| LLM Price Prediction | ❌ No | ❌ No | ✅ Yes | ❌ No |
| **Our Work** | **✅ Yes** | **✅ Yes** | **✅ Yes** | **✅ Explicit** |

---

**Status**: Template created - needs literature review and citations
**Word Count Target**: 1500-2000 words
**Next**: Complete citations for dealer constraint literature
