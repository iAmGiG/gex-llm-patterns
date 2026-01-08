# Intraday Infrastructure

Documentation for intraday options data collection and storage (Paper #3 support).

**Related Issues**: #203, #204, #205

---

## 1. Overview

The intraday infrastructure captures granular options chain data throughout the trading day using adaptive theta decay sampling. This enables 0DTE gamma evolution analysis for Paper #3 research on market microstructure.

## 2. Database Schema

### 2.1 Table Structure

```sql
CREATE TABLE intraday_snapshots (
  id SERIAL,
  symbol VARCHAR(10) NOT NULL,
  strike NUMERIC NOT NULL,
  expiration_date DATE NOT NULL,
  snapshot_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  snapshot_type VARCHAR(20) NOT NULL,
  option_type VARCHAR(4),
  open_interest INTEGER,
  volume INTEGER,
  implied_volatility NUMERIC,
  spot_price NUMERIC,
  delta NUMERIC,
  gamma NUMERIC,
  theta NUMERIC,
  vega NUMERIC,
  bid NUMERIC,
  ask NUMERIC,
  last_price NUMERIC,
  PRIMARY KEY (symbol, strike, expiration_date, snapshot_timestamp, option_type)
) PARTITION BY RANGE (snapshot_timestamp);
```

### 2.2 Partitioning

Yearly partitions for optimal query performance:

| Partition | Date Range |
|-----------|------------|
| `intraday_snapshots_2025` | 2025-01-01 to 2025-12-31 |
| `intraday_snapshots_2026` | 2026-01-01 to 2026-12-31 |

### 2.3 Indices

```sql
idx_intraday_symbol_date ON (symbol, snapshot_timestamp)
idx_intraday_type ON (snapshot_type)
idx_intraday_expiry ON (expiration_date)
idx_intraday_symbol_expiry_type ON (symbol, expiration_date, snapshot_type)
```

## 3. OI Monitor Service

### 3.1 Sampling Schedule

21 snapshots per trading day with adaptive frequency:

| Period | Time Range | Interval | Snapshots |
|--------|------------|----------|-----------|
| Market Open | 9:30 AM | - | 1 |
| Morning Baseline | 10:00-14:00 | 30 min | 9 |
| Theta Acceleration | 14:15-15:00 | 15 min | 4 |
| Expiry Rush | 15:10-15:50 | 10 min | 5 |
| Final Rush | 15:55 | - | 1 |
| Market Close | 16:00 | - | 1 |

### 3.2 Quick Start

**Testing:**

```bash
PYTHONPATH=$(pwd) python scripts/data_collection/intraday_oi_monitor.py --dry-run --test-capture
```

**Production (Screen):**

```bash
screen -dmS intraday-monitor bash -c '
  cd /path/to/gex-llm-patterns && \
  PYTHONPATH=$(pwd) python scripts/data_collection/intraday_oi_monitor.py 2>&1 | tee /tmp/intraday_monitor.log
'
```

### 3.3 Command Line Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Run without API calls or database writes |
| `--symbols` | Override default symbol list |
| `--test-capture` | Run single capture and exit |
| `--db-host` | PostgreSQL host (default: localhost) |
| `--db-port` | PostgreSQL port (default: 5432) |

## 4. Common Queries

### Get all snapshots for a symbol

```sql
SELECT * FROM intraday_snapshots
WHERE symbol = 'SPY'
  AND snapshot_timestamp >= '2026-01-15'
  AND snapshot_timestamp < '2026-01-16'
ORDER BY snapshot_timestamp;
```

### Calculate intraday GEX evolution

```sql
SELECT
  snapshot_timestamp,
  snapshot_type,
  SUM(gamma * open_interest * 100) as total_gex
FROM intraday_snapshots
WHERE symbol = 'SPY'
  AND snapshot_timestamp >= '2026-01-15'
GROUP BY snapshot_timestamp, snapshot_type
ORDER BY snapshot_timestamp;
```

### Get 0DTE contracts only

```sql
SELECT * FROM intraday_snapshots
WHERE symbol = 'SPY'
  AND expiration_date = DATE(snapshot_timestamp)
  AND snapshot_type IN ('theta_accel', 'expiry_rush', 'final_rush');
```

## 5. Storage Estimates

| Metric | Value |
|--------|-------|
| Snapshots per day | 21 |
| Symbols monitored | 50 |
| Daily storage | ~1.5-2 GB |
| Annual storage | ~375-500 GB |

## 6. Maintenance

### Adding new partitions

```sql
CREATE TABLE intraday_snapshots_2028 PARTITION OF intraday_snapshots
  FOR VALUES FROM ('2028-01-01') TO ('2029-01-01');
```

### Check partition sizes

```sql
SELECT child.relname AS partition_name,
       pg_size_pretty(pg_relation_size(child.oid)) AS size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'intraday_snapshots';
```

## 7. Related Files

- **Service**: `scripts/data_collection/intraday_oi_monitor.py`
- **Database docs**: `03-data-and-database.md`

---

Created: January 2026 | Issues: #203, #204, #205
