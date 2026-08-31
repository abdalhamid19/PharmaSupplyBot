"""Hypothesis test-runner: executes all hypothesis modules and prints scoring.

Run: python -m pytest tests/hypotheses/automatched/ -q  (per-module)
Or:  python tests/hypotheses/automatched/run_all.py     (aggregate scoring)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tests.hypotheses.automatched.h1_tuple_truthiness import (  # noqa: E402
    H1TupleTruthinessTests,
)
from tests.hypotheses.automatched.h2_config_flag_off import (  # noqa: E402
    H2ConfigFlagOffTests,
)
from tests.hypotheses.automatched.h3_manual_review_required import (  # noqa: E402
    H3ManualReviewRequiredTests,
)
from tests.hypotheses.automatched.h4_preserve_existing import (  # noqa: E402
    H4PreserveExistingTests,
)
from tests.hypotheses.automatched.h5_forced_match_guard import (  # noqa: E402
    H5ForcedMatchGuardTests,
)
from tests.hypotheses.automatched.h6_db_write_failure import (  # noqa: E402
    H6DbWriteFailureTests,
)

ALL_HYPOTHESES = [
    # NOTE: pre-fix, H1 confirmed (score 95) and was the root cause.
    # Post-fix these run as regression guards: a "CONFIRMED" result here now
    # means a regression of that hypothesis' guarded behaviour, not a live bug.
    ("H1", "tuple truthiness always-true at call site (regression guard)", H1TupleTruthinessTests, 95),
    ("H2", "enable_auto_save_verified_match disabled (flag semantics)", H2ConfigFlagOffTests, 30),
    ("H3", "manual_review_required routes items away (routing semantics)", H3ManualReviewRequiredTests, 40),
    ("H4", "_preserve_existing_decision blocks upsert (guard semantics)", H4PreserveExistingTests, 25),
    ("H5", "forced manual-review guard skips re-save (guard semantics)", H5ForcedMatchGuardTests, 15),
    ("H6", "DB write silently fails (store persistence)", H6DbWriteFailureTests, 5),
]


def run_all() -> None:
    total_scored: list[tuple[str, str, int, str]] = []
    for code, desc, case, prior in ALL_HYPOTHESES:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
        runner = unittest.TextTestRunner(verbosity=0, stream=open("nul", "w"))
        result = runner.run(suite)
        passed = result.testsRun - len(result.failures) - len(result.errors)
        confirmed = bool(result.failures or result.errors)
        score = prior if confirmed else 0
        status = "CONFIRMED" if confirmed else "rejected"
        print(f"[{code}] {desc}\n    tests={result.testsRun} passed={passed} "
              f"prior={prior} -> score={score} ({status})")
        total_scored.append((code, desc, score, status))

    print("\n=== SCORING SUMMARY (prior x confirmation) ===")
    for code, desc, score, status in sorted(total_scored, key=lambda x: -x[2]):
        print(f"{score:4d}  [{code}] {desc} -> {status}")
    winner = max(total_scored, key=lambda x: x[2])
    print(f"\nMOST LIKELY ROOT CAUSE: [{winner[0]}] {winner[1]}")


if __name__ == "__main__":
    run_all()
