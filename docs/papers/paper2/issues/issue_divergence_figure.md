# [Paper #2] Add Intraday vs Overnight Divergence Figure ("Great Divergence")

**Status**: ✅ Complete
**Created**: January 13, 2026
**Closed**: January 13, 2026
**GitHub Issue**: #232
**Branch**: figure/review

## Summary

Create a figure showing the divergence between overnight and intraday returns, segmented by GEX regime. This supports the "scar tissue" mechanism by demonstrating a real-world consequence: alpha shifted from intraday to overnight as 0DTE proliferated.

## Preliminary Analysis

Quick analysis of SPY returns (2020-2025) shows:

| Year | Overnight | Intraday | Total |
|------|-----------|----------|-------|
| 2020 | +13.8% | +5.2% | +19.7% |
| 2021 | +14.7% | +10.3% | +24.8% |
| 2022 | -15.2% | -3.7% | -18.7% |
| 2023 | +4.5% | +18.2% | +22.6% |
| 2024 | +21.2% | +0.6% | +21.7% |
| 2025 | +6.1% | +6.7% | +12.8% |

**Key Finding**: In negative GEX regimes:
- 2020: Overnight +0.048%, Intraday +0.050% (roughly equal)
- 2024: Overnight +0.085%, Intraday +0.002% (overnight dominates)

## Visual Design

"Jaw" Chart (Cumulative Returns):
- Two lines starting from same point
- Solid line: Overnight Return (Close T → Open T+1)
- Dashed line: Intraday Return (Open T+1 → Close T+1)
- Shaded region between lines showing "Alpha Gap"
- Annotations: Mark 0DTE adoption period (2022-2023)

## Data Requirements

- [x] OHLC data exists in Alpha Vantage (6,590 days, 1999-present)
- [ ] Backfill 2020-2023 OHLC to consolidated_historical.db
- [ ] Create figure script: fig12_overnight_intraday_divergence.py

## Placement

Discussion section as supplementary evidence for "scar tissue" mechanism.

## Caveats (must include in caption)

1. Correlation, not causation - divergence coincides with 0DTE but other factors (interest rates) also changed
2. Supplementary evidence, not core validation
3. Does not prove mechanism, only consistent with hypothesis

## Tasks

- [x] Backfill OHLC data (2020-2023) to database
- [x] Create figure generation script
- [x] Add to LaTeX Discussion section
- [x] Update figures README

## Labels

paper2, figure, discussion
