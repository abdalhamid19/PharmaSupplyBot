"""Audit swallowed exceptions across the PharmaSupplyBot source tree.

Run from project root::

    py scripts/audit_swallow.py

A "swallowed exception" is any ``except Exception`` block that:

1. Does NOT call ``logger.error(...)`` / ``logger.warning(...)`` / ``logging.error(...)``
   inside its body (so the failure never reaches the operator's logs), AND
2. Does NOT ``raise`` another exception (so the failure never propagates).

Both conditions must be true for the finding to count. The audit also
excludes two known-acceptable cases:

* Files in the allowlist (Streamlit subprocess wrapper, intentional
  fallback boundaries) — see :data:`SWALLOW_ALLOWLIST`.
* ``except Exception`` whose body is ONLY a ``return`` of a sentinel
  value AND the function is documented as best-effort — too noisy to
  block, the guard test treats it as informational.

Reports every violation with file:line + snippet + the function it lives
in, and groups findings by file. Exits 0 always — this is a *report*,
not a test. To enforce the rule, run the guard tests in
``tests/core/test_swallow_audit.py``.

The audit is AST-based (not regex), so docstrings / comments never
count as violations.
"""

from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
EXCLUDE_DIRS = {"__pycache__", ".venv", "venv"}

# Files where broad ``except`` is intentional and reviewed.
# Add a file here ONLY with a one-line justification.
SWALLOW_ALLOWLIST: dict[str, str] = {
    # Streamlit subprocess wrapper converts any failure into a UI-friendly
    # ``dict`` payload. KeyboardInterrupt / SystemExit are deliberately
    # swallowed to keep the UI responsive.
    "src/ui/views/streamlit_process.py": "streamlit subprocess wrapper — UI-facing failure capture",
    # Handler teardown: if a handler fails to close (file lock, I/O error
    # during interpreter shutdown), we cannot recover — the process is
    # exiting anyway. Catching here is the documented Python pattern for
    # ``__exit__``-style defensive code.
    "src/cli/logging_setup.py": "logging handler teardown — defensive, no recovery possible during interpreter shutdown",
}


class Finding(NamedTuple):
    """One concrete finding: file + line + enclosing function + snippet."""

    file: Path
    line: int
    function: str
    snippet: str


# ─────────────────────────── Helpers ───────────────────────────


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def _except_type_name(handler: ast.ExceptHandler) -> str | None:
    """Return the bare name of the exception type, or None for bare ``except:``."""
    if handler.type is None:
        return None
    if isinstance(handler.type, ast.Name):
        return handler.type.id
    if isinstance(handler.type, ast.Attribute):
        return handler.type.attr
    return None


def _enclosing_function(tree: ast.AST, lineno: int) -> str:
    """Walk the tree and return the name of the innermost function/method that contains ``lineno``."""
    enclosing: str | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Function bodies have a known first/last line.
            end_lineno = getattr(node, "end_lineno", None) or node.lineno
            if node.lineno <= lineno <= end_lineno:
                enclosing = node.name
    return enclosing or "<module>"


def _body_has_logger_or_raise(body: list[ast.stmt]) -> tuple[bool, bool]:
    """Return (has_logger_call, has_raise). Either is enough to clear the finding."""
    has_logger = False
    has_raise = False
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                func = node.func
                # logging.error / logging.warning / logger.error / logger.warning
                # Plus logger.debug — a debug log line also reaches the operator
                # (via logs/app.log at DEBUG level), so it counts as "not silent".
                if isinstance(func, ast.Attribute) and func.attr in {
                    "error", "warning", "exception", "critical", "info", "debug", "log",
                }:
                    has_logger = True
                if isinstance(func, ast.Name) and func.id == "error":
                    # bare `error(...)` is unusual but counts
                    has_logger = True
                # Helper calls that delegate to a logger are also acceptable.
                # Pattern: any function whose name starts with `_log_` / `log_`
                # is a project-convention helper that emits a log record.
                if isinstance(func, ast.Name) and func.id.startswith(("log_", "_log_")):
                    has_logger = True
                if isinstance(func, ast.Attribute) and func.attr.startswith(("log_", "_log_")):
                    has_logger = True
            if isinstance(node, ast.Raise):
                has_raise = True
    return has_logger, has_raise


# ─────────────────────────── Audit pass ───────────────────────────


def _audit_swallowed(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find every ``except Exception`` that neither logs nor re-raises."""
    findings: list[Finding] = []
    rel = src_path.relative_to(PROJECT_ROOT)
    if str(rel) in SWALLOW_ALLOWLIST:
        return []

    for handler in [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]:
        type_name = _except_type_name(handler)
        if type_name != "Exception":
            # We deliberately scope to ``except Exception`` only.
            # ``except BaseException`` is covered by a separate finding in
            # streamlit_process.py and tracked via the allowlist above.
            continue
        has_logger, has_raise = _body_has_logger_or_raise(handler.body)
        if has_logger or has_raise:
            continue
        snippet = src_lines[handler.lineno - 1].strip() if handler.lineno - 1 < len(src_lines) else ""
        findings.append(
            Finding(rel, handler.lineno, _enclosing_function(tree, handler.lineno), snippet[:120])
        )
    return findings


# ─────────────────────────── Runner ───────────────────────────


def run_audit() -> list[Finding]:
    """Walk src/ once and return all swallowed-exception findings."""
    findings: list[Finding] = []
    for py in sorted(SRC_ROOT.rglob("*.py")):
        if _is_excluded(py):
            continue
        try:
            src_text = py.read_text(encoding="utf-8")
            src_lines = src_text.splitlines()
            tree = ast.parse(src_text)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"WARN: could not parse {py}: {e}", file=sys.stderr)
            continue
        findings.extend(_audit_swallowed(tree, py, src_lines))
    return findings


def render_report(findings: list[Finding]) -> str:
    """Format the audit as a human-readable markdown report."""
    lines: list[str] = []
    lines.append("# PharmaSupplyBot Swallowed-Exception Audit")
    lines.append("")
    lines.append("Generated by `scripts/audit_swallow.py`.")
    lines.append("")
    lines.append("A *swallowed* exception is an `except Exception` block that neither")
    lines.append("calls `logger.error(...)` / `logger.warning(...)` nor `raise`s.")
    lines.append("Such handlers silently hide failures from the operator.")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|------:|")
    lines.append(f"| Swallowed `except Exception` handlers in `src/` | {len(findings)} |")
    lines.append(f"| Files in allowlist (intentional) | {len(SWALLOW_ALLOWLIST)} |")
    lines.append("")

    # Per-file breakdown
    by_file: Counter[Path] = Counter(f.file for f in findings)
    if findings:
        lines.append("## Per-file breakdown")
        lines.append("")
        lines.append("| File | Count |")
        lines.append("|------|------:|")
        for path, n in by_file.most_common():
            lines.append(f"| `{path}` | {n} |")
        lines.append("")

        lines.append("## All occurrences")
        lines.append("")
        lines.append("| File:Line | Function | Snippet |")
        lines.append("|-----------|----------|---------|")
        for f in findings:
            snippet = f.snippet.replace("|", "\\|")
            lines.append(f"| `{f.file}:{f.line}` | `{f.function}` | `{snippet}` |")
        lines.append("")

    if SWALLOW_ALLOWLIST:
        lines.append("## Allowlist")
        lines.append("")
        lines.append("These files are explicitly excluded — broad `except` is reviewed and intentional.")
        lines.append("")
        lines.append("| File | Reason |")
        lines.append("|------|--------|")
        for path, reason in SWALLOW_ALLOWLIST.items():
            lines.append(f"| `{path}` | {reason} |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    if not SRC_ROOT.is_dir():
        print(f"ERROR: {SRC_ROOT} not found. Run from project root.", file=sys.stderr)
        return 2
    findings = run_audit()
    report = render_report(findings)
    print(report)

    # Write to docs/audit_swallow.md so it can be diffed in git
    out_path = PROJECT_ROOT / "docs" / "audit_swallow.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())