# GEX Formula Comparison: Issue #186 Ablation Study

## Research Question

**Is LLM regime detection calculation-independent, or does it depend on absolute dollar magnitude?**

## Methodology

### Control: Absolute GEX (Current)
```
GEX = Σ ± OI × Γ × S² × 0.01 × 100
Range: -$50B to +$50B
Magnitude criterion: >$5B avg
```

### Treatment: Normalized GEX (Ratio-Based)
```
GEX_norm = (Σ call_gamma × OI) / Σ call_OI - (Σ put_gamma × OI) / Σ put_OI
Range: -1.0 to +1.0
Magnitude criterion: REMOVED (scale-independent)
```

## Expected Outcomes

| Outcome | Interpretation |
|---------|---|
| **AR > 90%** | Calculation-Independent |
| **AR 70-90%** | Partially Dependent |
| **AR < 70%** | Magnitude-Dependent |

## Files

- `src/validation/formula_agreement_test.py` - Core comparison logic
- `scripts/validation/paper2/run_formula_agreement.py` - Test runner
- `reports/validation/paper2_formula_agreement/` - Results output

## Running the Test

```bash
python scripts/validation/paper2/run_formula_agreement.py --subset Q1
```

## Related Issues

- #140: Phase 4A multi-year expansion
- #169: ResearchCache deployment
- #114: Sensitivity analysis
- Paper 2 Section VI.K: GEX formulation sensitivity
