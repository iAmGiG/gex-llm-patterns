# Prompt Bias Mitigation

**Date**: November 4, 2025
**Status**: Implementation Complete
**Issue**: 100% detection rate requires prompt bias analysis
**Action**: Reviewed prompts for bias, implemented neutral framework

---

## 1. Bias Identification

### Problem Statement

Phase 1 proof-of-concept showed 100% detection rate (120/120 windows). While this could reflect market reality (dealer constraints exist daily in 2024), must rule out prompt bias before proceeding.

### Original Prompt Analysis

**System Prompt** (BIASED - LEADING):

```
You are a market mechanics analyst specializing in dealer positioning
and forced hedging flows.

Your task is to identify WHO is forcing WHOM to do WHAT in the market
based on gamma exposure (GEX) data.

Focus on:
1. Dealer hedging mechanics (forced buying/selling due to gamma)
2. Squeeze setups (aggressive positioning to force dealer flows)
3. Pin dynamics (large OI creating price magnetism)
4. Trap patterns (dealers being flipped from long to short gamma)
```

**Bias Identified**:

- ❌ "Your task is to identify" - **Presupposes pattern exists**
- ❌ "forced hedging flows" - **Assumes forcing occurs**
- ❌ "Squeeze setups", "Trap patterns" - **Pre-categorizes outcomes**
- ❌ No option to say "no constraint detected"

**User Prompt** (PARTIALLY BIASED):

```
Analyze the following 5-day gamma exposure trajectory for INDEX_1.
Determine if any consistent constraint dynamics are present.

QUESTIONS TO ANSWER:
1. Do you detect any constraint trajectory over these 5 days?
   - Accumulation (gamma magnitude increasing)
   - Relief (gamma magnitude decreasing)
   - Reversal (gamma sign flip)
   - Persistent (stable magnitude)
2. If a trajectory exists, identify: WHO is forcing WHOM to do WHAT
3. How does this 5-day trajectory inform your prediction for Day T+1?
4. Confidence level (0-100): Set to 0 if no clear trajectory pattern
```

**Good Parts** (✅):
- "Determine IF" - allows for no constraint
- "If a trajectory exists" - conditional, not assumptive
- "Set to 0 if no clear trajectory pattern" - escape hatch provided

**Biased Parts** (❌):
- Question 2 assumes trajectory exists
- Question 3 assumes trajectory informs prediction
- Pre-defined categories may constrain thinking

### Root Cause

**Hypothesis**: LLM follows system-level instruction ("identify") over user-level question ("determine if"), resulting in 100% detection.

---

## 2. Neutral Framework Design

### Why Sequential Needs More Protection

| Aspect | Paper #1 (Single-Day) | Paper #2 (Sequential) |
|--------|----------------------|---------------------|
| **Temporal Scope** | Snapshot (Day T EOD) | Trajectory (T-4 to T+0) |
| **Pattern Type** | Static constraint | Dynamic trajectory |
| **Detection Target** | "Is forcing present?" | "Is there a forcing TREND?" |
| **Bias Risk** | Lower (binary state) | **Higher (change detection)** |
| **Null Hypothesis** | "No forcing" | "No trajectory" |
| **Bias Protections** | Obfuscation only | **Obfuscation + Neutral prompting** |

**Why Sequential Has Higher Bias Risk**:

1. **Change detection**: LLM looks for trends, may "see" patterns in noise
2. **Small sample**: 5 points, easy to spuriously connect
3. **Pre-defined categories**: Trajectory labels may anchor LLM
4. **Temporal bias**: Sequence order matters more than single snapshot

### New System Prompt (NEUTRAL)

```
You are a market mechanics analyst specializing in dealer positioning
and hedging dynamics.

Your task is to analyze gamma exposure (GEX) data and assess WHETHER
dealer hedging constraints are present in the market.

ANALYSIS FRAMEWORK:

If dealer constraints ARE present:
- Identify the forcing mechanism (WHO forces WHOM to do WHAT)
- Explain the causal chain (X leads to Y leads to Z)
- Provide confidence level based on data clarity

If dealer constraints are NOT clearly present:
- Explain why the data does not support forced hedging behavior
- Identify what would be needed to detect constraints
- Set confidence to 0

Be rigorous. Only detect patterns when the data clearly supports them.
Absence of evidence is valid - saying "no pattern" is acceptable.
```

**Changes**:

- ✅ "assess WHETHER" instead of "identify WHO"
- ✅ Explicit instructions for both detection AND non-detection cases
- ✅ "Absence of evidence is valid" - permission to say no
- ✅ "Be rigorous" - encourages discrimination

### New User Prompt (NEUTRAL)

**Key Changes**:

**BEFORE**:
```python
prompt_parts.append("QUESTIONS TO ANSWER:")
prompt_parts.append("1. Do you detect any constraint trajectory over these 5 days?")
prompt_parts.append("2. If a trajectory exists, identify: WHO is forcing WHOM to do WHAT")
```

**AFTER**:
```python
prompt_parts.append("CONSTRAINT ASSESSMENT:")
prompt_parts.append("1. Does this 5-day sequence show dealer hedging constraints?")
prompt_parts.append("   - If YES: What type of trajectory? (accumulation, relief, reversal, persistent)")
prompt_parts.append("   - If NO: Why does the data not support dealer constraints?")
prompt_parts.append("")
prompt_parts.append("IMPORTANT: It is acceptable and correct to find NO clear pattern.")
prompt_parts.append("Do not force a detection if the data is ambiguous or noisy.")
```

**New Features**:

- ✅ Explicit YES/NO branching logic
- ✅ "IMPORTANT: It is acceptable to find NO pattern"
- ✅ "Do not force a detection" - permission to not detect
- ✅ Added "incoherent" and "none" trajectory types in JSON schema

---

## 3. Implementation

### Files Modified

**1. Neutral Prompt Method** (`src/llm/mechanics_prompt_builder.py:456-559`)

Implemented `build_sequential_prompt_neutral()` - the core neutral framework method.

**Key Features**:
- No leading language ("assess WHETHER" vs "identify WHO")
- Explicit YES/NO branching logic
- Permission to detect no pattern ("IMPORTANT: It is acceptable...")
- Confidence scale defined (0 = valid)
- Trajectory options include "incoherent" and "none"

**View implementation**: [mechanics_prompt_builder.py#L456-L559](../../../../src/llm/mechanics_prompt_builder.py#L456-L559)

**2. Config File** (`config_defaults/analysis_config.yaml:140-162`)

Added `mechanics_analyst_neutral` system prompt:

```yaml
mechanics_analyst_neutral:
  role: system
  content: |
    You are a market mechanics analyst specializing in dealer positioning
    and hedging dynamics.

    Your task is to analyze GEX data and assess WHETHER dealer hedging
    constraints are present in the market.

    [... neutral framework as defined above ...]
```

**3. AutoGen Client** (`src/llm/autogen_market_mechanics.py:24-70`)

Added `prompt_style` parameter:

```python
def __init__(self, prompt_style='leading'):
    """
    Initialize AutoGen client.

    Args:
        prompt_style: 'leading' (original) or 'neutral' (bias-mitigated)
    """
    if prompt_style == 'neutral':
        self.system_prompt = self.config.get('analysis.llm.system_prompts.mechanics_analyst_neutral')
    else:
        self.system_prompt = self.config.get('analysis.llm.system_prompts.mechanics_analyst')
```

**Backwards Compatible**: Defaults to 'leading' (original behavior)

### Usage

```python
# Leading prompt (original, for comparison)
client_leading = AutoGenMarketMechanics(prompt_style='leading')

# Neutral prompt (bias-mitigated)
client_neutral = AutoGenMarketMechanics(prompt_style='neutral')
```

---

## 4. Validation Approach

### Test Design

Compare leading vs neutral prompts on:

1. **Same Real Data** (10 windows)
   - Expected: Similar detection rates (~10% difference)
   - Pass: Difference ≤ 10%

2. **Random Synthetic Data** (10 windows)
   - Expected: <30% detection with neutral
   - Pass: Detection <30%

3. **Zero-GEX Data** (10 windows)
   - Expected: 0-10% detection with neutral
   - Pass: Detection 0-10%

### Validation Script

**Script**: `scripts/validation/validate_p2_negative_controls.py`

**Commands**:
```bash
# Test prompt comparison
python scripts/validation/validate_p2_negative_controls.py --test prompt_comparison

# Test all controls
python scripts/validation/validate_p2_negative_controls.py --all
```

**Output**: `reports/validation/paper2/negative_controls_{timestamp}.yaml`

---

## 5. Current Status

**Implementation**: ✅ COMPLETE (Nov 4, 2025)

- [x] Bias analysis documented
- [x] Neutral system prompt created
- [x] Neutral user prompt method added
- [x] AutoGenMarketMechanics updated with prompt_style parameter
- [x] Backwards compatibility maintained

**Testing**: ⏸ PENDING

- [ ] Run prompt comparison test
- [ ] Run negative controls
- [ ] Analyze results
- [ ] Make go/no-go decision

---

## 6. Decision Criteria

### If Tests Pass (All 3 Criteria Met)

- ✅ Prompt comparison: Difference ≤ 10%
- ✅ Random synthetic: Detection <30%
- ✅ Zero-GEX: Detection 0-10%

**Action**: Proceed with Q1 2024 sequential validation using neutral prompts

### If Tests Fail

**If Prompt Comparison Fails** (>20% difference):
- Indicates prompt bias in leading version
- Use neutral only for Paper #2

**If Synthetic/Zero-GEX Fails** (high false positive rate):
- Add explicit "no pattern" training examples
- Strengthen null hypothesis language in prompt
- Re-test before proceeding

---

## Navigation

**Prerequisites**: [../adr/005_prompt_design.md](../adr/005_prompt_design.md) (original design)
**Related**: [negative_controls_design.md](negative_controls_design.md) (validation tests)
**Next Steps**: Run negative control tests, analyze results
**GitHub Issues**: #89, #107, #108
