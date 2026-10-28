-- =============================================================================
-- gex-llm-patterns: Electronics extension (iAmGiG/gex-llm-patterns#261)
-- Result tables in schema backups (project-owned, per gex-database-infrastructure
-- docs/009_PROJECT_BACKUP_STRATEGY.md)
--
-- WHY THIS EXISTS
--   The Paper 2 regime-detection study is re-run with gpt-6-luna on several daily
--   GEX series (the exact published Phase 4A inputs, the rebuilt 0DTE-inclusive
--   series, an ex-0DTE series, the pre-rebuild archive, an intraday slot) for
--   SPY/QQQ/IWM 2008-2026.  Every input shown to the model, every deterministic
--   classifier verdict and every model answer is stored here so the paper's
--   tables and figures are reproducible from SQL alone.  The 1,412 published
--   o4-mini results (Jan 2026) are backfilled as arm r1_o4mini.
--
-- LOADERS   scripts/validation/electronics/01_build_series.py   -> gex_llm_regime_series
--           scripts/validation/electronics/02_build_windows.py  -> gex_llm_regime_windows
--           scripts/validation/electronics/03_backfill_round1.py-> gex_llm_regime_detections (r1_o4mini)
--           scripts/validation/electronics/04_llm_runner.py     -> gex_llm_regime_runs, _detections
-- DOCS      gex-database-infrastructure/docs/gex-llm-patterns/backup-schema.md
-- CLEANUP   DROP VIEW backups.gex_llm_regime_rates_summary;
--           DROP TABLE backups.gex_llm_regime_detections, backups.gex_llm_regime_runs,
--                      backups.gex_llm_regime_windows, backups.gex_llm_regime_series;
--
-- SAFE TO RUN ANY TIME outside 21:50-22:45 UTC.  Creates only new objects in
-- schema backups; touches nothing else; no monitor restart; idempotent
-- (CREATE ... IF NOT EXISTS, CREATE OR REPLACE VIEW, COMMENT ON is repeatable).
-- Archive tables backups.*_pre_rebuild_20261004 are read by the loaders and
-- never written.
--
-- TEST FIRST (no dev database):   strip BEGIN/COMMIT into a copy, run it inside
--   BEGIN; ... ROLLBACK; and inspect \d+ backups.gex_llm_regime_*
-- APPLY:  psql -h 127.0.0.1 -d gex_options -X -v ON_ERROR_STOP=1 \
--             -f scripts/validation/electronics/sql/gex_llm_regime_schema.sql
-- =============================================================================

BEGIN;
SET LOCAL lock_timeout = '5s';

-- -----------------------------------------------------------------------------
-- 1. Daily GEX series as shown to the model (one row per series/symbol/day)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backups.gex_llm_regime_series (
    series_id        bigserial PRIMARY KEY,
    series_key       varchar(24)      NOT NULL,
    symbol           varchar(10)      NOT NULL,
    trading_date     date             NOT NULL,
    net_gex          double precision NOT NULL,
    call_gex         double precision,
    put_gex          double precision,
    gex_0dte         double precision,
    n_contracts      integer,
    n_0dte           integer,
    spot             double precision,
    source_table     varchar(120)     NOT NULL,
    source_timestamp timestamp with time zone,
    series_metadata  jsonb,
    created_at       timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT gex_llm_regime_series_natural_key UNIQUE (series_key, symbol, trading_date)
);

CREATE INDEX IF NOT EXISTS idx_gex_llm_regime_series_symbol_date
    ON backups.gex_llm_regime_series (symbol, trading_date);

COMMENT ON TABLE backups.gex_llm_regime_series IS
    '[gex-llm-patterns regime] Daily net dealer GEX series used to build the 30-day windows of the Electronics extension (iAmGiG/gex-llm-patterns#261). One row per (series_key, symbol, trading_date). Conventions differ by series_key (see column comment). Written only by scripts/validation/electronics/01_build_series.py; never by the monitors.';
COMMENT ON COLUMN backups.gex_llm_regime_series.series_id IS 'Surrogate key';
COMMENT ON COLUMN backups.gex_llm_regime_series.series_key IS
    'jan2026_phase4a = exact Phase 4A inputs recovered from the 2026-01-04 batch file (SPY 2020-2025, values at 0.01B precision, January calendar which lacks 2023-07-12 and 2024-03-11); old_bs = archive backups.options_daily_summary_pre_rebuild_20261004 (pre-2026-10-08 daily path: Black-Scholes gamma on integer DTE, same-day expiries zeroed); new_full = gex.options_daily_summary after the 2026-10-08 rebuild (stored per-contract gamma, 0DTE included); new_ex0dte = recomputed from gex.options_chains_partitioned with expiration > trading_date; intraday_late = gex.intraday_gex_summary snapshot_type final_rush (19:55:59 UTC)';
COMMENT ON COLUMN backups.gex_llm_regime_series.symbol IS 'Underlying ETF ticker (SPY, QQQ, IWM); joins to core tables by value';
COMMENT ON COLUMN backups.gex_llm_regime_series.trading_date IS 'Trading date the value belongs to; joins to core tables by value';
COMMENT ON COLUMN backups.gex_llm_regime_series.net_gex IS 'Net dealer gamma exposure in USD, calls positive, puts negative. Where recomputed: SUM(sign * gamma * open_interest * 100 * underlying_price^2 * 0.01) over contracts with gamma IS NOT NULL AND open_interest > 0 AND underlying_price > 0';
COMMENT ON COLUMN backups.gex_llm_regime_series.call_gex IS 'Call leg of net_gex in USD (positive); NULL where the source has no legs';
COMMENT ON COLUMN backups.gex_llm_regime_series.put_gex IS 'Put leg of net_gex in USD (negative); NULL where the source has no legs';
COMMENT ON COLUMN backups.gex_llm_regime_series.gex_0dte IS 'Net GEX of same-day expiries in USD on that date; NULL where the source does not expose it';
COMMENT ON COLUMN backups.gex_llm_regime_series.n_contracts IS 'Contracts included in net_gex; NULL where unknown';
COMMENT ON COLUMN backups.gex_llm_regime_series.n_0dte IS 'Same-day-expiry contracts on that date; NULL where unknown';
COMMENT ON COLUMN backups.gex_llm_regime_series.spot IS 'Underlying price used (USD); NULL where unknown';
COMMENT ON COLUMN backups.gex_llm_regime_series.source_table IS 'Table or file the row was built from';
COMMENT ON COLUMN backups.gex_llm_regime_series.source_timestamp IS 'intraday_late only: snapshot_timestamp of the row used';
COMMENT ON COLUMN backups.gex_llm_regime_series.series_metadata IS 'JSON: build parameters (SQL identity, planner settings, caps) and any per-day flags';
COMMENT ON COLUMN backups.gex_llm_regime_series.created_at IS 'Row insert/update time';

-- -----------------------------------------------------------------------------
-- 2. 30-day windows with the deterministic Paper 2 classifier verdict (no LLM)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backups.gex_llm_regime_windows (
    window_id           bigserial PRIMARY KEY,
    series_key          varchar(24)      NOT NULL,
    symbol              varchar(10)      NOT NULL,
    window_end          date             NOT NULL,
    window_start        date             NOT NULL,
    n_days              integer          NOT NULL DEFAULT 30,
    window_rule         varchar(8)       NOT NULL DEFAULT 'B',
    gex_sequence        jsonb            NOT NULL,
    input_sha256        char(64)         NOT NULL,
    clf_regime_type     varchar(24)      NOT NULL,
    clf_should_detect   boolean          NOT NULL,
    clf_positive_days   integer          NOT NULL,
    clf_negative_days   integer          NOT NULL,
    clf_persistence_pct double precision NOT NULL,
    clf_avg_magnitude   double precision NOT NULL,
    clf_sign_flips      integer          NOT NULL,
    clf_version         varchar(160)     NOT NULL,
    window_metadata     jsonb,
    created_at          timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT gex_llm_regime_windows_natural_key UNIQUE (series_key, symbol, window_end)
);

CREATE INDEX IF NOT EXISTS idx_gex_llm_regime_windows_symbol_end
    ON backups.gex_llm_regime_windows (symbol, window_end);

COMMENT ON TABLE backups.gex_llm_regime_windows IS
    '[gex-llm-patterns regime] 30-trading-day windows (T-29..T+0) built from backups.gex_llm_regime_series, with the Paper 2 deterministic verdict (src/validation/regime_classifier.py: >= 21 of 30 days same sign, mean |GEX| >= $5B, <= 5 sign flips). Zero LLM cost; the reference label for every LLM arm. Written only by 02_build_windows.py.';
COMMENT ON COLUMN backups.gex_llm_regime_windows.window_id IS 'Surrogate key';
COMMENT ON COLUMN backups.gex_llm_regime_windows.series_key IS 'Series the window was cut from (see gex_llm_regime_series.series_key)';
COMMENT ON COLUMN backups.gex_llm_regime_windows.symbol IS 'Underlying ETF ticker';
COMMENT ON COLUMN backups.gex_llm_regime_windows.window_end IS 'trading_date of day T+0 (the last day of the window)';
COMMENT ON COLUMN backups.gex_llm_regime_windows.window_start IS 'trading_date of day T-29';
COMMENT ON COLUMN backups.gex_llm_regime_windows.n_days IS 'Always 30';
COMMENT ON COLUMN backups.gex_llm_regime_windows.window_rule IS 'A = 30 consecutive series rows (Phase 4A convention); B = additionally no missing day against the symbol''s gex.options_daily_summary calendar; J = January 2026 calendar (jan2026_phase4a only)';
COMMENT ON COLUMN backups.gex_llm_regime_windows.gex_sequence IS 'JSON array of 30 objects {"date": "Day T-29".."Day T+0", "net_gex_usd": <float>} exactly as passed to MechanicsPromptBuilder.build_regime_prompt (dates and ticker removed)';
COMMENT ON COLUMN backups.gex_llm_regime_windows.input_sha256 IS 'sha256 of the canonical gex_sequence JSON; identical windows across series share it';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_regime_type IS 'persistent_positive | persistent_negative | low_conviction | transitional';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_should_detect IS 'TRUE for persistent_positive / persistent_negative';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_positive_days IS 'Days with net_gex > 0';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_negative_days IS '30 - positive days (zero counts as non-positive)';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_persistence_pct IS 'max(positive, negative) / 30 * 100';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_avg_magnitude IS 'Mean |net_gex| over the window, USD';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_sign_flips IS 'Count of sign changes between consecutive days';
COMMENT ON COLUMN backups.gex_llm_regime_windows.clf_version IS 'Classifier identity: git sha of gex-llm-patterns plus the thresholds used';
COMMENT ON COLUMN backups.gex_llm_regime_windows.window_metadata IS 'JSON: build flags (e.g. days missing from the master calendar)';
COMMENT ON COLUMN backups.gex_llm_regime_windows.created_at IS 'Row insert/update time';

-- -----------------------------------------------------------------------------
-- 3. LLM runs (one row per OpenAI Batch job or synchronous pilot)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backups.gex_llm_regime_runs (
    run_id            varchar(80)  PRIMARY KEY,
    arm               varchar(40)  NOT NULL,
    series_key        varchar(24)  NOT NULL,
    symbol            varchar(10)  NOT NULL,
    model             varchar(60)  NOT NULL,
    model_created_at  timestamp with time zone,
    prompt_version    varchar(40)  NOT NULL,
    reasoning_effort  varchar(10),
    response_format   varchar(20),
    max_completion_tokens integer,
    mode              varchar(10)  NOT NULL,
    openai_batch_id   varchar(80),
    input_file_id     varchar(80),
    output_file_id    varchar(80),
    error_file_id     varchar(80),
    input_sha256      char(64),
    output_sha256     char(64),
    backup_dir        text,
    window_end_min    date,
    window_end_max    date,
    n_requests        integer,
    n_responses       integer,
    n_parsed          integer,
    n_failed          integer,
    prompt_tokens     bigint,
    completion_tokens bigint,
    reasoning_tokens  bigint,
    est_cost_usd      double precision,
    status            varchar(20)  NOT NULL,
    submitted_at      timestamp with time zone,
    completed_at      timestamp with time zone,
    ingested_at       timestamp with time zone,
    git_sha           varchar(40),
    run_metadata      jsonb,
    created_at        timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gex_llm_regime_runs_arm ON backups.gex_llm_regime_runs (arm);

COMMENT ON TABLE backups.gex_llm_regime_runs IS
    '[gex-llm-patterns regime] One row per LLM run: an OpenAI Batch job (mode batch) or a synchronous pilot (mode sync). The row is written at submit time so the batch id is never lost; raw input/output JSONL plus a parquet copy of the detections live under backup_dir in the gex-llm-patterns repo (data/backups/gex_llm/<run_id>/).';
COMMENT ON COLUMN backups.gex_llm_regime_runs.run_id IS '<arm>_<model>_<mode>_<UTC timestamp>';
COMMENT ON COLUMN backups.gex_llm_regime_runs.arm IS 'Experiment arm, e.g. bridge_jan, full_spy, ex0dte_spy, full_qqq, full_iwm, intraday_spy, pilot_*';
COMMENT ON COLUMN backups.gex_llm_regime_runs.series_key IS 'Series the arm reads (see gex_llm_regime_series.series_key)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.symbol IS 'Underlying ETF ticker';
COMMENT ON COLUMN backups.gex_llm_regime_runs.model IS 'Model alias sent to the API (gpt-6-luna); the alias carries no dated snapshot';
COMMENT ON COLUMN backups.gex_llm_regime_runs.model_created_at IS 'created timestamp of the model object as returned by GET /v1/models/<model> at submit time';
COMMENT ON COLUMN backups.gex_llm_regime_runs.prompt_version IS 'v2.0_postgresql = the unchanged Phase 4A prompt text';
COMMENT ON COLUMN backups.gex_llm_regime_runs.reasoning_effort IS 'reasoning_effort request field (medium for all arms)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.response_format IS 'json_schema (strict) | none';
COMMENT ON COLUMN backups.gex_llm_regime_runs.max_completion_tokens IS 'max_completion_tokens request field';
COMMENT ON COLUMN backups.gex_llm_regime_runs.mode IS 'batch | sync';
COMMENT ON COLUMN backups.gex_llm_regime_runs.openai_batch_id IS 'OpenAI batch id (batch mode)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.input_file_id IS 'OpenAI file id of the uploaded input JSONL';
COMMENT ON COLUMN backups.gex_llm_regime_runs.output_file_id IS 'OpenAI file id of the output JSONL';
COMMENT ON COLUMN backups.gex_llm_regime_runs.error_file_id IS 'OpenAI file id of the error JSONL, if any';
COMMENT ON COLUMN backups.gex_llm_regime_runs.input_sha256 IS 'sha256 of the local input JSONL';
COMMENT ON COLUMN backups.gex_llm_regime_runs.output_sha256 IS 'sha256 of the local output JSONL';
COMMENT ON COLUMN backups.gex_llm_regime_runs.backup_dir IS 'Absolute path of the raw backup directory in the gex-llm-patterns repo';
COMMENT ON COLUMN backups.gex_llm_regime_runs.window_end_min IS 'Earliest window_end in the run';
COMMENT ON COLUMN backups.gex_llm_regime_runs.window_end_max IS 'Latest window_end in the run';
COMMENT ON COLUMN backups.gex_llm_regime_runs.n_requests IS 'Requests submitted';
COMMENT ON COLUMN backups.gex_llm_regime_runs.n_responses IS 'Response lines received';
COMMENT ON COLUMN backups.gex_llm_regime_runs.n_parsed IS 'Responses with parse_status ok or fallback';
COMMENT ON COLUMN backups.gex_llm_regime_runs.n_failed IS 'Responses with parse_status failed or missing';
COMMENT ON COLUMN backups.gex_llm_regime_runs.prompt_tokens IS 'Sum of usage.prompt_tokens';
COMMENT ON COLUMN backups.gex_llm_regime_runs.completion_tokens IS 'Sum of usage.completion_tokens (reasoning included)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.reasoning_tokens IS 'Sum of usage.completion_tokens_details.reasoning_tokens';
COMMENT ON COLUMN backups.gex_llm_regime_runs.est_cost_usd IS 'Token usage priced with the table in common.py (batch: $0.05/$0.25 per 1M for gpt-6-luna)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.status IS 'generated | submitted | in_progress | completed | failed | expired | cancelled | ingested';
COMMENT ON COLUMN backups.gex_llm_regime_runs.submitted_at IS 'Batch creation time (UTC)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.completed_at IS 'Batch completion time (UTC)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.ingested_at IS 'Time the output was parsed into gex_llm_regime_detections (UTC)';
COMMENT ON COLUMN backups.gex_llm_regime_runs.git_sha IS 'gex-llm-patterns commit the run was made from';
COMMENT ON COLUMN backups.gex_llm_regime_runs.run_metadata IS 'JSON: package versions, infra git sha, batch object snapshot, chunk index, notes';
COMMENT ON COLUMN backups.gex_llm_regime_runs.created_at IS 'Row insert time';

-- -----------------------------------------------------------------------------
-- 4. LLM detections (one row per window per run)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backups.gex_llm_regime_detections (
    detection_id           bigserial PRIMARY KEY,
    run_id                 varchar(80)  NOT NULL,
    arm                    varchar(40)  NOT NULL,
    series_key             varchar(24)  NOT NULL,
    symbol                 varchar(10)  NOT NULL,
    window_end             date         NOT NULL,
    model                  varchar(60)  NOT NULL,
    prompt_version         varchar(40)  NOT NULL,
    custom_id              varchar(80),
    response_id            varchar(80),
    regime_detected        boolean,
    regime_type            varchar(24),
    confidence             double precision,
    positive_days          integer,
    negative_days          integer,
    avg_magnitude_billions double precision,
    sign_flips             integer,
    persistence_pct        double precision,
    metrics_agree          boolean,
    reasoning              text,
    raw_response           text,
    parse_status           varchar(20)  NOT NULL,
    finish_reason          varchar(20),
    prompt_tokens          integer,
    completion_tokens      integer,
    reasoning_tokens       integer,
    detection_metadata     jsonb,
    created_at             timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT gex_llm_regime_detections_natural_key UNIQUE (arm, series_key, symbol, window_end, model, prompt_version)
);

CREATE INDEX IF NOT EXISTS idx_gex_llm_regime_detections_run ON backups.gex_llm_regime_detections (run_id);
CREATE INDEX IF NOT EXISTS idx_gex_llm_regime_detections_series_symbol_end ON backups.gex_llm_regime_detections (series_key, symbol, window_end);

COMMENT ON TABLE backups.gex_llm_regime_detections IS
    '[gex-llm-patterns regime] LLM regime verdict per window and run. Arm r1_o4mini holds the 1,412 published Phase 4A results (o4-mini-2025-04-16, batch of 2026-01-04) backfilled from the surviving output file; other arms are gpt-6-luna re-runs. Join to gex_llm_regime_windows on (series_key, symbol, window_end) for the deterministic reference label.';
COMMENT ON COLUMN backups.gex_llm_regime_detections.detection_id IS 'Surrogate key';
COMMENT ON COLUMN backups.gex_llm_regime_detections.run_id IS 'gex_llm_regime_runs.run_id (no FK by design; join by value)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.arm IS 'Experiment arm (see gex_llm_regime_runs.arm)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.series_key IS 'Series of the window';
COMMENT ON COLUMN backups.gex_llm_regime_detections.symbol IS 'Underlying ETF ticker';
COMMENT ON COLUMN backups.gex_llm_regime_detections.window_end IS 'trading_date of day T+0 of the window';
COMMENT ON COLUMN backups.gex_llm_regime_detections.model IS 'Model alias (gpt-6-luna) or dated id for the backfill (o4-mini-2025-04-16)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.prompt_version IS 'v2.0_postgresql';
COMMENT ON COLUMN backups.gex_llm_regime_detections.custom_id IS 'Batch custom_id: <arm>|<symbol>|<window_end>; window-<date> for r1_o4mini';
COMMENT ON COLUMN backups.gex_llm_regime_detections.response_id IS 'OpenAI response id (chatcmpl-...) when available';
COMMENT ON COLUMN backups.gex_llm_regime_detections.regime_detected IS 'Model verdict';
COMMENT ON COLUMN backups.gex_llm_regime_detections.regime_type IS 'persistent_positive | persistent_negative | transitional | low_conviction (model vocabulary)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.confidence IS 'Model confidence 0-100';
COMMENT ON COLUMN backups.gex_llm_regime_detections.positive_days IS 'Model-reported count';
COMMENT ON COLUMN backups.gex_llm_regime_detections.negative_days IS 'Model-reported count';
COMMENT ON COLUMN backups.gex_llm_regime_detections.avg_magnitude_billions IS 'Model-reported mean |GEX| in billions USD';
COMMENT ON COLUMN backups.gex_llm_regime_detections.sign_flips IS 'Model-reported sign-flip count (least reliable field; compare with clf_sign_flips)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.persistence_pct IS 'Model-reported persistence percentage';
COMMENT ON COLUMN backups.gex_llm_regime_detections.metrics_agree IS 'TRUE when the model-reported counts, magnitude and persistence equal the classifier values for the same window (tolerance 0.5 day / 0.05B / 0.5 pp)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.reasoning IS 'Model reasoning text';
COMMENT ON COLUMN backups.gex_llm_regime_detections.raw_response IS 'Verbatim assistant message content';
COMMENT ON COLUMN backups.gex_llm_regime_detections.parse_status IS 'ok (schema-valid JSON) | fallback (recovered by src/utils/json_parser) | failed | missing (no response line)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.finish_reason IS 'API finish_reason (stop, length, ...)';
COMMENT ON COLUMN backups.gex_llm_regime_detections.prompt_tokens IS 'usage.prompt_tokens for this request';
COMMENT ON COLUMN backups.gex_llm_regime_detections.completion_tokens IS 'usage.completion_tokens for this request';
COMMENT ON COLUMN backups.gex_llm_regime_detections.reasoning_tokens IS 'usage.completion_tokens_details.reasoning_tokens for this request';
COMMENT ON COLUMN backups.gex_llm_regime_detections.detection_metadata IS 'JSON: per-field differences vs the classifier, refusal text, retry notes';
COMMENT ON COLUMN backups.gex_llm_regime_detections.created_at IS 'Row insert/update time';

-- -----------------------------------------------------------------------------
-- 5. Read-only summary view: LLM vs classifier detection rate by arm/series/year
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW backups.gex_llm_regime_rates_summary AS
SELECT d.arm,
       d.series_key,
       d.symbol,
       d.model,
       EXTRACT(YEAR FROM d.window_end)::integer                        AS year,
       COUNT(*)                                                       AS n_windows,
       COUNT(*) FILTER (WHERE d.parse_status IN ('ok', 'fallback'))    AS n_parsed,
       COUNT(*) FILTER (WHERE d.regime_detected)                      AS n_llm_detect,
       ROUND(100.0 * COUNT(*) FILTER (WHERE d.regime_detected)
             / NULLIF(COUNT(*) FILTER (WHERE d.parse_status IN ('ok', 'fallback')), 0), 1) AS llm_detect_pct,
       COUNT(*) FILTER (WHERE w.clf_should_detect)                    AS n_clf_detect,
       ROUND(100.0 * COUNT(*) FILTER (WHERE w.clf_should_detect) / NULLIF(COUNT(*), 0), 1) AS clf_detect_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE d.regime_detected = w.clf_should_detect)
             / NULLIF(COUNT(*) FILTER (WHERE d.parse_status IN ('ok', 'fallback')), 0), 1) AS llm_clf_agree_pct,
       ROUND((AVG(w.clf_avg_magnitude) / 1e9)::numeric, 2)            AS mean_abs_gex_bn,
       ROUND(AVG(d.confidence)::numeric, 1)                           AS mean_confidence
FROM backups.gex_llm_regime_detections d
LEFT JOIN backups.gex_llm_regime_windows w
       ON w.series_key = d.series_key AND w.symbol = d.symbol AND w.window_end = d.window_end
GROUP BY 1, 2, 3, 4, 5;

COMMENT ON VIEW backups.gex_llm_regime_rates_summary IS
    '[gex-llm-patterns regime] Yearly LLM detection rate per arm next to the deterministic classifier rate on the same windows (iAmGiG/gex-llm-patterns#261)';

COMMIT;

-- Verify:
--   \dt backups.gex_llm_regime*            -- 4 tables
--   \dv backups.gex_llm_regime*            -- 1 view
--   SELECT relname, obj_description(oid) FROM pg_class
--    WHERE relnamespace = 'backups'::regnamespace AND relname LIKE 'gex_llm_regime%';
--   SELECT count(*) FROM backups.gex_llm_regime_series;   -- 0 until 01_build_series.py runs
