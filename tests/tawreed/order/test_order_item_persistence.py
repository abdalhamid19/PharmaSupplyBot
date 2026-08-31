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

    def test_store_snapshot_is_forwarded_to_persistence(self) -> None:
        """The offering stores must reach the same write as the item fact."""
        target = "src.tawreed.order.tawreed_order_summary_build.record_run_item"
        snapshot = {
            "stores": [{"storeId": 1, "storeProductId": 77}],
            "store_selections": [({"storeId": 1, "storeProductId": 77}, 10)],
            "store_source": "store_details",
        }
        with mock.patch(target) as record:
            with artifact_run("order", "wardany", "20260830_1809", self.root):
                append_order_item_artifacts(
                    "wardany", self.item, _summary(), None, store_snapshot=snapshot
                )
        self.assertEqual(record.call_args.kwargs["store_source"], "store_details")
        self.assertEqual(len(record.call_args.kwargs["stores"]), 1)

    def test_absent_snapshot_still_writes_item_facts(self) -> None:
        """Callers without a snapshot (and old tests) must keep working."""
        target = "src.tawreed.order.tawreed_order_summary_build.record_run_item"
        with mock.patch(target) as record:
            self._append()
        self.assertNotIn("stores", record.call_args.kwargs)


class SummaryRecorderSnapshotTests(unittest.TestCase):
    """The recorder must pull the snapshot off the bot automatically."""

    def test_recorder_forwards_bot_store_snapshot(self) -> None:
        """This is the wiring that makes captured stores reach the database."""
        from src.core.config.config_models import DatabaseConfig, MatchingConfig
        from src.tawreed.order.tawreed_order_summary import OrderSummaryRecorder
        from src.tawreed.store.tawreed_store_snapshot import (
            record_store_rows,
            record_store_selections,
        )

        store_row = {"storeId": 1, "storeProductId": 77}
        bot = SimpleNamespace(
            profile_key="wardany",
            summary_label_suffix=None,
            last_match_decision=None,
            config=SimpleNamespace(
                matching=MatchingConfig(), database=DatabaseConfig()
            ),
        )
        record_store_rows(bot, [store_row], "store_details")
        record_store_selections(bot, [(store_row, 10)])
        recorder = OrderSummaryRecorder.__new__(OrderSummaryRecorder)
        recorder.bot = bot

        target = (
            "src.tawreed.order.tawreed_order_summary.append_order_item_artifacts"
        )
        with mock.patch(target) as append:
            recorder.record_order_run_artifacts(
                Item(code="12345", name="CAL MAG", qty=10), _summary()
            )
        snapshot = append.call_args.kwargs["store_snapshot"]
        self.assertEqual(snapshot["stores"], [store_row])
        self.assertEqual(snapshot["store_selections"], [(store_row, 10)])
        self.assertEqual(snapshot["store_source"], "store_details")
        self.assertTrue(append.call_args.kwargs["database_options"]["enabled"])


if __name__ == "__main__":
    unittest.main()
