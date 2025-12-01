# GEX-LLM Development Tools

## Code Review Agent (`code_reviewer.py`)

Comprehensive Python code review tool for maintaining code quality, managing imports, and enforcing GEX project standards.

### Features

#### 🔍 Import Analysis

- **Unused Import Detection**: Identifies and removes unused imports
- **Import Organization**: Ensures imports are at the top of files
- **Import Order**: Checks standard library → third-party → local import order

#### 🔧 Code Quality Checks

- **Linting Integration**: Runs flake8 if available
- **GEX Standards**: Project-specific coding standards
- **Docstring Validation**: Ensures modules have proper documentation
- **TODO/FIXME Detection**: Identifies technical debt comments

#### 💡 Automatic Fixes

- **Import Cleanup**: Automatically removes unused imports
- **Safe Operations**: Only modifies imports, preserves all other code

### Usage

#### Basic Code Review

```bash
# Review a single file
python tools/code_reviewer.py src/tokenization/gex_tokenizer.py

# Review with automatic import fixing
python tools/code_reviewer.py src/tokenization/gex_tokenizer.py --fix-imports
```

#### Example Output

```
📋 Code Review Report: src/tokenization/gex_tokenizer.py
============================================================
Found 2 issues:

🔍 Import Issues:
  ⚠️ Line 8: Remove unused import: typing.Tuple
  ⚠️ Line 8: Remove unused import: typing.Union

💡 Suggestions:
  • Remove unused imports: typing.Tuple, typing.Union
```

#### Integration with VS Code

The code reviewer can be integrated with VS Code through tasks or the terminal. Add to `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Review Current File",
            "type": "shell",
            "command": "python",
            "args": ["tools/code_reviewer.py", "${file}"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "Fix Imports in Current File", 
            "type": "shell",
            "command": "python",
            "args": ["tools/code_reviewer.py", "${file}", "--fix-imports"],
            "group": "build"
        }
    ]
}
```

### GEX Project Standards

The code reviewer enforces specific standards for the GEX-LLM project:

#### Import Organization

1. **Built-in modules** (os, sys, datetime)
2. **Standard library** (typing, logging, json)  
3. **Third-party packages** (pandas, numpy, requests)
4. **Local project modules** (tokenization, gex, agents)

#### Code Quality Rules

- ✅ Module docstrings required
- ✅ Use logging instead of print() statements
- ✅ Avoid hardcoded file paths
- ✅ Mark TODO/FIXME comments for tracking

#### Severity Levels

- **🔴 Error**: Must be fixed (syntax errors, imports not at top)
- **🟡 Warning**: Should be fixed (unused imports, hardcoded paths)
- **🔵 Info**: Consider fixing (TODO comments, print statements)

### Requirements

#### Python Dependencies

```bash
pip install ast  # Built-in
```

#### Optional Linters (Enhanced Analysis)

```bash
pip install flake8  # For advanced linting
pip install pylint  # Additional static analysis
```

### CLI Options

```bash
usage: code_reviewer.py [-h] [--fix-imports] [--project-root PROJECT_ROOT] file

GEX-LLM Code Review Agent

positional arguments:
  file                  Python file to review

optional arguments:
  -h, --help            show this help message and exit
  --fix-imports         Automatically fix import issues
  --project-root PROJECT_ROOT
                        Project root directory (default: .)
```

### Integration Examples

#### Review All Python Files

```bash
find src/ -name "*.py" -exec python tools/code_reviewer.py {} \;
```

#### Fix Imports in All Files

```bash
find src/ -name "*.py" -exec python tools/code_reviewer.py {} --fix-imports \;
```

#### Review Modified Files (Git)

```bash
git diff --name-only --diff-filter=M | grep '\.py$' | xargs -I {} python tools/code_reviewer.py {}
```

### Configuration

The code reviewer is configured for the GEX-LLM project structure:

- **Project root**: `/mnt/bst/yxie2/cregan1/gex-llm-patterns/`
- **Source directory**: `src/`
- **Known project modules**: `tokenization`, `gex`, `agents`, `data_sources`, `validation`

### Extending the Reviewer

The code reviewer is designed to be extensible:

#### Add Custom Checks

```python
def _check_custom_standard(self, tree: ast.AST, content: str, file_path: Path) -> List[CodeIssue]:
    """Add custom project-specific checks."""
    issues = []
    # Add your custom logic here
    return issues
```

#### Add New Issue Types

```python
@dataclass
class CustomIssue:
    line_number: int
    issue_type: str
    message: str
    suggestion: str
    severity: str
```

### Best Practices

1. **Run before commits**: Review code before committing
2. **Fix imports automatically**: Use `--fix-imports` for quick cleanup
3. **Address high-severity issues first**: Focus on errors, then warnings
4. **Regular codebase scans**: Periodically review entire codebase

### Troubleshooting

#### Common Issues

- **flake8 not found**: Install with `pip install flake8`
- **Syntax errors**: Fix Python syntax before running reviewer
- **Permission errors**: Ensure write permissions for import fixing

The code reviewer is integrated into the development workflow to maintain high code quality standards throughout the GEX-LLM project.
