# Documentation Cleanup and Consolidation Plan

**Date**: November 22, 2025
**Context**: Issue #149 complete, Chat C Paper #1 work in progress
**Current Branch**: `paper2-sequential-gex`

---

## Current State

### Unstaged Files (Main Worktree)

**Paper #1 Analysis** (Chat C):
- `docs/papers/paper1/analysis/issue_146_complete_analysis.md` (17.6 KB)
- `docs/papers/paper1/analysis/issue_146_mc_summary.md` (9.1 KB)
- `docs/papers/paper1/analysis/issue_146_mc_paper1_recommendations.md` (10.5 KB)
- `docs/papers/paper1/analysis/batch_jobs/batch_metadata_batch_69225e32e6e8819085a97e2e31ecb789.yaml`

**Paper #1 Planning** (Chat C):
- `docs/papers/paper1/planning/issue_145_analysis_plan.md` (19.9 KB)

### Issue #149 Files (Worktree - Need to Merge)

**Infrastructure** (`/mnt/bst/yxie2/cregan1/gex-llm-patterns-issue149`):
- `docs/infrastructure/grooming_audit_nov22_2025.md` (570 lines) ✅ Committed
- `docs/development/worktree_cache_management.md` (503 lines) ✅ Committed

**Config** (already committed):
- `config_defaults/llm_prompts.yaml` (+196 lines)
- `config_defaults/analysis_config.yaml` (+44 lines)

**Code** (already committed):
- `src/validation/regime_classifier.py` (config integration)
- `src/llm/mechanics_prompt_builder.py` (prompt documentation)

---

## Naming Convention Analysis

### Existing Patterns

**Top-level docs structure**:
```
docs/
├── archive/          # Deprecated/historical docs
├── dissertation/     # PhD archive (Paper #1 final versions)
├── guides/          # System-wide guides (numbered 01-09)
├── infrastructure/  # System architecture, audits
├── papers/          # Paper-specific docs
│   ├── paper1/
│   │   ├── analysis/      # Analysis reports
│   │   ├── planning/      # Planning docs
│   │   ├── latex/         # LaTeX source
│   │   └── tables/        # Generated tables
│   └── paper2/
│       ├── guides/        # Paper-specific guides
│       ├── infrastructure/# Paper-specific infra
│       ├── planning/      # Planning docs
│       └── latex/         # LaTeX source
├── presentations/   # Conference presentations
├── reference/       # External references
├── system/          # System documentation
└── validation/      # Validation methodology
```

**Naming patterns**:
- System guides: `01-topic-name.md`, `02-topic-name.md` (numbered, lowercase with hyphens)
- Infrastructure: `descriptive_name_YYYYMMDD.md` (underscores, dated)
- Paper analysis: `issue_NNN_description.md` (issue numbers, underscores)
- Paper planning: `issue_NNN_plan.md` or `phaseN_description.md`

---

## Actions Required

### 1. Review Chat C Files (Paper #1)

**Issue #146 Files** (Alpha Divergence MC Defense):
- ✅ Keep: `issue_146_complete_analysis.md` (full analysis)
- ⚠️ **Consolidate**: `issue_146_mc_summary.md` → append to complete analysis as "Executive Summary"
- ⚠️ **Consolidate**: `issue_146_mc_paper1_recommendations.md` → append as "Recommendations" section
- **Action**: Merge 3 files → 1 comprehensive `issue_146_complete_analysis.md`

**Issue #145 File** (Temporal Mismatch):
- ✅ Keep: `planning/issue_145_analysis_plan.md` (planning doc, correct location)
- **Action**: Verify naming follows convention, commit as-is

**Batch Metadata**:
- ⚠️ **Archive**: `batch_metadata_batch_69225e32e6e8819085a97e2e31ecb789.yaml`
- **Reason**: Temporary batch tracking, not needed long-term
- **Action**: Move to `docs/papers/paper1/analysis/batch_jobs/.archive/` or delete

---

### 2. Merge Issue #149 Branch to Main

**From worktree** (`infrastructure-issue149-config-externalization`):

```bash
# Checkout main development branch
git checkout paper2-sequential-gex

# Merge Issue #149 work
git merge infrastructure-issue149-config-externalization

# Resolve any conflicts (likely none)
# Verify docs/infrastructure/ and docs/development/ directories created

# Push to remote
git push origin paper2-sequential-gex
```

**Result**:
- `docs/infrastructure/grooming_audit_nov22_2025.md` → main
- `docs/development/` directory created → main
- `docs/development/worktree_cache_management.md` → main

---

### 3. Consolidate Chat C Issue #146 Files

**Current** (3 separate files):
```
docs/papers/paper1/analysis/
├── issue_146_complete_analysis.md     (17.6 KB)
├── issue_146_mc_summary.md            (9.1 KB)  ← Merge into complete
├── issue_146_mc_paper1_recommendations.md (10.5 KB)  ← Merge into complete
```

**Target** (1 consolidated file):
```
docs/papers/paper1/analysis/
└── issue_146_alpha_divergence_complete.md  (~37 KB)
    ├── Executive Summary (from mc_summary)
    ├── Full Analysis (from complete_analysis)
    ├── Statistical Evidence
    ├── Linguistic Evidence
    └── Paper #1 Recommendations (from mc_paper1_recommendations)
```

**Naming**:
- Change: `issue_146_complete_analysis.md` → `issue_146_alpha_divergence_complete.md`
- **Reason**: Descriptive name follows pattern (`issue_NNN_description.md`)

---

### 4. Clean Up Batch Metadata

**Current**:
```
docs/papers/paper1/analysis/batch_jobs/
└── batch_metadata_batch_69225e32e6e8819085a97e2e31ecb789.yaml
```

**Decision**: **Delete** (temporary tracking file)

**Rationale**:
- Batch ID: `batch_69225e32e6e8819085a97e2e31ecb789`
- Status: `validating` (incomplete, not finalized)
- Purpose: Temporary tracking for Issue #146 Phase 2 batch submission
- Not needed after analysis complete

**Alternative**: Move to `.archive/` subdirectory if keeping for provenance

---

### 5. Create Development Docs Index

**New file**: `docs/development/README.md`

**Purpose**: Index development guides (worktree, testing, etc.)

**Content**:
```markdown
# Development Guides

Infrastructure and workflow documentation for developers.

## Guides

1. **Worktree Cache Management** (`worktree_cache_management.md`)
   - Multi-worktree workflows
   - Cache strategies (symlink, independent, rsync)
   - Issue #140 lessons learned

## Related

- Infrastructure: `docs/infrastructure/`
- System docs: `docs/system/`
- General guides: `docs/guides/`
```

---

### 6. Update Infrastructure Index

**New file**: `docs/infrastructure/README.md`

**Purpose**: Index infrastructure audits and architecture docs

**Content**:
```markdown
# Infrastructure Documentation

System architecture, audits, and design decisions.

## Audits

1. **Configuration Grooming** (`grooming_audit_nov22_2025.md`)
   - Hardcoded values analysis
   - Config externalization recommendations
   - Agent vs Direct API rationale (Paper #2)
   - Issue #149 foundation

## Related

- Development: `docs/development/`
- Paper #2 Infrastructure: `docs/papers/paper2/infrastructure/`
```

---

## Execution Sequence

### Step 1: Merge Issue #149 (Immediate)

```bash
cd /mnt/bst/yxie2/cregan1/gex-llm-patterns
git checkout paper2-sequential-gex
git merge infrastructure-issue149-config-externalization
git push origin paper2-sequential-gex
```

**Result**: Infrastructure docs now in main worktree

---

### Step 2: Consolidate Issue #146 Files (Chat C's Work)

**Option A - Consolidate Now** (if Chat C done):
```bash
# Combine 3 files into 1
cat issue_146_mc_summary.md \
    issue_146_complete_analysis.md \
    issue_146_mc_paper1_recommendations.md \
    > issue_146_alpha_divergence_complete.md

# Review, edit, commit
git add docs/papers/paper1/analysis/issue_146_alpha_divergence_complete.md
git commit -m "docs(paper1): Consolidate Issue #146 alpha divergence analysis"
git rm docs/papers/paper1/analysis/issue_146_{mc_summary,complete_analysis,mc_paper1_recommendations}.md
```

**Option B - Wait for Chat C** (if in progress):
- Leave files as-is until Chat C completes Issue #146 work
- Coordinate handoff to avoid conflicts

---

### Step 3: Clean Up Batch Metadata

```bash
# Delete temporary batch metadata
git rm docs/papers/paper1/analysis/batch_jobs/batch_metadata_batch_69225e32e6e8819085a97e2e31ecb789.yaml

# Or archive if provenance needed
mkdir -p docs/papers/paper1/analysis/batch_jobs/.archive
git mv docs/papers/paper1/analysis/batch_jobs/batch_metadata_*.yaml \
       docs/papers/paper1/analysis/batch_jobs/.archive/
```

---

### Step 4: Create Index Files

```bash
# Development index
cat > docs/development/README.md <<'EOF'
# Development Guides
...
EOF

# Infrastructure index
cat > docs/infrastructure/README.md <<'EOF'
# Infrastructure Documentation
...
EOF

git add docs/development/README.md docs/infrastructure/README.md
git commit -m "docs: Add development and infrastructure indexes"
```

---

## Summary of Changes

**Files to Keep** (commit):
- ✅ `docs/papers/paper1/planning/issue_145_analysis_plan.md` (as-is)
- ⚠️ `docs/papers/paper1/analysis/issue_146_alpha_divergence_complete.md` (consolidated)

**Files to Remove** (consolidation):
- ❌ `issue_146_mc_summary.md` → merged into consolidated
- ❌ `issue_146_complete_analysis.md` → merged into consolidated
- ❌ `issue_146_mc_paper1_recommendations.md` → merged into consolidated

**Files to Delete** (temporary):
- ❌ `batch_metadata_batch_69225e32e6e8819085a97e2e31ecb789.yaml` (temp tracking)

**Files to Create**:
- ✅ `docs/development/README.md` (new index)
- ✅ `docs/infrastructure/README.md` (new index)

**From Issue #149 Merge**:
- ✅ `docs/infrastructure/grooming_audit_nov22_2025.md` (already committed)
- ✅ `docs/development/worktree_cache_management.md` (already committed)

---

## Naming Convention Violations

**None detected** - all files follow existing patterns:
- Infrastructure: `descriptive_name_YYYYMMDD.md` ✅
- Paper analysis: `issue_NNN_description.md` ✅
- Guides: `topic_name.md` ✅

**Recommendation**: Rename `issue_146_complete_analysis.md` → `issue_146_alpha_divergence_complete.md` for clarity

---

## Open Questions

1. **Issue #146 Status**: Is Chat C still working on this, or is analysis complete?
   - If complete: Consolidate 3 files now
   - If in progress: Wait for handoff

2. **Batch Metadata**: Archive or delete?
   - Recommendation: **Delete** (temporary, not valuable long-term)

3. **Issue #145 Plan**: Ready to commit?
   - Appears complete, should commit with Paper #1 work

---

**Next Action**: Merge Issue #149 branch to bring infrastructure docs into main worktree
