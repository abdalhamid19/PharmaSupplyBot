"""Guard tests for the swallowed-exception policy.

The unified logging system already requires every diagnostic to land in
``logs/app.log`` or ``logs/errors.log``. A *swallowed* exception is the
counterpart anti-pattern: an ``except Exception`` that neither logs the
failure nor re-raises it. Such handlers silently hide bugs from the
operator — the run finishes with the wrong count and no clue what
went wrong.

These tests fail loudly when the source tree violates the invariant:

* Every ``except Exception`` handler must EITHER call
  ``logger.error(...)`` / ``logger.warning(...)`` / ``logging.error(...)``
  (or any logger method that publishes the failure) OR ``raise`` another
  exception. Anything else is a swallow.

Files in the explicit allowlist (``scripts/audit_swallow.py``) are
reviewed and intentional.

The expected shape of the suite today (after Stage 1 audit):

* The baseline is locked via :func:`test_swallow_baseline_matches_audit`
  — the audit script reports N, the guard test asserts N. Any new
  swallow breaks the guard.
* The audit script + baseline doc must exist and parse.

The bulk-replacement stages (Stage 5+ of the incremental refactor)
will move these numbers down. The guard test is the contract that
prevents new swallows from sneaking in.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DOCS_DIR = PROJECT_ROOT / "docs"
BASELINE_DOC = DOCS_DIR / "audit_swallow.md"
AUDIT_SCRIPT = SCRIPTS_DIR / "audit_swallow.py"

# Files where broad ``except`` is intentional. MUST match the
# SWALLOW_ALLOWLIST in scripts/audit_swallow.py.
SWALLOW_ALLOWLIST: dict[str, str] = {
    "src/ui/views/streamlit_process.py": "streamlit subprocess wrapper — UI-facing failure capture",
}

EXCLUDE_DIRS = {"__pycache__", ".venv", "venv"}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def _except_type_name(handler: ast.ExceptHandler) -> str | None:
    if handler.type is None:
        return None
    if isinstance(handler.type, ast.Name):
        return handler.type.id
    if isinstance(handler.type, ast.Attribute):
        return handler.type.attr
    return None


def _body_has_logger_or_raise(body: list[ast.stmt]) -> tuple[bool, bool]:
    """Return (has_logger_call, has_raise). Either is enough to clear the finding."""
    has_logger = False
    has_raise = False
    LOGGER_METHODS = {"error", "warning", "exception", "critical", "info"}
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in LOGGER_METHODS:
                    has_logger = True
                if isinstance(func, ast.Name) and func.id == "error":
                    has_logger = True
            if isinstance(node, ast.Raise):
                has_raise = True
    return has_logger, has_raise


def _all_swallowed_handlers() -> list[tuple[Path, int]]:
    """Walk src/ and return every swallowed ``except Exception`` as (file, lineno)."""
    findings: list[tuple[Path, int]] = []
    for py in sorted(SRC_ROOT.rglob("*.py")):
        if _is_excluded(py):
            continue
        rel = py.relative_to(PROJECT_ROOT)
        if str(rel) in SWALLOW_ALLOWLIST:
            continue
        try:
            text = py.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for handler in [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]:
            if _except_type_name(handler) != "Exception":
                continue
            has_logger, has_raise = _body_has_logger_or_raise(handler.body)
            if has_logger or has_raise:
                continue
            findings.append((rel, handler.lineno))
    return findings


# ─────────────────────────── Guards ───────────────────────────


def test_no_swallowed_exceptions_in_src() -> None:
    """No swallowed ``except Exception`` anywhere in src/.

    A handler is "swallowed" when it neither logs the failure nor
    re-raises. Future commits that introduce one will fail this test.
    The first run is expected to fail until the Stage-5 bulk-replacement
    stages bring the count down to zero — see
    :func:`test_swallow_baseline_matches_audit` for the current baseline.
    """
    offenders = _all_swallowed_handlers()
    assert not offenders, (
        "Swallowed `except Exception` handlers are forbidden. "
        "Either log the failure (`logger.error(...)`) or re-raise "
        "(`raise ... from exc`):\n"
        + "\n".join(f"  {p}:{ln}" for p, ln in offenders)
    )


def test_swallow_baseline_matches_audit() -> None:
    """The baseline doc reports N swallows; the guard test asserts N.

    Locks the contract so the bulk-replacement stages (Stage 5+) move
    the number down in observable, auditable commits. If the doc and
    the script disagree, this test fails — the doctor catches drift
    between the two sources of truth.
    """
    # Run the audit script and capture its summary line.
    if not AUDIT_SCRIPT.is_file():
        pytest.skip(f"{AUDIT_SCRIPT} not present — run from project root")
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"audit_swallow.py exited {result.returncode}\n"
        f"stderr: {result.stderr[-1000:]}"
    )
    # Parse the headline count from the rendered report.
    import re
    m = re.search(
        r"\|\s*Swallowed\s+`except Exception`\s+handlers\s+in\s+`src/`\s*\|\s*(\d+)\s*\|",
        result.stdout,
    )
    assert m, "could not find headline count in audit_swallow.py output"
    audit_count = int(m.group(1))

    # The baseline doc must mirror the audit script's output.
    assert BASELINE_DOC.is_file(), f"missing baseline doc: {BASELINE_DOC}"
    doc_text = BASELINE_DOC.read_text(encoding="utf-8")
    m2 = re.search(
        r"\|\s*Swallowed\s+`except Exception`\s+handlers\s+in\s+`src/`\s*\|\s*(\d+)\s*\|",
        doc_text,
    )
    assert m2, f"missing headline row in {BASELINE_DOC}"
    doc_count = int(m2.group(1))

    assert audit_count == doc_count, (
        f"audit script reports {audit_count} but baseline doc says {doc_count} — "
        "regenerate the doc by running audit_swallow.py from project root"
    )


def test_swallow_allowlist_matches_audit_script() -> None:
    """The guard's allowlist and the audit script's allowlist must agree.

    Two lists, one policy. Drift between them silently relaxes or
    tightens the rule on one side — this test catches that.
    """
    assert AUDIT_SCRIPT.is_file(), f"missing {AUDIT_SCRIPT}"
    tree = ast.parse(AUDIT_SCRIPT.read_text(encoding="utf-8"))
    script_allowlist: dict[str, str] = {}
    for node in ast.walk(tree):
        # Module-level dict literal: ``SWALLOW_ALLOWLIST: dict[str, str] = {...}``
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "SWALLOW_ALLOWLIST"
            and isinstance(node.value, ast.Dict)
        ):
            for k, v in zip(node.value.keys, node.value.values):
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                    script_allowlist[k.value] = v.value
    assert script_allowlist == SWALLOW_ALLOWLIST, (
        f"allowlist drift: guard test has {SWALLOW_ALLOWLIST}, "
        f"audit script has {script_allowlist}"
    )


# ─────────────────────────── Tooling sanity ───────────────────────────


def test_audit_swallow_script_exists_and_parses() -> None:
    """The audit script must be present and importable."""
    assert AUDIT_SCRIPT.is_file(), f"missing {AUDIT_SCRIPT}"
    ast.parse(AUDIT_SCRIPT.read_text(encoding="utf-8"))


def test_audit_swallow_baseline_doc_exists() -> None:
    """The baseline numbers live in docs/audit_swallow.md so they can be diffed."""
    assert BASELINE_DOC.is_file(), f"missing {BASELINE_DOC}"