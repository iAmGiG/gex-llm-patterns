# Cache System Audit Report
**Date**: September 12, 2025  
**Branch**: dbreorg  
**Issues**: #44, #45

## Executive Summary
The `.cache/` directory contains **8 SQLite databases** (mostly test files), **78 pickle files**, **23 JSON files**, and inconsistent directory structures. Only **1 database has real data**. **Immediate cleanup required.**

## Database Files Analysis

### SQLite Databases Audit
| Database | Size | Records | Status | Purpose |
|----------|------|---------|---------|---------|
| `consolidated_historical.db` | 36K | **13** | ✅ **ACTIVE** | **Main production DB** |
| `january_2024_gex.db` | 220K | 6 | ⚠️ Partial | January 2024 only |
| `test_gex_pipeline.db` | 144K | 7 | ❌ Test file | Should be deleted |
| `test_fixed.db` | 68K | 1 | ❌ Test file | Should be deleted |
| `gex_database.db` | 56K | 0 | ❌ Empty | Should be deleted |
| `test_gex_database.db` | 56K | 0 | ❌ Empty test | Should be deleted |
| `test_single.db` | 56K | 0 | ❌ Empty test | Should be deleted |
| `debug_test.db` | 0K | - | ❌ Corrupted | Should be deleted |

### Key Findings
- ✅ **`consolidated_historical.db` is the source of truth** (13 records)
- ❌ **6 test/debug databases** cluttering production cache (348K wasted)
- ⚠️ **`january_2024_gex.db`** might have data not in main DB

## Directory Structure Analysis

### Active Directories (Contains Data)
| Directory | Size | Files | Purpose | Status |
|-----------|------|-------|---------|---------|
| `options/` | **34M** | 66 pickle files | Options chain data from API | ✅ **ACTIVE** |
| `market_data/` | 1.4M | 46+ pickle files | Stock OHLCV data | ✅ **ACTIVE** |
| `gex_data/` | 32K | Subdirectories | GEX calculations? | ❓ **UNCLEAR** |
| `fed_data/` | 12K | Fed indicators | Fed economic data | ✅ **ACTIVE** |
| `fed_analysis/` | 16K | Fed analysis | Fed analysis results | ✅ **ACTIVE** |

### Utility Directories
| Directory | Size | Purpose | Status |
|-----------|------|---------|---------|
| `pattern_analysis/` | 20K | Pattern detection results | ✅ ACTIVE |
| `stocks/` | 4K | Stock-specific data | ❓ UNCLEAR |
| `metadata/` | 32K | System metadata | ❓ UNCLEAR |
| `index/` | 36K | Index data | ❓ UNCLEAR |
| `news/` | 12K | News cache | ❓ UNCLEAR |

## Code Usage Analysis

### Scripts Using Main Database
```bash
grep -r "consolidated_historical.db" src/ scripts/
```
**6 files** reference the main database:
- `src/testing/expanded_pattern_detection.py` ✅
- `src/testing/comprehensive_backtest.py` ✅  
- `src/analysis/baseline_comparison.py` ✅
- `scripts/run_experiment.py` ✅

### Cache Access Patterns
- **Mixed patterns**: Some use `.cache/consolidated_historical.db`, others relative paths
- **No unified interface**: Direct SQLite connections throughout codebase
- **Inconsistent**: Some scripts may use pickle files, others database

## File Analysis Summary

### Junk Files (Safe to Delete)
```
.cache/test_*.db                    # 4 test databases
.cache/debug_test.db               # Corrupted debug file
.cache/gex_database.db             # Empty duplicate
.cache/gex_database_build_summary_*.json  # 10+ build logs
```
**Estimated savings**: ~400K disk space

### Data Files (Keep/Investigate)
```
.cache/consolidated_historical.db   # MAIN DATABASE - KEEP
.cache/january_2024_gex.db         # Check for unique data first
.cache/options/*.pickle             # 34M of API data - KEEP
.cache/market_data/*.pickle         # 1.4M of market data - KEEP
```

### Unknown Purpose (Investigate)
```
.cache/gex_data/                   # 32K - used or abandoned?
.cache/metadata/                   # 32K - what metadata?
.cache/index/                      # 36K - index of what?
.cache/stocks/                     # 4K - overlap with market_data?
```

## Critical Issues Identified

### 1. Database Chaos
- **8 databases** when only 1 should exist
- **Test files in production** cache directory
- **No clear migration path** from old to new schemas

### 2. Data Duplication
- **Options data**: Both in `.cache/options/` pickles AND database?
- **Market data**: In `.cache/market_data/` pickles but not database?
- **GEX calculations**: In database but also `.cache/gex_data/`?

### 3. Inconsistent Access
- **No unified cache interface**
- **Direct SQLite connections** scattered across codebase
- **Mixed pickle/database usage** patterns

### 4. Documentation Gap
- **Unknown directory purposes** (gex_data, metadata, index, stocks)
- **Unclear data flow** API → pickle → database?
- **No cache management** strategy or rotation

## Immediate Actions Required

### Phase 1: Emergency Cleanup (Today)
1. **Backup main database**: Copy `consolidated_historical.db` 
2. **Delete test files**: Remove all `test_*.db` and `debug_*.db`
3. **Clean build logs**: Remove duplicate JSON summary files
4. **Verify january_2024_gex.db**: Check if has data not in main DB

### Phase 2: Investigation (This Week)
1. **Map data flow**: Document pickle → database transformation
2. **Directory audit**: Determine purpose of unclear directories
3. **Code analysis**: Find all cache access patterns
4. **Schema analysis**: Understand current database structure

### Phase 3: Design & Implementation (Next Week)
1. **Design unified cache system** (Issue #45)
2. **Create migration plan** for data consolidation
3. **Implement unified cache interface**
4. **Update all code** to use consistent patterns

## Recommendations

### Proposed Clean Architecture
```
.cache/
├── unified.db                  # Single source of truth
├── raw/                        # API responses (pickle)
│   ├── options/{symbol}/
│   ├── market/{symbol}/
│   └── fed/
├── calculated/                 # Computed metrics  
│   ├── gex/{symbol}/
│   └── patterns/
└── logs/                       # System logs
    └── api_calls.log
```

### Priority Actions
1. 🚨 **CRITICAL**: Clean test files immediately
2. 🔥 **HIGH**: Document current data flow 
3. 📋 **MEDIUM**: Design unified system
4. 🔧 **LOW**: Implement new architecture

**This audit reveals the cache system needs immediate attention before any further development.**