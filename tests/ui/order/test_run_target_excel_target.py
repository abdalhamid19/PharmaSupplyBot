"""Tests for the Streamlit Run Order form fields and command builder."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.core.config.config_models import AppConfig
from src.ui.fields.streamlit_profile_fields import (
    OrderRunFields,
    profile_run_fields,
    profile_run_fields_with_workers,
)
from src.ui.order.streamlit_order_command import (
    _excel_target_path_overrides,
    _legacy_target_args,
    _order_target_args,
    order_command,
)
from src.ui.order.streamlit_order_form import (
    selected_excel_targets,
    target_profile_keys,
)


def _make_app_config(profiles=("wardany",), excel_targets=("alnasr",)) -> SimpleNamespace:
    """Build a simple app_config stand-in covering both profiles and targets."""
    profile_dict = {
        key: SimpleNamespace(display_name=key.title()) for key in profiles
    }
    target_dict = {
        key: SimpleNamespace(
            name_col="صنف",
            price_col="سعر",
            discount_col="الخصم",
            enabled=True,
        )
        for key in excel_targets
    }

    def _enabled():
        return {k: v for k, v in target_dict.items() if v.enabled}

    return SimpleNamespace(
        profiles=profile_dict,
        excel_targets=target_dict,
        enabled_excel_targets=_enabled,
        runtime=SimpleNamespace(item_workers=1),
    )


class StreamlitRunTargetTests(unittest.TestCase):
    """Tests covering the new checkbox + excel-target wire-up."""

    def test_order_run_fields_has_selected_targets(self) -> None:
        """The named tuple must include ``selected_targets``."""
        names = OrderRunFields._fields
        self.assertIn("selected_targets", names)
        self.assertIn("profile_mode", names)

    def test_legacy_profile_mode_routes_to_single_profile(self) -> None:
        """Old callers using ``profile_mode == 'Single profile'`` keep working."""
        args = _legacy_target_args(
            {
                "profile_mode": "Single profile",
                "profile_key": "wardany",
            }
        )
        self.assertEqual(args, ["--profile", "wardany"])

    def test_legacy_all_profiles_routes_to_all_flag(self) -> None:
        """``profile_mode == 'All profiles'`` still emits ``--all-profiles``."""
        args = _legacy_target_args({"profile_mode": "All profiles"})
        self.assertEqual(args, ["--all-profiles"])

    def test_target_args_with_only_excel_target(self) -> None:
        """A selection of only Excel targets must emit ``--excel-target``."""
        args = _order_target_args(
            {"selected_targets": ("excel-target:alnasr",), "_config_path": "x"}
        )
        self.assertEqual(args, ["--excel-target", "alnasr"])

    def test_target_args_with_only_tawreed_profile(self) -> None:
        """A single Tawreed profile among many must emit ``--profile``."""
        with patch(
            "src.ui.order.streamlit_order_command._configured_profiles",
            return_value=["wardany", "other"],
        ):
            args = _order_target_args(
                {
                    "selected_targets": ("profile:wardany",),
                    "_config_path": "x",
                }
            )
        self.assertEqual(args, ["--profile", "wardany"])

    def test_target_args_with_all_profiles_selected(self) -> None:
        """Selecting every configured profile must emit ``--all-profiles``."""
        with patch(
            "src.ui.order.streamlit_order_command._configured_profiles",
            return_value=["wardany"],
        ):
            args = _order_target_args(
                {
                    "selected_targets": ("profile:wardany",),
                    "_config_path": "x",
                }
            )
        self.assertEqual(args, ["--all-profiles"])

    def test_target_args_with_both_kinds(self) -> None:
        """Mixed selections must emit both flags in the same command."""
        with patch(
            "src.ui.order.streamlit_order_command._configured_profiles",
            return_value=["wardany", "other"],
        ):
            args = _order_target_args(
                {
                    "selected_targets": (
                        "profile:wardany",
                        "excel-target:alnasr",
                    ),
                    "_config_path": "x",
                }
            )
        self.assertEqual(
            args, ["--profile", "wardany", "--excel-target", "alnasr"]
        )

    def test_target_args_with_multiple_excel_targets(self) -> None:
        """Multiple Excel targets fan out to repeated flags + ``--all-excel-targets``."""
        args = _order_target_args(
            {
                "selected_targets": (
                    "excel-target:alnasr",
                    "excel-target:bakkah",
                ),
                "_config_path": "x",
            }
        )
        self.assertIn("--all-excel-targets", args)
        self.assertIn("--excel-target", args)
        self.assertIn("alnasr", args)
        self.assertIn("bakkah", args)

    def test_target_profile_keys_extracts_profiles(self) -> None:
        """``target_profile_keys`` filters selected profile tokens."""
        form_values = {"selected_targets": ("profile:wardany", "excel-target:alnasr")}
        self.assertEqual(target_profile_keys(SimpleNamespace(profiles={}), form_values), ["wardany"])

    def test_selected_excel_targets_extracts_keys(self) -> None:
        """``selected_excel_targets`` only returns Excel target keys."""
        form_values = {
            "selected_targets": (
                "profile:wardany",
                "excel-target:alnasr",
                "excel-target:bakkah",
            )
        }
        self.assertEqual(selected_excel_targets(form_values), ["alnasr", "bakkah"])


class StreamlitRunTargetSmokeTests(unittest.TestCase):
    """Smoke-test that the widget builder does not raise on minimal config."""

    def test_profile_run_fields_returns_named_tuple(self) -> None:
        """The widget builder must return the OrderRunFields tuple."""
        from src.ui.fields.streamlit_profile_fields import (
            profile_run_fields as public_profile_run_fields,
        )
        fields, item_workers = profile_run_fields_with_workers(_make_app_config())
        self.assertIsInstance(fields, OrderRunFields)
        self.assertIsInstance(item_workers, int)


class StreamlitExcelTargetUploadTests(unittest.TestCase):
    """Cover the upload + existing-file modes for Excel targets."""

    def test_existing_file_emits_path_override(self) -> None:
        """``Existing file`` mode emits ``--excel-target-path key=value``."""
        overrides = _excel_target_path_overrides(
            form_values={
                "excel_target_uploads": {
                    "alnasr": {
                        "mode": "Existing file",
                        "paths": ["data/input/excel target/alnasr.xlsx"],
                        "upload": None,
                    }
                }
            },
            excel_target_keys=["alnasr"],
        )
        self.assertEqual(
            overrides,
            ["--excel-target-path", "alnasr=data/input/excel target/alnasr.xlsx"],
        )

    def test_existing_file_multiselect_emits_path_per_file(self) -> None:
        """Several files in the multiselect must fan out to repeated flags."""
        overrides = _excel_target_path_overrides(
            form_values={
                "excel_target_uploads": {
                    "alnasr": {
                        "mode": "Existing file",
                        "paths": [
                            "data/input/excel target/alnasr.xlsx",
                            "data/input/excel target/alnasr_alt.xlsx",
                        ],
                        "upload": None,
                    }
                }
            },
            excel_target_keys=["alnasr"],
        )
        self.assertEqual(
            overrides,
            [
                "--excel-target-path",
                "alnasr=data/input/excel target/alnasr.xlsx",
                "--excel-target-path",
                "alnasr=data/input/excel target/alnasr_alt.xlsx",
            ],
        )

    def test_uploaded_file_persists_to_artifacts(self) -> None:
        """``Upload file`` mode persists the bytes under artifacts/uploaded-excel-targets."""
        upload = SimpleNamespace(name="alnasr.xlsx", getvalue=lambda: b"fake-bytes")
        with TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            with patch(
                "src.ui.streamlit_uploads.ARTIFACTS_DIR",
                artifacts_dir,
            ):
                overrides = _excel_target_path_overrides(
                    form_values={
                        "excel_target_uploads": {
                            "alnasr": {
                                "mode": "Upload file",
                                "paths": [],
                                "upload": upload,
                            }
                        }
                    },
                    excel_target_keys=["alnasr"],
                )
                self.assertEqual(len(overrides), 2)
                self.assertEqual(overrides[0], "--excel-target-path")
                path_arg = overrides[1]
                self.assertTrue(path_arg.startswith("alnasr="))
                persisted_path = Path(path_arg.split("=", 1)[1])
                self.assertTrue(persisted_path.exists(), f"missing {persisted_path}")
                self.assertEqual(persisted_path.read_bytes(), b"fake-bytes")

    def test_order_command_emits_excel_target_path_override(self) -> None:
        """End-to-end: ``order_command`` should emit ``--excel-target-path``."""
        upload = SimpleNamespace(name="alnasr.xlsx", getvalue=lambda: b"more-bytes")
        with TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            with patch(
                "src.ui.streamlit_uploads.ARTIFACTS_DIR",
                artifacts_dir,
            ):
                command = order_command(
                    Path("config.yaml"),
                    {
                        "limit": 5,
                        "profile_mode": "Excel targets only",
                        "selected_targets": ("excel-target:alnasr",),
                        "profile_key": "",
                        "debug_browser": False,
                        "resume": False,
                        "match_only": True,
                        "execution_mode": "api",
                        "highest_discount": False,
                        "min_discount_percent": 0,
                        "item_workers": 1,
                        "prevented_items_excel": "data/input/prevented_items/drugprevented.xlsx",
                        "excel_target_uploads": {
                            "alnasr": {
                                "mode": "Upload file",
                                "paths": [],
                                "upload": upload,
                            }
                        },
                    },
                    Path("data/input/order_items/test_new_feature.xlsx"),
                )
        self.assertIn("--excel-target", command)
        idx = command.index("--excel-target")
        self.assertEqual(command[idx + 1], "alnasr")
        self.assertIn("--excel-target-path", command)
        idx = command.index("--excel-target-path")
        path_arg = command[idx + 1]
        self.assertTrue(path_arg.startswith("alnasr="))


class ExcelTargetConfigDisplayNameTests(unittest.TestCase):
    """``display_name`` is kept as optional data (YAML compat) but is no longer
    surfaced in the GUI. The checkbox label is always ``📊 Excel target (<key>)``
    and the source panel header is just the key."""

    def test_excel_target_config_supports_display_name(self) -> None:
        from src.core.config.config_models import ExcelTargetConfig

        cfg = ExcelTargetConfig(
            name_col="صنف",
            price_col="سعر",
            discount_col="الخصم",
            display_name="Alnasr Pharmacy",
        )
        self.assertEqual(cfg.display_name, "Alnasr Pharmacy")

    def test_excel_target_config_display_name_defaults_to_empty(self) -> None:
        from src.core.config.config_models import ExcelTargetConfig

        cfg = ExcelTargetConfig(name_col="صنف", price_col="سعر", discount_col="الخصم")
        self.assertEqual(cfg.display_name, "")

    def test_build_excel_target_reads_display_name(self) -> None:
        from src.core.config.config_factory import build_excel_target

        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
                "display_name": "صيدلية النصر",
            }
        )
        self.assertEqual(cfg.display_name, "صيدلية النصر")


class ExcelTargetCheckboxWidgetTests(unittest.TestCase):
    """Cover the checkbox-group redesign of the target picker."""

    FIXTURE = Path(__file__).resolve().parent / "order_tab_fixture.py"

    def test_excel_target_checkbox_appears_even_when_unticked(self) -> None:
        """The Excel-target checkbox is visible without any user action."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.session_state["excel_target_selected_targets"] = ()
        at.run()

        labels = [str(c.label) for c in at.main.checkbox]
        self.assertTrue(
            any("Excel target" in label and "alnasr" in label for label in labels),
            f"alnasr checkbox must be visible by default; got {labels}",
        )

    def test_ticking_alnasr_renders_source_radio(self) -> None:
        """Ticking the alnasr checkbox must render the source radio panel."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.session_state["excel_target_selected_targets"] = ()
        at.run()

        alnasr_box = next(
            (c for c in at.main.checkbox if c.label and "alnasr" in str(c.label)),
            None,
        )
        self.assertIsNotNone(alnasr_box)
        alnasr_box.set_value(True).run()

        source_radio = next(
            (r for r in at.main.radio if r.label == "Source"), None
        )
        self.assertIsNotNone(source_radio)
        self.assertEqual(
            [str(o) for o in source_radio.options],
            ["Existing file", "Upload file"],
        )

    def test_upload_file_mode_renders_file_uploader(self) -> None:
        """Upload-file mode must render a file uploader widget."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.session_state["excel_target_selected_targets"] = ()
        at.run()

        alnasr_box = next(
            (c for c in at.main.checkbox if c.label and "alnasr" in str(c.label)),
            None,
        )
        self.assertIsNotNone(alnasr_box)
        alnasr_box.set_value(True).run()

        source_radio = next(
            (r for r in at.main.radio if r.label == "Source"), None
        )
        self.assertIsNotNone(source_radio)
        source_radio.set_value("Upload file").run()

        uploaders = list(at.main.file_uploader)
        self.assertTrue(
            any("Upload catalog" in str(u.label) for u in uploaders),
            f"upload widget missing; got {[u.label for u in uploaders]}",
        )

    def test_existing_file_renders_multiselect_and_select_all(self) -> None:
        """Existing file mode must render a multiselect + Select all toggle."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.session_state["excel_target_selected_targets"] = ()
        at.run()

        alnasr_box = next(
            (c for c in at.main.checkbox if c.label and "alnasr" in str(c.label)),
            None,
        )
        self.assertIsNotNone(alnasr_box)
        alnasr_box.set_value(True).run()

        select_all = next(
            (c for c in at.main.checkbox if c.label == "Select all"), None
        )
        self.assertIsNotNone(select_all, "Select all toggle must be visible")

        multi = next(
            (m for m in at.main.multiselect if m.label == "Catalog files"), None
        )
        self.assertIsNotNone(multi, "Catalog files multiselect must be visible")

    def test_add_excel_target_button_is_visible(self) -> None:
        """The `+ Add Excel target` button is rendered for the operator."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.run()

        add_button = next(
            (
                b
                for b in at.main.button
                if b.label and "Add Excel target" in str(b.label)
            ),
            None,
        )
        self.assertIsNotNone(add_button, "Add Excel target button must be visible")


class ExcelTargetManagerWidgetTests(unittest.TestCase):
    """The trash button shows up only for user-added targets."""

    FIXTURE = Path(__file__).resolve().parent / "order_tab_fixture.py"

    def test_trash_button_hidden_for_hard_coded_target(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.run()
        trash_buttons = [
            b for b in at.main.button if b.label and "🗑" in str(b.label)
        ]
        self.assertEqual(
            trash_buttons,
            [],
            "alnasr is hard-coded in the fixture; no trash button expected",
        )

    def test_trash_button_visible_for_user_added_target(self) -> None:
        """When the config marks a target as user-added, a trash button appears."""
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        with patch(
            "src.ui.fields.streamlit_excel_target_manager_widgets.user_added_targets",
            return_value=["alnasr"],
        ):
            at.run()
        trash_buttons = [
            b for b in at.main.button if b.label and "🗑" in str(b.label)
        ]
        self.assertTrue(
            any("alnasr" in b.key for b in trash_buttons),
            f"trash button for alnasr expected; got {[b.key for b in trash_buttons]}",
        )

    def test_trash_sets_pending_flag(self) -> None:
        """Pressing 🗑 sets the pending flag the dialog body uses to dispatch."""
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        with patch(
            "src.ui.fields.streamlit_excel_target_manager_widgets.user_added_targets",
            return_value=["alnasr"],
        ):
            at.run()

        trash = next(
            (
                b
                for b in at.main.button
                if b.key and "excel_target_remove_alnasr" in b.key
            ),
            None,
        )
        self.assertIsNotNone(trash, "trash button must exist for alnasr")
        trash.click()
        at.run()
        self.assertIn(
            "excel_target_remove_pending",
            at.session_state,
            "remove_pending flag must be set after trash click",
        )
        self.assertEqual(
            at.session_state["excel_target_remove_pending"],
            "alnasr",
        )

    def test_edit_button_is_visible_for_every_target(self) -> None:
        """An ✏ Edit button must be rendered next to every Excel target."""
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        with patch(
            "src.ui.fields.streamlit_excel_target_manager_widgets.user_added_targets",
            return_value=["alnasr"],
        ):
            at.run()
        edit_buttons = [
            b for b in at.main.button if b.key and "excel_target_edit_alnasr" in b.key
        ]
        self.assertEqual(
            len(edit_buttons), 1, f"expected one edit button, got {[b.key for b in edit_buttons]}"
        )

    def test_edit_button_sets_pending_flag(self) -> None:
        """Pressing ✏ Edit sets the edit_pending flag the dialog body uses."""
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        with patch(
            "src.ui.fields.streamlit_excel_target_manager_widgets.user_added_targets",
            return_value=["alnasr"],
        ):
            at.run()

        edit = next(
            (
                b
                for b in at.main.button
                if b.key and "excel_target_edit_alnasr" in b.key
            ),
            None,
        )
        self.assertIsNotNone(edit, "edit button must exist for alnasr")
        edit.click()
        at.run()
        self.assertIn(
            "excel_target_edit_pending",
            at.session_state,
            "edit_pending flag must be set after ✏ click",
        )
        self.assertEqual(
            at.session_state["excel_target_edit_pending"],
            "alnasr",
        )

    def test_excel_source_upload_renders_file_uploader_reactively(self) -> None:
        """Toggling the order Excel source to Upload file must show the uploader."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self.FIXTURE), default_timeout=30)
        at.run()

        # Initially: "Existing file" is selected — no uploader for the order Excel.
        initial_uploaders = [
            u for u in at.main.file_uploader if "Upload Excel" in str(u.label)
        ]
        self.assertEqual(
            initial_uploaders, [],
            "Upload Excel should be hidden until the operator picks Upload file",
        )

        # Flip the order Excel source radio to "Upload file".
        excel_source = next(
            (r for r in at.main.radio if r.label == "Excel source"), None
        )
        self.assertIsNotNone(excel_source)
        excel_source.set_value("Upload file").run()

        # The uploader must appear on the SAME rerun — no Run Order click required.
        uploaders = [
            u for u in at.main.file_uploader if "Upload Excel" in str(u.label)
        ]
        self.assertTrue(
            uploaders,
            f"Upload Excel uploader did not appear reactively; got {[u.label for u in at.main.file_uploader]}",
        )


if __name__ == "__main__":
    unittest.main()