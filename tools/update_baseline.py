"""Update BASELINE_VIOLATIONS to match current actual violations."""

import ast
from pathlib import Path

MAX_FILE_LINES = 100
MAX_FUNCTION_LINES = 20
MAX_LINE_LENGTH = 100
ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "run.py",
    ROOT / "streamlit_app.py",
    *sorted((ROOT / "src").rglob("*.py")),
]
EXCEPTED_FILE_LENGTHS = {
    "src/core/drug_matching/indexer.py",
    "src/core/drug_matching/normalizer.py",
    "src/core/matching_rules.py",
    "src/core/product_matching.py",
    "src/tawreed/tawreed.py",
    "src/tawreed/tawreed_checkout.py",
    "src/tawreed/tawreed_match_logs.py",
    "src/tawreed/tawreed_products_flow.py",
    "src/tawreed/tawreed_session.py",
    # P3 merged files
    "src/cli/cli_order_items.py",
    "src/cli/cli_order.py",
    "src/cli/cli_parser.py",
    "src/cli/item_worker.py",
    "src/cli/cli_match_products.py",
    "src/ui/streamlit_order.py",
    "src/ui/streamlit_remove_cart.py",
    "src/ui/streamlit_results.py",
    "src/ui/streamlit_manual_review_cli.py",
    "src/ui/streamlit_manual_review_page.py",
    "src/ui/streamlit_manual_review_page_saved.py",
}


def collect_violations() -> list[str]:
    """Return every current audit violation across repository targets."""
    violations: list[str] = []
    for path in TARGETS:
        violations.extend(file_length_violations(path))
        violations.extend(line_length_violations(path))
        violations.extend(function_length_violations(path))
        violations.extend(docstring_violations(path))
    return violations


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
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    violations = sorted(collect_violations())
    print(f"Total current violations: {len(violations)}")
    print(f"Old baseline had: 342 violations")
    print(f"Reduction: {342 - len(violations)} violations")
    print("\nBASELINE_VIOLATIONS = {")
    for v in violations:
        print(f'    "{v}",')
    print("}")
