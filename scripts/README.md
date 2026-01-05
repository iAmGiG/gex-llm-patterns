# Scripts Directory

Executable scripts for the GEX-LLM Patterns project, organized by purpose.

## Directory Structure

### `analysis/` - Data Analysis & Comparison

| Script | Purpose |
|--------|---------|
| `explain_options_data.py` | Analyze and explain options data structure |
| `gamma_pinning_validator.py` | Validate Friday gamma pinning patterns |
| `run_baseline_comparison.py` | Compare LLM-filtered vs baseline strategies |
| `example_flexible_algo_times.py` | Flexible algo time analysis demo |

### `data_collection/` - Data Gathering

See [data_collection/README.md](data_collection/README.md) for details.

| Script | Purpose |
|--------|---------|
| `collect_leveraged_etfs.py` | Primary historical options collection |
| `check_progress.py` | Collection progress by symbol |
| `monitor_collection.py` | Real-time collection monitoring |
| `validate_data_quality.py` | Data quality validation |

### `database/` - Database Operations

| Script | Purpose |
|--------|---------|
| `create_intraday_schema.sql` | Intraday tables SQL schema |
| `migrate_to_intraday.py` | Add intraday tables |
| `migrate_add_dual_gex.py` | Add dual GEX columns |
| `rebuild_gex_database.py` | Full GEX database rebuild |
| `validate_database_integrity.py` | Validate GEX calculations |

### `experiments/` - Experiment Orchestration

| Script | Purpose |
|--------|---------|
| `orchestrate_experiment.py` | Simple experiment runner |
| `orchestrate_experiment_yaml.py` | Enhanced experiment runner with YAML output |
| `checkpoint_manager.py` | Resumable backtest checkpointing |

### `statistical_validation/` - Statistical Analysis

Paper 1 statistical validation scripts for GEX predictive analysis.

| Script | Purpose |
|--------|---------|
| `p1_extract_validation_data.py` | Extract validation data |
| `p1_granger_analysis_main.py` | Granger causality analysis |
| `p1_granger_variations.py` | Granger analysis variations |
| `p1_leadlag_analysis_main.py` | Lead-lag relationship analysis |
| `p1_leadlag_variations.py` | Lead-lag variations |

### `validation/` - Pattern Validation

Comprehensive validation suite organized by research paper. Scripts are numbered by workflow order.

```text
validation/
├── paper1/     # Paper 1 validation (17 scripts)
│   ├── 01_validate_raw_options_chain.py     - Data validation
│   ├── 02-04_validate_*.py                  - Pattern validation
│   ├── 05-09_*materialization*.py           - Materialization analysis
│   ├── 10_analyze_non_detections.py         - Non-detection analysis
│   ├── 11-13_narrative_test_*.py            - Narrative framework tests
│   ├── 14-15_*reasoning*.py                 - Reasoning extraction
│   ├── 16_analyze_eod_latent_information.py - Latent info analysis
│   └── 17_regenerate_validation_figures.py  - Figure generation
├── paper2/     # Paper 2 validation (7 scripts)
│   ├── 01-03_generate_*_windows.py          - Negative control generators
│   ├── 04-05_validate_regime_*.py           - Regime validation
│   └── 06-07_test_*.py                      - Testing scripts
└── shared/     # Shared utilities (2 scripts)
    ├── export_db_to_cache.py
    └── production_cache_test.py
```

## Usage Examples

**Run baseline comparison:**

```bash
python scripts/analysis/run_baseline_comparison.py --start-date 2024-01-02 --end-date 2024-03-29
```

**Validate gamma pinning:**

```bash
python scripts/analysis/gamma_pinning_validator.py --start-date 2024-01-01 --end-date 2024-06-30
```

**Run pattern validation:**

```bash
python scripts/validation/paper1/02_validate_pattern_taxonomy.py --pattern gamma_positioning --symbol SPY
```

**Run statistical validation:**

```bash
python scripts/statistical_validation/p1_granger_analysis_main.py
```
