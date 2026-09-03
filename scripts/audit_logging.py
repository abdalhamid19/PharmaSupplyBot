"""Audit logging usage across the PharmaSupplyBot source tree.

Run from project root::

    py scripts/audit_logging.py

Reports:

* Every ``print(...)`` call in src/ with file:line
* Every ``basicConfig`` call (excluding comments / docstrings)
* Every ``pharmasupplybot.matching`` literal as a logger name
* Every ``console_safe`` wrapper usage
* Every manual ``logger.addHandler`` / ``logger.handlers = [...]``
* Every module-level ``logging.getLogger(...)`` call (so we know how many
  loggers exist and whether they follow the __name__ convention)

Exits 0 always — this is a *report*, not a test. To enforce the rules,
run the guard tests in tests/core/test_logging_audit.py.
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


class Finding(NamedTuple):
    """One concrete finding: file + line + symbol + brief context."""

    file: Path
    line: int
    kind: str
    snippet: str


# ─────────────────────────── Helpers ───────────────────────────


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def _callee_name(func: ast.expr) -> str | None:
    """Return the dotted name of a Call's function, or None."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        # Build dotted name by walking back through nested attributes.
        parts: list[str] = []
        cur: ast.expr = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _call_arg_str(node: ast.Call, idx: int = 0) -> str | None:
    """Return the source snippet of the idx-th positional argument, if any."""
    if idx >= len(node.args):
        return None
    try:
        return ast.unparse(node.args[idx])
    except Exception:
        return None


def _scan_calls(tree: ast.AST, predicate) -> list[ast.Call]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and predicate(node)
    ]


# ─────────────────────────── Audit passes ───────────────────────────


def _audit_print(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find every top-level print() call (we ignore comments / docstrings)."""
    findings: list[Finding] = []
    for call in _scan_calls(tree, lambda n: _callee_name(n.func) == "print"):
        snippet = src_lines[call.lineno - 1].strip() if call.lineno - 1 < len(src_lines) else ""
        findings.append(Finding(src_path, call.lineno, "print", snippet[:120]))
    return findings


def _audit_basicconfig(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find every logging.basicConfig() call (only real calls, not docstring text)."""
    findings: list[Finding] = []
    for call in _scan_calls(tree, lambda n: _callee_name(n.func) == "basicConfig"):
        snippet = src_lines[call.lineno - 1].strip() if call.lineno - 1 < len(src_lines) else ""
        findings.append(Finding(src_path, call.lineno, "basicConfig", snippet[:120]))
    return findings


def _audit_matching_logger_literal(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find ``logging.getLogger("pharmasupplybot.matching")`` literal."""
    findings: list[Finding] = []

    def is_match(n: ast.Call) -> bool:
        if not (_callee_name(n.func) in ("logging.getLogger", "getLogger")):
            return False
        return any(
            isinstance(a, ast.Constant) and a.value == "pharmasupplybot.matching"
            for a in n.args
        )

    for call in _scan_calls(tree, is_match):
        snippet = src_lines[call.lineno - 1].strip() if call.lineno - 1 < len(src_lines) else ""
        findings.append(Finding(src_path, call.lineno, "literal-logger", snippet[:120]))
    return findings


def _audit_get_logger(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find every ``logging.getLogger(...)`` call to enumerate loggers."""
    findings: list[Finding] = []
    for call in _scan_calls(
        tree,
        lambda n: (
            _callee_name(n.func) == "logging.getLogger"
            or _callee_name(n.func) == "getLogger"
        ),
    ):
        snippet = src_lines[call.lineno - 1].strip() if call.lineno - 1 < len(src_lines) else ""
        findings.append(Finding(src_path, call.lineno, "getLogger", snippet[:120]))
    return findings


def _audit_console_safe(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find every ``print(_console_safe(...))`` or ``_console_safe(...)`` standalone."""
    findings: list[Finding] = []
    for call in _scan_calls(tree, lambda n: _callee_name(n.func) == "_console_safe"):
        snippet = src_lines[call.lineno - 1].strip() if call.lineno - 1 < len(src_lines) else ""
        findings.append(Finding(src_path, call.lineno, "console_safe", snippet[:120]))
    return findings


def _audit_manual_handlers(tree: ast.AST, src_path: Path, src_lines: list[str]) -> list[Finding]:
    """Find manual logger handler manipulation outside logging_setup.py."""
    if "logging_setup.py" in str(src_path):
        return []
    findings: list[Finding] = []
    for node in ast.walk(tree):
        # logger.handlers = [...]
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "handlers"
                ):
                    snippet = src_lines[node.lineno - 1].strip() if node.lineno - 1 < len(src_lines) else ""
                    findings.append(Finding(src_path, node.lineno, "handlers-assign", snippet[:120]))
        # logger.addHandler(...) / logger.removeHandler(...)
        if isinstance(node, ast.Call):
            name = _callee_name(node.func)
            if name and name.endswith(".addHandler"):
                snippet = src_lines[node.lineno - 1].strip() if node.lineno - 1 < len(src_lines) else ""
                findings.append(Finding(src_path, node.lineno, "addHandler", snippet[:120]))
    return findings


# ─────────────────────────── Runner ───────────────────────────


def run_audit() -> dict[str, list[Finding]]:
    """Walk src/ once and return all findings, grouped by category."""
    results: dict[str, list[Finding]] = {
        "print": [],
        "basicConfig": [],
        "literal-logger": [],
        "getLogger": [],
        "console_safe": [],
        "manual-handler": [],
    }
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

        rel = py.relative_to(PROJECT_ROOT)
        results["print"].extend(_audit_print(tree, rel, src_lines))
        results["basicConfig"].extend(_audit_basicconfig(tree, rel, src_lines))
        results["literal-logger"].extend(_audit_matching_logger_literal(tree, rel, src_lines))
        results["getLogger"].extend(_audit_get_logger(tree, rel, src_lines))
        results["console_safe"].extend(_audit_console_safe(tree, rel, src_lines))
        results["manual-handler"].extend(_audit_manual_handlers(tree, rel, src_lines))
    return results


def render_report(results: dict[str, list[Finding]]) -> str:
    """Format the audit as a human-readable markdown report."""
    lines: list[str] = []
    lines.append("# PharmaSupplyBot Logging Audit")
    lines.append("")
    lines.append("Generated by `scripts/audit_logging.py`.")
    lines.append("")

    # Headline counts
    headline = [
        ("print() calls", len(results["print"])),
        ("basicConfig() calls", len(results["basicConfig"])),
        ('"pharmasupplybot.matching" literal loggers', len(results["literal-logger"])),
        ("logging.getLogger() calls (all)", len(results["getLogger"])),
        ("_console_safe() calls", len(results["console_safe"])),
        ("Manual handler manipulation", len(results["manual-handler"])),
    ]
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|------:|")
    for label, n in headline:
        lines.append(f"| {label} | {n} |")
    lines.append("")

    # Per-category breakdown by file
    def _by_file(findings: list[Finding]) -> dict[Path, int]:
        counter: Counter[Path] = Counter()
        for f in findings:
            counter[f.file] += 1
        return dict(counter.most_common())

    sections = [
        ("print", "print() calls", results["print"]),
        ("basicConfig", "basicConfig() calls", results["basicConfig"]),
        ("literal-logger", '"pharmasupplybot.matching" literal loggers', results["literal-logger"]),
        ("console_safe", "_console_safe() calls", results["console_safe"]),
        ("manual-handler", "Manual handler manipulation", results["manual-handler"]),
        ("getLogger", "logging.getLogger() callers (informational)", results["getLogger"]),
    ]
    for _key, title, findings in sections:
        if not findings:
            continue
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| File | Count |")
        lines.append("|------|------:|")
        for path, n in _by_file(findings).items():
            lines.append(f"| `{path}` | {n} |")
        lines.append("")
        lines.append("**All occurrences:**")
        lines.append("")
        lines.append("| File:Line | Snippet |")
        lines.append("|-----------|---------|")
        for f in findings:
            snippet = f.snippet.replace("|", "\\|")
            lines.append(f"| `{f.file}:{f.line}` | `{snippet}` |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    if not SRC_ROOT.is_dir():
        print(f"ERROR: {SRC_ROOT} not found. Run from project root.", file=sys.stderr)
        return 2
    results = run_audit()
    report = render_report(results)
    print(report)

    # Also write to docs/audit_logging.md so it can be diffed in git
    out_path = PROJECT_ROOT / "docs" / "audit_logging.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())