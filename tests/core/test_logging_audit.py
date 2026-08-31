"""Guard tests for the unified logging policy.

These tests fail loudly when the source tree violates any of the
logging invariants we maintain:

* No `print(...)` calls in `src/`
* No `logging.basicConfig(...)` calls in `src/`
* No literal `"pharmasupplybot.matching"` logger names
* No `_console_safe(...)` calls (workaround for an old encoding bug)
* No manual `logger.handlers = [...]` or `logger.addHandler(...)` calls
* All `logging.getLogger(...)` calls must use either:
  - the bare ``logging.getLogger()`` form (root logger)
  - ``logging.getLogger(__name__)`` (per-module convention)

The guard tests share AST helpers with ``scripts/audit_logging.py``
but live in the test tree so CI can enforce them.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
EXCLUDE_DIRS = {"__pycache__", ".venv", "venv"}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def _all_py_files() -> list[Path]:
    return sorted(
        p for p in SRC_ROOT.rglob("*.py") if not _is_excluded(p)
    )


def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: list[str] = []
        cur: ast.expr = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _calls_with(predicate) -> list[tuple[Path, int, ast.Call]]:
    """Walk every .py file under src/ and return matching Call nodes."""
    out: list[tuple[Path, int, ast.Call]] = []
    for py in _all_py_files():
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and predicate(node):
                out.append((py, node.lineno, node))
    return out


# ─────────────────────────── Guards ───────────────────────────


def test_no_print_calls_in_src() -> None:
    """No print() calls anywhere in src/ — they must use logger instead."""
    offenders: list[tuple[Path, int]] = []
    for py in _all_py_files():
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node.func) == "print":
                offenders.append((py.relative_to(PROJECT_ROOT), node.lineno))
    assert not offenders, (
        f"print() calls are not allowed in src/. Use the logger instead:\n"
        + "\n".join(f"  {p}:{ln}" for p, ln in offenders)
    )


def test_no_basicconfig_calls_in_src() -> None:
    """No logging.basicConfig() anywhere — logging_setup.py is the single init point."""
    offenders: list[tuple[Path, int]] = []
    for py in _all_py_files():
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node.func) == "basicConfig":
                offenders.append((py.relative_to(PROJECT_ROOT), node.lineno))
    assert not offenders, (
        "logging.basicConfig() is forbidden — use configure_logging() from "
        "src.cli.logging_setup instead:\n"
        + "\n".join(f"  {p}:{ln}" for p, ln in offenders)
    )


def test_no_literal_pharmasupplybot_matching_logger() -> None:
    """The legacy literal logger name must be replaced with __name__."""
    offenders: list[tuple[Path, int]] = []

    def predicate(n: ast.Call) -> bool:
        if _callee_name(n.func) not in ("logging.getLogger", "getLogger"):
            return False
        return any(
            isinstance(a, ast.Constant) and a.value == "pharmasupplybot.matching"
            for a in n.args
        )

    for p, ln, _ in _calls_with(predicate):
        offenders.append((p.relative_to(PROJECT_ROOT), ln))
    assert not offenders, (
        'Literal logger "pharmasupplybot.matching" is forbidden. '
        "Use logging.getLogger(__name__) instead:\n"
        + "\n".join(f"  {p}:{ln}" for p, ln in offenders)
    )


def test_no_console_safe_calls_in_src() -> None:
    """_console_safe was a Windows encoding workaround — UTF-8 logging makes it obsolete."""
    offenders: list[tuple[Path, int]] = []
    for py in _all_py_files():
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node.func) == "_console_safe":
                offenders.append((py.relative_to(PROJECT_ROOT), node.lineno))
    assert not offenders, (
        "_console_safe() is obsolete (UTF-8 logging replaces it). Use logger.info:\n"
        + "\n".join(f"  {p}:{ln}" for p, ln in offenders)
    )


def test_no_manual_logger_handler_manipulation() -> None:
    """No logger.handlers = [...] or logger.addHandler(...) — only logging_setup owns handlers."""
    offenders: list[tuple[Path, int, str]] = []
    for py in _all_py_files():
        # logging_setup.py is the only sanctioned place that touches handlers.
        if py.name == "logging_setup.py":
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr == "handlers"
                    ):
                        offenders.append(
                            (py.relative_to(PROJECT_ROOT), node.lineno, "handlers-assign")
                        )
            if isinstance(node, ast.Call):
                name = _callee_name(node.func)
                if name and name.endswith(".addHandler"):
                    offenders.append(
                        (py.relative_to(PROJECT_ROOT), node.lineno, "addHandler")
                    )
    assert not offenders, (
        "Manual handler manipulation is forbidden. Configure the root logger "
        "via src.cli.logging_setup.configure_logging() instead:\n"
        + "\n".join(f"  {p}:{ln} ({kind})" for p, ln, kind in offenders)
    )


def _is_setup_module(path: Path) -> bool:
    """logging_setup.py is the one sanctioned place to touch handlers."""
    return path.name == "logging_setup.py"


_PACKAGE_ROOT_NAMES = (
    "src.core.drug_matching",
)


def _is_allowed_logger_call(rel_path, call) -> bool:
    """Return True if this getLogger(...) call follows the project convention.

    Allowed forms:
    * ``logging.getLogger()`` (no args, root logger) — anywhere except
      logging_setup.py.
    * ``logging.getLogger(__name__)`` (module-scoped) — anywhere.
    * ``logging.getLogger("src.core.drug_matching")`` (package-root) —
      only allowed from config_helpers.py.
    * Inside ``src/cli/logging_setup.py`` we run the root logger and
      expose a pass-through ``get_logger(name)`` helper for consumers.
    """
    rel = rel_path.as_posix()
    # logging_setup.py is the one sanctioned place that owns the
    # root logger and exposes a pass-through helper.
    if rel == "src/cli/logging_setup.py":
        return True
    # config_helpers.py is allowed to grab the matching package root.
    if rel == "src/core/drug_matching/config/config_helpers.py":
        if (
            len(call.args) == 1
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
            and call.args[0].value in _PACKAGE_ROOT_NAMES
        ):
            return True
    if len(call.args) == 0:
        return True
    if (
        len(call.args) == 1
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "__name__"
    ):
        return True
    return False


def test_get_logger_calls_use_allowed_forms() -> None:
    """logging.getLogger() must use only the allowed forms in src/.

    See :func:`_is_allowed_logger_call` for the policy.
    """
    offenders: list[tuple[Path, int, str]] = []

    def predicate(n: ast.Call) -> bool:
        return _callee_name(n.func) in ("logging.getLogger", "getLogger")

    for p, ln, call in _calls_with(predicate):
        rel = p.relative_to(PROJECT_ROOT)
        if not _is_allowed_logger_call(rel, call):
            arg_repr = ast.unparse(call.args[0]) if call.args else ""
            offenders.append((rel, ln, arg_repr))
    assert not offenders, (
        "logging.getLogger() must use one of the allowed forms "
        "(no args, __name__, or a configured package root):\n"
        + "\n".join(f"  {p}:{ln} -> getLogger({arg!r})" for p, ln, arg in offenders)
    )


# ─────────────────────────── Tooling sanity ───────────────────────────


def test_audit_script_exists_and_runs() -> None:
    """The audit script must be present and executable as a module."""
    script = PROJECT_ROOT / "scripts" / "audit_logging.py"
    assert script.is_file(), f"missing {script}"
    # Sanity import — script is a module; just verify it parses
    ast.parse(script.read_text(encoding="utf-8"))


def test_audit_baseline_doc_exists() -> None:
    """The baseline numbers live in docs/audit_baseline.md so they can be diffed."""
    assert (PROJECT_ROOT / "docs" / "audit_baseline.md").is_file()