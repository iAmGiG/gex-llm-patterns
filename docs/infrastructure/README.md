# Infrastructure Documentation

System architecture, design decisions, implementation guides, and maintenance documentation for the GEX LLM Patterns system.

---

## Quick Start: Learning Path

**New to the system?** Follow this sequential reading order:

1. **[01-project-overview.md](01-project-overview.md)** - Start here to understand the research hypothesis and system vision
2. **[02-architecture-overview.md](02-architecture-overview.md)** - High-level system design and component interactions
3. **[03-data-and-database.md](03-data-and-database.md)** - Understand the 2-tier data system and database architecture
4. **[04-cache-and-performance.md](04-cache-and-performance.md)** - Learn about multi-layer caching, token optimization, and ResearchCache
5. **[05-llm-integration.md](05-llm-integration.md)** - Model selection decisions and LLM integration patterns
6. **[06-implementation-guide.md](06-implementation-guide.md)** - Actionable patterns and intraday support implementation
7. **[07-experiments-and-validation.md](07-experiments-and-validation.md)** - Continuous experiment framework and validation methodology
8. **[08-maintenance-and-audits.md](08-maintenance-and-audits.md)** - Infrastructure maintenance, audits, and best practices
9. **[09-intraday-infrastructure.md](09-intraday-infrastructure.md)** - Intraday data collection, database schema, and OI monitor service (Paper #3)

**Time Investment**: ~2-3 hours for complete sequential reading

---

## Documentation Organization

### Sequential Learning (01-09)

**Numbered files (01-09) follow a logical progression from high-level concepts to specific implementation details.** Each document builds on previous knowledge and includes navigation links.

#### Part 1: System Foundation (01-03)

**[01-project-overview.md](01-project-overview.md)** - Research Hypothesis and Vision

- What problem we're solving with LLMs
- Core research question: Can LLMs detect institutional patterns?
- System architecture diagram
- Key pattern example: Short Put Arbitrage
- Development status and methodology

**[02-architecture-overview.md](02-architecture-overview.md)** - High-Level Design

- Component interactions and data flow
- MarketMechanicsAgent, Pattern Library, GEX Calculator
- Data obfuscation and validation framework
- LLM architecture (dual-model setup)
- Design principles (modularity, caching-first, research integrity)

**[03-data-and-database.md](03-data-and-database.md)** - Data and Database Architecture

- **Part 1: Data Architecture** - 2-tier system (Database → Cache → AutoGen Tools → API)
- **Part 2: Database Architecture** - SQLite schema, tables, indexes
- Performance characteristics and optimization
- Integration points with agents and validation

#### Part 2: Performance and Integration (04-05)

**[04-cache-and-performance.md](04-cache-and-performance.md)** - Cache System and Optimization

- **Part 1: Cache Architecture** - UnifiedCacheManager, GEXCacheManager, IntradayCacheManager
- **Part 2: Token Configuration** - Zero-token operations vs LLM reasoning
- Lazy directory creation and concurrent processing
- Cost optimization strategies

**[05-llm-integration.md](05-llm-integration.md)** - LLM Selection and Integration

- **Part 1: Model Selection Research** - O3-mini vs GPT-4o (Issue #62)
- **Part 2: Academic Rigor Analysis** - O4-mini for Paper #2 (80% confidence)
- **Part 3: Paper-Specific Decisions** - Paper #1 (o3-mini, 90%) vs Paper #2 (o4-mini, 80%)
- **Part 4: Configuration History** - Evolution of model choices

#### Part 3: Implementation and Validation (06-08)

**[06-implementation-guide.md](06-implementation-guide.md)** - Patterns and Intraday Support

- **Part 1: Actionable Trading Patterns** - Gamma squeeze, pin risk, dealer hedging
- **Part 2: Intraday Implementation** - 10-minute intervals, gamma pinning validation
- Database schema (intraday tables), cache system, validation framework
- Key algo times (9:30, 10:00, 14:30, 15:30, 15:40, 15:50)

**[07-experiments-and-validation.md](07-experiments-and-validation.md)** - Continuous Experiment Framework

- Resumable experiment system with checkpoint/resume
- GEX strategy framework (V0-V4)
- Performance-optimized architecture (3-tier fallback)
- Advanced metrics capture (strike-level, GEX regime tracking)

**[08-maintenance-and-audits.md](08-maintenance-and-audits.md)** - Maintenance and Audits

- **Part 1: Configuration Grooming Audit** - Hardcoded values, prompt extraction
- **Part 2: Documentation Cleanup** - Consolidation strategy
- **Part 3-4: Recommendations and History** - Completed actions and future work
- **Part 5-7: Best Practices, Known Issues, Audit Schedule**

#### Part 4: Specialized Infrastructure (09)

**[09-intraday-infrastructure.md](09-intraday-infrastructure.md)** - Intraday Data Collection (Paper #3)

- PostgreSQL `intraday_snapshots` table with yearly partitioning
- Intraday OI Monitor service (21 snapshots/day adaptive sampling)
- 0DTE gamma evolution analysis support
- Common queries and maintenance procedures

---

## Content Index by Topic

### System Architecture

- High-level design: [02-architecture-overview.md](02-architecture-overview.md)
- Data flow: [03-data-and-database.md](03-data-and-database.md)
- Cache system: [04-cache-and-performance.md](04-cache-and-performance.md)

### Database and Storage

- Database schema: [03-data-and-database.md](03-data-and-database.md)
- Cache architecture: [04-cache-and-performance.md](04-cache-and-performance.md)
- Intraday storage: [06-implementation-guide.md](06-implementation-guide.md)
- Intraday PostgreSQL: [09-intraday-infrastructure.md](09-intraday-infrastructure.md)

### LLM Integration

- Model selection: [05-llm-integration.md](05-llm-integration.md)
- Token optimization: [04-cache-and-performance.md](04-cache-and-performance.md)
- Paper-specific decisions: [05-llm-integration.md](05-llm-integration.md)

### Implementation Guides

- Trading patterns: [06-implementation-guide.md](06-implementation-guide.md)
- Intraday support: [06-implementation-guide.md](06-implementation-guide.md)
- Experiment framework: [07-experiments-and-validation.md](07-experiments-and-validation.md)

### Maintenance

- Configuration audit: [08-maintenance-and-audits.md](08-maintenance-and-audits.md)
- Best practices: [08-maintenance-and-audits.md](08-maintenance-and-audits.md)
- Known issues: [08-maintenance-and-audits.md](08-maintenance-and-audits.md)

---

## Key Features of This Documentation

### 1. Sequential Numbering

Files are numbered 01-08 to provide a clear learning progression. Read in order for optimal understanding.

### 2. Consolidated Content

Related concepts are merged into single files to reduce fragmentation while maintaining high detail:

- 03-data-and-database.md = data-architecture + database-architecture
- 04-cache-and-performance.md = cache-architecture + token-configuration
- 05-llm-integration.md = llm-model-selection + model-selection-research
- 06-implementation-guide.md = actionable-patterns + intraday-implementation
- 08-maintenance-and-audits.md = grooming_audit + cleanup_plan

### 3. Navigation Links

Every file includes:

- **Prerequisites**: What to read first
- **Next**: Where to go next
- **Related**: Similar/connected topics

### 4. Part-Based Organization

Larger files (03-08) use "Part 1, Part 2" structure for easy navigation within long documents.

---

## Related Documentation

### Development Guides

[docs/development/](../development/) - Developer workflows (worktree management, testing)

### Paper-Specific Infrastructure

- [docs/papers/paper1/](../papers/paper1/) - Paper #1 (single-day framework)
- [docs/papers/paper2/infrastructure/](../papers/paper2/infrastructure/) - Paper #2 (sequential framework, PostgreSQL migration)

### User Guides

[docs/guides/](../guides/) - End-user guides (GEX metrics, pattern taxonomy)

### Validation Methodology

[docs/validation/](../validation/) - Research validation methods

---

## Audits

### Configuration Grooming Audit (November 22, 2025)

**File**: [08-maintenance-and-audits.md](08-maintenance-and-audits.md)

**Scope**: Configuration management, prompt templates, database/cache architecture

**Key Actions**:

- Externalized 240 lines of hardcoded config (196 prompt + 44 thresholds)
- Fixed field name aliasing bug
- Documented worktree cache strategy
- Created developer guides

**GitHub Issue**: [#149 - Infrastructure Grooming](https://github.com/iAmGiG/gex-llm-patterns/issues/149)

### Documentation Consolidation (November 24, 2025)

**File**: [08-maintenance-and-audits.md](08-maintenance-and-audits.md)

**Scope**: Documentation organization and consolidation

**Key Actions**:

- Consolidated 13 system/reference/infrastructure files → 9 sequential files
- Created infrastructure index and learning path
- Merged Paper #1 Issue #146 files (3 → 1)
- Removed temporary batch metadata files

**Result**: Reduced file count while preserving detail, created clear learning path

---

## Contributing

### Adding Infrastructure Documentation

1. **Determine placement**: Which numbered file (01-08) does it belong in?
2. **Use part-based structure**: Add as "Part N" if file is already long
3. **Follow naming**: `kebab-case` for file names
4. **Add navigation**: Include Prerequisites/Next/Related sections
5. **Update this README**: Add entry to Content Index

### Audit Documentation

For infrastructure audits:

1. Add summary to [08-maintenance-and-audits.md](08-maintenance-and-audits.md) Part 4 (Audit History)
2. Include date, scope, findings, and actions taken
3. Link to related GitHub issues
4. Update this README's Audits section

### Deprecating Documentation

1. Move to `docs/archive/` with appropriate subdirectory
2. Update references in active docs
3. Note in [CHANGELOG.md](../CHANGELOG.md)
4. Keep for historical reference (don't delete)

---

## File Statistics

### Active Documentation

- **Infrastructure**: 10 files (01-09 sequential + README)
- **Total Size**: ~230 KB
- **Line Count**: ~4,200 lines
- **Last Update**: January 8, 2026

### Consolidation Impact

**Before consolidation** (Nov 22, 2025):

- Legacy scattered docs (system-level): 9 files
- docs/reference/: 2 files
- docs/infrastructure/: 2 files
- **Total**: 13 files

**After consolidation** (Nov 24, 2025):

- docs/infrastructure/: 9 files (01-08, README)
- **Total**: 9 files

**Reduction**: 4 files eliminated (31% reduction)

**Detail Preserved**: 100% (all content consolidated, not deleted)

---

## Meta-Goal: AutoTrader-AgentEdge Adoption

This infrastructure documentation is designed to support future adoption of GEX tools in the **AutoTrader-AgentEdge** companion project. The sequential structure and consolidated content provide:

- **Clear learning path**: New developers can understand the system quickly
- **Living documentation**: Not archived, actively maintained
- **High detail preservation**: Enough depth to avoid "project death from lack of understanding"
- **Implementation guidance**: Practical examples for integration

---

## Quick Reference

### Most Important Files for...

**Understanding the system**: Start with [01-project-overview.md](01-project-overview.md)
**Implementing new features**: See [06-implementation-guide.md](06-implementation-guide.md)
**Debugging data issues**: Check [03-data-and-database.md](03-data-and-database.md)
**Optimizing performance**: Review [04-cache-and-performance.md](04-cache-and-performance.md)
**Model selection questions**: See [05-llm-integration.md](05-llm-integration.md)
**Running experiments**: Study [07-experiments-and-validation.md](07-experiments-and-validation.md)
**Maintenance tasks**: Consult [08-maintenance-and-audits.md](08-maintenance-and-audits.md)

### External Links

- **GitHub Repository**: [iAmGiG/gex-llm-patterns](https://github.com/iAmGiG/gex-llm-patterns)
- **Issues**: [Project Issues](https://github.com/iAmGiG/gex-llm-patterns/issues)
- **Project Board**: [Development Board](https://github.com/iAmGiG/gex-llm-patterns/projects)

---

**Last Updated**: January 7, 2026
**Maintained By**: Infrastructure Team
**Status**: Active Development

---

## Recent Updates (January 2026)

### Documentation Consolidation (January 8, 2026)

- Merged `intraday_schema.md` + `intraday_monitor.md` → **[09-intraday-infrastructure.md](09-intraday-infrastructure.md)**
- Merged `RESEARCH_CACHE_GUIDE.md` → **[04-cache-and-performance.md](04-cache-and-performance.md)** Part 3
- Archived `DATABASE_UPGRADE_PLAN.md` → `archive/` (PostgreSQL migration complete)
- Updated file statistics and navigation

### Intraday Infrastructure (Issues #203, #204, #205)

**Added January 7, 2026** (now in [09-intraday-infrastructure.md](09-intraday-infrastructure.md)):

- `intraday_snapshots` PostgreSQL table with yearly partitioning
- Intraday OI Monitor background service (21 snapshots/day)
- Adaptive theta decay sampling schedule

**Service Status**: Running on HPCC (screen session `intraday-monitor`)

**Data Collection**: Q1 2026 (~59 trading days, ~1,239 snapshots expected)
