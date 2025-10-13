-- Intraday Database Schema for Gamma Pinning Validation
-- 10-minute intervals aligned with algo system updates
-- Market hours: 9:30 AM - 4:15 PM ET

-- Intraday GEX metrics table (10-minute snapshots)
CREATE TABLE IF NOT EXISTS intraday_gex_metrics (
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,          -- YYYY-MM-DD HH:MM:SS format
    spot_price REAL,
    total_gex REAL,
    net_call_gex REAL,
    net_put_gex REAL,
    gamma_flip_point REAL,
    flip_ratio REAL,
    gex_regime TEXT,
    data_quality_score REAL,
    options_count INTEGER,
    market_session TEXT,              -- 'regular', 'extended'
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, timestamp)
);

-- Intraday strike-level details (10-minute snapshots)
CREATE TABLE IF NOT EXISTS intraday_strike_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,          -- YYYY-MM-DD HH:MM:SS format
    strike REAL NOT NULL,
    call_gex REAL,
    put_gex REAL,
    net_gex REAL,
    call_oi INTEGER,
    put_oi INTEGER,
    call_volume INTEGER DEFAULT 0,
    put_volume INTEGER DEFAULT 0,
    distance_from_spot REAL,
    gamma_concentration REAL,         -- % of total gamma at this strike
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (symbol, timestamp) REFERENCES intraday_gex_metrics (symbol, timestamp)
);

-- Algo timing markers (for key market times)
CREATE TABLE IF NOT EXISTS algo_time_markers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,               -- YYYY-MM-DD
    market_open TEXT,                 -- 09:30:00
    algo_10am TEXT,                   -- 10:00:00
    fomc_230pm TEXT,                  -- 14:30:00 (FOMC days only)
    gamma_330pm TEXT,                 -- 15:30:00
    gamma_340pm TEXT,                 -- 15:40:00
    gamma_350pm TEXT,                 -- 15:50:00
    market_close TEXT,                -- 16:00:00
    extended_close TEXT,              -- 16:15:00
    is_fomc_day BOOLEAN DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(symbol, date)
);

-- Performance indexes for intraday queries
CREATE INDEX IF NOT EXISTS idx_intraday_symbol_time
ON intraday_gex_metrics(symbol, timestamp);

CREATE INDEX IF NOT EXISTS idx_intraday_date_range
ON intraday_gex_metrics(symbol, DATE(timestamp));

CREATE INDEX IF NOT EXISTS idx_intraday_time_only
ON intraday_gex_metrics(TIME(timestamp));

CREATE INDEX IF NOT EXISTS idx_strike_symbol_time
ON intraday_strike_details(symbol, timestamp);

CREATE INDEX IF NOT EXISTS idx_strike_gamma_desc
ON intraday_strike_details(symbol, timestamp, net_gex DESC);

-- Views for common gamma pinning queries
CREATE VIEW IF NOT EXISTS friday_gamma_analysis AS
SELECT
    symbol,
    DATE(timestamp) as date,
    timestamp,
    spot_price,
    gamma_flip_point,
    total_gex,
    gex_regime,
    TIME(timestamp) as time_only
FROM intraday_gex_metrics
WHERE strftime('%w', timestamp) = '5'  -- Fridays only
ORDER BY symbol, timestamp;

CREATE VIEW IF NOT EXISTS key_algo_times AS
SELECT
    symbol,
    timestamp,
    spot_price,
    total_gex,
    gex_regime,
    CASE
        WHEN TIME(timestamp) = '09:30:00' THEN 'MARKET_OPEN'
        WHEN TIME(timestamp) = '10:00:00' THEN 'ALGO_10AM'
        WHEN TIME(timestamp) = '14:30:00' THEN 'FOMC_230PM'
        WHEN TIME(timestamp) = '15:30:00' THEN 'GAMMA_330PM'
        WHEN TIME(timestamp) = '15:40:00' THEN 'GAMMA_340PM'
        WHEN TIME(timestamp) = '15:50:00' THEN 'GAMMA_350PM'
        WHEN TIME(timestamp) = '16:00:00' THEN 'MARKET_CLOSE'
        WHEN TIME(timestamp) = '16:15:00' THEN 'EXTENDED_CLOSE'
        ELSE 'OTHER'
    END as algo_marker
FROM intraday_gex_metrics
WHERE TIME(timestamp) IN ('09:30:00', '10:00:00', '14:30:00', '15:30:00', '15:40:00', '15:50:00', '16:00:00', '16:15:00')
ORDER BY symbol, timestamp;

-- Max gamma strike finder for pinning analysis
CREATE VIEW IF NOT EXISTS max_gamma_strikes AS
WITH ranked_strikes AS (
    SELECT
        symbol,
        timestamp,
        strike,
        ABS(net_gex) as abs_gamma,
        distance_from_spot,
        ROW_NUMBER() OVER (PARTITION BY symbol, timestamp ORDER BY ABS(net_gex) DESC) as gamma_rank
    FROM intraday_strike_details
    WHERE ABS(net_gex) > 0
)
SELECT
    symbol,
    timestamp,
    strike as max_gamma_strike,
    abs_gamma as max_gamma_value,
    distance_from_spot
FROM ranked_strikes
WHERE gamma_rank = 1;

-- Friday 3:30 PM gamma pinning validation query template
CREATE VIEW IF NOT EXISTS friday_330_validation AS
SELECT
    igm.symbol,
    DATE(igm.timestamp) as friday_date,
    igm.spot_price,
    mgs.max_gamma_strike,
    mgs.max_gamma_value,
    ABS(igm.spot_price - mgs.max_gamma_strike) as distance_to_max_gamma,
    igm.gex_regime,
    igm.total_gex
FROM intraday_gex_metrics igm
JOIN max_gamma_strikes mgs ON igm.symbol = mgs.symbol AND igm.timestamp = mgs.timestamp
WHERE strftime('%w', igm.timestamp) = '5'  -- Fridays
  AND TIME(igm.timestamp) = '15:30:00'     -- 3:30 PM
ORDER BY igm.symbol, igm.timestamp DESC;