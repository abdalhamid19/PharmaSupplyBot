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
    _legacy_target_args,
    _order_target_args,
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
            name_col="صنف", price_col="سعر", discount_col="الخصم", enabled=True
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
    """Tests covering the new multiselect + excel-target wire-up."""

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
        with (
            patch("streamlit.multiselect", return_value=["👤 Tawreed profile — Wardany (wardany)"]),
            patch("streamlit.selectbox", return_value="wardany"),
            patch("streamlit.number_input", return_value=1500),
            patch("streamlit.expander") as expander,
            patch("streamlit.checkbox", return_value=False),
            patch("streamlit.selectbox") as sb,
            patch("streamlit.number_input") as ni,
        ):
            # Stub expander to a no-op context manager.
            expander.return_value.__enter__ = lambda self: None
            expander.return_value.__exit__ = lambda self, *args: None
            app_config = _make_app_config()
            fields = profile_run_fields(app_config)
            self.assertIsInstance(fields, OrderRunFields)
            self.assertEqual(fields.profile_key, "wardany")


if __name__ == "__main__":
    unittest.main()