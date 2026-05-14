"""Run the repeatable validation suite used after implementation phases."""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    """Run static checks, tests, and optional smoke checks."""
    args = _parse_args()
    commands = _base_commands()
    if args.smoke:
        commands.extend(_smoke_commands())
    for command in commands:
        result = _run(command)
        if result != 0:
            return result
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run safe CLI smoke checks")
    return parser.parse_args()


def _base_commands() -> list[list[str]]:
    python = sys.executable
    return [
        [python, "-m", "compileall", "-q", "run.py", "streamlit_app.py", "src", "tests", "tools"],
        [python, "tools/run_unit_tests.py"],
        [python, "tools/rule_audit.py"],
    ]


def _smoke_commands() -> list[list[str]]:
    python = sys.executable
    excel = "data/input/order_items/shortage_report_total_20260502.xlsx"
    return [
        [python, "run.py", "--help"],
        [python, "run.py", "order", "--help"],
        [python, "run.py", "remove-cart", "--help"],
        [python, "run.py", "export-products", "--help"],
        [python, "run.py", "match-products", "--help"],
        [
            python,
            "run.py",
            "match-products",
            "--profile",
            "wardany",
            "--excel",
            excel,
            "--limit",
            "5",
            "--no-ai",
            "--trace",
            "--output",
            "artifacts/wardany/phase_validation_match_products.csv",
        ],
    ]


def _run(command: list[str]) -> int:
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
