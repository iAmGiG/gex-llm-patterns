# Figure Captions for Paper #1

This document contains all figure captions for the paper.

---

## Figure 7: Biased vs Unbiased Prompt Comparison

**Figure 7a** (dual y-axis version): Detection rate and prediction accuracy comparison across three dealer constraint patterns using biased (with regime labels) vs unbiased (raw GEX only) prompts. Bars show detection rates with 95% confidence intervals (error bars). Lines show prediction accuracy (secondary y-axis). All patterns exceed the 60% mechanical threshold (red dashed line) even with unbiased prompts. Data: 242 trading days per pattern, full year 2024 (N=726 total tests).

**Figure 7b** (simple version): Detection rate comparison showing prompt bias impact. Biased prompts (blue bars) achieved 100% detection by including regime labels, while unbiased prompts (orange bars) achieved 71.5% average detection using raw GEX values only. Yellow annotations show the -22.3% to -32.6% detection rate decrease. All patterns remain above the 60% mechanical threshold (red dashed line) with 95% confidence intervals (error bars). Data: 242 trading days per pattern, full year 2024 (N=726 total tests).

**Key Messages**:

- Unbiased detection (71.5%) proves LLM detects market structure without label hints
- High accuracy maintained (91.2%) regardless of prompt type
- Prompt bias quantified (-28.5% average impact) demonstrates methodological rigor
- All patterns remain MECHANICAL (>60% threshold) with conservative unbiased prompts

**Referenced in**: Section 5 (Results), Section 6 (Discussion - Ablation Study)

---

## Figure 1: System Architecture Diagram

**Caption**: Validation pipeline architecture showing the six-stage process from raw options data to statistical validation. Flowchart depicts: (1) Options Data (raw SPY chain with strike, OI, IV), (2) GEX Calculator (computes net GEX, flip point), (3) Data Obfuscator (converts to Day T+0, INDEX_1 format), (4) LLM Agent (GPT-4 extracts WHO/WHOM/WHAT with confidence), (5) Outcome Calculator (measures T+1 returns, realized volatility), (6) Statistical Validator (aggregates detection rates over N=242 days). Output examples shown below each component illustrate data transformation at each stage. Color coding: blue (data source), orange (processing), purple (LLM analysis), green (validation). Bottom annotation explains obfuscation purpose: preventing training data leakage.

**Key Messages**:

- Complete end-to-end pipeline from raw data to validation results
- Obfuscation occurs in Stage 3 (critical for rigor)
- LLM sees only quantitative structure (no temporal context)
- Outcome calculation validates predictions with forward returns

**Referenced in**: Section 4 (Experimental Setup - Validation Pipeline)

**Status**: ✅ COMPLETE (Chat A, Oct 16, 2025)

---

## Figure 2: Obfuscation Example

**Caption**: Before/after comparison demonstrating data obfuscation methodology. Left panel (BEFORE) shows raw market data with temporal context: real date (2024-01-16), ticker (SPY), and event context ("Fed meeting tomorrow", "VIX at 14.2", "Earnings season starting"). Right panel (AFTER) shows obfuscated version: date → "Day T+0", ticker → "INDEX_1", all context removed. Quantitative values (Net GEX: -$32.9B, spot price, gamma components) are preserved unchanged. Red highlighting indicates temporal information that enables training data memorization. Green highlighting shows cleaned data forcing LLM to reason from market structure alone. Bottom annotations clarify preservation (quantitative structure) vs removal (temporal/narrative information).

**Key Messages**:

- Obfuscation strips temporal context while preserving market structure
- Prevents LLM from memorizing training data (e.g., "GameStop Jan 2021")
- Forces genuine structural understanding vs pattern matching
- Key methodological innovation ensuring rigor

**Referenced in**: Section 3 (Methodology - Obfuscation Testing Framework)

**Status**: ✅ COMPLETE (Chat A, Oct 16, 2025)

---

## Figure 3: Detection vs Profitability Divergence ⭐ CRITICAL

**Caption**: Detection capability remains stable while economic profitability declines across Q2-Q4 2024. Dual-axis chart shows detection rate (blue line, left y-axis) maintaining high levels (84-100%) while net alpha (purple line, right y-axis) declines from +1.6 bps to -0.7 bps. Blue dashed line shows unbiased detection rate (69.4%) for comparison. Red dotted line marks the 60% mechanical threshold. This divergence proves the LLM detects structural dealer constraints rather than profitable trading opportunities. Data: gamma_positioning pattern, Q2 N=61, Q3 N=64, Q4 N=64 trading days.

**Key Messages**:

- Detection stable (84-100%) despite profitability decline (+1.6 → -0.7 bps)
- Proves methodology detects STRUCTURE not PROFITS
- Visual proof of main finding: LLM identifies constraints even when unprofitable
- Unbiased detection (69.4%) shows pattern persists without regime label hints

**Referenced in**: Section 5 (Results - Temporal Stability), Section 6 (Discussion)

**Status**: ✅ COMPLETE (Chat A, Oct 16, 2025)

---

## Figure 4: GEX Profile Visualization

**Figure 4a** (main version): Example GEX profile showing gamma exposure distribution across strike prices for a negative gamma regime day. Red bars indicate negative GEX (dealers short gamma), green bars indicate positive GEX (dealers long gamma). Blue dashed line marks the spot price. Large negative GEX concentration at-the-money creates dealer hedging constraints that amplify price movements. Net GEX annotation shows aggregate gamma position. This visualization illustrates the market structure data that the LLM analyzes to detect dealer constraint patterns.

**Figure 4b** (comparison version): Side-by-side comparison of negative gamma (left) vs positive gamma (right) regimes. Panel (a) shows negative net GEX where dealers are forced to sell into rallies and buy into selloffs (pro-cyclical hedging). Panel (b) shows positive net GEX where dealers provide liquidity by buying into selloffs and selling into rallies (counter-cyclical hedging). Yellow/green shading highlights the at-the-money region where GEX concentration is highest.

**Key Messages**:

- Visualizes the raw GEX data structure that LLM analyzes
- Illustrates dealer hedging constraints in negative gamma regime
- Shows GEX concentration at-the-money (ATM region)
- Helps reader understand input format for pattern detection

**Referenced in**: Section 3 (Methodology), Section 4 (Experimental Setup)

---

## Figure 5: Confidence Distribution

**Figure 5a** (histogram version): Distribution of detection confidence scores across three dealer constraint patterns (N=242 days each). Overlapping histograms show gamma positioning (blue), stock pinning (purple), and 0DTE hedging (orange). Red dashed line marks the 60% mechanical threshold. All patterns show strong concentration above threshold with mean confidences of 79-80%. Statistics box shows exact percentages: Gamma Positioning (79.5% mean, 100% ≥60%), Stock Pinning (80.2% mean, 100% ≥60%), 0DTE Hedging (80.1% mean, 100% ≥60%). Data: unbiased prompts, full year 2024.

**Figure 5b** (KDE smooth version): Probability density curves showing smooth distribution of confidence scores. Curves use same color scheme as histogram version. All three patterns peak strongly in the 70-90% range, well above the 60% threshold (red dashed line). Demonstrates consistent high-confidence detection across different pattern types.

**Key Messages**:

- All patterns show mean confidence ~80% (well above 60% threshold)
- 100% of detections exceed mechanical threshold for all patterns
- Tight clustering demonstrates consistent LLM pattern recognition
- No significant variation between pattern types (79.5-80.2% range)

**Referenced in**: Section 5 (Results - Primary Detection Results)

**Status**: ✅ COMPLETE (Chat A, Oct 16, 2025)

---

## Figure 6: Pattern Detection Heatmap

**Figure 6a** (detection heatmap): Heatmap visualization showing detection rates across three dealer constraint patterns for full year 2024 (N=242 days). Color scale from red (50%) to green (100%) indicates detection rate strength. All patterns consistently exceed the 60% mechanical threshold (annotated in yellow box). 0DTE hedging shows strongest detection (77.7%), followed by gamma positioning (69.4%) and stock pinning (67.4%). Values displayed in cells show exact detection percentages. Data: unbiased prompts (raw GEX only), 242 trading days.

**Figure 6b** (combined detection + accuracy): Side-by-side heatmaps comparing (a) detection rates and (b) prediction accuracy across patterns and time. Left panel shows detection rates (green scale), right panel shows accuracy rates (blue scale). Demonstrates that high accuracy (90-92%) is maintained even with moderate detection rates (67-78%). All text annotations show exact percentages for each pattern-period combination. Data: unbiased prompts, full year 2024.

**Figure 6c** (effectiveness score): Heatmap showing overall pattern detection effectiveness calculated as Detection Rate × Prediction Accuracy. Blue gradient indicates combined metric quality. Each cell displays effectiveness score (large bold text) and component breakdown (smaller text below). Scores range from 60.9% to 70.6%, with 0DTE hedging showing highest effectiveness (70.6%). Side annotation explains effectiveness calculation methodology.

**Key Messages**:

- All patterns exceed 60% mechanical threshold across full 2024
- Detection rates: 67.4% - 77.7% (unbiased prompts)
- Accuracy rates: 90.4% - 92.5% (high materialization)
- 0DTE hedging shows strongest structural signal (77.7% detection)
- Consistent performance demonstrates robustness across time

**Referenced in**: Section 5 (Results - Multi-Pattern Validation)

---

## Figure 8: Validation Funnel

**Figure 8a** (funnel diagram): Traditional funnel visualization showing progression from total pattern tests (N=726) through LLM detection (519, 71.5%) to materialized predictions (473, 91.2% of detected). Each stage shown as colored box (blue→orange→green) with connecting arrows. Percentage annotations highlight detection rate (71.5% in yellow box) and accuracy rate (91.2% in green box). Overall success rate (65.2%) displayed at bottom showing 473/726 tests resulted in correct predictions. Funnel width represents volume at each stage. Data: 242 days × 3 patterns, unbiased prompts.

**Figure 8b** (flow diagram): Sankey-style flow visualization showing all validation pathways. Five boxes represent: Total Tests (726), Detected (519), Materialized (473), Not Detected (207), and False Positives (46). Gray arrows with varying thickness indicate flow volume between stages. Arrow labels show exact counts. Demonstrates that 71.5% of tests are detected, 91.2% of detections materialize, 28.5% are not detected, and 8.8% are false positives. Summary statistics box shows all validation metrics. Data: unbiased prompts, full 2024.

**Figure 8c** (breakdown by pattern): Grouped bar chart showing three validation metrics (detection rate, prediction accuracy, overall success) for each of the three patterns plus overall average. Orange bars show detection (67.4-77.7%), green bars show accuracy (90.4-92.5%), blue bars show overall success (60.9-70.6%). Red dashed line marks 60% mechanical threshold. Value labels on each bar show exact percentages. Demonstrates consistent high performance across all pattern types with 0DTE hedging strongest (77.7% detection, 70.6% success). N=242 days per pattern.

**Key Messages**:

- 726 total tests (242 days × 3 patterns) with unbiased prompts
- 71.5% detection rate (519/726) - all patterns exceed 60% threshold
- 91.2% prediction accuracy (473/519) - high materialization rate
- 65.2% overall success rate (473/726) - combines detection and accuracy
- Consistent performance across all three dealer constraint patterns

**Referenced in**: Section 5 (Results - Validation Overview), Section 7 (Conclusion)

---

Last updated: October 16, 2025
