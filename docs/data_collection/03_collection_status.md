# Data Collection Status

> ⚠️ **Snapshot: last validated 2025-12-17.** Paper 1 (published) and Paper 2 (AIAI 2026 accepted, JRFM under review) used the data reflected below. For live collection status, see CLAUDE.md. Active trading-infrastructure data collection has been migrated to the AutoTrader-AgentEdge repository.

Last updated: 2025-12-17 00:35 UTC

## Current Collection Progress

### Database Stats

- **Total Records**: 45,251,558 options contracts
- **Database Size**: 18.79 GB
- **Storage**: SQLite (`a:\Projects\gex-llm-patterns\.cache\options_historical.db`)

### Tier 1 Progress (Highest Liquidity)

| Symbol | Records | Days | Coverage | Date Range | Status |
|--------|---------|------|----------|------------|--------|
| TQQQ | 2,295,064 | 1,458 | 97.1% | 2020-01-02 to 2025-12-16 | ✅ Nearly Complete |
| SQQQ | 1,443,700 | 1,448 | 96.5% | 2020-01-02 to 2025-12-16 | ✅ Nearly Complete |
| SOXL | 1,950,364 | 1,450 | 96.6% | 2020-01-02 to 2025-12-16 | ✅ Nearly Complete |
| SOXS | 978,144 | 1,189 | 79.2% | 2020-01-02 to 2024-11-12 | 🔄 In Progress |
| UVXY | 1,231,956 | 731 | 48.7% | 2020-01-02 to 2023-02-06 | 🔄 Paused |

**Tier 1 Overall**: 4 of 5 symbols nearly complete

### Tier 2 Status (S&P & Russell Leveraged)

**Not Started**: SPXL, SPXS, UPRO, SPXU, TNA, TZA

### Tier 3 Status (Sector-Specific Leveraged)

**Not Started**: FAS, FAZ, LABU, LABD, TECL, TECS, NUGT, DUST

## Resuming Collection

The collection can be resumed at any time with no data loss. Use the following commands:

### Resume Tier 1 (where we left off)

```bash
# Sequential mode (recommended for stability)
python scripts/data_collection/collect_leveraged_etfs.py --tier 1 --sequential -y
```

This will automatically:

- Skip completed dates for TQQQ, SQQQ, SOXL (97%+ done)
- Continue SOXS from 2024-11-13
- Continue UVXY from 2023-02-07

### Start Tier 2 Collection

```bash
# After Tier 1 completes
python scripts/data_collection/collect_leveraged_etfs.py --tier 2 --sequential -y
```

### Start Tier 3 Collection

```bash
# After Tier 2 completes
python scripts/data_collection/collect_leveraged_etfs.py --tier 3 --sequential -y
```

### Full Auto-Queue (All Tiers)

```bash
# Run all tiers sequentially with tier skip options
python scripts/data_collection/collect_all_tiers.py --sequential -y
```

## Collection Modes

**Sequential Mode** (Recommended):

- One symbol at a time
- Stable, no database lock contention
- ~150-200 trading days per hour
- Lower RAM usage

**Buffered Mode** (Advanced):

- RAM queue + async DB writes
- ~15x faster, but higher lock risk on slower systems
- Requires more RAM (~1-10 GB buffer)
- Use `--buffered` flag

## Monitoring Progress

```bash
# Real-time monitoring
python scripts/data_collection/monitor_collection.py

# Watch mode (updates every 60 seconds)
python scripts/data_collection/monitor_collection.py --watch

# Check status
python scripts/data_collection/collect_leveraged_etfs.py --status
```

## Data Quality Validation

After collection completes (or for completed symbols):

```bash
# Validate all leveraged ETFs
python scripts/data_collection/validate_data_quality.py

# Validate specific symbols
python scripts/data_collection/validate_data_quality.py --symbols TQQQ SQQQ SOXL

# Verbose output with anomaly details
python scripts/data_collection/validate_data_quality.py --verbose
```

## Collection Timeline

**Target Date Range**: 2020-01-01 to present (~1,500 trading days per symbol)

**Estimated Completion**:

- Tier 1: ~43 days remaining (97% complete for top 3 symbols)
- Tier 2: ~9,000 symbol-days (6 symbols × 1,500 days)
- Tier 3: ~12,000 symbol-days (8 symbols × 1,500 days)

**Total Remaining**: ~21,000 symbol-days at 150/hour = ~140 hours = ~6 days continuous runtime

## Notes

- Collection uses `skip_existing=True` by default - safe to restart anytime
- Progress is persisted to SQLite immediately after each API call
- Unique constraints prevent duplicate records
- Sequential mode recommended for background/unattended collection
- Rate limit: 900-1000 API calls per minute (Alpha Vantage Premium)
