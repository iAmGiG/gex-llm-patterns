# GEX-LLM Development Tools

Developer utilities for code quality, database maintenance, and debugging.

## Tools

### Code Review Agent (`code_reviewer.py`)

Comprehensive Python code review tool for maintaining code quality.

```bash
# Review a single file
python tools/code_reviewer.py src/gex/gex_calculator.py

# Review with automatic import fixing
python tools/code_reviewer.py src/gex/gex_calculator.py --fix-imports
```

**Note**: Pre-commit hooks (black, isort, flake8) handle most linting automatically.

### Pickle Viewer (`pickle_viewer.py`)

Quick utility to inspect pickle files.

```bash
python tools/pickle_viewer.py path/to/file.pickle
```

### Database Utilities (`database/`)

#### Backup Database (`database/backup_database.py`)

Creates timestamped backups before major operations.

```bash
python tools/database/backup_database.py
python tools/database/backup_database.py --database gex_database.db
python tools/database/backup_database.py --all
```

#### Backfill Missing Dates (`database/backfill_missing_dates.py`)

Collects missing SPY options data for specific dates.

```bash
python tools/database/backfill_missing_dates.py --dry-run
python tools/database/backfill_missing_dates.py --dates 2024-02-02 2024-02-09
```
