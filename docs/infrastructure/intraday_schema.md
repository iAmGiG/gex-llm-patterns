# Intraday Snapshots Database Schema

## Overview

The `intraday_snapshots` table stores granular options chain data captured throughout the trading day for 0DTE gamma evolution analysis. This infrastructure supports Paper #3 research on intraday market microstructure.

## Table Structure

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

## Partitioning Strategy

The table is partitioned by year for optimal query performance:

| Partition | Date Range | Status |
|-----------|------------|--------|
| `intraday_snapshots_2025` | 2025-01-01 to 2025-12-31 | Active |
| `intraday_snapshots_2026` | 2026-01-01 to 2026-12-31 | Active |
| `intraday_snapshots_2027` | 2027-01-01 to 2027-12-31 | Active |

## Snapshot Types

| Type | Description | Time Window |
|------|-------------|-------------|
| `market_open` | Opening snapshot | 9:30 AM ET |
| `morning_baseline` | Regular morning samples | 10:00 AM - 2:00 PM (30-min) |
| `theta_accel` | Theta decay acceleration | 2:00 PM - 3:00 PM (15-min) |
| `expiry_rush` | Algo storm period | 3:00 PM - 3:50 PM (10-min) |
| `final_rush` | Final rush | 3:55 PM |
| `market_close` | Closing snapshot | 4:00 PM ET |

## Indices

Optimized for common query patterns:

```sql
-- Symbol + timestamp queries (most common)
idx_intraday_symbol_date ON (symbol, snapshot_timestamp)

-- Filter by snapshot type
idx_intraday_type ON (snapshot_type)

-- Expiration-based queries
idx_intraday_expiry ON (expiration_date)

-- Combined queries for specific patterns
idx_intraday_symbol_expiry_type ON (symbol, expiration_date, snapshot_type)
```

## Storage Estimates

| Metric | Value |
|--------|-------|
| Snapshots per day | 21 |
| Symbols monitored | 50 |
| Contracts per snapshot | ~1.6M (estimated) |
| Daily storage | ~1.5-2 GB |
| Annual storage | ~375-500 GB |
| 5-year projection | ~2 TB |

## Common Queries

### Get all snapshots for a symbol on a date

```sql
SELECT * FROM intraday_snapshots
WHERE symbol = 'SPY'
  AND snapshot_timestamp >= '2026-01-15'
  AND snapshot_timestamp < '2026-01-16'
ORDER BY snapshot_timestamp;
```

### Get 0DTE contracts only

```sql
SELECT * FROM intraday_snapshots
WHERE symbol = 'SPY'
  AND expiration_date = DATE(snapshot_timestamp)
  AND snapshot_type IN ('theta_accel', 'expiry_rush', 'final_rush');
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
  AND snapshot_timestamp < '2026-01-16'
GROUP BY snapshot_timestamp, snapshot_type
ORDER BY snapshot_timestamp;
```

### Compare morning vs afternoon gamma

```sql
SELECT
  CASE
    WHEN EXTRACT(HOUR FROM snapshot_timestamp) < 14 THEN 'morning'
    ELSE 'afternoon'
  END as session,
  AVG(ABS(gamma * open_interest * 100)) as avg_gex
FROM intraday_snapshots
WHERE symbol = 'SPY'
  AND snapshot_timestamp >= '2026-01-01'
GROUP BY session;
```

## Related Issues

- Issue #203: Database infrastructure (this schema)
- Issue #204: Intraday OI monitor service
- Issue #205: Pattern validation framework (Paper #3)

## Maintenance

### Adding new yearly partitions

```sql
CREATE TABLE intraday_snapshots_2028 PARTITION OF intraday_snapshots
  FOR VALUES FROM ('2028-01-01') TO ('2029-01-01');
```

### Check partition sizes

```sql
SELECT
  child.relname AS partition_name,
  pg_size_pretty(pg_relation_size(child.oid)) AS size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'intraday_snapshots';
```

---

**Created**: January 7, 2026
**Issue**: #203
**Author**: Chat B (Claude Code)
