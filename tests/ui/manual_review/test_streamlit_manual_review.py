"""Tests for Streamlit manual-review learning helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from src.core.manual_review.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.core.manual_review.manual_review_candidates import ReviewCandidateOption
from src.ui.manual_review.streamlit_manual_review_input import (
    editable_manual_review_rows,
    manual_review_decisions_from_rows,
    save_manual_review_rows,
)
from src.ui.manual_review.streamlit_manual_review_cli import (
    manual_review_remove_command,
    write_not_matching_review_csv,
)
from src.ui.manual_review.streamlit_manual_review_page_saved import (
    _convert_to_approved,
    _decision_row,
    _default_sort_preferences,
    _prepare_display_df,
    deleted_identity_pairs,
)
from src.ui.manual_review.streamlit_manual_review_page import (
    _configured_candidate_limit,
    _limit_candidates_by_source,
)
from src.ui.manual_review.streamlit_manual_review_page import _group_options_by_source
from src.ui.manual_review import streamlit_manual_review_page as manual_review_page


class StreamlitManualReviewTests(unittest.TestCase):
    """Validate conversion from edited UI rows to persisted decisions."""

    def test_builds_decision_from_approved_checkbox(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [
                {
                    "item_code": "123",
                    "item_name": "Panadol",
                    "approved_match": True,
                    "correct_store_product_id": "store-1",
                }
            ],
            "20260514_1252",
        )

        self.assertEqual(len(decisions), 1)
        self.assertTrue(decisions[0].approved)
        self.assertEqual(decisions[0].manual_decision, "approved_match")
        self.assertEqual(decisions[0].correct_store_product_id, "store-1")

    def test_approved_table_row_preserves_matching_provenance(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [
                {
                    "item_code": "90951",
                    "item_name": "INODEP CAPSULES 30",
                    "approved_match": True,
                    "correct_store_product_id": "baraka-1",
                    "matching_source": "excel-target",
                    "matching_source_label": "baraka@baraka.xlsx",
                    "excel_target_key": "baraka",
                    "excel_target_source_file": "baraka.xlsx",
                    "identity_evidence_kind": "dictionary",
                    "identity_evidence": "INODEP -> اينوديب",
                }
            ],
            "20260907_1752",
        )

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].manual_decision, "approved_match")
        self.assertEqual(decisions[0].matching_source, "excel-target")
        self.assertEqual(decisions[0].matching_source_label, "baraka@baraka.xlsx")
        self.assertEqual(decisions[0].excel_target_key, "baraka")
        self.assertEqual(decisions[0].identity_evidence_kind, "dictionary")

    def test_builds_not_matching_decision(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [
                {
                    "item_code": "123",
                    "item_name": "Panadol",
                    "not_matching": True,
                    "correct_store_product_id": "store-1",
                }
            ],
            "20260514_1252",
        )

        self.assertEqual(decisions[0].manual_decision, "not_matching")

    def test_skips_empty_unapproved_row(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [{"item_code": "123", "item_name": "Panadol", "approved_match": False}],
            "20260514_1252",
        )

        self.assertEqual(decisions, [])

    def test_save_decision_can_be_read_by_new_store_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            count = save_manual_review_rows(
                [
                    {
                        "item_code": "123",
                        "item_name": "Panadol",
                        "approved_match": True,
                        "correct_store_product_id": "store-1",
                        "correct_query": "Panadol 24",
                    }
                ],
                "20260514_1252",
                db_path,
            )

            decision = ManualReviewStore(db_path).lookup("123", "Panadol")

        self.assertEqual(count, 1)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.correct_store_product_id, "store-1")
        self.assertEqual(decision.correct_query, "Panadol 24")

    def test_editable_rows_show_saved_decision_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManualReviewStore(Path(temp_dir) / "manual.sqlite3")
            store.upsert(
                ManualReviewDecision(
                    "123", "Panadol", True, "store-2", "Panadol Extra", "Pana"
                )
            )

            rows = editable_manual_review_rows(
                [{"item_code": "123", "item_name": "Panadol"}], store
            )

        self.assertEqual(rows[0]["decision_source"], "saved_manual_review")
        self.assertTrue(rows[0]["approved_match"])
        self.assertFalse(rows[0]["not_matching"])
        self.assertEqual(rows[0]["correct_store_product_id"], "store-2")

    def test_writes_not_matching_csv_for_current_run_removal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "artifacts/order/wardany/20260514_2107"
            run_dir.mkdir(parents=True)

            path = write_not_matching_review_csv(
                [
                    {"item_code": "1", "item_name": "Panadol", "not_matching": True},
                    {"item_code": "2", "item_name": "Cetal", "not_matching": False},
                ],
                run_dir,
            )
            content = path.read_text(encoding="utf-8")

        self.assertTrue(path.name.startswith("manual_review_not_matching_"))
        self.assertIn("Panadol", content)
        self.assertNotIn("Cetal", content)

    def test_manual_review_remove_command_uses_run_profile(self) -> None:
        command = manual_review_remove_command(
            Path("config.yaml"),
            Path("artifacts/order/wardany/20260514_2107"),
            Path("manual.csv"),
        )

        self.assertEqual(command[command.index("--profile") + 1], "wardany")
        self.assertIn("--from-manual-review", command)

    def test_saved_decision_row_exposes_run_date_from_run_id(self) -> None:
        row = _decision_row(
            ManualReviewDecision(
                item_code="123",
                item_name="Panadol",
                approved=True,
                run_id="20260622_1425",
            )
        )

        self.assertEqual(row["run_date"], "20260622_1425")
        self.assertEqual(row["run_id"], "20260622_1425")

    def test_saved_corrections_default_to_newest_run_date_first(self) -> None:
        self.assertEqual(
            _default_sort_preferences(["item_name", "run_date"]),
            ("run_date", False),
        )

    def test_saved_corrections_keep_newest_rows_at_top(self) -> None:
        import pandas as pd

        frame = pd.DataFrame(
            [
                {"item_code": "old", "run_date": "20260601_1000"},
                {"item_code": "new", "run_date": "20260602_1000"},
            ]
        )

        with patch(
            "src.ui.manual_review.streamlit_manual_review_page_saved._get_sort_preferences",
            return_value=("run_date", False),
        ):
            display = _prepare_display_df(
                frame,
                ["item_code", "run_date"],
                ["item_code", "run_date"],
            )

        self.assertEqual(display["item_code"].tolist(), ["new", "old"])

    def test_saved_corrections_keep_csv_import_after_timestamped_runs(self) -> None:
        import pandas as pd

        frame = pd.DataFrame(
            [
                {"item_code": "new", "run_date": "20260909_1259"},
                {"item_code": "legacy", "run_date": "csv_import"},
            ]
        )

        with patch(
            "src.ui.manual_review.streamlit_manual_review_page_saved._get_sort_preferences",
            return_value=("run_date", False),
        ):
            display = _prepare_display_df(
                frame,
                ["item_code", "run_date"],
                ["item_code", "run_date"],
            )

        self.assertEqual(display["item_code"].tolist(), ["new", "legacy"])

    def test_saved_decision_row_exposes_matching_source_and_decision(self) -> None:
        from types import SimpleNamespace

        row = _decision_row(
            SimpleNamespace(
                item_code="90951",
                item_name="INODEP CAPSULES 30",
                approved=True,
                manual_decision="auto_matched",
                correct_store_product_id="baraka-1",
                correct_product_name="INODEP 30 CAPS",
                correct_product_name_ar="اينوديب 30 كبسول",
                correct_query="",
                run_id="20260907_1600",
                matching_source="excel_target",
                matching_source_label="baraka@baraka.xlsx",
                identity_evidence_kind="dictionary",
                identity_evidence="INODEP",
                excel_target_key="baraka",
                excel_target_source_file="baraka.xlsx",
            )
        )

        self.assertEqual(row["matching_source"], "excel_target")
        self.assertEqual(row["matching_source_label"], "baraka@baraka.xlsx")
        self.assertEqual(row["manual_decision"], "auto_matched")
        self.assertEqual(row["excel_target_key"], "baraka")
        self.assertEqual(row["identity_evidence_kind"], "dictionary")

    def test_run_discovery_includes_excel_target_summary_and_candidate_artifacts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts = Path(temp_dir) / "artifacts"
            run_dir = artifacts / "excel-target" / "baraka" / "20260907_1600"
            run_dir.mkdir(parents=True)
            (run_dir / "match_only_summary_baraka.csv").write_text("status\nno-results\n", encoding="utf-8")
            with patch.object(manual_review_page, "ARTIFACTS_DIR", artifacts):
                runs = manual_review_page._available_runs_with_candidates()

        self.assertEqual(runs, [run_dir])

    def test_run_discovery_skips_directory_when_windows_denies_listing(self) -> None:
        class DeniedDirectory:
            def iterdir(self):
                raise PermissionError(5, "Access is denied", "artifacts/pytest_runtime")

        self.assertEqual(
            manual_review_page._safe_child_directories(DeniedDirectory()),
            (),
        )

    def test_run_discovery_puts_latest_run_first_for_default_selection(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts = Path(temp_dir) / "artifacts"
            older = artifacts / "order" / "wardany" / "20260906_2359"
            latest = artifacts / "excel-target" / "baraka" / "20260907_0001"
            for run_dir in (older, latest):
                run_dir.mkdir(parents=True)
                (run_dir / "manual_review_candidates_test.jsonl").write_text(
                    "", encoding="utf-8"
                )
            with patch.object(manual_review_page, "ARTIFACTS_DIR", artifacts):
                runs = manual_review_page._available_runs_with_candidates()

        self.assertEqual(runs, [latest, older])

    def test_same_run_id_prefers_source_with_more_review_items(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts = Path(temp_dir) / "artifacts"
            tawreed = artifacts / "order" / "wardany" / "20260907_1839"
            baraka = artifacts / "excel-target" / "baraka" / "20260907_1839"
            for run_dir, records in ((tawreed, 1), (baraka, 8)):
                run_dir.mkdir(parents=True)
                (run_dir / "manual_review_candidates_test.jsonl").write_text(
                    "{}\n" * records, encoding="utf-8"
                )
            with patch.object(manual_review_page, "ARTIFACTS_DIR", artifacts):
                runs = manual_review_page._available_runs_with_candidates()

        self.assertEqual(runs[0], baraka)

    def test_run_groups_merge_all_sources_with_the_same_run_id(self) -> None:
        tawreed = Path("artifacts/order/wardany/20260907_1839")
        baraka = Path("artifacts/excel-target/baraka/20260907_1839")
        older = Path("artifacts/order/wardany/20260907_1700")

        groups = manual_review_page._group_runs_by_id([tawreed, older, baraka])

        self.assertEqual([run_id for run_id, _ in groups], ["20260907_1839", "20260907_1700"])
        self.assertEqual(set(groups[0][1]), {tawreed, baraka})

    def test_run_groups_do_not_default_to_non_timestamp_verification_run(self) -> None:
        verification = Path("artifacts/excel-target/alnasr/impl_verify_20260908")
        latest = Path("artifacts/order/wardany/20260908_1700")

        groups = manual_review_page._group_runs_by_id([verification, latest])

        self.assertEqual([run_id for run_id, _ in groups], [
            "20260908_1700", "impl_verify_20260908",
        ])

    def test_group_candidate_loader_combines_tawreed_and_baraka(self) -> None:
        tawreed_dir = Path("artifacts/order/wardany/20260907_1839")
        baraka_dir = Path("artifacts/excel-target/baraka/20260907_1839")
        tawreed_option = ReviewCandidateOption(
            store_product_id="t-1", name_en="TEST", name_ar="",
            supplier="wardany", available_quantity=1, price=10.0,
            score=15.0, rejection_reason="", orderable=True,
        )
        baraka_option = ReviewCandidateOption(
            store_product_id="b-1", name_en="", name_ar="منتج",
            supplier="excel-target:baraka", available_quantity=1, price=9.0,
            score=14.0, rejection_reason="strength not proven", orderable=True,
            matching_source="excel-target", matching_source_label="baraka@baraka.xlsx",
            target_key="baraka", excel_target_key="baraka",
        )

        def candidates_for(run_dir):
            option = tawreed_option if run_dir == tawreed_dir else baraka_option
            return {"1::TEST": [option]}

        with patch.object(
            manual_review_page, "load_review_candidates", side_effect=candidates_for
        ):
            merged = manual_review_page._load_group_candidates(
                (tawreed_dir, baraka_dir)
            )

        self.assertEqual(len(merged["1::TEST"]), 2)
        self.assertEqual(
            {option.matching_source for option in merged["1::TEST"]},
            {"tawreed", "excel-target"},
        )

    def test_tawreed_saved_decision_does_not_hide_baraka_candidates(self) -> None:
        option = ReviewCandidateOption(
            store_product_id="baraka-1",
            name_en="",
            name_ar="منتج البركة",
            supplier="excel-target:baraka",
            available_quantity=1,
            price=10.0,
            score=20.0,
            rejection_reason="candidate strength is not proven",
            orderable=True,
            matching_source="excel-target",
            target_key="baraka",
            excel_target_key="baraka",
        )
        store = Mock()
        store.lookup_all.return_value = [
            ManualReviewDecision(
                item_code="1",
                item_name="TEST",
                approved=True,
                manual_decision="auto_matched",
                matching_source="tawreed",
            )
        ]

        visible = manual_review_page._filter_and_prepare_items(
            {"1::TEST": [option]}, store, hide_completed=True
        )

        self.assertEqual(visible, [("1::TEST", [option])])

    def test_any_saved_supplier_row_hides_only_its_own_candidate_scope(self) -> None:
        tawreed = ReviewCandidateOption(
            store_product_id="t-1", name_en="TEST", name_ar="", supplier="wardany",
            available_quantity=1, price=10.0, score=90.0, matching_source="tawreed",
            rejection_reason="", orderable=True,
        )
        baraka = ReviewCandidateOption(
            store_product_id="b-1", name_en="", name_ar="منتج", supplier="baraka",
            available_quantity=1, price=10.0, score=90.0,
            matching_source="excel-target", target_key="baraka", excel_target_key="baraka",
            rejection_reason="", orderable=True,
        )
        store = Mock()
        store.lookup_all.return_value = [
            ManualReviewDecision(
                item_code="1", item_name="TEST", approved=True,
                manual_decision="approved_match", matching_source="excel-target",
                excel_target_key="baraka",
            )
        ]

        visible = manual_review_page._filter_and_prepare_items(
            {"1::TEST": [tawreed, baraka]}, store, hide_completed=True
        )

        self.assertEqual(visible, [("1::TEST", [tawreed])])

    def test_deleted_identity_pairs_targets_exact_row_not_shared_code(self) -> None:
        """Deletion must include supplier scope when the same item has two rows."""
        import pandas as pd

        original = pd.DataFrame(
            [
                {"item_code": "47853", "item_name": "ZOCOZET 10/10", "matching_source": "tawreed", "matching_source_label": "wardany"},
                {"item_code": "47853", "item_name": "ZOCOZET 10/10", "matching_source": "excel-target", "matching_source_label": "baraka"},
            ]
        )
        edited = pd.DataFrame([{"item_code": "47853", "item_name": "ZOCOZET 10/10", "matching_source": "excel-target", "matching_source_label": "baraka"}])

        self.assertEqual(
            deleted_identity_pairs(original, edited),
            [("47853", "ZOCOZET 10/10", "tawreed", "wardany", "")],
        )

    def test_convert_to_approved_looks_up_exact_supplier_row(self) -> None:
        import pandas as pd

        selected = pd.DataFrame([{
            "item_code": "47853", "item_name": "ZOCOZET 10/10",
            "matching_source": "excel-target", "matching_source_label": "baraka",
            "excel_target_key": "baraka",
        }])
        decision = ManualReviewDecision(
            item_code="47853", item_name="ZOCOZET 10/10", approved=True,
            manual_decision="auto_matched", matching_source="excel-target",
            matching_source_label="baraka", excel_target_key="baraka",
        )
        store = Mock()
        store.lookup.return_value = decision

        with patch("src.ui.manual_review.streamlit_manual_review_page_saved.st"):
            _convert_to_approved(selected, store)

        store.lookup.assert_called_once_with(
            "47853", "ZOCOZET 10/10", matching_source="excel-target",
            excel_target_key="baraka",
        )
        self.assertEqual(store.upsert.call_args.args[0].manual_decision, "approved_match")

    def test_configured_candidate_limit_defaults_to_five(self) -> None:
        self.assertEqual(_configured_candidate_limit(None), 5)

    def test_configured_candidate_limit_reads_app_config_matching(self) -> None:
        from types import SimpleNamespace

        app_config = SimpleNamespace(
            matching=SimpleNamespace(manual_review_display_candidate_limit=9)
        )

        self.assertEqual(_configured_candidate_limit(app_config), 9)

    def test_candidate_options_are_grouped_by_excel_target_scope(self) -> None:
        options = [
            ReviewCandidateOption(
                store_product_id="baraka-1",
                name_en="ALPHAVIM",
                name_ar="",
                supplier="baraka",
                available_quantity=1,
                price=10.0,
                score=20.0,
                rejection_reason="",
                orderable=True,
                matching_source="excel-target",
                matching_source_label="البركة شركات@محروس1.xlsx",
                target_key="البركة شركات",
                excel_target_key="البركة شركات",
            ),
            ReviewCandidateOption(
                store_product_id="qaysar-1",
                name_en="ALPHAVIM",
                name_ar="",
                supplier="qaysar",
                available_quantity=1,
                price=9.0,
                score=20.0,
                rejection_reason="",
                orderable=True,
                matching_source="excel-target",
                matching_source_label="القيصر شركات@جملة محروس.xlsx",
                target_key="القيصر شركات",
                excel_target_key="القيصر شركات",
            ),
        ]

        groups = _group_options_by_source(options)

        self.assertEqual(
            [scope for scope, _ in groups],
            [
                ("excel-target", "البركة شركات"),
                ("excel-target", "القيصر شركات"),
            ],
        )
        self.assertEqual([len(group) for _, group in groups], [1, 1])

    def test_multi_source_selectors_save_one_decision_per_source(self) -> None:
        from contextlib import nullcontext
        from pathlib import Path
        from src.core.utils.excel import Item
        from src.ui.manual_review import streamlit_manual_review_page as page

        options = [
            ReviewCandidateOption(
                store_product_id="baraka-1", name_en="ALPHAVIM", name_ar="",
                supplier="baraka", available_quantity=1, price=10.0,
                score=20.0, rejection_reason="", orderable=True,
                matching_source="excel-target",
                matching_source_label="baraka@baraka.xlsx",
                target_key="baraka", excel_target_key="baraka",
            ),
            ReviewCandidateOption(
                store_product_id="qaysar-1", name_en="ALPHAVIM", name_ar="",
                supplier="qaysar", available_quantity=1, price=9.0,
                score=20.0, rejection_reason="", orderable=True,
                matching_source="excel-target",
                matching_source_label="qaysar@qaysar.xlsx",
                target_key="qaysar", excel_target_key="qaysar",
            ),
        ]
        groups = _group_options_by_source(options)
        store = Mock()
        radio_calls = []

        def capture_radio(*args, **kwargs):
            radio_calls.append(kwargs)
            return 0

        with patch.object(page, "st") as streamlit:
            streamlit.session_state = {}
            streamlit.columns.return_value = (nullcontext(), nullcontext())
            streamlit.radio.side_effect = capture_radio
            page._render_multi_source_selection_form(
                Item("ALP", "ALPHAVIM 600 MG 20 TAB", 1),
                groups,
                Path("20260909_1259"),
                store,
                "ALP::ALPHAVIM 600 MG 20 TAB",
            )
            self.assertEqual(len(radio_calls), 2)
            for call in radio_calls:
                streamlit.session_state[call["key"]] = 1
                call["on_change"]()

        saved = [call.args[0] for call in store.upsert.call_args_list]
        self.assertEqual(
            {decision.excel_target_key for decision in saved},
            {"baraka", "qaysar"},
        )

    def test_candidate_display_limit_keeps_each_source_visible(self) -> None:
        def option(source: str, target: str, index: int) -> ReviewCandidateOption:
            return ReviewCandidateOption(
                store_product_id=f"{target}-{index}",
                name_en=f"ALPHAVIM {target} {index}",
                name_ar="",
                supplier=target,
                available_quantity=1,
                price=10.0,
                score=20.0,
                rejection_reason="",
                orderable=True,
                matching_source=source,
                matching_source_label=f"{target}@file.xlsx",
                target_key=target,
                excel_target_key=target,
            )

        options = [
            option("excel-target", "baraka", 1),
            option("excel-target", "baraka", 2),
            option("excel-target", "baraka", 3),
            option("excel-target", "qaysar", 1),
        ]

        visible = _limit_candidates_by_source(options, limit=3)

        self.assertEqual(
            [candidate.excel_target_key for candidate in visible],
            ["baraka", "qaysar", "baraka"],
        )


if __name__ == "__main__":
    unittest.main()
