# GEX-LLM Pattern Analysis Source Code

This directory holds the shared modules of the GEX-LLM pattern analysis project: the deterministic regime rule, the frozen prompt builder and JSON parser that the Electronics pipeline uses, and the legacy code of the Paper 1 and Paper 2 pipelines, which tested whether Large Language Models can identify patterns in daily Gamma Exposure (GEX) calculations combined with price action.

## Status (2026-11-18)

Read-only audit of `src/` on 2026-11-18 (kept locally, not committed): 74 tracked modules, 34,002 lines. Nothing in it is a blocker and no secret was found. Nothing has been deleted or moved yet; the dispositions below are proposals for the authors to decide.

- **On the Electronics path (5 modules).** `scripts/validation/electronics/` imports only `llm/mechanics_prompt_builder.py`, `validation/regime_classifier.py` and `utils/json_parser.py`, and these pull in `utils/config_manager.py` and `utils/date_utils.py` (the latter through imports the prompt builder does not use). They open no network or database connection. The audit found nothing in `src/` that makes an Electronics result wrong. What they do is frozen: the prompt text is pinned byte for byte by the stored Batch inputs and the rule defines every detection rate, so change them only with the fidelity checks of the pipeline README (section 7) in hand.
- **Legacy (48 modules reachable only from Paper 1 and Paper 2 scripts) and unused (21 modules).** The Paper 1 and 2 reproduction code carries known defects (for example a silent default spot of 450, a canned fallback analysis when the JSON fails, GEX read from a pre-rebuild SQLite cache). It must not be repaired in place, because the published pipelines depend on its present behaviour; the proposal is a legacy banner first and a move into a legacy package later.
- **Proposals, by module count (75 rows including this README).** 27 modules to delete, 26 to move under a legacy package, 16 to keep with small fixes, 4 to keep as they are, 2 to refactor (the `analysis/` and `cache/` package `__init__` files, which load every submodule). This README is one of the 16. The per-module list is below.
- **Known broken.** `tools/autogen_tools.py` and the legacy agents call `get_options_chain`, which no PostgreSQL options manager defines (legacy only). Five legacy imports point at modules that the database repository no longer has (`sequential_gex_fetcher`, `batch_regime_validator`, `historical_gex_builder`, `fed_data_integration`), so the Paper 2 scripts that use them fail at import; the copies in `src/` are the only ones left.
- **Tests.** Only `tests/test_json_parser.py` is tracked (with `tests/__init__.py`); `.gitignore` line 160 ignores `tests/`, so a new test would not be committed unless that rule is changed. Nothing tests the classifier, the prompt builder, `config_manager` or `date_utils`. The audit proposes golden tests for the prompt and the classifier first.
- **Config keys never resolve.** `RegimeClassifier` and `MechanicsPromptBuilder` look their thresholds up under keys that are missing the section prefix, so the class constants (21 of 30 days, $5 B, 5 sign flips) decide every label; `00_env_check.py` compares them with the protocol. Do not wire the YAML config into them (the audit's advice, so that the rule comes from one place).

## Project Structure

```
src/
├── agents/                # Legacy market mechanics agent (Paper 1 and 2) and an unused agent stack
├── analysis/              # Legacy pattern analysis and baseline comparison
├── backtesting/           # Strategy backtesting utilities (legacy, self-contained)
├── base_agent.py          # Unused (proposed for deletion)
├── cache/                 # Legacy caches (SQLite-era store, ResearchCache, unified cache)
├── data/                  # Legacy market data system
├── data_sources/          # Vendor stubs and legacy collectors (Alpha Vantage retired, Polygon.io ended)
├── gex/                   # GEX modules (legacy; the maintained calculator is in the database repository)
├── llm/                   # Prompt builder (Electronics) and legacy AutoGen client
├── tools/                 # Legacy AutoGen tool registry and data-fetch tools
├── utils/                 # JSON parser, config manager, date utilities, legacy report writers
└── validation/            # Regime classifier (Electronics) and legacy validators
```

Only `agents/`, `analysis/`, `backtesting/`, `cache/` and `gex/` have an `__init__.py`; `llm/`, `utils/` and `validation/` have none, so importing the Electronics modules runs no package code.

## Core Modules

### On the Electronics path

- **llm/mechanics_prompt_builder.py** - `MechanicsPromptBuilder.build_regime_prompt`, the prompt of the Phase 4A run; pure and deterministic. Text frozen.
- **validation/regime_classifier.py** - `RegimeClassifier`, the deterministic Paper 2 rule on a 30-day window: at least 21 days of one sign, mean |GEX| of at least $5 B, at most 5 sign flips; $3 B is the low-conviction floor. `classify_window` takes a list of 30 dicts with a `net_gex` key. Every detection rate of the Electronics paper is defined by this file. The database repository has its own copy that accepts raw float lists; the two have drifted, and the Electronics pipeline uses this one.
- **utils/json_parser.py** - the strict-to-lenient JSON extraction ladder; the fallback parser is on the Electronics path (the src audit counts 85 stored fallback rows). A proposed fix is to be gated by replaying those answers.
- **utils/config_manager.py**, **utils/date_utils.py** - imported by the two modules above; `date_utils` is off the path once the unused imports are removed (proposed).

### Legacy Paper 1 and Paper 2 code

The move proposal covers only the 26 modules the audit marks move_to_legacy (`audit/2026-11-12/src/src_modules.csv` in the paper folder). `pattern_library.py` (keep and fix) and the `backtesting/` package (keep, or keep and fix) stay where they are; any move is left to the authors.

These reproduce the published pipelines. Their results depend on the pre-rebuild data; do not cite numbers from `pattern_library`, `pattern_taxonomy`, `enhanced_pattern_detector`, `validated_trading_engine`, `baseline_gex_strategy` or the December 2025 backtesting results.

- **agents/market_mechanics_agent.py** - the market mechanics agent (Paper 1 and Paper 2 scripts); with **tools/autogen_tools.py**, **llm/autogen_market_mechanics.py**, **utils/market_intelligence.py**, **utils/indicator_library.py** and **utils/unified_reports_manager.py**.
- **analysis/** - **pattern_library.py** (15 WHO/WHOM/WHAT pattern definitions, Issue #54; kept in place, it feeds the legacy prompts), **actionable_patterns.py**, **baseline_comparison.py**, **baseline_gex_strategy.py**.
- **cache/** - **sqlite_options_manager.py**, **unified_cache.py**, **research_cache.py** (owns the Phase 4A store schema; the Electronics pipeline reads the `.cache/research_cache.db` file read-only by sha256 and does not import this module), **gex_cache_manager.py**, **intraday_cache.py**; **data/market_data_system.py**.
- **gex/** - **live_gex_interface.py**, **enhanced_pattern_detector.py**.
- **data_sources/** - **historical_gex_builder.py** (provenance of the Paper 2 daily GEX table; it does not run) and **sequential_gex_fetcher.py** (the only copy of the Paper 2 fetcher).
- **validation/** - **data_obfuscation.py**, **pattern_taxonomy.py**, **outcome_calculator.py**, **formula_agreement_test.py**, **options_chain_validator.py**, **options_data_validator.py**, **batch_regime_validator.py** (the Paper 2 Phase 4A batch client; the Electronics runner is `scripts/validation/electronics/04_llm_runner.py`).
- **backtesting/** - **backtest_engine.py**, **portfolio.py**, **results.py**, **enhanced_metrics.py**, **baselines.py** and **signals/**; self-contained and offline, used by `scripts/backtesting/` (the engine cannot fetch prices since the vendor retirement).

### Proposed for deletion (unused, dead or superseded; nothing is deleted yet)

- **agents/** - `agent_bus.py`, `agent_factory.py`, `data_retrieval_agent.py`, and `base_agent.py` (no live caller; the subclasses import a missing module).
- **analysis/** - `pattern_engine_integration.py` (cannot be imported), `confidence_scorer.py`, `statistical_validator.py`, `technical_indicator_baseline.py`, `validated_trading_engine.py`.
- **cache/** - `postgresql_options_manager.py` (a stale copy that reads `option_type` with the default `call`, the Paper 2 input defect; the database repository's copy is the maintained one), `concurrent_gex_processor.py` (reports failures as success; `autogen_tools.process_gex_concurrent` imports it at function level and has to be removed with it), `research_cache_queries.py`.
- **data_sources/** - `polygon_client.py` (access ended 2026-11-01, no kill switch), `historical_collector.py`, `fed_data_integration.py`, `fed_data_analyzer.py`, `sample_data_loader.py`.
- **gex/gex_calculator.py** - a diverged duplicate of the database repository's `gex_db_infrastructure.gex.gex_calculator`, which is the one to use.
- **llm/batch_processor.py**, **tools/** (`options_analyzer.py`, `registry_integration.py`, `tool_registry.py`), **utils/** (`experiment_tracker.py`, `reports_manager.py`, `yaml_reports_manager.py`), **validation/** (`date_sanitizer.py`, `mechanics_validation_dataset.py`).

## Retired vendors

- **Alpha Vantage** was retired on 2026-10-10 and is kill-switched; equity options come from Cboe delayed quotes since 2026-10-12, through the database repository. `data_sources/alpha_vantage_gex.py` is a verbatim copy of the package module. Its constructor raises `RuntimeError` when a premium key is configured, unless the explicit override variable is set (a manual override, never for scheduled code). It stays only because `tools/autogen_tools.py` and the legacy agents import it, so it loads in every legacy agent script; delete it after the last importer goes. The premium key must not be used.
- **Polygon.io** access ended on 2026-11-01. `data_sources/polygon_client.py` has no importer and is proposed for deletion.
- **data_sources/retired_vendors.py** provides `RetiredVendorClient`, a stand-in that raises a `RuntimeError` naming the vendor on first use instead of making any network call. Code paths that only fetched from a retired vendor (the backtest engine, `historical_collector` and several scripts) get it since PR #277.

## Modules the database repository took over

The database repository (`gex-database-infrastructure`) removes a set of modules from its package (gex-database-infrastructure issue #228 for the first set below, issue #272 of this repository for the second). So that the Paper 1 and 2 scripts keep importing, the copies in this directory are now the code that is used, and every import points at `src.*`:

- PR #270 (2026-11-07): `sqlite_options_manager`, `unified_cache`, `research_cache`, `research_cache_queries`, `intraday_cache`, `concurrent_gex_processor`, `historical_collector` and `outcome_calculator` (`unified_cache` is the package version with the fix that reads every pickle file of a symbol).
- PR #277 (2026-11-08): `data_obfuscation`, `options_chain_validator`, `options_data_validator`, `pattern_taxonomy`, `formula_agreement_test`, `live_gex_interface`, `enhanced_pattern_detector`, `gex_cache_manager` and `alpha_vantage_gex`; each copy has a header naming the source commit (`fc70767`).

The copies drift from the database repository's own (15 same-named modules exist in both, among them `regime_classifier`, `config_manager` and `date_utils`), and nobody else maintains the ones here. The audit advises against copying further modules and against merging the two repositories. About 35 import lines here use `gex_db_infrastructure` (for example the GEX calculator that the live interface and the backtesting package import); no file of the database repository imports `src.*` from this repository.

## Usage

```python
# Deterministic regime verdict for a 30-day GEX sequence (USD), as the Electronics pipeline uses it
from src.validation.regime_classifier import RegimeClassifier

result = RegimeClassifier().classify_window([{"net_gex": v} for v in thirty_daily_net_gex_values])
print(result["regime_type"], result["should_detect"])

# Obfuscation of a market-data DataFrame (legacy Paper 1/2 flow); returns (frame, metadata)
from src.validation.data_obfuscation import DataObfuscator
obfuscated_df, metadata = DataObfuscator().obfuscate_market_data(market_df)
```

Run scripts from the repository root with `PYTHONPATH` set to it (the pipeline README, section 2, has the environment block). The legacy agent scripts build database and vendor clients at import, so stub them in tests and audits.

## Research Context

The code supports research into whether LLMs identify persistent dealer-gamma regimes from sequences of options-derived metrics. Earlier work used GPT-4o-mini and GPT-4o through Microsoft's AutoGen framework, and the Paper 2 Phase 4A run used o4-mini through the OpenAI Batch API; the Electronics extension (issue #261) re-runs the test with `gpt-6-luna` through the Batch API and with three open-weights models, using only the Electronics-path modules above. The status of that paper is in `docs/papers/electronics/README.md`.
