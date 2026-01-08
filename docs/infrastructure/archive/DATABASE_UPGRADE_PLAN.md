# Database Architecture Upgrade Plan

**Branch**: `db/upgrades`
**Created**: 2026-01-02
**Status**: ✅ **PostgreSQL Migration COMPLETE** (January 2-5, 2026)
**Purpose**: Scale infrastructure for Papers 3 & 4 (50M+ records, GNN support)

---

## ⚠️ UPDATE: PostgreSQL Migration Complete (January 2-5, 2026)

**Original Plan** (this document): Hybrid SQLite + Parquet + Graph
**Actual Implementation**: PostgreSQL 18.1 + ResearchCache (SQLite) + Future Parquet/Graph

**What Changed**:

- Migrated from SQLite to **PostgreSQL 18.1** (Issues #194, #179, #183, #193)
- Database: `gex_options` (20.58 GB, 81.8M contracts)
- Coverage: 50 symbols, 2020-2025 (6 years, 1,507 trading days)
- Schema: 31 fields per contract (27 original + 4 calculated)
- Partitioning: Yearly partitions (2020-2025) for performance
- Concurrency: Thread-safe, supports 100+ concurrent writers
- **ResearchCache** added: SQLite research metadata layer (Issue #169)

**Why PostgreSQL Instead of Parquet**:

- Better write concurrency (no locks)
- Native SQL query capabilities
- ACID transactions for data integrity
- Easier to maintain than Parquet for collection phase
- Parquet export still planned for Papers 3-4 analytics

**Current Status**: Production ready, Papers 2-5 infrastructure complete

---

## Original Plan (Archived for Reference)

**Original Proposal**: SQLite → Parquet migration
**Actual Implementation**: SQLite → PostgreSQL migration (see above)

### Executive Summary (ARCHIVED)

**Current** (OUTDATED): SQLite (options_historical.db, 5GB, growing to 20-25GB)
**Problem** (SOLVED): Concurrent write locks, no partitioning, not GNN-friendly
**Original Solution** (OUTDATED): Hybrid multi-format architecture (SQLite + Parquet + Graph)
**Actual Solution** (IMPLEMENTED): PostgreSQL 18.1 + ResearchCache

**Timeline** (OUTDATED): 2-3 weeks implementation while data collection continues
**Actual Timeline**: 3 days (January 2-5, 2026)

---

## Paper Requirements Analysis

### Paper 2: Regime Detection (CURRENT)

- ✅ SQLite sufficient
- ✅ 1,475 days SPY
- ✅ File cache (`.cache/gex_data/`)

### Paper 3: Cross-Asset (Q2 2026)

**Needs**:

- 18+ symbols × 1,500 days = 27,000 symbol-days
- ~50M options contracts
- Dask parallel processing
- Cross-asset correlation matrices
- Volatility spillover analysis

**Tooling Required**:

1. Dask pipeline (`dask_gex_pipeline.py` - already exists from AutoGen-Trader)
2. Parquet for analytics (pandas/dask native)
3. Fast aggregations (100x faster than SQLite)

### Paper 4: Graph Neural Networks (Year 3+)

**Needs**:

- Options network graph structure
- Node features: Delta, Gamma, OI, Volume, GEX
- Edge types: Strike adjacency, expiration chains, temporal, cross-asset
- GNN framework: PyTorch Geometric or DGL

**Tooling Required**:

1. Graph-friendly format (Parquet or Neo4j)
2. PyTorch Geometric data loaders
3. Strike network builder
4. Temporal graph constructor

---

## Proposed Architecture: Hybrid Multi-Format

### Phase 1: Keep SQLite for Collection ✅

```bash
.cache/options_historical.db (SQLite)
├── options_chains (11.8M rows, growing)
└── options_daily_summary (to be populated)
```

**Why**: Collection scripts already working, don't break what works

### Phase 2: Add Parquet Export (Paper 3 Ready)

```bash
.cache/parquet/
├── options/
│   ├── symbol=SPY/
│   │   └── year=2024/
│   │       ├── Q1.parquet
│   │       ├── Q2.parquet
│   │       ├── Q3.parquet
│   │       └── Q4.parquet
│   ├── symbol=QQQ/year=2024/*.parquet
│   └── ...
├── gex_summary/
│   ├── symbol=SPY/year=2024/*.parquet
│   └── ...
└── metadata/
    └── schema_version.json
```

**Benefits**:

- Column-store (read only needed columns)
- Compression (3-5x smaller than SQLite)
- Dask/Pandas native
- Fast aggregations (100x faster)

### Phase 3: Add Graph Format (Paper 4 Ready)

```bash
.cache/graphs/
├── strike_networks/
│   ├── SPY_2024-01-15.pt  # PyTorch Geometric format
│   └── ...
├── temporal_graphs/
│   ├── SPY_2024_Q1.pt
│   └── ...
└── cross_asset_graphs/
    └── indices_2024_Q1.pt
```

**Benefits**:

- PyTorch Geometric native
- Pre-built edge indices
- Fast GNN training

---

## Implementation Phases

### Phase 1: SQLite → Parquet Migration (Week 1)

**Script**: `scripts/database/migrate_to_parquet.py`

```python
# Pseudo-code
def migrate_to_parquet():
    db = sqlite3.connect('.cache/options_historical.db')

    # Get all symbols
    symbols = db.execute("SELECT DISTINCT symbol FROM options_chains").fetchall()

    for symbol in symbols:
        # Export by year/quarter for manageable file sizes
        for year in [2020, 2021, 2022, 2023, 2024, 2025]:
            for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
                df = pd.read_sql(f"""
                    SELECT * FROM options_chains
                    WHERE symbol = '{symbol}'
                    AND trading_date BETWEEN '{year}-{quarter_start}' AND '{year}-{quarter_end}'
                """, db)

                output_path = f".cache/parquet/options/symbol={symbol}/year={year}/{quarter}.parquet"
                df.to_parquet(output_path, compression='zstd', index=False)
```

**Output**: Partitioned Parquet files (~60% smaller than SQLite)

---

### Phase 2: Dask GEX Pipeline Integration (Week 1-2)

**Script**: `scripts/data_processing/dask_gex_pipeline.py` (from AutoGen-Trader)

```python
# Already implemented in AutoGen-Trader
# Processing: 50.88M records in 10 minutes (vs 8-12 hours single-threaded)

import dask.dataframe as dd
from src.gex.gex_calculator import GEXCalculator

def calculate_gex_dask(parquet_path):
    # Read Parquet with Dask
    ddf = dd.read_parquet(parquet_path)

    # Parallel GEX calculation
    gex_summary = ddf.groupby(['symbol', 'trading_date']).apply(
        lambda group: calculate_daily_gex(group),
        meta=gex_summary_schema
    ).compute()

    # Write to parquet
    gex_summary.to_parquet('.cache/parquet/gex_summary/')
```

**Performance**:

- 50M records in ~10 minutes
- 96% time reduction vs single-threaded

---

### Phase 3: Graph Builder (Week 2-3)

**Script**: `scripts/graph/build_strike_networks.py` (NEW)

```python
import torch
from torch_geometric.data import Data

def build_strike_network(options_df):
    """Build strike adjacency graph for single trading day."""

    # Nodes: Each unique option contract
    nodes = options_df[['strike', 'option_type', 'expiration',
                       'delta', 'gamma', 'open_interest', 'volume']]

    # Edges: Strike adjacency (same expiration, ±1 strike)
    edges = []
    for exp in options_df['expiration'].unique():
        exp_df = options_df[options_df['expiration'] == exp]
        sorted_strikes = sorted(exp_df['strike'].unique())

        for i in range(len(sorted_strikes) - 1):
            # Bidirectional edge
            edges.append([i, i+1])
            edges.append([i+1, i])

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    x = torch.tensor(nodes.values, dtype=torch.float)

    return Data(x=x, edge_index=edge_index)

def build_temporal_graph(symbol, start_date, end_date):
    """Build temporal graph linking same contracts across days."""
    # Load parquet for date range
    # Build edges: contract_t -> contract_t+1
    # Return PyTorch Geometric Data object
    pass

def build_cross_asset_graph(symbols, date):
    """Build cross-asset correlation graph."""
    # Nodes: Contracts from multiple symbols
    # Edges: Based on correlation threshold
    # Return PyTorch Geometric Data object
    pass
```

**Output**: `.pt` files ready for GNN training

---

## Storage Estimates

### Current (SQLite only)

- `options_historical.db`: 5.0 GB (growing to 20-25 GB for 42 symbols)
- File cache: 11 GB
- **Total**: ~16 GB → ~36 GB when complete

### After Migration (Hybrid)

- `options_historical.db`: 20-25 GB (keep for collection)
- Parquet (compressed): ~8-12 GB (60% reduction)
- Graphs: ~2-3 GB (preprocessed)
- **Total**: ~30-40 GB (within 4TB easily)

**Savings**: Better compression, faster queries, GNN-ready

---

## Performance Comparison

| Operation | SQLite | Parquet + Dask | Speedup |
|-----------|--------|----------------|---------|
| GEX calculation (50M rows) | 8-12 hours | 10 minutes | **48-72x** |
| Symbol aggregation | 30 seconds | 0.3 seconds | **100x** |
| Date range query | 15 seconds | 0.2 seconds | **75x** |
| Cross-asset correlation | 5 minutes | 3 seconds | **100x** |

---

## Migration Checklist

### Week 1: Foundation

- [x] Create `db/upgrades` branch
- [ ] Write `migrate_to_parquet.py` script
- [ ] Test migration on SPY (smallest dataset)
- [ ] Validate Parquet integrity vs SQLite
- [ ] Document schema and partitioning strategy

### Week 2: Dask Integration

- [ ] Copy `dask_gex_pipeline.py` from AutoGen-Trader
- [ ] Install dependencies: `pip install dask[complete]`
- [ ] Run on 50M records
- [ ] Populate `gex_summary` parquet files
- [ ] Benchmark vs single-threaded

### Week 3: Graph Preparation (Paper 4)

- [ ] Implement `build_strike_network()`
- [ ] Implement `build_temporal_graph()`
- [ ] Test PyTorch Geometric integration
- [ ] Create sample GNN training notebook
- [ ] Document graph schema

### Week 4: Validation & Documentation

- [ ] Cross-validate all three formats (SQLite, Parquet, Graph)
- [ ] Update all scripts to use Parquet for analytics
- [ ] Write migration guide
- [ ] Merge to main branch
- [ ] Update CLAUDE.md with new architecture

---

## Rollout Strategy

### Phase 1: Parallel Operation (Safe)

1. Keep SQLite for collection (don't break current work)
2. Export to Parquet nightly
3. Test Paper 3 scripts on Parquet
4. Validate results match SQLite

### Phase 2: Gradual Migration (Low Risk)

1. New analytics scripts use Parquet
2. Old scripts still use SQLite (backward compatible)
3. Both formats maintained

### Phase 3: Full Transition (Paper 3+)

1. Paper 3 uses Parquet exclusively
2. SQLite becomes "raw archive"
3. Parquet is "analytics layer"
4. Graphs are "GNN layer"

**No Breaking Changes**: All existing scripts continue to work

---

## Alternative: PostgreSQL Consideration

### When to Consider PostgreSQL

- If concurrent collections exceed 10 parallel processes
- If database exceeds 100 GB
- If need multi-user access

### Migration Path

```sql
-- PostgreSQL with TimescaleDB
CREATE EXTENSION timescaledb;

CREATE TABLE options_chains (
    ...
) PARTITION BY RANGE (trading_date);

-- Automatic partitioning by month
SELECT create_hypertable('options_chains', 'trading_date',
                         chunk_time_interval => INTERVAL '1 month');
```

**Decision Point**: Re-evaluate if SQLite lock issues persist

---

## Success Metrics

### Paper 3 Ready

- [ ] 18+ symbols collected
- [ ] Dask pipeline processes 50M+ records in <15 minutes
- [ ] Cross-asset correlation analysis runs in <5 minutes
- [ ] All research scripts from AutoGen-Trader working

### Paper 4 Ready

- [ ] PyTorch Geometric can load graphs
- [ ] Strike networks built for all trading days
- [ ] Sample GNN training notebook works
- [ ] Graph queries run in <1 second

---

## Risks & Mitigation

### Risk 1: Data Loss During Migration

**Mitigation**:

- Keep SQLite untouched
- Export to Parquet is READ-ONLY operation
- Validate checksums after migration

### Risk 2: Parquet Corruption

**Mitigation**:

- Use `fastparquet` or `pyarrow` (battle-tested)
- Add CRC checksums
- Test with small datasets first

### Risk 3: GNN Framework Changes

**Mitigation**:

- Use standard PyTorch Geometric format
- Abstract graph building into separate module
- Document schema for future compatibility

---

## Next Steps

1. **Immediate**: Let collections finish (current: 10/42 symbols, 5GB/20GB)
2. **Week 1**: Implement Parquet migration on SPY test data
3. **Week 2**: Integrate Dask pipeline
4. **Week 3**: Build graph prototypes
5. **Week 4**: Validate and merge

---

## References

- Issue #147: Raw Options Database Storage (current SQLite schema)
- Issue #169: ResearchCache Production Architecture
- Issue #170: HPCC Migration to ResearchCache
- Issue #179: Multi-Symbol Data Collection (current)
- Issue #181-184: Paper 3 Analysis Scripts
- Issue #185: Dask Big Data Integration
- Issue #136: Paper 4 Graph Neural Networks

---

**Status**: ✅ Plan Complete - Ready for Implementation
**Next**: Build `migrate_to_parquet.py` prototype
