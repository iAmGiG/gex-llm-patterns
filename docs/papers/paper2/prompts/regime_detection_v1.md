# Regime Detection Prompt v1 - Paper #2

**Created**: November 5, 2025
**Purpose**: LLM prompt for 30-day regime classification
**Expected Detection Rate**: 30-50% (selective, not universal)
**Related**: [regime_windows_design.md](../methodology/regime_windows_design.md)

---

## Prompt Template

```yaml
You are a market structure analyst specializing in dealer gamma positioning regimes.

TASK: Analyze this 30-day period and determine if it represents a PERSISTENT regime where dealer constraints create forced, directional flows.

## 30-DAY GEX DATA

{gex_data_table}

## REGIME CLASSIFICATION FRAMEWORK

### PERSISTENT REGIMES (Detect These)

**1. PERSISTENT POSITIVE REGIME**
- Definition: Dealers are LONG gamma, forced to sell into strength
- Criteria:
  * >70% of days (21+/30) have positive net GEX
  * Average magnitude >$5B
  * ≤5 sign flips across 30 days
  * Stable directional constraint

**Mechanism**: When dealers hold long gamma:
- Price rises → Dealers MUST sell shares (rebalance)
- Price falls → Dealers MUST buy shares (rebalance)
- Creates dampening, mean-reverting flows
- Constraint is STRUCTURAL (dealers cannot avoid)

**2. PERSISTENT NEGATIVE REGIME**
- Definition: Dealers are SHORT gamma, forced to buy into strength
- Criteria:
  * >70% of days (21+/30) have negative net GEX
  * Average magnitude >$5B
  * ≤5 sign flips across 30 days
  * Stable directional constraint

**Mechanism**: When dealers hold short gamma:
- Price rises → Dealers MUST buy shares (chase)
- Price falls → Dealers MUST sell shares (chase)
- Creates amplifying, momentum flows
- Constraint is STRUCTURAL (dealers cannot avoid)

---

### NON-REGIMES (Reject These)

**3. TRANSITIONAL (Reject)**
- Frequent sign flips between positive/negative GEX
- No dominant regime direction (less than 70% same sign)
- Market in regime change period
- Example: 15 positive days, 15 negative days (50/50 split)

**Why Reject**: No persistent constraint. Dealers face mixed conditions daily. Not a structural regime.

**4. LOW CONVICTION (Reject)**
- Consistent sign BUT weak magnitude (<$5B average)
- Example: 25 days positive, avg $2B GEX
- Insufficient constraint to create persistent forced flows

**Why Reject**: Even if sign is consistent, magnitude too weak to force dealers into meaningful positions. Not a structural constraint.

---

## ANALYSIS QUESTIONS

Systematically evaluate the 30-day window:

**Step 1: Sign Persistence**
1. Count days with positive net GEX
2. Count days with negative net GEX
3. Calculate persistence percentage: max(positive_days, negative_days) / 30 * 100
4. Does it meet 70% threshold (21+ days)?

**Step 2: Magnitude Assessment**
1. Calculate average GEX magnitude (absolute value): sum(|net_gex|) / 30
2. Is average magnitude ≥$5B?
3. Check for extreme outliers that might distort average

**Step 3: Stability Check**
1. Count sign flips: How many times does GEX switch from pos→neg or neg→pos?
2. Are there ≤5 sign flips across 30 days?
3. Stable regime should have low flip count

**Step 4: Regime Classification**
- If Steps 1, 2, 3 all pass AND positive dominates → PERSISTENT POSITIVE
- If Steps 1, 2, 3 all pass AND negative dominates → PERSISTENT NEGATIVE
- If Step 1 passes but Step 2 fails → LOW CONVICTION (reject)
- If Step 1 fails → TRANSITIONAL (reject)

---

## CONFIDENCE CALIBRATION (Mechanical Guidance)

Use these concrete anchors to calibrate confidence:

**90-100 (Very High Confidence)**
- 25-30 days same sign (83-100% persistence)
- Average magnitude >$10B
- 0-2 sign flips (highly stable)
- Example: "29 negative days, avg $15B, 1 flip"

**70-89 (High Confidence)**
- 21-24 days same sign (70-80% persistence)
- Average magnitude $5-10B
- 2-4 sign flips (moderately stable)
- Example: "23 negative days, avg $7B, 3 flips"

**50-69 (Borderline - Use with Caution)**
- 18-20 days same sign (60-67% persistence)
- Average magnitude $3-5B
- 5-7 sign flips
- Example: "20 negative days, avg $4B, 6 flips"
- **Note**: Borderline cases should generally be REJECTED unless other factors strengthen confidence

**0-49 (Reject - Not Persistent)**
- <18 days same sign (<60% persistence)
- OR average magnitude <$3B
- OR >7 sign flips
- These are NOT persistent regimes

**Important**: Confidence is a FILTER, not a probability. Use it to distinguish clear regimes (70+) from borderline (50-69) from noise (<50).

---

## OUTPUT FORMAT (JSON)

Provide your analysis in this exact JSON structure:

```json
{
    "regime_detected": true/false,
    "regime_type": "persistent_positive|persistent_negative|transitional|low_conviction",
    "positive_days": <count>,
    "negative_days": <count>,
    "avg_magnitude_billions": <value>,
    "sign_flips": <count>,
    "persistence_pct": <percentage>,
    "confidence": <0-100>,
    "reasoning": "Explain step-by-step why this is/isn't a persistent regime. Reference specific metrics (persistence %, avg magnitude, sign flips). If rejecting, state which criterion failed."
}
```

**regime_detected Rules**:

- `true` ONLY if regime_type is "persistent_positive" or "persistent_negative"
- `false` if regime_type is "transitional" or "low_conviction"

**Example Output (Persistent Negative)**:

```json
{
    "regime_detected": true,
    "regime_type": "persistent_negative",
    "positive_days": 4,
    "negative_days": 26,
    "avg_magnitude_billions": 8.5,
    "sign_flips": 3,
    "persistence_pct": 86.7,
    "confidence": 85,
    "reasoning": "Strong persistent negative regime. 26/30 days (86.7%) show negative GEX with avg magnitude $8.5B (well above $5B threshold). Only 3 sign flips indicates stable regime. Dealers consistently short gamma, forced to chase price moves. High confidence (85) reflects strong persistence and magnitude."
}
```

**Example Output (Transitional - Reject)**:

```json
{
    "regime_detected": false,
    "regime_type": "transitional",
    "positive_days": 15,
    "negative_days": 15,
    "avg_magnitude_billions": 6.2,
    "sign_flips": 12,
    "persistence_pct": 50.0,
    "reasoning": "Rejected as transitional. Only 50% persistence (need 70%+). 12 sign flips indicates unstable regime switching between positive and negative. Despite adequate magnitude ($6.2B), lack of directional persistence means no structural constraint. Not a regime."
}
```

**Example Output (Low Conviction - Reject)**:

```json
{
    "regime_detected": false,
    "regime_type": "low_conviction",
    "positive_days": 24,
    "negative_days": 6,
    "avg_magnitude_billions": 3.2,
    "sign_flips": 4,
    "persistence_pct": 80.0,
    "reasoning": "Rejected as low conviction. While 24/30 days (80%) show positive GEX, average magnitude only $3.2B (below $5B threshold). Constraint too weak to force meaningful dealer flows despite sign persistence. Not a structural regime."
}
```

---

## KEY PRINCIPLES

1. **Selectivity is Expected**: Most windows will NOT be persistent regimes (expect 30-50% detection rate)

2. **ALL Criteria Must Pass**: Persistence + Magnitude + Stability required for detection

3. **Rejection is Valid**: Saying "no persistent regime" is a correct answer for transitional/weak periods

4. **Mechanical Over Qualitative**: Use concrete thresholds (70%, $5B, 5 flips) rather than subjective judgment

5. **Structural Focus**: Only detect when dealers are FORCED into directional positions by constraints

---

## CONTEXT: Why 30-Day Windows?

**Research Evolution**:

- Initially tested 5-day trajectory windows
- Found 98-100% detection across ALL market conditions
- Interpretation: 5-day detects universal daily hedging (known since 1973), not distinctive regimes
- Pivoted to 30-day windows to detect PERSISTENT structural constraints (sometimes present = interesting)

**Expected Selectivity**:

- 2024: 30-50% detection (4-8 persistent regimes out of ~223 windows)
- 2020 (pre-0DTE): 20-30% detection (2-4 persistent regimes)
- Hypothesis: 0DTE proliferation increased regime persistence

This selectivity (not 98-100%!) is the GOAL. Universal detection = trivial finding.

---

## VALIDATION

This prompt will be tested on:

1. Q1 2024 (~32 windows): Expect 1-2 persistent negative regimes detected
2. Full 2024 (~223 windows): Expect 4-8 persistent regimes detected
3. 2020 baseline (~223 windows): Expect 2-4 persistent regimes detected
4. Negative controls: Random synthetic (expect 0% detection)

---

**Version**: v1
**Status**: Initial design - pending Phase 1 validation
**Next Iteration**: Adjust thresholds if detection rate deviates significantly from 30-50%
