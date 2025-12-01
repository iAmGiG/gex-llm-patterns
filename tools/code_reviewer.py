"""
GEX-LLM Code Review Agent
Comprehensive code review tool for Python code quality, imports, and project standards.
"""

import ast
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ImportIssue:
    """Represents an import-related issue."""

    line_number: int
    issue_type: str  # 'unused', 'wrong_order', 'missing_from', etc.
    import_name: str
    suggestion: str
    severity: str  # 'error', 'warning', 'info'


@dataclass
class CodeIssue:
    """Represents a general code issue."""

    line_number: int
    issue_type: str
    message: str
    suggestion: str
    severity: str


class ImportAnalyzer(ast.NodeVisitor):
    """Analyzes Python imports using AST."""

    def __init__(self):
        self.imports: List[Tuple[int, str, str]] = []  # (line, type, name)
        self.used_names: Set[str] = set()
        self.from_imports: Dict[str, List[str]] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append((node.lineno, "import", name))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append((node.lineno, "from", f"{module}.{name}"))
            if module not in self.from_imports:
                self.from_imports[module] = []
            self.from_imports[module].append(name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Handle cases like np.array where 'np' is used
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


class GEXCodeReviewer:
    """Main code review agent for GEX-LLM project."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src"

        # GEX project specific standards
        self.standard_imports_order = [
            "builtins",  # Built-in modules
            "standard",  # Standard library
            "third_party",  # Third-party packages
            "local",  # Local/project modules
        ]

        self.common_third_party = {
            "pandas",
            "numpy",
            "scipy",
            "matplotlib",
            "requests",
            "typing",
            "datetime",
            "logging",
            "json",
            "os",
            "sys",
            "pathlib",
            "dataclasses",
            "enum",
            "abc",
        }

        self.project_modules = {
            "tokenization",
            "data_sources",
            "validation",
            "gex",
            "agents",
            "cache",
            "tools",
            "utils",
        }

        # Typing simplification for computational effectiveness
        self.typing_simplification_enabled = True
        self.complex_typing_patterns = [
            # param: Optional[Type] = default
            r"(\w+):\s*Optional\[[^\]]+\]\s*(=)",
            # param: Union[Type1, Type2] = default
            r"(\w+):\s*Union\[[^\]]+\]\s*(=)",
            # param: List[Type] = default
            r"(\w+):\s*List\[[^\]]*\]\s*(=)",
            # param: Dict[K, V] = default
            r"(\w+):\s*Dict\[[^\]]*\]\s*(=)",
            r"(\w+):\s*Set\[[^\]]*\]\s*(=)",  # param: Set[Type] = default
            # param: Tuple[Type, ...] = default
            r"(\w+):\s*Tuple\[[^\]]*\]\s*(=)",
        ]

    def review_file(self, file_path: str) -> Dict[str, List]:
        """
        Comprehensive review of a Python file.

        Args:
            file_path: Path to the Python file to review

        Returns:
            Dictionary with different types of issues found
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {"error": [f"File not found: {file_path}"]}

        if file_path.suffix != ".py":
            return {"error": [f"Not a Python file: {file_path}"]}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            return {"error": [f"Syntax error: {e}"]}

        issues = {"import_issues": [], "code_issues": [], "lint_issues": [], "suggestions": []}

        # Analyze imports
        import_issues = self._analyze_imports(tree, content, file_path)
        issues["import_issues"].extend(import_issues)

        # Run linting
        lint_issues = self._run_linter(file_path)
        issues["lint_issues"].extend(lint_issues)

        # GEX-specific checks
        gex_issues = self._check_gex_standards(tree, content, file_path)
        issues["code_issues"].extend(gex_issues)

        # Generate suggestions
        suggestions = self._generate_suggestions(issues, file_path)
        issues["suggestions"].extend(suggestions)

        return issues

    def _analyze_imports(self, tree: ast.AST, content: str, file_path: Path) -> List[ImportIssue]:
        """Analyze import statements for issues."""
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        issues = []
        lines = content.split("\n")

        # Find unused imports
        for line_no, import_type, import_name in analyzer.imports:
            # Extract the actual name that would be used
            if import_type == "import":
                used_name = import_name.split(".")[0]
            else:
                used_name = import_name.split(".")[-1]

            if used_name not in analyzer.used_names and used_name != "*":
                issues.append(
                    ImportIssue(
                        line_number=line_no,
                        issue_type="unused_import",
                        import_name=import_name,
                        suggestion=f"Remove unused import: {import_name}",
                        severity="warning",
                    )
                )

        # Check import ordering
        import_lines = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and not stripped.startswith("#"):
                import_lines.append((i, stripped))

        # Check if imports are at the top (after docstring and comments)
        if import_lines:
            first_import_line = import_lines[0][0]
            code_before_imports = False

            for i in range(1, first_import_line):
                line = lines[i - 1].strip()
                if line and not line.startswith("#") and not line.startswith('"""') and not line.startswith("'''"):
                    if not self._is_docstring_line(lines, i - 1):
                        code_before_imports = True
                        break

            if code_before_imports:
                issues.append(
                    ImportIssue(
                        line_number=first_import_line,
                        issue_type="imports_not_at_top",
                        import_name="",
                        suggestion="Move all imports to the top of the file (after module docstring)",
                        severity="error",
                    )
                )

        return issues

    def _is_docstring_line(self, lines: List[str], line_idx: int) -> bool:
        """Check if a line is part of a module docstring."""
        # Simple heuristic - proper AST analysis would be better
        line = lines[line_idx].strip()
        if line.startswith('"""') or line.startswith("'''"):
            return True

        # Check if we're inside a multi-line docstring
        in_docstring = False
        quote_char = None

        for i in range(line_idx + 1):
            current_line = lines[i].strip()
            if current_line.startswith('"""'):
                if quote_char is None:
                    quote_char = '"""'
                    in_docstring = True
                elif quote_char == '"""':
                    in_docstring = False
                    quote_char = None
            elif current_line.startswith("'''"):
                if quote_char is None:
                    quote_char = "'''"
                    in_docstring = True
                elif quote_char == "'''":
                    in_docstring = False
                    quote_char = None

        return in_docstring

    def _run_linter(self, file_path: Path) -> List[CodeIssue]:
        """Run external linters (flake8, pylint, etc.)."""
        issues = []

        try:
            # Try flake8 first
            result = subprocess.run(
                ["flake8", "--max-line-length=100", str(file_path)], capture_output=True, text=True, timeout=30
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            try:
                                line_no = int(parts[1])
                                col_no = int(parts[2])
                                message = parts[3].strip()

                                issues.append(
                                    CodeIssue(
                                        line_number=line_no,
                                        issue_type="flake8",
                                        message=message,
                                        suggestion=f"Fix flake8 issue at line {line_no}, column {col_no}",
                                        severity="warning",
                                    )
                                )
                            except ValueError:
                                continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # flake8 not available or timed out
            pass

        return issues

    def _check_gex_standards(self, tree: ast.AST, content: str, file_path: Path) -> List[CodeIssue]:
        """Check GEX project-specific coding standards."""
        issues = []
        lines = content.split("\n")

        # Check for proper docstrings
        if not self._has_module_docstring(tree):
            issues.append(
                CodeIssue(
                    line_number=1,
                    issue_type="missing_docstring",
                    message="Module missing docstring",
                    suggestion="Add a module-level docstring explaining the purpose",
                    severity="warning",
                )
            )

        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            if "TODO" in line.upper() or "FIXME" in line.upper():
                issues.append(
                    CodeIssue(
                        line_number=i,
                        issue_type="todo_comment",
                        message=f"TODO/FIXME comment found: {line.strip()}",
                        suggestion="Address TODO/FIXME or create GitHub issue",
                        severity="info",
                    )
                )

        # Check for hardcoded paths or credentials
        for i, line in enumerate(lines, 1):
            if re.search(r'["\'][/\\].*[/\\].*["\']', line) and "test" not in line.lower():
                issues.append(
                    CodeIssue(
                        line_number=i,
                        issue_type="hardcoded_path",
                        message="Possible hardcoded path found",
                        suggestion="Use pathlib.Path or os.path for cross-platform paths",
                        severity="warning",
                    )
                )

        # Check for proper logging instead of print
        for i, line in enumerate(lines, 1):
            if "print(" in line and "test" not in file_path.name.lower():
                issues.append(
                    CodeIssue(
                        line_number=i,
                        issue_type="print_statement",
                        message="print() statement found",
                        suggestion="Use logging instead of print() for production code",
                        severity="info",
                    )
                )

        return issues

    def _has_module_docstring(self, tree: ast.AST) -> bool:
        """Check if module has a docstring."""
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            return True
        return False

    def _generate_suggestions(self, issues: Dict[str, List], file_path: Path) -> List[str]:
        """Generate actionable suggestions based on found issues."""
        suggestions = []

        # Import-related suggestions
        unused_imports = [issue for issue in issues["import_issues"] if issue.issue_type == "unused_import"]
        if unused_imports:
            imports_to_remove = [issue.import_name for issue in unused_imports]
            suggestions.append(
                f"Remove {len(imports_to_remove)} unused imports: {', '.join(imports_to_remove[:3])}..."
                if len(imports_to_remove) > 3
                else f"Remove unused imports: {', '.join(imports_to_remove)}"
            )

        # Code quality suggestions
        if any(issue.issue_type == "print_statement" for issue in issues["code_issues"]):
            suggestions.append("Replace print() statements with logging for better debugging")

        if any(issue.issue_type == "missing_docstring" for issue in issues["code_issues"]):
            suggestions.append("Add module docstring explaining the file's purpose")

        # Linting suggestions
        if issues["lint_issues"]:
            suggestions.append(f"Fix {len(issues['lint_issues'])} linting issues")

        return suggestions

    def fix_imports(self, file_path: str) -> Dict[str, Any]:
        """Automatically fix import issues."""
        file_path = Path(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        tree = ast.parse(content)

        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        # Find unused imports
        unused_lines = set()
        for line_no, import_type, import_name in analyzer.imports:
            if import_type == "import":
                used_name = import_name.split(".")[0]
            else:
                used_name = import_name.split(".")[-1]

            if used_name not in analyzer.used_names and used_name != "*":
                unused_lines.add(line_no - 1)  # Convert to 0-based

        # Remove unused import lines
        fixed_lines = []
        removed_count = 0

        for i, line in enumerate(lines):
            if i not in unused_lines:
                fixed_lines.append(line)
            else:
                removed_count += 1

        fixed_content = "\n".join(fixed_lines)

        return {"fixed_content": fixed_content, "removed_imports": removed_count, "changes_made": removed_count > 0}

    def simplify_typing(self, content: str) -> Tuple[str, int]:
        """
        Simplify complex parameter typing for computational effectiveness.

        Returns:
            (simplified_content, changes_made_count)
        """
        if not self.typing_simplification_enabled:
            return content, 0

        original_content = content
        changes_made = 0

        # Remove complex parameter type hints
        for pattern in self.complex_typing_patterns:
            matches = re.findall(pattern, content)
            if matches:
                changes_made += len(matches)
                # Replace: param: ComplexType = default -> param=default
                content = re.sub(pattern, r"\1\2", content)

        # Remove simple parameter typing without defaults
        simple_patterns = [
            r"(\w+):\s*str(?=\s*[,)])",  # param: str
            r"(\w+):\s*int(?=\s*[,)])",  # param: int
            r"(\w+):\s*bool(?=\s*[,)])",  # param: bool
            r"(\w+):\s*float(?=\s*[,)])",  # param: float
        ]

        for pattern in simple_patterns:
            matches = re.findall(pattern, content)
            if matches:
                changes_made += len(matches)
                content = re.sub(pattern, r"\1", content)

        # Remove complex return types as well
        return_type_patterns = [
            r"-> Dict\[.*?\]:",  # -> Dict[str, Any]:
            r"-> List\[.*?\]:",  # -> List[Something]:
            r"-> Optional\[.*?\]:",  # -> Optional[Type]:
            r"-> Union\[.*?\]:",  # -> Union[Type1, Type2]:
            r"-> Set\[.*?\]:",  # -> Set[Type]:
            r"-> Tuple\[.*?\]:",  # -> Tuple[Type, ...]:
            r"-> Dict:",  # -> Dict: (without brackets)
            r"-> List:",  # -> List: (without brackets)
            r"-> Optional:",  # -> Optional: (without brackets)
            r"-> Union:",  # -> Union: (without brackets)
            r"-> Set:",  # -> Set: (without brackets)
            r"-> Tuple:",  # -> Tuple: (without brackets)
        ]

        for pattern in return_type_patterns:
            matches = re.findall(pattern, content)
            if matches:
                changes_made += len(matches)
                # Replace with simple colon
                content = re.sub(pattern, ":", content)

        # Remove unused typing imports if no complex types remain
        if changes_made > 0:
            # Check if typing imports are still needed
            typing_usage = ["Optional", "Union", "List", "Dict", "Set", "Tuple", "Any"]

            still_used = any(f"-> {t}" in content or f": {t}" in content for t in typing_usage)

            if not still_used:
                # Remove typing imports
                content = re.sub(r"from typing import.*\n", "", content)
                content = re.sub(r"import typing.*\n", "", content)

        return content, changes_made

    def fix_all_issues(self, file_path: str) -> Dict[str, Any]:
        """Fix all detected issues in a file."""
        file_path = Path(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            total_changes = 0

            # 1. Simplify typing (do this first)
            if self.typing_simplification_enabled:
                content, typing_changes = self.simplify_typing(content)
                total_changes += typing_changes
                if typing_changes > 0:
                    print(f"🎯 Simplified {typing_changes} parameter type hints")

            # 2. Fix imports
            import_result = self.fix_imports_content(content)
            if import_result["changes_made"]:
                content = import_result["fixed_content"]
                total_changes += import_result["removed_imports"]
                print(f"🗑️ Removed {import_result['removed_imports']} unused imports")

            # Write changes if any were made
            if total_changes > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                return {
                    "success": True,
                    "total_changes": total_changes,
                    "typing_simplified": typing_changes if self.typing_simplification_enabled else 0,
                    "imports_removed": import_result["removed_imports"] if import_result["changes_made"] else 0,
                    "message": f"Fixed {total_changes} issues",
                }
            else:
                return {"success": True, "total_changes": 0, "message": "No issues found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def fix_imports_content(self, content: str) -> Dict[str, Any]:
        """Fix imports for content string."""
        try:
            lines = content.split("\n")
            tree = ast.parse(content)

            analyzer = ImportAnalyzer()
            analyzer.visit(tree)

            # Find unused imports
            unused_lines = set()
            for line_no, import_type, import_name in analyzer.imports:
                if import_type == "import":
                    used_name = import_name.split(".")[0]
                else:
                    used_name = import_name.split(".")[-1]

                if used_name not in analyzer.used_names and used_name != "*":
                    unused_lines.add(line_no - 1)  # Convert to 0-based

            # Remove unused import lines
            fixed_lines = []
            removed_count = 0

            for i, line in enumerate(lines):
                if i not in unused_lines:
                    fixed_lines.append(line)
                else:
                    removed_count += 1

            fixed_content = "\n".join(fixed_lines)

            return {"fixed_content": fixed_content, "removed_imports": removed_count, "changes_made": removed_count > 0}
        except:
            return {"fixed_content": content, "removed_imports": 0, "changes_made": False}

    def generate_report(self, file_path: str) -> str:
        """Generate a comprehensive review report."""
        issues = self.review_file(file_path)

        if "error" in issues:
            return f"❌ Error reviewing {file_path}:\n" + "\n".join(issues["error"])

        report_lines = [f"📋 Code Review Report: {file_path}", "=" * 60]

        # Summary
        total_issues = len(issues["import_issues"]) + len(issues["code_issues"]) + len(issues["lint_issues"])

        if total_issues == 0:
            report_lines.append("✅ No issues found! Code looks good.")
            return "\n".join(report_lines)

        report_lines.append(f"Found {total_issues} issues:")
        report_lines.append("")

        # Import issues
        if issues["import_issues"]:
            report_lines.append("🔍 Import Issues:")
            for issue in issues["import_issues"]:
                severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[issue.severity]
                report_lines.append(f"  {severity_icon} Line {issue.line_number}: {issue.suggestion}")
            report_lines.append("")

        # Code issues
        if issues["code_issues"]:
            report_lines.append("🔧 Code Issues:")
            for issue in issues["code_issues"]:
                severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[issue.severity]
                report_lines.append(f"  {severity_icon} Line {issue.line_number}: {issue.message}")
            report_lines.append("")

        # Lint issues
        if issues["lint_issues"]:
            report_lines.append("🔨 Lint Issues:")
            for issue in issues["lint_issues"][:5]:  # Show first 5
                report_lines.append(f"  ⚠️ Line {issue.line_number}: {issue.message}")
            if len(issues["lint_issues"]) > 5:
                report_lines.append(f"  ... and {len(issues['lint_issues']) - 5} more")
            report_lines.append("")

        # Suggestions
        if issues["suggestions"]:
            report_lines.append("💡 Suggestions:")
            for suggestion in issues["suggestions"]:
                report_lines.append(f"  • {suggestion}")

        return "\n".join(report_lines)


def main():
    """CLI interface for the code reviewer."""
    import argparse

    parser = argparse.ArgumentParser(description="GEX-LLM Code Review Agent - Computational Effectiveness Focus")
    parser.add_argument("file", help="Python file to review")
    parser.add_argument("--fix", action="store_true", help="Automatically fix all issues (typing + imports)")
    parser.add_argument("--fix-imports", action="store_true", help="Only fix import issues (legacy)")
    parser.add_argument("--no-typing-simplification", action="store_true", help="Disable typing simplification")
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    reviewer = GEXCodeReviewer(args.project_root)

    # Disable typing simplification if requested
    if args.no_typing_simplification:
        reviewer.typing_simplification_enabled = False

    if args.fix:
        # Use new comprehensive fix method
        result = reviewer.fix_all_issues(args.file)

        if result["success"]:
            if result["total_changes"] > 0:
                print(f"✅ Fixed {result['total_changes']} issues")
                if result.get("typing_simplified", 0) > 0:
                    print(f"   🎯 Simplified {result['typing_simplified']} parameter type hints")
                if result.get("imports_removed", 0) > 0:
                    print(f"   🗑️ Removed {result['imports_removed']} unused imports")
            else:
                print("ℹ️ No issues found! Code looks good.")
        else:
            print(f"❌ Error: {result['error']}")

    elif args.fix_imports:
        # Legacy import-only fixing
        result = reviewer.fix_imports(args.file)
        if result["changes_made"]:
            print(f"✅ Fixed {result['removed_imports']} unused imports")
            with open(args.file, "w") as f:
                f.write(result["fixed_content"])
        else:
            print("ℹ️ No import fixes needed")
    else:
        # Generate report only
        report = reviewer.generate_report(args.file)
        print(report)


if __name__ == "__main__":
    main()
