# Backtesting Research

**Status**: Auxiliary research for materialization validation
**Related Issue**: #8 (Walk-Forward Backtesting Framework)

---

## Purpose

This backtesting work supports **materialization validation**:

- Do LLM-detected patterns actually predict price movement?
- Supports Paper 1's 91.2% accuracy figure
- NOT for trading strategy optimization (that's AutoGen-Trader's scope)

---

## Framework Location

**Scripts**: `scripts/backtesting/`
**Signals**: `src/backtesting/signals/`
**Results**: `reports/backtesting_research/`

---

## Key Distinction

### What We Test Here

```text
LLM detects pattern → Did predicted price movement occur?
                     ↓
              Materialization Rate (%)
```

### What AutoGen-Trader Tests

```text
GEX signal generated → Did trade profit?
                      ↓
                Sharpe Ratio, Alpha
```

---

## Results Summary

### GEX vs Technicals Comparison (December 2025)

**Note**: This comparison used a simplified "flip" strategy, not practitioner regime methods.

| Period | GEX Wins | Technical Wins | Notes |
|--------|----------|----------------|-------|
| Full 2020-2024 | 2/42 (4.8%) | 40/42 | Flip strategy underperformed |
| COVID Crash | Notable | - | SOXL Sharpe 2.51 |

**Interpretation**: The flip-based approach differs from practitioner methods. This comparison belongs in AutoGen-Trader for proper methodology alignment.

### Materialization Validation (TBD)

Pending: Test LLM pattern detections against forward returns.

---

## Files

- `gex_vs_technicals_results.yaml` - Strategy comparison results
- `run_gex_vs_technicals.py` - Comparison script
- `gex_regime_signal.py` - Regime-based signal (practitioner-aligned)
- `gex_pattern_signal.py` - Original flip-based signal

---

## Cross-Project Notes

**AutoGen-Trader backtesting** (Issue #394):

- Tests practitioner GEX rules
- Achieved +1.019 Sharpe on TQQQ
- Uses regime transition signals

**This project backtesting** (Issue #8):

- Tests pattern materialization
- Validates LLM detection accuracy
- Uses our threshold-based methodology

The strategy comparison work (flip vs regime vs technicals) should be coordinated with AutoGen-Trader rather than duplicated here.
