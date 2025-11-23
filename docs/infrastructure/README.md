# Infrastructure Documentation

System architecture, audits, design decisions, and infrastructure planning for the GEX LLM Patterns system.

---

## Audits

### Configuration Grooming Audit
**File**: `grooming_audit_nov22_2025.md`
**Date**: November 22, 2025 (Issue #149)

Comprehensive infrastructure audit covering:

1. **Hardcoded Values Analysis**
   - Paper #2 regime prompt (163 lines in code)
   - Regime classifier thresholds (4 constants)
   - Recommendations with effort estimates

2. **Architectural Decisions**
   - Why Paper #2 doesn't use agent system (vs Paper #1)
   - Direct API + Batch mode rationale (simplicity, 50% cost savings)
   - Single-shot classification vs multi-step reasoning

3. **Database & Cache Architecture**
   - Single vs Dual GEX schema (Issue #140 migration)
   - File cache structure (`.cache/gex_data/`)
   - Symlink vs independent cache strategies

**Key Findings**:
- 240 lines externalized to config (196 prompt + 44 thresholds)
- Agent system not needed for Paper #2 (correct decision)
- Worktree cache divergence solved (documented in dev guides)

---

### Cleanup and Consolidation Plan
**File**: `cleanup_plan_nov22_2025.md`
**Date**: November 22, 2025 (Post Issue #149)

Action plan for organizing unstaged documentation:

- **Chat C Paper #1 Files**: Issue #146, #145 analysis and planning
- **Batch Metadata Cleanup**: Temporary tracking files
- **Naming Conventions**: Existing patterns and compliance
- **Consolidation Strategy**: 3 Issue #146 files → 1 comprehensive doc

---

## Related Documentation

- **Development**: `docs/development/` - Workflow guides (worktree, testing)
- **Paper #2 Infrastructure**: `docs/papers/paper2/infrastructure/` - Paper-specific infra docs
- **System Architecture**: `docs/system/` - Core system design
- **Database Schema**: `docs/papers/paper2/infrastructure/database_coverage_audit.md`

---

## Contributing

When adding infrastructure docs:
1. Use naming pattern: `descriptive_name_YYYYMMDD.md`
2. Include date in filename for audit/planning docs
3. Document **why** decisions were made (rationale, context)
4. Update this README with new entries
5. Cross-reference related docs (Paper #1, Paper #2, system)
