# Intraday OI Monitor Service

## Overview

Background service that captures intraday options snapshots using adaptive theta decay sampling matching 0DTE activity patterns.

**Issue**: #204

## Sampling Schedule

The service captures 21 snapshots per trading day with adaptive frequency:

| Period | Time Range | Interval | Snapshots | Rationale |
|--------|------------|----------|-----------|-----------|
| Market Open | 9:30 AM | - | 1 | Opening snapshot |
| Morning Baseline | 10:00-14:00 | 30 min | 9 | Low activity period |
| Theta Acceleration | 14:15-15:00 | 15 min | 4 | Theta decay speeds up |
| Expiry Rush | 15:10-15:50 | 10 min | 5 | Algo storm period |
| Final Rush | 15:55 | - | 1 | Last-minute positioning |
| Market Close | 16:00 | - | 1 | Closing snapshot |

**Capture Timing**: All snapshots occur at :59 seconds to ensure algorithmic trading streams complete.

## Quick Start

### Testing (Dry Run)

```bash
cd /mnt/bst/a100/yxie2/cregan1/gex-llm-patterns
source ~/miniconda3/etc/profile.d/conda.sh
conda activate AutoGex

# Single test capture
PYTHONPATH=$(pwd) python scripts/collection/intraday_oi_monitor.py --dry-run --test-capture

# Run scheduler in dry mode
PYTHONPATH=$(pwd) python scripts/collection/intraday_oi_monitor.py --dry-run
```

### Production (Screen Session)

```bash
# Start in detached screen session
screen -dmS intraday-monitor bash -c '
  cd /mnt/bst/a100/yxie2/cregan1/gex-llm-patterns && \
  source ~/miniconda3/etc/profile.d/conda.sh && \
  conda activate AutoGex && \
  PYTHONPATH=$(pwd) python scripts/collection/intraday_oi_monitor.py 2>&1 | tee /tmp/intraday_monitor.log
'

# Check status
screen -r intraday-monitor

# Detach from screen: Ctrl+A, then D

# List running screens
screen -ls

# Kill the session
screen -S intraday-monitor -X quit
```

### Production (Systemd User Service)

```bash
# Reload systemd user daemon
systemctl --user daemon-reload

# Enable service (auto-start on login)
systemctl --user enable intraday-oi-monitor

# Start service
systemctl --user start intraday-oi-monitor

# Check status
systemctl --user status intraday-oi-monitor

# View logs
journalctl --user -u intraday-oi-monitor -f

# Stop service
systemctl --user stop intraday-oi-monitor
```

## Command Line Options

```
usage: intraday_oi_monitor.py [-h] [--dry-run] [--symbols SYMBOLS [SYMBOLS ...]]
                              [--test-capture] [--db-host DB_HOST] [--db-port DB_PORT]

Options:
  --dry-run           Run without API calls or database writes
  --symbols           Override default symbol list
  --test-capture      Run single capture and exit
  --db-host           PostgreSQL host (default: localhost)
  --db-port           PostgreSQL port (default: 5432)
```

## Monitoring

### Log Files

- **Primary**: `/tmp/intraday_oi_monitor.log`
- **Systemd**: `journalctl --user -u intraday-oi-monitor`

### Database Queries

```sql
-- Today's snapshot count
SELECT snapshot_type, COUNT(*) as count
FROM intraday_snapshots
WHERE snapshot_timestamp >= CURRENT_DATE
GROUP BY snapshot_type
ORDER BY MIN(snapshot_timestamp);

-- Storage usage
SELECT
  pg_size_pretty(pg_relation_size('intraday_snapshots')) as table_size,
  pg_size_pretty(pg_indexes_size('intraday_snapshots')) as index_size;

-- Recent captures
SELECT
  symbol,
  snapshot_type,
  snapshot_timestamp,
  COUNT(*) as contracts
FROM intraday_snapshots
WHERE snapshot_timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY symbol, snapshot_type, snapshot_timestamp
ORDER BY snapshot_timestamp DESC;
```

## API Capacity

| Metric | Value |
|--------|-------|
| Symbols monitored | 30 (configurable) |
| Snapshots/day | 21 |
| API calls/day | 630 (30 × 21) |
| Premium tier limit | 1,000/min |
| Utilization | ~1% of capacity |

## Error Handling

The service includes:

1. **Rate limit retry**: Exponential backoff on rate limit errors
2. **Network recovery**: Automatic retry up to 3 times on network failures
3. **Missing data logging**: Track failed snapshots for investigation
4. **Auto-restart**: Systemd restarts service on failure after 60 seconds

## Troubleshooting

### Service won't start

```bash
# Check logs
tail -100 /tmp/intraday_oi_monitor.log

# Verify conda environment
source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
python -c "import schedule; print('OK')"

# Verify database connection
psql -d gex_options -c "SELECT 1"
```

### No data captured

1. Check if within market hours (9:30 AM - 4:00 PM ET)
2. Verify Alpha Vantage API key is valid
3. Check rate limit status in logs

### High error rate

1. Check API rate limits (should be <1000/min for premium)
2. Verify network connectivity
3. Check PostgreSQL connection pool

## Related Files

- **Service script**: `scripts/collection/intraday_oi_monitor.py`
- **Database schema**: `docs/infrastructure/intraday_schema.md`
- **Systemd service**: `~/.config/systemd/user/intraday-oi-monitor.service`

## Related Issues

- Issue #203: Database infrastructure
- Issue #204: This monitor service
- Issue #205: Pattern validation framework

---

**Created**: January 7, 2026
**Author**: Chat B (Claude Code)
