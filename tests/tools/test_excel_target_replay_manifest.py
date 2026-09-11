from __future__ import annotations

import hashlib
import json
from pathlib import Path

import openpyxl
import pytest

from tools.excel_target_replay_manifest import (
    ReplayManifestInputs,
    build_manifest,
    main,
)


def _write_config(path: Path) -> None:
    path.write_text(
        """
site:
  base_url: https://example.test
excel:
  code_col: code
  name_col: name
  qty_col: qty
profiles:
  wardany:
    display_name: wardany
    pharmacy_switch: {}
excel_targets:
  target-a:
    name_col: name
    price_col: price
    discount_col: discount
    code_col: code
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_catalog(path: Path, name: str = "VOLTAREN 3AMP") -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["code", "name", "price", "discount"])
    sheet.append(["3100", name, 10, 0])
    workbook.save(path)


def test_build_manifest_is_read_only_and_fingerprints_catalog(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    order = tmp_path / "order.xlsx"
    catalog = tmp_path / "catalog.xlsx"
    prevented = tmp_path / "prevented.xlsx"
    manual_db = tmp_path / "manual.db"
    runs_db = tmp_path / "runs.db"
    _write_config(config)
    _write_catalog(order, "ORDER")
    _write_catalog(catalog)
    _write_catalog(prevented, "PREVENTED")
    manual_db.write_bytes(b"manual")
    runs_db.write_bytes(b"runs")
    input_paths = (config, order, catalog, prevented, manual_db, runs_db)
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in input_paths
    }

    manifest = build_manifest(
        ReplayManifestInputs(
            config_path=config,
            order_workbook=order,
            catalog_paths={"target-a": catalog},
            prevented_workbook=prevented,
            manual_review_db=manual_db,
            order_runs_db=runs_db,
            run_id="run-1",
            command_line="python run.py order --match-only",
        )
    )

    assert manifest["manifest_version"] == 1
    assert manifest["run_id"] == "run-1"
    assert manifest["catalog_workbook_sha256"]["target-a"]
    assert manifest["target_catalog_fingerprint"]["target-a"]
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before
    } == before


def test_catalog_fingerprint_changes_when_a_row_changes(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    catalog = tmp_path / "catalog.xlsx"
    _write_config(config)
    _write_catalog(catalog)
    first = build_manifest(
        ReplayManifestInputs(
            config_path=config,
            order_workbook=catalog,
            catalog_paths={"target-a": catalog},
        )
    )
    _write_catalog(catalog, "XITHRONE 500MG 3TAB")
    second = build_manifest(
        ReplayManifestInputs(
            config_path=config,
            order_workbook=catalog,
            catalog_paths={"target-a": catalog},
        )
    )

    assert (
        first["target_catalog_fingerprint"]["target-a"]
        != second["target_catalog_fingerprint"]["target-a"]
    )


def test_manifest_cli_writes_json_only(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    order = tmp_path / "order.xlsx"
    catalog = tmp_path / "catalog.xlsx"
    output = tmp_path / "manifest.json"
    _write_config(config)
    _write_catalog(order, "ORDER")
    _write_catalog(catalog)

    assert main(
        [
            "--config",
            str(config),
            "--order-workbook",
            str(order),
            "--catalog",
            f"target-a={catalog}",
            "--output",
            str(output),
        ]
    ) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["target_catalog_fingerprint"]["target-a"]


def test_missing_catalog_configuration_fails_closed(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    catalog = tmp_path / "catalog.xlsx"
    _write_config(config)
    _write_catalog(catalog)

    with pytest.raises(KeyError, match="not configured"):
        build_manifest(
            ReplayManifestInputs(
                config_path=config,
                order_workbook=catalog,
                catalog_paths={"unknown": catalog},
            )
        )
