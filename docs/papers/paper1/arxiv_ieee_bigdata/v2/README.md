# arXiv v2 Errata Corrections

**Paper**: LLM-Based Detection of Dealer Gamma Constraints: Obfuscation Testing Methodology
**arXiv ID**: 2512.17923
**Original Version**: v1 (December 2024)
**This Version**: v2 (December 2025)

## Summary of Corrections

This folder contains corrected versions of files for arXiv v2 submission. The corrections address data discrepancies identified during journal revision (Issue #187, #188).

## Changed Files

### 05_Results.tex

#### Table: Prediction Materialization Criteria and Results (Exhibit 14)

| Metric | v1 (Incorrect) | v2 (Corrected) | Source Data |
|--------|----------------|----------------|-------------|
| Volatility Amplification (C1) | 89.2% | **41.6%** | 216/519 detection days |
| Directional Follow-through (C2) | 85.7% | **N/A** | Excluded (99.4% too loose) |
| Strike Convergence (C3) | 93.4% | **N/A** | gamma_flip_point unavailable |
| 0DTE Range Expansion (C4) | 91.1% | **21.6%** | 112/519 detection days |
| Overall | 91.2% | **41.6%** | C1 ∪ C4 union |

### Root Cause

The original v1 values (89.2%, 93.4%, 91.1%) were not supported by the validation data in `issue_144_materialization_criteria.csv`. The corrected values reflect actual materialization rates calculated from 519 detection days.

### Key Finding

The corrected moderate-to-low materialization rates (21-42%) actually **strengthen** the paper's central claim: the LLM detects selective structural constraints, not universal outcomes. This refutes p-hacking concerns more effectively than high rates would.

## Related GitHub Issues

- **#187**: Materialization rate contradictions (primary)
- **#188**: Raw Chain sample size documentation
- **#144**: Original materialization criteria analysis

## Files Not Changed

All other LaTeX files remain identical to v1. Only `05_Results.tex` contains corrections.

## IEEE BigData 2025 Note

The IEEE BigData 2025 published version (in `../ieee_bigdata_2025/`) retains the original v1 values as a frozen historical artifact matching the IEEE Xplore record. The corrections apply only to arXiv and the journal revision.
