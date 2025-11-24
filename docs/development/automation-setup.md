# Automation Setup Guide

**Last Updated**: November 24, 2025

Auto-formatting and linting setup for minimal manual review.

---

## Quick Start (5 Minutes)

### 1. Install Pre-Commit Hooks (Local Automation)

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Test the setup
pre-commit run --all-files
```

**What this does**:

- Automatically formats code before every commit
- Fixes markdown linting issues (MD022, MD032)
- Sorts Python imports
- Removes trailing whitespace
- Fixes end-of-file formatting

### 2. Enable GitHub Actions (Remote Automation)

Already configured! When you push to:

- `paper2-sequential-gex`
- `feature/**` branches
- `issue*` branches

GitHub Actions will:

- Auto-fix any issues you missed locally
- Commit and push the fixes automatically
- Add `[skip ci]` to prevent infinite loops

---

## How It Works

### Pre-Commit Hooks (Local, Instant)

**Runs before every commit**:

```bash
git commit -m "your message"
# ↓
# Auto-fixes run automatically:
# ✓ Black formatting (Python)
# ✓ isort (import sorting)
# ✓ Markdown linting
# ✓ Whitespace cleanup
# ↓
# Files fixed and staged automatically
# ↓
# Commit completes with fixed files
```

**Bypass if needed**:

```bash
git commit --no-verify -m "urgent fix"
```

### Auto-Fix on Push (Remote, 2-3 min)

**Runs after you push**:

```bash
git push
# ↓
# GitHub Actions triggered
# ↓
# All formatters run on entire codebase
# ↓
# If changes needed:
#   - Commit created: "style: Auto-fix code quality issues [skip ci]"
#   - Changes pushed automatically
# ↓
# Your local branch gets behind by 1 commit
# ↓
# Next pull: git pull (fast-forward merge)
```

**Important**: After pushing, wait 2-3 minutes then:

```bash
git pull  # Pull the auto-fix commit
```

---

## Configuration Files

### `.pre-commit-config.yaml`

Defines which auto-fixes run locally:

- **markdownlint-cli2**: Markdown formatting
- **black**: Python code formatting (line length 120)
- **isort**: Import sorting
- **trailing-whitespace**: Removes trailing spaces
- **end-of-file-fixer**: Ensures newline at EOF

### `.markdownlint.json`

Markdown rules:

- **MD032**: Blank lines around lists ✅
- **MD022**: Blank lines around headings ✅
- **MD013**: Line length ❌ (disabled for research docs)
- **MD033**: Allow HTML tags for special formatting

### `.flake8`

Python linting rules:

- Max line length: 120
- Ignores conflicts with black (E203, W503)
- Per-file ignores for `__init__.py` and tests

### `pyproject.toml`

Tool configuration:

- Black settings (line length, Python version)
- isort profile (compatible with black)
- pytest configuration

---

## Workflows

### `auto-fix-on-push.yml`

**Triggers**: Push to `paper2-sequential-gex`, `feature/**`, `issue*`
**Actions**:

- Runs black, isort, docformatter on Python
- Runs markdownlint on all `.md` files
- Commits and pushes fixes if changes detected
**Time**: ~2-3 minutes

### `quality-check.yml`

**Triggers**: Pull requests to any branch
**Actions**:

- Non-blocking checks (warnings only)
- Comments on PR with summary
- Helps catch issues before merge
**Time**: ~1-2 minutes

---

## Typical Workflow

### Scenario 1: Normal Commit (Everything Works)

```bash
# Make changes
echo "new code" >> src/new_file.py

# Commit (pre-commit auto-fixes run)
git commit -am "feat: Add new feature"
# [INFO] black....................................................Passed
# [INFO] isort....................................................Passed
# [INFO] markdownlint.............................................Passed

# Push
git push
# GitHub Actions runs, no additional fixes needed
```

### Scenario 2: Pre-Commit Fixes Issues

```bash
# Make changes with bad formatting
echo "x=1" >> src/bad_format.py

# Commit triggers auto-fix
git commit -am "feat: Add feature"
# [INFO] black....................................................Failed
# - hook id: black
# - files were modified by this hook
# reformatted src/bad_format.py

# Files auto-fixed and staged
# Commit again (now passes)
git commit -am "feat: Add feature"
# [INFO] black....................................................Passed

git push
```

### Scenario 3: Bypass and Remote Fix

```bash
# Urgent commit, skip local checks
git commit --no-verify -m "fix: Critical bug"

# Push
git push

# GitHub Actions detects issues
# Auto-fix commit pushed: "style: Auto-fix code quality issues [skip ci]"

# Pull the fix
git pull
# Fast-forward merge, now in sync
```

---

## Maintenance

### Update Pre-Commit Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Run updated hooks
pre-commit run --all-files
```

### Disable Specific Hooks Temporarily

Edit `.pre-commit-config.yaml` and comment out:

```yaml
#  - repo: https://github.com/psf/black
#    rev: 24.3.0
#    hooks:
#      - id: black
```

### Check What Will Run

```bash
# Dry run (no changes)
pre-commit run --all-files --verbose
```

---

## Troubleshooting

### Pre-Commit Too Slow

```bash
# Only run on changed files (default)
git commit -am "message"

# Skip if urgent
git commit --no-verify -m "urgent"
```

### Conflicts with Auto-Fix Commits

```bash
# Pull before pushing
git pull --rebase
git push
```

### Disable GitHub Actions Temporarily

Add `[skip ci]` to your commit message:

```bash
git commit -m "wip: Work in progress [skip ci]"
```

---

## Cost Analysis

### GitHub Actions Usage

- **Free tier**: 2,000 minutes/month
- **Auto-fix workflow**: ~2-3 min per push
- **Quality check workflow**: ~1-2 min per PR
- **Estimated usage**: ~10-20 pushes/week = 40-80 min/month
- **Verdict**: Well within free tier ✅

### Local Performance

- **Pre-commit hooks**: ~5-15 seconds per commit
- **Impact**: Minimal, runs in background
- **Verdict**: Negligible ✅

---

## When to Use What

| Situation | Use Pre-Commit | Use Auto-Fix on Push | Use `--no-verify` |
|-----------|----------------|----------------------|-------------------|
| Normal development | ✅ Yes | ✅ Yes (safety net) | ❌ No |
| Urgent hotfix | ⚠️ Maybe | ✅ Yes | ✅ Yes |
| WIP commits | ✅ Yes | ❌ No (`[skip ci]`) | ⚠️ Maybe |
| Large refactoring | ✅ Yes | ✅ Yes | ❌ No |
| Documentation only | ✅ Yes | ✅ Yes | ❌ No |

---

## Advanced Configuration

### Run Specific Hook Only

```bash
# Only run black
pre-commit run black --all-files

# Only run markdown linting
pre-commit run markdownlint-cli2 --all-files
```

### Add Custom Hooks

Edit `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: check-large-files
        name: Check for large CSV files
        entry: bash -c 'find . -name "*.csv" -size +10M'
        language: system
```

### Adjust Markdown Rules

Edit `.markdownlint.json`:

```json
{
  "MD013": { "line_length": 120 }  // Enable line length limit
}
```

---

## Next Steps

1. **Install pre-commit**: `pip install pre-commit && pre-commit install`
2. **Test it**: `pre-commit run --all-files`
3. **Make a commit**: Watch it auto-fix
4. **Push to GitHub**: Watch Actions auto-fix remotely
5. **Pull changes**: `git pull` after Actions complete

---

## Related Documentation

- [Worktree Cache Management](worktree_cache_management.md)
- [Infrastructure README](../infrastructure/README.md)

**Last Updated**: November 24, 2025
