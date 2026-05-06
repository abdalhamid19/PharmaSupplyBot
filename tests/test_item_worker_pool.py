"""Integration tests for item-worker pool wiring without Playwright."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from src.cli.cli_cart_removal import run_remove_cart_command
from src.core.cart_removal_items import CartRemovalItem
from src.core.config.config_models import AppConfig


class ItemWorkerPoolTests(unittest.TestCase):
    """Test parallel cart-removal chunking, worker files, merging, and stops."""

    def setUp(self) -> None:
        """Create a temporary working directory simulating a CLI run."""
        self._tmp = tempfile.TemporaryDirectory()
        self._original_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.profile = "testprofile"
        self.artifacts_dir = Path("artifacts") / self.profile
        self.written_worker_ids: list[int] = []
        self.payload_lengths: list[int] = []

    def tearDown(self) -> None:
        """Restore original working directory and cleanup."""
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    def test_cart_workers_chunk_write_and_merge(self) -> None:
        """Cart removal uses chunks, writes worker files, then merges them."""
        items = [CartRemovalItem(str(i), f"Item {i}") for i in range(5)]
        result = self._run_command(items, workers=3)

        self.assertEqual(result, 0)
        self.assertEqual(self.payload_lengths, [2, 2, 1])
        self.assertEqual(self.written_worker_ids, [0, 1, 2])
        rows = self._read_csv(self.artifacts_dir / "cart_removal_summary.csv")
        self.assertEqual([row["item_code"] for row in rows], ["0", "1", "2", "3", "4"])
        self.assertFalse(
            list(self.artifacts_dir.glob("cart_removal_summary.worker_*.csv"))
        )

    def test_stop_flag_short_circuits_remaining_workers(self) -> None:
        """A shared stop flag can stop later workers before they write rows."""
        stop_flag = Path("artifacts") / "run_control" / "remove_cart_stop.flag"
        items = [CartRemovalItem(str(i), f"Item {i}") for i in range(4)]
        self._run_command(items, workers=2, stop_flag=stop_flag)

        self.assertTrue(stop_flag.exists())
        self.assertEqual(self.payload_lengths, [2, 2])
        self.assertEqual(self.written_worker_ids, [0])
        rows = self._read_csv(self.artifacts_dir / "cart_removal_summary.csv")
        self.assertEqual([row["item_code"] for row in rows], ["0", "1"])

    def _run_command(
        self,
        items: list[CartRemovalItem],
        workers: int,
        stop_flag: Path | None = None,
    ) -> int:
        """Run remove-cart with a fake multiprocessing context and worker."""
        app_config = self._app_config(workers)
        args = self._args(workers, stop_flag)
        with (
            patch("src.cli.cli_cart_removal.require_state_file"),
            patch(
                "src.cli.cli_cart_removal.load_cart_removal_items", return_value=items
            ),
            patch(
                "src.cli.cli_cart_removal.multiprocessing.get_context", self._context
            ),
            patch(
                "src.cli.item_worker_runner.run_cart_removal_chunk", self._fake_worker
            ),
        ):
            return run_remove_cart_command(
                cast(AppConfig, app_config), cast(Namespace, args)
            )

    def _fake_worker(self, payload: dict) -> dict:
        """Write a fake per-worker CSV unless a stop flag already exists."""
        self.payload_lengths.append(len(payload["items"]))
        flag = self._stop_flag(payload)
        if flag and flag.exists():
            return {"status": "ok", "profile_key": payload["profile_key"]}
        self._write_worker_csv(payload)
        if flag and payload["worker_id"] == 0:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("stop", encoding="utf-8")
        return {"status": "ok", "profile_key": payload["profile_key"]}

    def _write_worker_csv(self, payload: dict) -> None:
        """Write one fake worker partition summary."""
        worker_id = int(payload["worker_id"])
        self.written_worker_ids.append(worker_id)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifacts_dir / f"cart_removal_summary.worker_{worker_id}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["item_code", "item_name", "worker_id"]
            )
            writer.writeheader()
            for code, name in payload["items"]:
                writer.writerow(
                    {"item_code": code, "item_name": name, "worker_id": worker_id}
                )

    def _context(self, method: str):
        """Return an inline multiprocessing context recording the requested method."""
        self.assertEqual(method, "spawn")
        return _InlineContext()

    def _app_config(self, workers: int):
        """Return a minimal AppConfig-like object for remove-cart."""
        profile = SimpleNamespace()
        return SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            runtime=SimpleNamespace(item_workers=workers),
            profiles_to_run=lambda profile=None, all_profiles=False: [
                (self.profile, profile)
            ],
        )

    def _args(self, workers: int, stop_flag: Path | None):
        """Return a minimal CLI args namespace."""
        return SimpleNamespace(
            config="config.yaml",
            excel="data/input/remove_items/remove.xlsx",
            profile=self.profile,
            all_profiles=False,
            debug_browser=False,
            item_workers=workers,
            stop_flag=str(stop_flag) if stop_flag else None,
        )

    def _stop_flag(self, payload: dict) -> Path | None:
        """Return the stop flag path from a fake worker payload."""
        flag = payload.get("options", {}).get("stop_flag")
        return Path(flag) if flag else None

    def _read_csv(self, path: Path) -> list[dict]:
        """Read a CSV file into a list of dicts."""
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))


class _InlineContext:
    def Pool(self, processes: int):
        return _InlinePool(processes)


class _InlinePool:
    def __init__(self, processes: int) -> None:
        self.processes = processes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False

    def map(self, func, payloads):
        return [func(payload) for payload in payloads]


if __name__ == "__main__":
    unittest.main()
