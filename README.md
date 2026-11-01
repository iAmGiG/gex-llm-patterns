# GEX-LLM Pattern Analysis: LLM Structural Reasoning in Financial Markets

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![IEEE BigData 2025](https://img.shields.io/badge/IEEE%20BigData-2025%20Published-success.svg)](https://arxiv.org/abs/2512.17923)
[![AIAI 2026](https://img.shields.io/badge/AIAI-2026%20Accepted-success.svg)](docs/papers/paper2/aiai/)
[![JRFM (MDPI)](https://img.shields.io/badge/JRFM%20(MDPI)-Under%20Review-yellow.svg)](docs/papers/jrfm/)
[![Research](https://img.shields.io/badge/Research-PhD%20Dissertation-purple.svg)](docs/papers/research_roadmap.md)

[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2018.1-336791.svg)](https://www.postgresql.org/)
[![Alpha Vantage](https://img.shields.io/badge/Data-Alpha%20Vantage%20Premium-0066CC.svg)](https://www.alphavantage.co/)

---

## Overview

PhD research investigating whether Large Language Models can detect structural constraints in financial markets through genuine reasoning rather than training data memorization.

**Core Innovation**: **Temporal obfuscation testing** — stripping all dates, ticker symbols, and contextual markers from financial data, forcing LLMs to reason from numerical structure alone.

**Application Domain**: Options dealer gamma exposure (GEX) — the aggregate hedging constraints that market makers face due to their options inventory positions.

---

## Key Results

### Single-Day Detection (IEEE BigData 2025)

| Metric | Result |
|--------|--------|
| Detection Rate | 71.5% (obfuscated, unbiased prompts) |
| Predictive Accuracy | 90.9% (forward returns) |
| Raw Chain Superiority | 92.3% vs 61.5% GEX-assisted (+30.8pp) |
| Test Coverage | 242 trading days (SPY, 2024) |

**Finding**: LLMs reconstruct dealer positioning from raw strike-level data, outperforming pre-calculated metrics — empirical evidence that scalar GEX aggregation discards structural signal.

### Multi-Day Regime Detection (AIAI 2026)

| Metric | Result |
|--------|--------|
| 2024 Detection | 81.2% (persistent regimes) |
| 2020 Detection | 12.1% (pre-0DTE baseline) |
| Discrimination | 69.1pp separation (φ = 0.672, p < 0.0001) |
| False Positives | 0% on transitional/low-magnitude controls |
| Coverage | 1,412 windows + 809 controls (2020–2025) |

**Finding**: Detection tracks 0DTE options adoption — 3.7% (2021) → 100% (2024) — with GEX magnitude growing 360%, revealing a structural market reorganization.

### Detection ≠ Profitability

Stable detection (68–74% quarterly) persists while economic profitability collapses (Sharpe 1.8 → 0.1), confirming detected patterns are structural mechanics, not exploitable anomalies.

---

## Research Papers

### IEEE BigData 2025 ✅ Published — Single-Day Obfuscation Testing

**Title**: *Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing*

- **arXiv**: [2512.17923](https://arxiv.org/abs/2512.17923)
- **Venue**: 2nd IEEE Workshop on LLMs for Finance @ IEEE BigData 2025 (Dec 2025, Macau)
- **LaTeX**: [`docs/papers/paper1/`](docs/papers/paper1/)
- **Headline**: 71.5% obfuscated detection, 90.9% predictive accuracy on forward returns

### AIAI 2026 ✅ Accepted — 30-Day Regime Detection

**Title**: *Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation*

- **Venue**: IFIP International Conference on AI Applications and Innovations (Springer LNCS; camera-ready May 2026)
- **LaTeX**: [`docs/papers/paper2/aiai/`](docs/papers/paper2/aiai/)
- **Headline**: 81.2% detection (2024) vs 12.1% (2020) — 69.1pp separation, φ = 0.672, p < 0.0001 over 2,221 evaluations

### JRFM (MDPI) 🔄 Under Review — Combined Methodology + Regime Detection

**Title**: *Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation*

A journal-length submission that combines the obfuscation methodology validated at IEEE BigData 2025 with the multi-day regime-detection results from the AIAI 2026 paper, plus reviewer-driven additions: full prompt reproducibility, bootstrap CIs, χ² + Fisher contingency tests, threshold sensitivity, and a Markov-switching benchmark.

- **Venue**: Journal of Risk and Financial Management (MDPI)
- **LaTeX**: [`docs/papers/jrfm/`](docs/papers/jrfm/)
- **Status**: Major revision (R3 round) submitted April 2026

### Future Directions

Research extensions not pursued within this repository (cross-asset generalization, intraday/per-strike analysis, GNN-based cross-asset hedging networks): [`docs/papers/extensions/`](docs/papers/extensions/).

---

## Methodology

### Obfuscation Testing

```text
Raw:        SPY, 2024-03-15: Net GEX: -$32.9B, Flip: $485.00
Obfuscated: Day T+0, INDEX_1: Net GEX: -$32.9B, Flip: $485.00
```

Remove dates, tickers, events → preserve only quantitative structure → force structural reasoning.

### WHO → WHOM → WHAT Causal Framework

Every detection must specify:

- **WHO**: The constrained actor (e.g., dealers with negative gamma)
- **WHOM**: The affected parties (e.g., directional traders)
- **WHAT**: The forced mechanism (e.g., pro-cyclical hedging amplifying volatility)

### Regime Classification (30-Day Windows)

| Criterion | Threshold | Purpose |
|-----------|-----------|---------|
| Persistence | ≥ 70% days same sign | Exceeds random binomial (~2.2σ) |
| Magnitude | ≥ $5B average \|GEX\| | Economically significant positioning |
| Stability | ≤ 5 sign flips | Sustained directional bias |

---

## Infrastructure

### Database

- **PostgreSQL 18.1**: 81.8M contracts, 50 symbols, 2020–2025 (20.58 GB)
- **Intraday snapshots**: Yearly-partitioned table, 21 snapshots/day

### Data Sources

- **Alpha Vantage Premium**: Historical options chains (1000 calls/min)
- **Polygon.io**: Stock price data (free tier)

### LLM

- **OpenAI o4-mini**: Reasoning model via Batch API
- **Cost**: $11.07 for all 2,221 evaluations

---

## Project Structure

```text
gex-llm-patterns/
├── src/
│   ├── agents/              # LLM market mechanics agent
│   ├── analysis/            # Pattern library (15 patterns)
│   ├── gex/                 # GEX calculator (Black-Scholes)
│   ├── llm/                 # LLM integration
│   ├── validation/          # Obfuscation & regime classification
│   └── data_sources/        # Alpha Vantage, Polygon clients
├── scripts/
│   ├── validation/          # IEEE BigData + AIAI/JRFM validation pipelines
│   ├── analysis/            # Sensitivity analysis, figures
│   └── data_collection/     # Intraday OI monitor
├── docs/
│   ├── papers/
│   │   ├── paper1/          # Single-day obfuscation source — IEEE BigData 2025 (published)
│   │   ├── paper2/          # Regime detection source — AIAI 2026 (accepted)
│   │   ├── jrfm/            # Combined journal submission — JRFM/MDPI (under review)
│   │   └── extensions/      # Forward-looking research directions (snapshot)
│   └── presentations/       # PhD symposium, fundamentals
├── reports/                  # Validation results (YAML)
└── config_defaults/          # Configuration templates
```

---

## Getting Started

```bash
git clone https://github.com/iAmGiG/gex-llm-patterns.git
cd gex-llm-patterns
pip install -r requirements.txt

# Configure API keys
export OPENAI_API_KEY="your_key"
export POLYGON_API_KEY="your_key"

# Verify
python -c "from src.analysis.pattern_library import PatternLibrary; print('OK')"
```

## Research Ethics

- **Academic research only** — not trading advice
- **Public data only** — Alpha Vantage options chains
- **Open source** — methodology and code fully available
- **Not financial advice** — detection rates do not imply profitable strategies

## Citation

```bibtex
@inproceedings{regan2025obfuscation,
  author = {Regan, Christopher and Xie, Ying},
  title = {Inferring Latent Market Forces: Evaluating {LLM} Detection of
           Gamma Exposure Patterns via Obfuscation Testing},
  booktitle = {2nd IEEE International Workshop on Large Language Models
               for Finance, IEEE International Conference on Big Data},
  year = {2025},
  publisher = {IEEE},
  url = {https://arxiv.org/abs/2512.17923}
}
```

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

---

**Last Updated**: April 2026
**Contact**: Christopher Regan (`cregan1@kennesaw.edu`) · Ying Xie (`yxie2@kennesaw.edu`)
**Institution**: Kennesaw State University, College of Computing and Software Engineering
