# Documentation

**Last Updated**: November 4, 2025

---

## Quick Navigation

### New to the Project?

1. Start with [System Overview](system/architecture/01-project-overview.md)
2. Read [Architecture Overview](system/architecture/02-architecture-overview.md)
3. Understand [GEX Metrics](guides/02-gex-metrics-explained.md)
4. Explore [Pattern Taxonomy](guides/03-pattern-taxonomy.md)

### Looking for Something Specific?

- **Research Papers** → [papers/](papers/)
- **User Guides** → [guides/](guides/)
- **System Architecture** → [system/architecture/](system/architecture/)
- **Validation Methodology** → [validation/](validation/)
- **Presentations** → [presentations/](presentations/)
- **Change History** → [CHANGELOG.md](CHANGELOG.md)

---

## Directory Structure

```
docs/
├── CHANGELOG.md                    # Project evolution tracking
├── README.md                       # This file (navigation hub)
│
├── papers/                         # Research papers
│   ├── adr/                        # Cross-paper architecture decisions
│   ├── planning/                   # Research planning docs
│   ├── paper1/                     # Paper #1 (single-day, submitted Oct 2025)
│   └── paper2/                     # Paper #2 (sequential, in progress)
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
├── system/                         # System architecture & implementation
│   ├── architecture/               # Design documents
│   │   ├── 01-project-overview.md
│   │   ├── 02-architecture-overview.md
│   │   ├── 03-data-architecture.md
│   │   ├── 04-database-architecture.md
│   │   ├── 05-cache-architecture.md
│   │   └── 06-continuous-experiment.md
│   └── implementation/             # Implementation notes
│       ├── actionable-patterns.md
│       ├── intraday-implementation.md
│       └── llm-cost-optimization/
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
│   ├── api/                        # API documentation
│   ├── technical/                  # Technical specs
│   └── model-selection-research.md
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

**Architecture**: Numbered by dependency (01-06)
- `01-project-overview.md` → Start here
- `02-architecture-overview.md` → High-level design
- `03-data-architecture.md` → Data layer
- ... builds on previous

**ADRs**: Numbered chronologically (001, 002, ...)
- Paper-specific: `papers/paper2/adr/001-scope-boundaries.md`
- Cross-paper: `papers/adr/001-validation-script-naming.md`

### Cross-References

All docs include **Navigation** sections with:
- **Prerequisites**: What to read first
- **Related**: Similar/connected topics
- **Next**: Where to go next
- **Issues**: Relevant GitHub issues

---

## Major Sections

### Papers

**Paper #1** (Single-Day Framework):
- **Status**: ✅ Submitted (Oct 26, 2025)
- **Results**: 100% detection, 87-98% accuracy (181 trading days)
- **Finding**: Detection stable despite alpha decline (Q1→Q4)
- **Location**: [papers/paper1/](papers/paper1/)

**Paper #2** (Sequential Framework):
- **Status**: 🔄 Phase 1 complete, Phase 2 pending
- **Innovation**: 5-day temporal trajectory analysis
- **Components**: SequentialGEXFetcher, neutral prompts, negative controls
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

### System

Architecture and implementation documentation:
- **Architecture**: 6 docs covering system design (01-06)
- **Implementation**: Specific feature implementations
- **Cost Optimization**: LLM model selection and optimization

**Start**: [system/architecture/01-project-overview.md](system/architecture/01-project-overview.md)

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

## Recent Updates (November 2025)

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

### Architecture Documentation (Nov 4)

- Created architecture separation ADR (Paper #1 vs #2)
- Documented shared vs paper-specific components
- Defined extension pattern for future papers
- **Impact**: Clear boundaries for Paper #3 planning

**Full History**: See [CHANGELOG.md](CHANGELOG.md)

---

## File Statistics

### Active Documentation

- **Papers**: 2 papers, 9 ADRs, 6 methodology docs, 4 session logs
- **Guides**: 8 sequenced guides
- **System**: 6 architecture docs, 3 implementation docs
- **Presentations**: 3 active, 1 archived
- **Total**: ~90 markdown files

### Size

- **Active docs**: ~2.5 MB
- **Archived**: ~3.5 MB
- **Total**: ~6 MB

---

## Contributing

### Adding New Documentation

1. **Determine type**: Guide, architecture, ADR, or session log?
2. **Choose location**: `guides/`, `system/`, `papers/adr/`, `papers/paper{N}/sessions/`
3. **Follow naming**: `kebab-case`, number if sequential
4. **Add navigation**: Prerequisites, related, next sections
5. **Update parent README**: Link from appropriate section

### Deprecating Documentation

1. Move to `archive/` with appropriate subdirectory
2. Update references in active docs
3. Note in [CHANGELOG.md](CHANGELOG.md)
4. Keep for historical reference (don't delete)

---

## Navigation

**Start Here**:
- [System Overview](system/architecture/01-project-overview.md)
- [GEX Metrics Explained](guides/02-gex-metrics-explained.md)
- [Paper #1 README](papers/paper1/README.md)
- [Paper #2 README](papers/paper2/README.md)

**Key References**:
- [CHANGELOG.md](CHANGELOG.md) - Project evolution
- [papers/adr/](papers/adr/) - Cross-paper decisions
- [validation/](validation/) - Research methodology

**GitHub**: [Issues](https://github.com/iAmGiG/gex-llm-patterns/issues) | [Projects](https://github.com/iAmGiG/gex-llm-patterns/projects)
