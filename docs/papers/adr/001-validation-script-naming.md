# Validation Script Naming Convention

**Created**: November 4, 2025
**Purpose**: Standardize script naming to separate Paper #1 from Paper #2 work

---

## Naming Standard

**Format**: `validate_p{paper_number}_{description}.py`

**Examples**:

- `validate_p1_pattern_taxonomy.py` - Paper #1 validation
- `validate_p2_negative_controls.py` - Paper #2 validation
- `validate_p2_sequential_patterns.py` - Paper #2 validation

---

## Current Script Mapping

### Paper #1 Scripts (Single-Day Explanatory Framework)

| Current Filename | Proposed P1 Name | Status | Description |
|-----------------|------------------|--------|-------------|
| `validate_pattern_taxonomy.py` | `validate_p1_pattern_taxonomy.py` | ✅ Exists | Pattern taxonomy validation (Q1, Q3, Q4 2024) |
| `validate_all_patterns.py` | `validate_p1_all_patterns.py` | ✅ Exists | Batch validation across patterns |

### Paper #2 Scripts (Sequential Causal Framework)

| Current Filename | Proposed P2 Name | Status | Description |
|-----------------|------------------|--------|-------------|
| `validate_sequential_patterns.py` | `validate_p2_sequential_patterns.py` | ✅ Exists | Sequential GEX validation (Phase 1 PoC) |
| N/A | `validate_p2_negative_controls.py` | ✅ Created | Negative controls (prompt bias, random, zero-GEX) |

---

## Rationale

**Problem**: Scripts for different papers mixed together, unclear which methodology is being tested

**Solution**: Prefix with paper number following academic convention

**Benefits**:

1. Clear separation of Paper #1 (single-day) vs Paper #2 (sequential) work
2. Easy to identify which framework is being validated
3. Follows academic standard of citing papers by number
4. Scalable to future papers (p3, p4, etc.)

---

## Implementation Notes

**Backward Compatibility**: Keep existing filenames as symlinks for now

**Migration Path**:

1. Create new p{N}_ prefixed scripts
2. Update CLAUDE.md and documentation
3. Update GitHub issues to reference new names
4. Deprecate old names after Paper #1 submission

**Directory Structure**:

```
scripts/validation/
├── validate_p1_pattern_taxonomy.py       # Paper #1
├── validate_p1_all_patterns.py           # Paper #1
├── validate_p2_sequential_patterns.py    # Paper #2
├── validate_p2_negative_controls.py      # Paper #2 (NEW)
└── [other test scripts]
```

---

## Related Documentation

- **Paper #1 Framework**: `docs/papers/paper1/` (single-day explanatory)
- **Paper #2 Framework**: `docs/papers/paper2/` (sequential causal)
- **CLAUDE.md**: Main system context (updated with naming convention)

---

**Next Actions**:

1. ✅ Created `validate_p2_negative_controls.py`
2. ⏸ Optionally rename existing scripts (or create symlinks)
3. ⏸ Update CLAUDE.md with new naming convention
