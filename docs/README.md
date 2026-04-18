# Documentation

**Last Updated**: January 13, 2026

---

## Quick Navigation

### New to the Project?

1. Start with [Project Overview](infrastructure/01-project-overview.md)
2. Read [Architecture Overview](infrastructure/02-architecture-overview.md)
3. Understand [Data & Database](infrastructure/03-data-and-database.md)
4. Explore [GEX Metrics Guide](guides/02-gex-metrics-explained.md)

**Full Infrastructure Learning Path**: See [infrastructure/README.md](infrastructure/README.md) for sequential 01-09 reading order (~2-3 hours)

### Looking for Something Specific?

- **Research Papers** → [papers/](papers/)
- **User Guides** → [guides/](guides/)
- **Infrastructure & Architecture** → [infrastructure/](infrastructure/) (📖 start here for system understanding)
- **Development Workflows** → [development/](development/)
- **Validation Methodology** → [validation/](validation/)
- **Presentations** → [presentations/](presentations/)
- **Change History** → [CHANGELOG.md](CHANGELOG.md)

---

## Directory Structure

```bash
docs/
├── CHANGELOG.md                    # Project evolution tracking
├── README.md                       # This file (navigation hub)
│
├── infrastructure/                 # 📖 System architecture & implementation (START HERE)
│   ├── 01-project-overview.md     # Research hypothesis and vision
│   ├── 02-architecture-overview.md # High-level system design
│   ├── 03-data-and-database.md    # Data architecture & database schema
│   ├── 04-cache-and-performance.md # Cache system & token optimization
│   ├── 05-llm-integration.md      # Model selection & LLM integration
│   ├── 06-implementation-guide.md # Patterns & intraday support
│   ├── 07-experiments-and-validation.md # Continuous experiment framework
│   ├── 08-maintenance-and-audits.md # Maintenance & infrastructure audits
│   ├── 09-intraday-infrastructure.md # Intraday data & OI monitor (Paper #3)
│   └── README.md                  # Sequential learning path guide
│
├── development/                    # Developer workflows & tools
│   ├── worktree_cache_management.md # Git worktree cache strategies
│   └── README.md                  # Development guide index
│
├── papers/                         # Research papers
│   ├── adr/                        # Cross-paper architecture decisions
│   ├── planning/                   # Research planning docs
│   ├── paper1/                     # Paper #1 (single-day, IEEE BigData 2025 — published)
│   ├── paper2/                     # Paper #2 (regime detection — AIAI accepted, JRFM under review)
│   └── extensions/                 # Forward-looking research directions (snapshot)
│
├── guides/                         # User-facing how-to guides
│   ├── 02-gex-metrics-explained.md
│   ├── 03-pattern-taxonomy.md
│   ├── 04-pattern-validation.md
│   ├── 05-data-obfuscation.md
│   ├── 06-validation-framework.md
│   ├── 07-yaml-reporting.md
│   ├── 08-baseline-strategy.md
│   └── 09-documentation-security.md
│
├── validation/                     # Validation methodology
│   └── statistical/                # Statistical validation methods
│       ├── granger-causality-pipeline.md
│       └── lead-lag-pipeline.md
│
├── presentations/                  # Educational and presentation materials
│   ├── 2025-symposium.md          # PhD symposium (Oct 2025)
│   ├── fundamentals-explained.md   # Market mechanics education
│   ├── technical-deep-dive.md      # System deep dive
│   └── archive/                    # Historical presentations
│
├── reference/                      # Technical reference
│   ├── api/                        # API documentation (Alpha Vantage, etc.)
│   └── technical/                  # Technical specs & audits
│
└── archive/                        # Historical/deprecated content
    ├── sessions/                   # Old session logs
    ├── guides/                     # Deprecated guides
    ├── reference/                  # Deprecated reference docs
    └── presentations/              # Old presentations
```

---

## Documentation Standards

### Naming Conventions

**Files**: All lowercase with hyphens (`kebab-case`)

- ✅ `gex-metrics-explained.md`
- ✅ `2025-symposium.md`
- ❌ `gex_metrics_explained.md` (no underscores)
- ❌ `GEX_METRICS.md` (no capitals)

**Exception**: `README.md` (uppercase standard)

### Sequencing

**Guides**: Numbered for linear progression (02-09)

- `02-gex-metrics-explained.md` → Foundation
- `03-pattern-taxonomy.md` → Core concepts
- `04-pattern-validation.md` → Methodology
- ... logical progression

**Infrastructure**: Numbered by dependency (01-09)

- `01-project-overview.md` → Start here
- `02-architecture-overview.md` → High-level design
- `03-data-and-database.md` → Data & database layer
- ... builds on previous (see [infrastructure/README.md](infrastructure/README.md))

**ADRs**: Numbered chronologically (001, 002, ...)

- Paper-specific: `papers/paper2/adr/001-scope-boundaries.md`
- Cross-paper: `papers/adr/001-validation-script-naming.md`

### Cross-References

All docs include **Navigation** sections with:

- **Prerequisites**: What to read first
- **Related**: Similar/connected topics
- **Next**: Where to go next
- **Issues**: Relevant GitHub issues

### Documentation Management

**File Consolidation Principles** (Nov 2025 update):

- **Sequential numbering** for learning paths (01-08 infrastructure, 02-09 guides)
- **Consolidate related content** to reduce file count while preserving detail
- **Part-based organization** for long files (Part 1, Part 2, etc.)
- **Living documentation** for active systems (not archived unless obsolete)
- **Clear naming** that describes content (`issue_NNN_description.md`, `topic-name.md`)

**Recent Consolidation** (Nov 24, 2025):

- Merged 13 files (system/ + reference/ + infrastructure/) → 9 sequential infrastructure files
- 31% reduction in file count, 100% detail preservation
- See [infrastructure/08-maintenance-and-audits.md](infrastructure/08-maintenance-and-audits.md) for audit history

---

## Major Sections

### Papers

**Paper #1** (Single-Day Framework):

- **Status**: ✅ Published (IEEE BigData 2025, Dec 2025)
- **Results**: 71.5% detection, 91.2% predictive accuracy (242 trading days, 726 evaluations)
- **Finding**: LLMs identify dealer constraint patterns under temporal obfuscation
- **Location**: [papers/paper1/](papers/paper1/)

**Paper #2** (30-Day Regime Framework):

- **Status**: ✅ Accepted at AIAI 2026 (camera-ready May 2026) · 🔄 Under review at JRFM (MDPI)
- **Results**: 81.2% detection 2024 vs 12.1% 2020 (69.1pp separation, φ = 0.672, p < 0.0001), 2,221 evaluations
- **Finding**: 0DTE-driven market structure evolution detected under temporal obfuscation
- **Location**: [papers/paper2/](papers/paper2/)

**Cross-Paper ADRs**:

- Architecture decisions affecting multiple papers
- Validation script naming conventions
- Shared infrastructure design
- **Location**: [papers/adr/](papers/adr/)

### Guides

Sequential how-to documentation for users:

- **Foundation**: GEX metrics, pattern taxonomy
- **Methodology**: Validation framework, obfuscation
- **Output**: YAML reporting, baseline strategy
- **Security**: Documentation security guidelines

**Start**: [guides/02-gex-metrics-explained.md](guides/02-gex-metrics-explained.md)

### Infrastructure

Comprehensive system architecture and implementation documentation (📖 recommended reading path):

- **Architecture** (01-03): Project overview, high-level design, data & database
- **Performance** (04-05): Cache system, token optimization, LLM integration
- **Implementation** (06-07): Patterns, intraday support, experiments, validation
- **Maintenance** (08): Infrastructure audits, best practices, known issues
- **Intraday** (09): Intraday data collection, OI monitor service (Paper #3)

**Start**: [infrastructure/01-project-overview.md](infrastructure/01-project-overview.md)
**Learning Path**: [infrastructure/README.md](infrastructure/README.md) (~2-3 hour sequential read)

### Validation

Research validation methodology:

- **Statistical**: Granger causality, lead-lag analysis
- **Negative Controls**: Paper #2 bias mitigation
- **Pattern Validation**: Obfuscation testing

**Location**: [validation/](validation/)

### Presentations

Educational materials and symposium presentations:

- **2025 Symposium**: Paper #1 results (October 2025)
- **Fundamentals**: Market mechanics education
- **Technical Deep Dive**: System architecture walkthrough

**Location**: [presentations/](presentations/)

---

## Recent Updates

### January 2026

- Added **09-intraday-infrastructure.md** for Paper #3 intraday data collection
- Paper #2 figure improvements and LaTeX polishing
- Options chain quality validation (Issue #16) implemented

### November 2025

#### Infrastructure Consolidation (Nov 24)

- Merged 13 files (system/ + reference/ + infrastructure/) → 9 sequential files (01-08)
- Created comprehensive learning path with sequential numbering
- Consolidated related concepts while preserving 100% detail
- Added navigation links (Prerequisites/Next/Related) to all infrastructure docs
- **Impact**: 31% reduction in file count, clear learning progression, AutoTrader-AgentEdge adoption ready

### Documentation Reorganization (Nov 4)

- Standardized all files to `kebab-case` naming
- Sequenced guides (02-09) and architecture (01-06)
- Created cross-paper ADR structure
- Archived 11 deprecated files
- **Impact**: 103 file operations, clear domain separation

### Paper #2 Phase 1 Complete (Nov 4)

- Implemented SequentialGEXFetcher (5-day windows)
- Created neutral prompt framework
- Built negative controls validation
- Fixed 3 critical bugs
- **Result**: Proof-of-concept validated (120 windows)

**Full History**: See [CHANGELOG.md](CHANGELOG.md)

---

## File Statistics

### Active Documentation

- **Papers**: 2 papers, 9 ADRs, 6 methodology docs, 4 session logs
- **Guides**: 8 sequenced guides (02-09)
- **Infrastructure**: 10 sequential docs (01-09 + README)
- **Development**: 2 guides (worktree management + README)
- **Presentations**: 3 active, 1 archived
- **Total**: ~85 markdown files (reduced from ~90 via consolidation)

### Size

- **Active docs**: ~2.7 MB
- **Archived**: ~3.5 MB
- **Total**: ~6.2 MB

### Consolidation Impact

- **Nov 2025**: 13 files (system/ + reference/) → 9 files (infrastructure/ 01-08)
- **Jan 2026**: Added 09-intraday-infrastructure.md → 10 files (01-09 + README)
- **Net Result**: Clear sequential learning path, 100% detail preserved

---

## Contributing

### Adding New Documentation

1. **Determine type**: Guide, infrastructure, ADR, or session log?
2. **Choose location**: `guides/`, `infrastructure/`, `papers/adr/`, `papers/paper{N}/sessions/`
3. **Follow naming**: `kebab-case`, number if sequential (01-08 for infrastructure, 02-09 for guides)
4. **Add navigation**: Prerequisites, related, next sections
5. **Update parent README**: Link from appropriate section
6. **Consolidate when possible**: Prefer adding to existing files (as "Part N") over creating new files

### Deprecating Documentation

1. Move to `archive/` with appropriate subdirectory
2. Update references in active docs
3. Note in [CHANGELOG.md](CHANGELOG.md)
4. Keep for historical reference (don't delete)

---

## Navigation

**Start Here**:

- [Infrastructure Overview](infrastructure/01-project-overview.md)
- [GEX Metrics Explained](guides/02-gex-metrics-explained.md)
- [Paper #1 README](papers/paper1/README.md)
- [Paper #2 README](papers/paper2/README.md)

**Key References**:

- [CHANGELOG.md](CHANGELOG.md) - Project evolution
- [papers/adr/](papers/adr/) - Cross-paper decisions
- [validation/](validation/) - Research methodology

**GitHub**: [Issues](https://github.com/iAmGiG/gex-llm-patterns/issues) | [Projects](https://github.com/iAmGiG/gex-llm-patterns/projects)
