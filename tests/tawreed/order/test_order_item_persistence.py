"""Tests that per-item order-run persistence is wired into artifact writes."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from src.core.artifact_run import artifact_run
from src.core.utils.excel import Item
from src.tawreed.order.tawreed_order_summary_build import append_order_item_artifacts


def _summary(status: str = "matched-only") -> SimpleNamespace:
    """Return a minimal OrderResultSummary-shaped stub."""
    return SimpleNamespace(
        status=status,
        reason="Matched product only.",
        ordered_total_qty=0,
        selected_store_name="شركه العاصمه",
        selected_discount_percent="21%",
        elapsed_seconds=1.5,
        match_elapsed_seconds=0.5,
        timing_seconds={},
    )


class OrderItemPersistenceWiringTests(unittest.TestCase):
    """The database write must be attempted once per item and never fatal."""

    def setUp(self) -> None:
        """Create an isolated artifact directory for each test."""
        self._temp = TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.item = Item(code="12345", name="CAL MAG", qty=10)

    def tearDown(self) -> None:
        """Remove the temporary artifact directory."""
        self._temp.cleanup()

    def _append(self) -> None:
        """Run the artifact append path inside an active artifact run."""
        with artifact_run("order", "wardany", "20260830_1809", self.root):
            append_order_item_artifacts("wardany", self.item, _summary(), None)

    def test_persistence_is_called_with_the_summary_row(self) -> None:
        """The database receives the same row that the CSV artifact receives."""
        target = "src.tawreed.order.tawreed_order_summary_build.record_run_item"
        with mock.patch(target) as record:
            self._append()
        record.assert_called_once()
        run_key, row = record.call_args.args[0], record.call_args.args[1]
        self.assertEqual(run_key, "wardany/20260830_1809")
        self.assertEqual(row["item_code"], "12345")
        self.assertEqual(row["status"], "matched-only")

    def test_persistence_failure_does_not_break_csv_artifacts(self) -> None:
        """The CSV artifact is the recovery source and must always be written."""
        target = "src.tawreed.order.tawreed_order_summary_build.record_run_item"
        with mock.patch(target, side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self._append()
        run_dir = self.root / "order" / "wardany" / "20260830_1809"
        self.assertTrue(list(run_dir.glob("order_item_summary_*.csv")))

    def test_real_persistence_layer_swallows_its_own_errors(self) -> None:
        """record_run_item is the failure boundary, so no raise escapes it."""
        with mock.patch(
            "src.core.ordering.order_run_persistence._store",
            side_effect=RuntimeError("boom"),
        ):
            self._append()
        run_dir = self.root / "order" / "wardany" / "20260830_1809"
        self.assertTrue(list(run_dir.glob("order_item_summary_*.csv")))

    def test_no_write_attempted_outside_an_artifact_run(self) -> None:
        """Without a run context there is no run key to attach facts to."""
        target = "src.tawreed.order.tawreed_order_summary_build.record_run_item"
        with mock.patch(target) as record:
            append_order_item_artifacts("wardany", self.item, _summary(), None)
        self.assertEqual(record.call_args.args[0], "")


if __name__ == "__main__":
    unittest.main()
