# Worktree Cache Management Guide

**Last Updated**: November 22, 2025
**Context**: Issue #149 (Infrastructure Config Externalization), Issue #140 (Multi-Year Validation)

---

## Problem Statement

Git worktrees share the Git history but have **independent working directories**. This creates challenges for large caches:

1. **Cache Data**: `.cache/` directory contains ~5-10GB of historical options data
2. **Database**: `.cache/consolidated_historical.db` (~500MB) with multi-year GEX metrics
3. **Worktree Independence**: Each worktree has its own `.cache/` directory by default
4. **Cost**: Duplicating cache across N worktrees wastes N×10GB disk space

### Real-World Impact (Issue #140)

During Paper #2 multi-year validation (November 2025):

- Main worktree: `/mnt/bst/yxie2/cregan1/gex-llm-patterns` (branch: `paper2-sequential-gex`)
- Issue #140 worktree: `/mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140` (branch: `paper2-issue140-phase4`)
- Cache divergence: Data collection in Issue #140 worktree, but queries from main worktree failed
- Root cause: Independent `.cache/` directories, database out of sync

---

## Cache Architecture

### Files and Locations

```
.cache/
├── gex_data/                     # Raw GEX data by symbol/date
│   └── SPY/
│       ├── 2020-01-02/
│       │   ├── gex_summary.json
│       │   └── options_chain.json
│       └── 2024-12-31/
│           └── ...
├── consolidated_historical.db    # SQLite database (single GEX only)
├── consolidated_historical_dual.db  # SQLite database (dual GEX, Issue #140+)
└── regime_windows/               # Paper #2 regime validation results
    └── batch_results_*.jsonl
```

### Database Schema

**Single GEX** (`consolidated_historical.db`):

- Table: `daily_gex_metrics`
- Columns: `symbol`, `date`, `spot_price`, `net_gex_usd`, `total_gamma`, `flip_point`, etc.
- Used by: Paper #1, legacy validation scripts

**Dual GEX** (`consolidated_historical_dual.db`, Issue #140+):

- Table: `daily_gex_metrics`
- Additional column: `short_dated_gex_usd` (0-1 DTE gamma)
- Used by: Paper #2 multi-year validation

### Ignore Status

```gitignore
# .gitignore
.cache/
*.db
*.db-journal
```

Cache data is **never committed to Git** (excluded via `.gitignore`).

---

## Worktree Cache Strategies

### Strategy 1: Symlink (Recommended)

**Use Case**: Multiple worktrees need to **share the same cache** (read-only or coordinated writes).

**Setup**:

```bash
# Main worktree (keep cache here)
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns
ls -la .cache/  # Verify cache exists

# New worktree (create without cache)
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140
rm -rf .cache/  # Remove independent cache if it exists

# Create symlink to main cache
ln -s /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache .cache

# Verify symlink
ls -la .cache  # Should show symlink arrow
readlink -f .cache  # Should show main worktree path
```

**Pros**:

- ✅ Zero disk space overhead (shared cache)
- ✅ Automatic sync (all worktrees see same data)
- ✅ Simple setup (single `ln -s` command)

**Cons**:

- ⚠️ **Concurrent writes**: Database writes from multiple worktrees can cause lock contention
- ⚠️ **Deletion risk**: `rm -rf .cache` in one worktree deletes shared cache
- ❌ **Worktree-specific configs**: Cannot have different cache configurations per worktree

**Best For**:

- Read-only workloads (validation, analysis)
- Single writer, multiple readers
- Development experiments (branching logic, not data collection)

---

### Strategy 2: Independent Caches

**Use Case**: Each worktree needs **isolated cache** (independent data collection, different date ranges).

**Setup**:

```bash
# Create new worktree (Git creates independent .cache by default)
git worktree add ../gex-llm-patterns-issue140 -b paper2-issue140-phase4

# No additional setup needed - .cache/ is already independent
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140
ls -la .cache/  # Empty or minimal cache
```

**Pros**:

- ✅ Complete isolation (no interference between worktrees)
- ✅ Safe concurrent writes (each worktree has own database)
- ✅ Worktree-specific cache configs possible

**Cons**:

- ❌ **Disk space**: N worktrees = N×10GB cache overhead
- ❌ **Data duplication**: Same GEX data stored multiple times
- ⚠️ **Manual sync**: Changes in one cache don't propagate to others

**Best For**:

- Data collection workflows (different years, symbols)
- Long-lived branches with divergent requirements
- Testing database schema changes (Issue #140 dual GEX migration)

---

### Strategy 3: Rsync on Demand

**Use Case**: Start with independent caches, sync **selectively** when needed.

**Setup**:

```bash
# Initial state: Independent caches
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140

# Sync specific data from main cache (one-time copy)
rsync -av --progress \
  /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache/gex_data/SPY/2024-* \
  .cache/gex_data/SPY/

# Sync database (careful: overwrites local changes)
rsync -av \
  /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache/consolidated_historical_dual.db \
  .cache/

# Verify sync
ls .cache/gex_data/SPY/ | wc -l  # Should match main worktree for synced dates
```

**Pros**:

- ✅ Selective sync (copy only needed data)
- ✅ Independent after sync (no ongoing dependency)
- ✅ Safe for concurrent workflows (snapshot in time)

**Cons**:

- ⚠️ **Manual process**: Requires explicit rsync commands
- ❌ **Stale data**: Synced cache becomes outdated over time
- ⚠️ **Overwrite risk**: rsync can accidentally overwrite newer local data

**Best For**:

- Bootstrapping new worktrees (copy base cache, then diverge)
- Periodic sync workflows (weekly/monthly cache updates)
- Cherry-picking specific date ranges (e.g., only 2024 data)

---

## Decision Matrix

| Scenario | Recommended Strategy | Rationale |
|----------|---------------------|-----------|
| **Paper #2 validation** (read-only) | Symlink | No writes, shared data, zero overhead |
| **Paper #1 extensions** (analysis) | Symlink | Existing cache, no collection needed |
| **Multi-year data collection** (Issue #140) | Independent + rsync | Isolated writes, merge later |
| **Database schema migration** | Independent | Test changes without breaking main |
| **Quick experiment** (bug fix) | Symlink | Fast setup, shared data |
| **Long-lived dev branch** | Independent | Full isolation for divergent work |

---

## Common Pitfalls

### Pitfall 1: Cache Divergence (Issue #140 Lesson)

**Symptom**: Script fails with "no data found" despite seeing files in `.cache/gex_data/`.

**Cause**: Data collection happened in worktree A, but query runs in worktree B (independent caches).

**Fix**:

```bash
# Option 1: Symlink both worktrees to main cache
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140
rm -rf .cache && ln -s /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache .cache

# Option 2: Rsync database from collection worktree
rsync -av \
  /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140/.cache/consolidated_historical_dual.db \
  /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache/
```

**Prevention**: Document which worktree owns the "source of truth" cache for each workflow.

---

### Pitfall 2: Database Lock Contention

**Symptom**: `sqlite3.OperationalError: database is locked` when running scripts in multiple worktrees simultaneously.

**Cause**: Symlinked cache + concurrent SQLite writes from different processes.

**Fix**:

```bash
# Option 1: Run scripts sequentially (not in parallel)
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns
python scripts/validation/collect_data.py  # Wait to finish

cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140
python scripts/analysis/analyze_results.py  # Run after first completes

# Option 2: Switch to independent caches for concurrent workflows
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140
rm .cache && mkdir .cache  # Break symlink, create independent cache
```

**Prevention**: Use symlink only for read-heavy workflows. Use independent caches for write-heavy data collection.

---

### Pitfall 3: Accidental Cache Deletion

**Symptom**: `rm -rf .cache` in one worktree deletes cache for all symlinked worktrees.

**Cause**: Symlink points to shared cache; deletion propagates.

**Fix**:

```bash
# Recovery: No Git backup exists (cache is .gitignored)
# Must re-collect data or restore from system backup

# Prevention: Use `unlink` instead of `rm -rf` for symlinks
unlink .cache  # Removes symlink only, preserves target
```

**Best Practice**: Never use `rm -rf .cache` when cache is symlinked. Check first:

```bash
if [ -L .cache ]; then
  echo "⚠️  Warning: .cache is a symlink. Use 'unlink .cache' instead of rm."
  readlink -f .cache
fi
```

---

## Workflow Recommendations

### Paper #2 Multi-Year Validation (Issue #140 Pattern)

**Scenario**: Collect data for 6 years (2020-2025), validate with Batch API.

**Setup**:

```bash
# Main worktree: analysis and writing (read-only cache)
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns
# (Keep main cache here as source of truth)

# Issue #140 worktree: data collection (independent cache)
git worktree add ../gex-llm-patterns-issue140 -b paper2-issue140-phase4
cd ../gex-llm-patterns-issue140

# Collect data (writes to independent cache)
export PYTHONPATH=$PWD:$PYTHONPATH
python scripts/data_collection/collect_multi_year_gex.py --start 2020-01-02 --end 2025-12-31

# After collection: rsync database to main for analysis
rsync -av .cache/consolidated_historical_dual.db \
  /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache/
```

**Rationale**:

- **Independent cache** during collection (safe concurrent writes, isolated testing)
- **Rsync to main** after collection (centralize results for analysis)
- **Main worktree symlink** for read-only validation scripts (shared access, zero overhead)

---

### Quick Development Experiment

**Scenario**: Test a bug fix on existing validation scripts.

**Setup**:

```bash
# Create worktree for fix
git worktree add ../gex-llm-patterns-bugfix -b fix-issue-123

# Symlink to main cache (no data collection needed)
cd ../gex-llm-patterns-bugfix
ln -s /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache .cache

# Run validation scripts (read-only)
export PYTHONPATH=$PWD:$PYTHONPATH
python scripts/validation/validate_pattern_taxonomy.py --pattern gamma_positioning

# No cleanup needed - cache is shared, no duplication
```

---

## Cache Verification Commands

### Check Symlink Status

```bash
# Is .cache a symlink?
ls -la .cache

# Where does symlink point?
readlink -f .cache

# Compare sizes (should match if symlinked)
du -sh /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache
du -sh /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140/.cache
```

### Database Integrity

```bash
# Check database exists and is readable
sqlite3 .cache/consolidated_historical_dual.db "SELECT COUNT(*) FROM daily_gex_metrics;"

# Verify date range coverage
sqlite3 .cache/consolidated_historical_dual.db "SELECT MIN(date), MAX(date) FROM daily_gex_metrics WHERE symbol='SPY';"

# Check dual GEX column exists (Issue #140+)
sqlite3 .cache/consolidated_historical_dual.db ".schema daily_gex_metrics" | grep short_dated_gex_usd
```

### File Cache Coverage

```bash
# Count cached dates for SPY
ls .cache/gex_data/SPY/ | wc -l

# Check specific date exists
ls .cache/gex_data/SPY/2024-01-02/

# Verify file structure
cat .cache/gex_data/SPY/2024-01-02/gex_summary.json | jq .
```

---

## Migration Guide: Independent → Symlink

**When**: After data collection is complete and you want to consolidate caches.

```bash
# 1. Verify main cache is up-to-date
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns
ls .cache/  # Should contain latest data

# 2. Backup issue worktree cache (if it has unique data)
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140
tar -czf cache_backup_$(date +%Y%m%d).tar.gz .cache/

# 3. Remove independent cache
rm -rf .cache

# 4. Create symlink to main cache
ln -s /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache .cache

# 5. Verify symlink works
ls .cache/gex_data/SPY/ | head -5
sqlite3 .cache/consolidated_historical_dual.db "SELECT COUNT(*) FROM daily_gex_metrics;"
```

---

## Cleanup and Maintenance

### Remove Stale Worktrees

```bash
# List all worktrees
git worktree list

# Remove worktree (preserves Git history, deletes working directory + cache)
git worktree remove /mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140

# Prune deleted worktree references
git worktree prune
```

### Cache Size Management

```bash
# Check total cache size
du -sh .cache/

# Identify large subdirectories
du -h --max-depth=1 .cache/ | sort -rh | head -10

# Clean old validation results (safe to delete)
rm -f .cache/regime_windows/batch_results_*.jsonl

# Archive old years (if only recent data needed)
tar -czf cache_archive_2020_2021.tar.gz .cache/gex_data/SPY/202{0,1}-*
rm -rf .cache/gex_data/SPY/202{0,1}-*
```

---

## Troubleshooting

### "Permission Denied" on Symlink Creation

**Cause**: Insufficient permissions on target directory.

**Fix**:

```bash
# Check permissions on main cache
ls -ld /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache

# Ensure readable
chmod -R u+r /mnt/bst/yxie2/cregan1/gex-llm-patterns/.cache
```

### "Database Malformed" Error

**Cause**: Incomplete write or corruption during concurrent access.

**Fix**:

```bash
# Check database integrity
sqlite3 .cache/consolidated_historical_dual.db "PRAGMA integrity_check;"

# If corrupted, restore from backup or re-collect data
# (No automatic backup - cache is .gitignored)
```

### "No Such Table" Error

**Cause**: Using wrong database file (single vs dual GEX schema).

**Fix**:

```bash
# Check which database script expects
grep "consolidated_historical" scripts/validation/validate_regime_windows_batch.py

# Verify table schema
sqlite3 .cache/consolidated_historical_dual.db ".tables"
sqlite3 .cache/consolidated_historical_dual.db ".schema daily_gex_metrics"
```

---

## Summary

**Key Takeaways**:

1. **Symlink for reads**: Fast, zero overhead, shared data (Paper #2 validation)
2. **Independent for writes**: Safe isolation during data collection (Issue #140 pattern)
3. **Rsync for merge**: Consolidate independent caches after collection
4. **Never `rm -rf` symlinks**: Use `unlink` to preserve shared cache
5. **Document ownership**: Which worktree owns the "source of truth" cache

**Default Recommendation**:

- Start with **symlink** (simplest, zero cost)
- Switch to **independent** if you need concurrent writes
- Use **rsync** to merge back after collection completes

---

**Related Documentation**:

- [Issue #140 Multi-Year Validation](https://github.com/iAmGiG/gex-llm-patterns/issues/140)
- [Issue #149 Infrastructure Grooming](https://github.com/iAmGiG/gex-llm-patterns/issues/149)
- [Database Schema Guide](../database/schema_migration_dual_gex.md)
