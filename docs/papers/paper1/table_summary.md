# Table Summary for Paper #1

**Last Updated**: October 17, 2025

This document consolidates all tables referenced in the paper for easy formatting and LaTeX conversion.

---

## Table 1: Obfuscation Transformations

**Location**: Section 3 (Methodology) - `03_methodology.md:116`

**Purpose**: Shows what data is preserved vs removed during obfuscation testing

| Data Type | Original Example | Obfuscated Example | Purpose |
|-----------|-----------------|-------------------|---------|
| Date | 2024-01-05 | Day T+0 | Remove temporal context |
| Ticker | SPY | INDEX_1 | Remove identity hints |
| Price | $552.10 | $552.10 | Preserve structure |
| GEX | -$5.2B | -$5.2B | Preserve magnitude |
| Event | "Fed meeting" | [removed] | Remove narrative context |

**LaTeX Notes**:

- Use `\texttt{}` for technical examples (dates, tickers)
- Bold the "Purpose" column headers
- Consider `tabularx` for better column width management

---

## Table 2: Primary Results - Unbiased Prompt Detection

**Location**: Section 5 (Results) - `05_results.md:13`

**Purpose**: Main results table showing detection rates and accuracy for all three patterns

| Pattern | Detection Rate | 95% CI | Predictive Accuracy | Mechanical Status |
|---------|---------------|--------|-------------------|-------------------|
| gamma_positioning | 69.4% | [63.4%, 75.4%] | 92.5% | ✅ MECHANICAL |
| stock_pinning | 67.4% | [61.4%, 73.4%] | 90.4% | ✅ MECHANICAL |
| 0dte_hedging | 77.7% | [72.0%, 83.4%] | 90.8% | ✅ MECHANICAL |
| **Average** | **71.5%** | **[68.1%, 74.9%]** | **91.2%** | **✅ MECHANICAL** |

**LaTeX Notes**:

- Bold the "Average" row
- Use checkmark symbol: `\checkmark`
- Right-align numerical columns
- Consider `booktabs` package for professional lines (`\toprule`, `\midrule`, `\bottomrule`)

---

## Table 3: Prompt Template Comparison (Sensitivity Analysis)

**Location**: Section 5 (Results) - `05_results.md:38`

**Purpose**: Ablation study showing prompt bias impact on detection vs accuracy

| Pattern | Biased Detection | Unbiased Detection | Absolute Δ | Biased Accuracy | Unbiased Accuracy |
|---------|-----------------|-------------------|-----------|----------------|------------------|
| gamma_positioning | 100.0% | 69.4% | -30.6% | 96.2% | 92.5% |
| stock_pinning | 100.0% | 67.4% | -32.6% | 89.9% | 90.4% |
| 0dte_hedging | 100.0% | 77.7% | -22.3% | 90.5% | 90.8% |
| **Average** | **100.0%** | **71.5%** | **-28.5%** | **92.2%** | **91.2%** |

**LaTeX Notes**:

- Use `$\Delta$` for delta symbol
- Negative values in "Absolute Δ" column should use minus sign (not hyphen): `$-$30.6\%`
- Bold the "Average" row
- Right-align all numerical columns

---

## Additional Tables (Optional/Future)

These tables appear in supporting documents but may not be needed in the main paper:

### Detection Rate Comparison (from biased_vs_unbiased_comparison.md)

**Status**: May be redundant with Table 3 above

| Pattern | Biased Prompt | Unbiased Prompt | Detection Δ |
|---------|--------------|----------------|-------------|
| Gamma Positioning | 100.0% | 69.4% | -30.6% |
| Stock Pinning | 100.0% | 67.4% | -32.6% |
| 0DTE Hedging | 100.0% | 77.7% | -22.3% |

### Prediction Accuracy Comparison (from biased_vs_unbiased_comparison.md)

**Status**: May be redundant with Table 3 above

| Pattern | Biased Accuracy | Unbiased Accuracy | Accuracy Δ |
|---------|----------------|------------------|-----------|
| Gamma Positioning | 96.2% | 92.5% | -3.7% |
| Stock Pinning | 89.9% | 90.4% | +0.5% |
| 0DTE Hedging | 90.5% | 90.8% | +0.3% |

---

## LaTeX Package Recommendations

For IEEE two-column format, use these packages:

```latex
\usepackage{booktabs}       % Professional table lines
\usepackage{tabularx}       % Better column width management
\usepackage{multirow}       % Multi-row cells if needed
\usepackage{array}          % Enhanced column formatting
\usepackage{siunitx}        % Number formatting and alignment
```

## IEEE Format Guidelines

**Table Placement**:

- Tables should appear at top or bottom of column (not mid-text)
- Use `\begin{table}[t]` for top placement (preferred)
- Use `\begin{table}[b]` for bottom placement

**Caption Style**:

- Caption above table (IEEE style)
- Format: `\caption{Brief descriptive title}`
- Full explanation in caption text below title

**Font Size**:

- Table content: `\small` or `\footnotesize` (9pt or 8pt)
- Caption: `\normalsize` (10pt)

**Column Width**:

- IEEE two-column width: 3.5 inches (89mm)
- Single column width for narrow tables: 3.5 inches
- Full page width for wide tables: 7 inches (use `table*` environment)

---

**Note**: All three main tables (1, 2, 3) should fit comfortably in single-column IEEE format. Tables 2 and 3 may benefit from slightly reduced font size (`\small`) to ensure readability while maintaining single-column width.
