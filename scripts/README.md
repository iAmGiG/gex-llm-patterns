# Scripts Directory

Executable scripts for the GEX-LLM Patterns project, organized by purpose and paper.

## Directory Structure

```text
scripts/
├── analysis/           # General analysis utilities
├── backtesting/        # Strategy backtesting (Paper 3 scope)
├── data_collection/    # Data gathering infrastructure
├── data_processing/    # Data pipeline processing
├── database/           # Database operations & migrations
├── experiments/        # Experiment orchestration
├── research/
│   ├── paper1/         # Paper 1 research scripts
│   └── paper3/         # Extension scripts (cross-asset, spillover) — see docs/papers/extensions/
└── validation/
    ├── paper1/         # Paper 1 validation (17 scripts)
    │   └── statistical/  # Statistical validation (Granger, lead-lag)
    ├── paper2/         # Paper 2 validation (10+ scripts)
    └── shared/         # Shared utilities
```

## Paper-Specific Scripts

### Paper 1: LLM-Based Validation of Dealer Constraints

**Research:** `scripts/research/paper1/`

| Script | Purpose |
|--------|---------|
| `gamma_pinning_validator.py` | Validate Friday gamma pinning patterns |
| `run_baseline_comparison.py` | Compare LLM-filtered vs baseline strategies |

**Validation:** `scripts/validation/paper1/`

- 01-04: Data and pattern validation
- 05-09: Materialization analysis
- 10: Non-detection analysis
- 11-13: Narrative framework tests
- 14-15: Reasoning extraction
- 16-17: Latent info and figures

**Statistical:** `scripts/validation/paper1/statistical/`

| Script | Purpose |
|--------|---------|
| `p1_granger_analysis_main.py` | Granger causality analysis |
| `p1_leadlag_analysis_main.py` | Lead-lag relationship analysis |

### Paper 2: LLM Regime Detection via GEX

**Validation:** `scripts/validation/paper2/`

| Script | Purpose |
|--------|---------|
| `01-03_generate_*_windows.py` | Negative control generators |
| `04-05_validate_regime_*.py` | Regime validation |
| `ablation_no_narrative.py` | Ablation study (Issue #191) |
| `run_formula_agreement.py` | Formula agreement test (Issue #217) |

### Research Extensions (Cross-Asset / Intraday)

> These scripts support the forward-looking research directions documented in [docs/papers/extensions/](../docs/papers/extensions/) — not an active paper in this repository.

**Research:** `scripts/research/paper3/` (folder name retained for git-history continuity)

| Script | Purpose |
|--------|---------|
| `cross_asset_correlation.py` | Cross-asset correlation analysis |
| `hedge_ratio_optimization.py` | Hedge ratio optimization |
| `volatility_spillover_analysis.py` | Volatility spillover signals |

## Infrastructure Scripts

### `data_collection/` - Data Gathering

See [data_collection/README.md](data_collection/README.md) for details.

| Script | Purpose |
|--------|---------|
| `collect_leveraged_etfs.py` | Primary historical options collection |
| `intraday_oi_monitor.py` | Intraday OI monitoring service |
| `validate_data_quality.py` | Data quality validation |

### `database/` - Database Operations

| Script | Purpose |
|--------|---------|
| `rebuild_gex_database.py` | Full GEX database rebuild |
| `validate_database_integrity.py` | Validate GEX calculations |
| `migrate_sqlite_to_parquet.py` | SQLite to Parquet migration |

### `analysis/` - General Utilities

| Script | Purpose |
|--------|---------|
| `explain_options_data.py` | Options data structure documentation |
| `example_flexible_algo_times.py` | Flexible algo time analysis demo |

## Usage Examples

**Run Paper 1 validation:**

```bash
python scripts/validation/paper1/02_validate_pattern_taxonomy.py --pattern gamma_positioning --symbol SPY
```

**Run Paper 2 regime validation:**

```bash
python scripts/validation/paper2/04_validate_regime_windows.py
```

**Run statistical analysis:**

```bash
python scripts/validation/paper1/statistical/p1_granger_analysis_main.py
```
