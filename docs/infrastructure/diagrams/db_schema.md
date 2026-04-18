# SQLite Schema — Options Data

Persistent storage for options-chain data, daily GEX summaries, and collection progress. Source of truth: [src/cache/sqlite_options_manager.py](../../../src/cache/sqlite_options_manager.py).

A second database, the research cache ([src/cache/research_cache.py](../../../src/cache/research_cache.py)), stores LLM outputs, validation results, and obfuscation mappings separately from the raw chain store.

```mermaid
erDiagram
    options_chains {
        INTEGER id PK
        TEXT symbol
        TEXT asset_class
        TEXT trading_date
        REAL strike
        TEXT option_type "call|put"
        TEXT expiration
        TEXT contract_symbol
        REAL bid
        REAL ask
        REAL last
        REAL mark
        INTEGER volume
        INTEGER open_interest
        REAL delta
        REAL gamma
        REAL theta
        REAL vega
        REAL rho
        REAL implied_volatility
        REAL underlying_price
        REAL mid_price
        REAL bid_ask_spread
        REAL vol_oi_ratio
        TEXT data_source
        REAL data_quality_score
        TEXT created_at
    }

    options_daily_summary {
        TEXT symbol PK
        TEXT trading_date PK
        TEXT asset_class
        REAL underlying_price
        REAL total_gex
        REAL net_call_gex
        REAL net_put_gex
        REAL zero_gamma_level
        REAL max_gamma_strike
        TEXT regime "POSITIVE_GAMMA|NEGATIVE_GAMMA|NEUTRAL"
        REAL call_oi_concentration
        REAL put_oi_concentration
        INTEGER contracts_count
        TEXT calculation_method
    }

    collection_progress {
        INTEGER id PK
        TEXT symbol
        TEXT trading_date
        TEXT status "pending|completed|failed|skipped"
        INTEGER contracts_count
        TEXT error_message
        INTEGER api_call_made
        REAL validation_quality_score
        TEXT created_at
    }

    research_market_data {
        TEXT symbol PK
        TEXT date PK
        REAL open
        REAL high
        REAL low
        REAL close
        INTEGER volume
    }

    research_gex_summary {
        TEXT symbol PK
        TEXT date PK
        REAL total_gex
        REAL zero_gamma_level
        TEXT regime
    }

    llm_detections {
        INTEGER id PK
        TEXT experiment_id FK
        TEXT symbol
        TEXT date
        TEXT regime_classification
        REAL confidence
        TEXT reasoning_trace
        TEXT model
    }

    validation_results {
        INTEGER id PK
        TEXT experiment_id FK
        TEXT window_id
        TEXT detected_regime
        TEXT ground_truth
        INTEGER matches
    }

    experiment_runs {
        TEXT experiment_id PK
        TEXT name
        TEXT phase
        TEXT config_json
        TEXT created_at
    }

    obfuscation_mappings {
        INTEGER id PK
        TEXT real_date
        TEXT obfuscated_date "Day T+N"
        TEXT real_ticker
        TEXT obfuscated_ticker "INDEX_1"
    }

    options_chains ||--o{ options_daily_summary : "aggregates into"
    options_chains ||--o{ collection_progress : "tracked by"
    experiment_runs ||--o{ llm_detections : "produces"
    experiment_runs ||--o{ validation_results : "validated by"
    llm_detections ||--o{ obfuscation_mappings : "reverses via"
```

## Notes

- **Two-database design.** `options_chains` / `options_daily_summary` / `collection_progress` live in the primary chain DB (paths configured per collection script). LLM outputs, validation results, and obfuscation mappings live in the research cache, so academic results can be reproduced without the 18+ GB raw chain data.
- **Uniqueness constraint** on `options_chains`: `(symbol, trading_date, strike, option_type, expiration)` — supports idempotent backfills.
- **Migration-safe columns.** `asset_class` (multi-asset support) and `validation_quality_score` (Issue #16) were added via `ALTER TABLE` in [`_migrate_schema`](../../../src/cache/sqlite_options_manager.py) rather than DB re-creation.
- **Indexes** exist on `(symbol, trading_date)`, `(symbol, trading_date, strike)`, `(symbol, trading_date, gamma, delta)`, and `expiration` for strike-level scans.
- **PostgreSQL alternative.** The active agent code path uses `PostgreSQLOptionsManager` from the `gex_db_infrastructure` package; `sqlite_options_manager.py` is the local/research path with an identical schema.
