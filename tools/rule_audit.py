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
    "src/matching_rules.py",
    "src/product_matching.py",
    "src/tawreed.py",
    "src/tawreed_checkout.py",
    "src/tawreed_match_logs.py",
    "src/tawreed_products_flow.py",
    "src/tawreed_session.py",
}
BASELINE_VIOLATIONS = {
    "src/cart_removal_items.py:file_lines:115",
    "src/cli_commands.py:file_lines:196",
    "src/cli_commands.py:26:line_length:107",
    "src/cli_commands.py:31:function_lines:run_order_command:30",
    "src/cli_commands.py:63:function_lines:run_remove_cart_command:24",
    "src/cli_commands.py:104:function_lines:load_order_items:21",
    "src/cli_parser.py:file_lines:118",
    "src/cli_parser.py:35:function_lines:_build_order_parser:50",
    "src/excel.py:file_lines:146",
    "src/matching_rules.py:file_lines:150",
    "src/prevented_items.py:file_lines:196",
    "src/prevented_items.py:94:function_lines:filter_prevented_order_items:25",
    "src/product_matching.py:file_lines:481",
    "src/selectors.py:file_lines:122",
    "src/streamlit_headless_auth.py:33:line_length:106",
    "src/streamlit_main.py:15:line_length:114",
    "src/streamlit_order.py:file_lines:203",
    "src/streamlit_order.py:22:function_lines:render_order_tab:25",
    "src/streamlit_order.py:67:function_lines:render_running_order_controls:36",
    "src/streamlit_order.py:105:function_lines:start_order_process:21",
    "src/streamlit_order.py:179:function_lines:order_command:25",
    "src/streamlit_order_form.py:file_lines:235",
    "src/streamlit_order_form.py:83:line_length:103",
    "src/streamlit_order_form.py:53:function_lines:render_prevented_items_manager:28",
    "src/streamlit_order_form.py:102:function_lines:render_prevented_items_editor:40",
    "src/streamlit_order_form.py:198:function_lines:profile_run_fields:24",
    "src/streamlit_overview.py:file_lines:112",
    "src/streamlit_overview.py:69:function_lines:render_input_files_table:24",
    "src/streamlit_process.py:file_lines:119",
    "src/streamlit_process.py:16:line_length:111",
    "src/streamlit_process.py:26:function_lines:start_cli_subprocess:23",
    "src/streamlit_remove_cart.py:file_lines:191",
    "src/streamlit_remove_cart.py:35:function_lines:remove_cart_form_values:26",
    "src/streamlit_remove_cart.py:132:function_lines:render_running_remove_cart_controls:29",
    "src/streamlit_results.py:file_lines:139",
    "src/tawreed.py:file_lines:484",
    "src/tawreed.py:302:line_length:105",
    "src/tawreed.py:312:line_length:104",
    "src/tawreed.py:61:function_lines:__init__:25",
    "src/tawreed.py:95:function_lines:_auth:52",
    "src/tawreed.py:152:function_lines:place_order_from_items:27",
    "src/tawreed.py:180:function_lines:remove_cart_items:25",
    "src/tawreed.py:273:function_lines:_process_single_item:53",
    "src/tawreed.py:421:function_lines:_record_item_summary:27",
    "src/tawreed_artifacts.py:file_lines:187",
    "src/tawreed_artifacts.py:64:line_length:101",
    "src/tawreed_auth_waits.py:file_lines:102",
    "src/tawreed_auth_waits.py:14:function_lines:wait_for_login_detection:30",
    "src/tawreed_cart_removal.py:file_lines:206",
    "src/tawreed_cart_removal.py:67:line_length:101",
    "src/tawreed_cart_removal.py:83:line_length:112",
    "src/tawreed_cart_removal.py:33:function_lines:remove_items_from_cart:35",
    "src/tawreed_checkout.py:file_lines:115",
    "src/tawreed_checkout.py:11:function_lines:confirm_order:22",
    "src/tawreed_match_logs.py:file_lines:313",
    "src/tawreed_match_logs.py:67:function_lines:append_order_result_summary:24",
    "src/tawreed_products_flow.py:file_lines:1014",
    "src/tawreed_products_flow.py:242:function_lines:add_item_from_store_dialogs:34",
    "src/tawreed_products_flow.py:278:function_lines:choose_next_store_for_remaining_quantity:36",
    "src/tawreed_products_flow.py:489:function_lines:close_visible_dialogs:21",
    "src/tawreed_products_flow.py:625:function_lines:_first_discount_value:21",
    "src/tawreed_products_flow.py:966:function_lines:_decisive_match:28",
    "src/tawreed_session.py:file_lines:259",
    "src/tawreed_session.py:23:line_length:104",
    "src/tawreed_session.py:82:function_lines:wait_for_login_detection:22",
    "src/tawreed_session.py:181:function_lines:ensure_logged_in:21",
    "src/tawreed_strategy.py:file_lines:115",
    "src/tawreed_strategy.py:99:line_length:102",
}


def main() -> int:
    """Run the repository rule audit and fail only on newly introduced violations."""
    violations = collect_violations()
    unexpected = unexpected_violations(violations)
    if not unexpected:
        print("rule_audit_ok")
        remaining = baseline_violations(violations)
        if remaining:
            print(f"baseline_violations_remaining:{len(remaining)}")
        return 0
    print("rule_audit_violations")
    for violation in unexpected:
        print(violation)
    return 1


def collect_violations() -> list[str]:
    """Return every current audit violation across repository targets."""
    violations: list[str] = []
    for path in TARGETS:
        violations.extend(file_length_violations(path))
        violations.extend(line_length_violations(path))
        violations.extend(function_length_violations(path))
        violations.extend(docstring_violations(path))
    return violations


def unexpected_violations(violations: list[str]) -> list[str]:
    """Return violations that are not part of the accepted baseline debt."""
    return sorted(
        violation
        for violation in violations
        if violation_key(violation) not in BASELINE_VIOLATION_KEYS
    )


def baseline_violations(violations: list[str]) -> list[str]:
    """Return the known baseline violations that still remain in the codebase."""
    return sorted(
        violation
        for violation in violations
        if violation_key(violation) in BASELINE_VIOLATION_KEYS
    )


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


def violation_key(violation: str) -> str:
    """Return a stable identity for one violation even when measured values improve."""
    parts = violation.split(":")
    if len(parts) == 3 and parts[1] == "file_lines":
        return f"{parts[0]}:file_lines"
    if len(parts) == 4 and parts[2] == "line_length":
        return f"{parts[0]}:line_length:{parts[3]}"
    if len(parts) == 5 and parts[2] == "function_lines":
        return f"{parts[0]}:function_lines:{parts[3]}"
    return violation


BASELINE_VIOLATION_KEYS = {violation_key(violation) for violation in BASELINE_VIOLATIONS}


if __name__ == "__main__":
    raise SystemExit(main())
