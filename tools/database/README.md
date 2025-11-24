# Database Tools

Utilities for managing GEX database backups and maintenance.

## backup_database.py

On-demand tool for creating timestamped backups of database files.

### Features

- **Timestamped backups**: Automatic timestamp in filename (YYYYMMDD_HHMMSS)
- **Metadata generation**: Creates .txt file with backup details
- **Database info**: Shows row counts, date ranges, and table structure
- **Batch mode**: Backup all databases at once with `--all`
- **List mode**: View all existing backups with `--list`

### Usage

```bash
# Backup main GEX database (default)
python tools/database/backup_database.py

# Backup specific database
python tools/database/backup_database.py --database consolidated_historical.db

# Backup all databases in .cache/
python tools/database/backup_database.py --all

# Add description to backup
python tools/database/backup_database.py --description "Before Issue #102 backfill"

# List all existing backups
python tools/database/backup_database.py --list
```

### Output

Backups are stored in `.cache/backups/` with the following naming:

```
{database_name}_backup_{timestamp}.db
{database_name}_backup_{timestamp}.txt  (metadata)
```

Example:

```
gex_database_backup_20251103_142420.db
gex_database_backup_20251103_142420.txt
```

### Metadata File

Each backup includes a metadata file with:

- Backup timestamp
- Source database name
- Database size
- Date range (if applicable)
- Table names and row counts
- Optional description

### Safety

- Backups are created in `.cache/backups/` (not tracked in git)
- Original database is never modified
- Backup verification is performed automatically
- Safe to run multiple times (unique timestamps prevent overwrites)

## Best Practices

### Before Major Operations

Always create a backup before:

- Backfilling missing data
- Database schema changes
- Bulk data modifications
- Running experimental scripts

Example:

```bash
python tools/database/backup_database.py --description "Before Issue #102 backfill"
```

### Regular Maintenance

Use `--list` to review backups and clean up old ones:

```bash
python tools/database/backup_database.py --list
```

### Batch Backups

For comprehensive safety, backup all databases:

```bash
python tools/database/backup_database.py --all --description "End of week backup"
```

## backfill_missing_dates.py

Collect missing trading dates and populate the GEX database using Alpha Vantage API.

### Features

- **Auto-detection**: Uses predefined list of missing 2024 dates (Issue #102)
- **Smart collection**: Uses Alpha Vantage Premium API with rate limiting
- **GEX calculation**: Automatically calculates gamma exposure metrics
- **Database insertion**: Populates both daily metrics and strike-level details
- **Dry-run mode**: Test without making database changes
- **Verification**: Checks database state before and after

### Usage

```bash
# Dry run (recommended first)
python tools/database/backfill_missing_dates.py --dry-run

# Backfill all missing dates
python tools/database/backfill_missing_dates.py

# Backfill specific dates only
python tools/database/backfill_missing_dates.py --dates 2024-02-02 2024-02-09

# Verify database state only
python tools/database/backfill_missing_dates.py --verify-only
```

### Missing Dates (Issue #102)

The tool targets 10 missing trading dates from 2024:

```
2024-02-02 (Friday)
2024-02-09 (Friday)
2024-02-16 (Friday - Monthly OPEX)
2024-02-23 (Friday)
2024-03-01 (Friday)
2024-03-08 (Friday)
2024-03-22 (Friday - Quarterly OPEX)
2024-03-28 (Thursday)
2024-06-04 (Tuesday)
2024-06-06 (Thursday)
```

### Process Flow

1. **Check**: Verify date doesn't already exist in database
2. **Collect**: Fetch options chain from Alpha Vantage API
3. **Calculate**: Compute GEX metrics using GEXCalculator
4. **Insert**: Store results in database (daily + strike level)
5. **Verify**: Confirm database integrity

### Safety Features

- Checks if date already exists (no duplicates)
- Dry-run mode for testing
- Rate limiting (2s between dates for 75 calls/min limit)
- Automatic caching via UnifiedCacheManager
- Database verification after completion

### Output

Shows real-time progress:

```
Processing: 2024-02-02 (Friday)
  📥 Collecting options data from Alpha Vantage...
  ✅ Collected 1,234 option contracts
  🧮 Calculating GEX metrics...
  ✅ Net GEX: $-15.23B
  💾 Inserting into database...
  ✅ Data inserted successfully
```

Final summary:

```
BACKFILL COMPLETE
Statistics:
  Attempted:  10
  Collected:  10
  Calculated: 10
  Inserted:   10
  Failed:     0

Duration: 45.2 seconds
Success rate: 100.0%
New coverage: 252/252 trading days
```

## Related Files

- **Backup tool**: `tools/database/backup_database.py`
- **Backfill tool**: `tools/database/backfill_missing_dates.py`
- **Backups**: `.cache/backups/`
- **Databases**: `.cache/*.db`
- **Cache**: `.cache/options/SPY/` (pickle files)
