# Development Guides

Infrastructure and workflow documentation for developers working on the GEX LLM Patterns system.

---

## Guides

### Worktree Cache Management

**File**: `worktree_cache_management.md`
**Created**: November 22, 2025 (Issue #149)

Comprehensive guide for managing `.cache/` directories across git worktrees:

- **3 Strategies**: Symlink, independent caches, rsync on demand
- **Decision Matrix**: Which strategy for which scenario
- **Real-World Lessons**: Issue #140 cache divergence (multi-year validation)
- **Troubleshooting**: Common pitfalls (database locks, accidental deletion, divergence)

**Key Topics**:

- Symlink strategy (recommended for read-only workflows)
- Independent caches (safe for concurrent data collection)
- Rsync patterns (selective sync, bootstrapping)
- Cache verification commands
- Migration guide (independent → symlink)

---

## Related Documentation

- **Infrastructure**: `docs/infrastructure/` - System architecture, audits, technical diagrams
- **General Guides**: `docs/guides/` - Numbered system-wide guides (01-09)
- **Paper #2 Infrastructure**: `docs/papers/paper2/infrastructure/` - Paper-specific infra

---

## Contributing

When adding development guides:

1. Use descriptive filenames: `topic_name_guide.md`
2. Include creation date and issue context in frontmatter
3. Follow existing structure (problem, solution, examples, troubleshooting)
4. Update this README with new entries
