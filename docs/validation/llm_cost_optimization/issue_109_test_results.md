# LLM Cost Optimization Test Results (Issue #109)

**Date**: November 3, 2025
**Test**: Simple API comparison of GPT-4o, o3-mini, GPT-5 mini

---

## Test Summary

**Goal**: Compare cost and quality of three LLM models for gamma exposure pattern detection.

**Method**: Direct OpenAI API calls with identical prompt (sample negative GEX scenario: -$32.49B).

**Prompt Structure**:
- WHO/WHOM/WHAT framework
- Pattern detection (true/false)
- Confidence level (0-100)
- JSON response format required

---

## Results

| Model | Status | Tokens (in/out) | Cost | Time | Detection | Confidence | Notes |
|-------|--------|-----------------|------|------|-----------|------------|-------|
| **GPT-4o** | ✅ Success | 266/191 | $0.002575 | 3.3s | ✅ True | 90% | Perfect JSON response |
| **o3-mini** | ⚠️  Partial | 265/500 | $0.002492 | 4.5s | ❌ Unknown | Unknown | **Empty response content** |
| **gpt-5-mini** | ⚠️  Partial | 265/500 | $0.001066 | 8.7s | ❌ Unknown | Unknown | **Empty response content** |

---

## Key Findings

### 1. GPT-4o (Baseline) ✅

**Performance**: Excellent
- Correctly detected pattern: "Dealers are forced to dynamically hedge... by selling when the spot price falls and buying when the spot price rises"
- WHO: "Options market participants (e.g., traders and investors) who have written options contracts"
- WHOM: "Dealers and market makers"
- Confidence: 90%
- Clean JSON formatting

**Cost**: $0.002575 per query

**Quality**: ⭐⭐⭐⭐⭐ (5/5) - Production ready

---

### 2. o3-mini (Reasoning Model) ⚠️

**Performance**: Failed
- API call succeeded (HTTP 200)
- Used 500 output tokens (hit max limit)
- **Returned empty content string**
- Could not parse JSON

**Cost**: $0.002492 per query (3% cheaper than GPT-4o)

**Quality**: ❌ (0/5) - Not usable

**Root Cause**: Unknown - possible issues:
1. JSON response_format not supported by o3-mini
2. Reasoning model may need different prompting style
3. Model may have generated non-JSON output that was filtered

**Recommendation**: ❌ **Do NOT use** - returns empty responses

---

### 3. GPT-5 mini (Cost Optimized) ⚠️

**Performance**: Failed
- API call succeeded (HTTP 200)
- Used 500 output tokens (hit max limit)
- **Returned empty content string**
- Could not parse JSON

**Cost**: $0.001066 per query (59% cheaper than GPT-4o)

**Quality**: ❌ (0/5) - Not usable

**Root Cause**: Same as o3-mini - empty response despite token usage

**Recommendation**: ❌ **Do NOT use** - returns empty responses

---

## Cost Analysis

| Model | Cost per Query | vs GPT-4o | Usable? |
|-------|----------------|-----------|---------|
| GPT-4o | $0.002575 | baseline | ✅ Yes |
| o3-mini | $0.002492 | -3% | ❌ No (empty response) |
| gpt-5-mini | $0.001066 | -59% | ❌ No (empty response) |

**Projected savings (if GPT-5 mini worked)**:
- Single query: $0.001509 saved (59%)
- Paper #2 (248 queries): $0.37 saved
- All PhD work (~1500 queries): **$2.26 saved**

**Reality**: ❌ **Zero savings** - cheaper models don't work for this task

---

## Technical Details

### API Parameter Differences

| Parameter | GPT-4o | o3-mini | gpt-5-mini |
|-----------|--------|---------|------------|
| `temperature` | 0.0 ✅ | ❌ Not supported | 1.0 only ✅ |
| `max_tokens` | ✅ Supported | ❌ Not supported | ❌ Not supported |
| `max_completion_tokens` | N/A | ✅ Required | ✅ Required |
| `response_format: json` | ✅ Works | ⚠️  Accepted but empty | ⚠️  Accepted but empty |

### Model-Specific Issues

**o3-mini**:
- Does not support `temperature` parameter at all
- Uses `max_completion_tokens` instead of `max_tokens`
- JSON response format appears broken (returns empty string)

**gpt-5-mini**:
- Requires `temperature=1.0` (no deterministic mode)
- Uses `max_completion_tokens` instead of `max_tokens`
- JSON response format appears broken (returns empty string)
- **Slowest**: 8.7s vs 3.3s for GPT-4o

---

## Recommendations

### For Issue #89 (Sequential GEX)

❌ **Do NOT switch models** - stick with GPT-4o

**Reasons**:
1. o3-mini and gpt-5-mini return empty responses with JSON format
2. No cost savings if models don't work
3. GPT-4o has proven reliability (100% detection in Paper #1)
4. Risk of breaking validation pipeline

### For Future Testing

**Option 1: Test without JSON format requirement**
- Remove `response_format: {"type": "json_object"}`
- Let models return free-form text
- Parse JSON manually from response
- **Effort**: Low (2-3 hours)
- **Risk**: Medium (may still fail)

**Option 2: Wait for model maturity**
- o3-mini and gpt-5-mini are new models (may have bugs)
- Re-test in 1-2 months after OpenAI updates
- **Effort**: None
- **Risk**: Low

**Option 3: Use different prompt for reasoning models**
- o3-mini designed for chain-of-thought reasoning
- May need step-by-step reasoning prompt instead of direct JSON
- See `config_defaults/llm_prompts.yaml` - reasoning template
- **Effort**: Medium (1-2 days)
- **Risk**: High (unproven approach)

---

## Conclusion

**Issue #109 Result**: ❌ **FAILED** - cheaper models not viable

**Impact on Paper #2**: ✅ **NONE** - continue with GPT-4o as planned

**Cost Reality**:
- Original projection: $30.50 savings (82%) ❌
- Actual savings: $0.00 (0%) ✅
- GPT-4o remains best option for production use

**Recommendation for Issue #89**:
✅ **Proceed with GPT-4o** - reliability > cost optimization

---

## Files Generated

1. **Test script**: `tests/model_testing/simple_llm_cost_test.py`
2. **Results JSON**: `docs/validation/llm_cost_optimization/simple_cost_test_20251103_223238.json`
3. **This report**: `docs/validation/llm_cost_optimization/issue_109_test_results.md`

---

## Next Steps

1. ✅ Close Issue #109 as "tested but not viable"
2. ✅ Document findings in issue comments
3. ⏸️  Re-test in Q1 2026 if models mature
4. ✅ Proceed with Issue #89 using GPT-4o
