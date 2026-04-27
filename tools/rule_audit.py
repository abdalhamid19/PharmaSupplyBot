"""Local rule audit for file length, function length, line length, and docstrings."""

from __future__ import annotations

import ast
from pathlib import Path


MAX_FILE_LINES = 100
MAX_FUNCTION_LINES = 20
MAX_LINE_LENGTH = 100
ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "run.py", ROOT / "streamlit_app.py", *sorted((ROOT / "src").glob("*.py"))]
EXCEPTED_FILE_LENGTHS = {
    "src\\matching_rules.py",
    "src\\product_matching.py",
    "src\\tawreed.py",
    "src\\tawreed_checkout.py",
    "src\\tawreed_match_logs.py",
    "src\\tawreed_products_flow.py",
    "src\\tawreed_session.py",
}


def main() -> int:
    """Run the repository rule audit and print any remaining violations."""
    violations = []
    for path in TARGETS:
        violations.extend(file_length_violations(path))
        violations.extend(line_length_violations(path))
        violations.extend(function_length_violations(path))
        violations.extend(docstring_violations(path))
    if not violations:
        print("rule_audit_ok")
        return 0
    print("rule_audit_violations")
    for violation in violations:
        print(violation)
    return 1


def file_length_violations(path: Path) -> list[str]:
    """Return file-length violations for one target file."""
    relative = relative_path(path)
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count <= MAX_FILE_LINES:
        return []
    if relative in EXCEPTED_FILE_LENGTHS:
        return []
    return [f"{relative}:file_lines:{line_count}"]


def line_length_violations(path: Path) -> list[str]:
    """Return line-length violations for one target file."""
    violations: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if len(line) > MAX_LINE_LENGTH:
            violations.append(f"{relative_path(path)}:{line_number}:line_length:{len(line)}")
    return violations


def function_length_violations(path: Path) -> list[str]:
    """Return function-length violations for one target file."""
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        function_length = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
        if function_length > MAX_FUNCTION_LINES:
            violations.append(
                f"{relative_path(path)}:{node.lineno}:function_lines:{node.name}:{function_length}"
            )
    return violations


def docstring_violations(path: Path) -> list[str]:
    """Return missing public docstring violations for one target file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    violations: list[str] = []
    if ast.get_docstring(tree) is None:
        violations.append(f"{relative_path(path)}:module_docstring")
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        if ast.get_docstring(node) is None:
            violations.append(f"{relative_path(path)}:{node.name}:docstring")
    return violations


def relative_path(path: Path) -> str:
    """Return the repository-relative path for one target file."""
    return str(path.relative_to(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
