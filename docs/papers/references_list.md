# References List for Paper #1

**Date**: October 16, 2025
**Purpose**: Comprehensive list of citations to format for IEEE LLM-Finance 2025 paper

---

## References We've Mentioned in Documents

### Regulatory Framework (Foundational)

1. **SEC Rule 15c3-1: Net Capital Rule**
   - Source: U.S. Securities and Exchange Commission
   - URL: https://www.sec.gov/rules-regulations
   - Purpose: Broker-dealer capital requirements, aggregate risk measurement
   - **Citation needed**: Official SEC regulation document

2. **FINRA Rule 4210: Margin Requirements**
   - Source: Financial Industry Regulatory Authority
   - URL: https://www.finra.org/rules-guidance
   - Purpose: Margin requirements for market makers
   - **Citation needed**: Official FINRA rule

3. **Basel III Banking Regulations**
   - Source: Basel Committee on Banking Supervision
   - Purpose: Bank capital requirements for trading desks
   - **Citation needed**: BIS Basel III framework document

4. **Dodd-Frank Wall Street Reform Act (2010)**
   - Source: U.S. Congress
   - Purpose: Post-2008 financial regulation, derivatives trading
   - **Citation needed**: Public Law 111-203

5. **EU MiFID II (Markets in Financial Instruments Directive)**
   - Source: European Parliament
   - Purpose: Position limits and risk management requirements
   - **Citation needed**: Directive 2014/65/EU

---

### Academic Papers (Core Theory)

6. **Ni, Pearson, Poteshman (2005): Stock Price Clustering on Option Expiration Dates**
   - Full citation needed: Journal of Financial Economics, Vol. 78
   - Topic: Option expiration pinning effect
   - Why relevant: Establishes dealer hedging creates price clustering

7. **Coval & Stafford (2007): Asset Fire Sales in Equity Markets**
   - Full citation needed: Journal of Financial Economics
   - Topic: Forced trading flows impact on prices
   - Why relevant: Parallel to forced dealer hedging flows

8. **Black & Scholes (1973): The Pricing of Options and Corporate Liabilities**
   - Full citation: Journal of Political Economy, Vol. 81, No. 3, pp. 637-654
   - Purpose: Foundational options pricing, gamma calculation
   - Why relevant: Our GEX calculations use Black-Scholes formula

9. **Grossman & Miller (1988): Liquidity and Market Structure**
   - Full citation needed: Journal of Finance
   - Topic: Market maker inventory risk and hedging
   - Why relevant: Theoretical foundation for dealer hedging behavior

---

### Practitioner Literature (Market Mechanics)

10. **SpotGamma (2019): Gamma Exposure and Market Dynamics**
    - Source: SpotGamma Research
    - URL: https://spotgamma.com (check for white papers)
    - Topic: Gamma exposure metrics in practice
    - Why relevant: Established GEX in practitioner community

11. **SqueezeMetrics (2020): Dark Index and Dealer Positioning**
    - Source: SqueezeMetrics Research
    - URL: https://squeezemetrics.com
    - Topic: Gamma exposure index (DIX)
    - Why relevant: Alternative GEX measurement approach

12. **Nomura (2017): Equity Derivatives Strategy - Gamma Hedging Flows**
    - Source: Nomura Securities Research
    - Authors: McElligott, Charlie (likely lead author)
    - Topic: Dealer gamma hedging impact on markets
    - Why relevant: Bank research establishing mechanic

13. **Goldman Sachs (2018): The Impact of Derivatives on Equity Volatility**
    - Source: Goldman Sachs Global Markets Research
    - Topic: Options positioning and volatility regime shifts
    - Why relevant: Major bank acknowledgment of GEX effects

---

### LLM Reasoning & Validation Papers (Context)

14. **Brown et al. (2020): Language Models are Few-Shot Learners (GPT-3)**
    - Full citation: NeurIPS 2020
    - Purpose: Establishes LLM reasoning capabilities
    - Why relevant: Foundation for our use of LLMs

15. **Wei et al. (2022): Chain-of-Thought Prompting Elicits Reasoning**
    - Full citation: NeurIPS 2022
    - Purpose: Shows LLMs can reason through problems
    - Why relevant: Our method relies on LLM causal reasoning

16. **OpenAI (2023): GPT-4 Technical Report**
    - Source: OpenAI
    - ArXiv: 2303.08774
    - Purpose: Model we used for validation
    - Why relevant: Document model capabilities

17. **Zheng et al. (2023): Judging LLM-as-a-Judge with MT-Bench**
    - Full citation needed: ArXiv or conference
    - Topic: LLM evaluation methodology
    - Why relevant: Related validation approach

---

### LLMs in Finance (Related Work)

18. **Lopez-Lira & Tang (2023): Can ChatGPT Forecast Stock Price Movements?**
    - Full citation needed: Recent ArXiv or journal
    - Topic: LLM financial forecasting
    - Why relevant: Related but different approach (we test reasoning, not forecasting)

19. **Xie et al. (2023): Wall Street GPT**
    - Full citation needed: If published
    - Topic: LLMs for financial analysis
    - Why relevant: Related work in LLMs + finance

20. **Chen et al. (2023): FinGPT: Open-Source Financial Large Language Models**
    - Full citation needed: ArXiv or conference
    - Topic: Domain-specific LLM for finance
    - Why relevant: Alternative approach to financial LLMs

---

### Market Microstructure (Background)

21. **O'Hara (1995): Market Microstructure Theory**
    - Full citation: Blackwell Publishers
    - Purpose: Foundational microstructure text
    - Why relevant: Theoretical background

22. **Hasbrouck (2007): Empirical Market Microstructure**
    - Full citation: Oxford University Press
    - Purpose: Empirical methods in microstructure
    - Why relevant: Methodological context

23. **Bouchaud et al. (2009): How Markets Slowly Digest Changes in Supply and Demand**
    - Full citation: Quantitative Finance or related journal
    - Topic: Price impact of trading flows
    - Why relevant: Theoretical foundation for hedging impact

---

### Options Market Studies (Empirical)

24. **Ni (2009): Stock Option Returns: A Puzzle**
    - Full citation needed: Journal of Finance or similar
    - Topic: Options market anomalies
    - Why relevant: Context for options-driven effects

25. **Garleanu, Pedersen, Poteshman (2009): Demand-Based Option Pricing**
    - Full citation: Review of Financial Studies
    - Topic: How demand affects option prices (and dealer hedging)
    - Why relevant: Theoretical support for dealer constraints

26. **Muravyev, Pearson, Broussard (2013): Is There Price Discovery in Equity Options?**
    - Full citation: Journal of Financial Economics
    - Topic: Options leading stock price movements
    - Why relevant: Mechanism we're studying

---

### 0DTE Options (Recent Phenomenon)

27. **CBOE (2023): The Rise of Zero Days to Expiration Options**
    - Source: CBOE Research
    - URL: https://www.cboe.com
    - Topic: 0DTE market growth and characteristics
    - Why relevant: Context for 0dte_hedging pattern

28. **JPMorgan (2023): 0DTE Options: Market Structure Implications**
    - Source: JPMorgan Markets Research
    - Topic: Impact of 0DTE on intraday volatility
    - Why relevant: Market regime change explanation

---

### Obfuscation Testing / AI Validation (Novel Methodology)

29. **Marcus & Davis (2019): Rebooting AI**
    - Full citation: Pantheon Books
    - Topic: AI understanding vs memorization
    - Why relevant: Motivates our obfuscation approach

30. **Mitchell (2023): AI Evaluation: Current Methods and Challenges**
    - Full citation needed: If recent publication exists
    - Topic: Validating AI capabilities
    - Why relevant: Our methodology addresses this challenge

---

### Efficient Market Hypothesis (Context)

31. **Fama (1970): Efficient Capital Markets**
    - Full citation: Journal of Finance, Vol. 25, No. 2, pp. 383-417
    - Purpose: EMH foundation
    - Why relevant: Context for discussing small inefficiencies

32. **Lo (2004): The Adaptive Markets Hypothesis**
    - Full citation: Journal of Portfolio Management
    - Purpose: Alternative to EMH
    - Why relevant: Reconciles patterns with evolving efficiency

---

## Citations We Should Add (Recommended)

### For Introduction

- **General LLM capabilities**: GPT-4 Technical Report (OpenAI, 2023)
- **LLMs in finance context**: Lopez-Lira & Tang (2023), Chen et al. (2023)
- **Market microstructure foundation**: O'Hara (1995), Hasbrouck (2007)

### For Methods

- **Options pricing**: Black & Scholes (1973)
- **Regulatory framework**: SEC Rule 15c3-1, FINRA Rule 4210
- **Obfuscation motivation**: Marcus & Davis (2019)
- **LLM reasoning**: Wei et al. (2022) - Chain of Thought

### For Results

- **Dealer hedging theory**: Ni et al. (2005), Garleanu et al. (2009)
- **Practitioner evidence**: SpotGamma (2019), Nomura (2017)
- **0DTE context**: CBOE (2023), JPMorgan (2023)

### For Discussion

- **Market efficiency**: Fama (1970), Lo (2004)
- **Price impact**: Bouchaud et al. (2009), Coval & Stafford (2007)
- **Options-stock linkage**: Muravyev et al. (2013)

---

## Priority for Main Chat

### Tier 1: Must Have (10-15 citations)

1. Black & Scholes (1973) - Options pricing foundation
2. SEC Rule 15c3-1 - Regulatory constraint
3. FINRA Rule 4210 - Market maker rules
4. Ni, Pearson, Poteshman (2005) - Pinning effect
5. Garleanu, Pedersen, Poteshman (2009) - Demand-based pricing
6. OpenAI GPT-4 Technical Report (2023) - Model used
7. Wei et al. (2022) - Chain-of-Thought reasoning
8. Fama (1970) - EMH context
9. O'Hara (1995) - Market microstructure theory
10. SpotGamma (2019) - Practitioner GEX metrics

### Tier 2: Nice to Have (5-10 citations)

11. Coval & Stafford (2007) - Forced flows
12. Nomura (2017) - Gamma hedging research
13. Lopez-Lira & Tang (2023) - LLMs in finance
14. CBOE (2023) - 0DTE market growth
15. Bouchaud et al. (2009) - Price impact theory

### Tier 3: Optional (5+ citations)

16. Basel III / Dodd-Frank - Regulatory context
17. MiFID II - International regulation
18. Marcus & Davis (2019) - AI understanding
19. Lo (2004) - Adaptive markets
20. Muravyev et al. (2013) - Price discovery

---

## Action Items for Main Chat

1. **Get full citations** for all Tier 1 papers (use Google Scholar)
2. **Verify publication details** (journal, volume, pages)
3. **Download key papers** for accuracy checking
4. **Create IEEE-style .bib file** with all entries
5. **In-text citations** should reference key claims:
   - Black-Scholes for GEX calculation
   - Ni et al. for pinning effect
   - SEC rules for regulatory constraint
   - GPT-4 report for model capabilities

---

## Notes on Citation Availability

**Easy to find** (published journals):
- Black & Scholes (1973)
- Fama (1970)
- Ni et al. (2005)
- Garleanu et al. (2009)
- O'Hara (1995)

**Moderate** (recent or ArXiv):
- OpenAI GPT-4 report (ArXiv)
- Wei et al. (2022) (NeurIPS)
- Lopez-Lira & Tang (2023) (check ArXiv)

**Harder** (practitioner/regulatory):
- SpotGamma (2019) - May need to cite website/white paper
- Nomura (2017) - Research report (not peer-reviewed)
- SEC/FINRA rules - Cite official regulation URLs
- CBOE (2023) - Exchange research paper

**Strategy**: Use academic citations where possible, supplement with practitioner sources for real-world validation.

---

**Document Version**: 1.0
**Last Updated**: October 16, 2025
**Next Step**: Main chat formats as IEEE-style .bib file
