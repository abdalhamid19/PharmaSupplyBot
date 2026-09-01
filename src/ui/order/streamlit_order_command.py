"""Order command building helpers for Streamlit."""

from __future__ import annotations

from pathlib import Path


# ============================================================================
# Command building
# ============================================================================


def order_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return the CLI command arguments for one order run."""
    command = _order_base_command(config_path, excel_path, form_values)
    command.extend(_order_target_args(form_values))
    command.extend(_order_debug_args(form_values))
    command.extend(_order_execution_args(form_values))
    command.extend(_order_worker_args(form_values))
    command.extend(_order_discount_args(form_values))
    command.extend(_order_item_range_args(form_values))
    command.extend(_matching_risk_command_args(form_values))
    return command


def _order_base_command(
    config_path: Path, excel_path: Path, form_values: dict[str, object]
) -> list[str]:
    """Return the base order command with config and excel."""
    command = ["order", "--config", str(config_path), "--excel", str(excel_path)]
    command.extend(["--limit", str(form_values["limit"])])
    return command


def _order_target_args(form_values: dict[str, object]) -> list[str]:
    """Return CLI arguments describing Tawreed profiles and Excel targets.

    Picks one of ``--profile``, ``--all-profiles``, ``--excel-target`` or
    ``--all-excel-targets`` depending on what the operator selected in the
    Run target multiselect. Multi-target selections fan out to repeated
    ``--excel-target`` flags plus ``--all-profiles`` when the operator asked
    for every Tawreed profile in addition to Excel targets.
    """
    selected_targets = list(form_values.get("selected_targets") or ())
    if not selected_targets:
        return _legacy_target_args(form_values)

    profile_keys = [
        token.split(":", 1)[1]
        for token in selected_targets
        if isinstance(token, str) and token.startswith("profile:")
    ]
    excel_target_keys = [
        token.split(":", 1)[1]
        for token in selected_targets
        if isinstance(token, str) and token.startswith("excel-target:")
    ]

    args: list[str] = []
    if profile_keys:
        all_profiles = len(profile_keys) == len(_configured_profiles(form_values))
        if all_profiles:
            args.append("--all-profiles")
        else:
            args.extend(["--profile", profile_keys[0]])
    if excel_target_keys:
        if len(excel_target_keys) > 1:
            args.append("--all-excel-targets")
            for key in excel_target_keys:
                args.extend(["--excel-target", str(key)])
        else:
            args.extend(["--excel-target", excel_target_keys[0]])
    args.extend(_excel_target_path_overrides(form_values, excel_target_keys))
    return args


def _excel_target_path_overrides(
    form_values: dict[str, object], excel_target_keys: list[str]
) -> list[str]:
    """Emit ``--excel-target-path key=value`` for each non-default upload."""
    uploads = form_values.get("excel_target_uploads") or {}
    if not isinstance(uploads, dict) or not uploads:
        return []
    overrides: list[tuple[str, str]] = []
    for target_key in excel_target_keys:
        entry = uploads.get(target_key) or {}
        mode = str(entry.get("mode") or "Configured")
        if mode == "Configured":
            continue
        path = _resolve_excel_target_upload_path(target_key, entry)
        if path:
            overrides.append((target_key, str(path)))
    if not overrides:
        return []
    args: list[str] = []
    for key, path in overrides:
        args.extend(["--excel-target-path", f"{key}={path}"])
    return args


def _resolve_excel_target_upload_path(
    target_key: str, entry: dict[str, object]
) -> str | None:
    """Return the on-disk catalog path for one Excel target upload entry."""
    mode = str(entry.get("mode") or "Configured")
    if mode == "Existing file":
        path = str(entry.get("path") or "").strip()
        return path or None
    if mode == "Upload file":
        from ..streamlit_uploads import uploaded_excel_target_path

        upload = entry.get("upload")
        if upload is None:
            return None
        persisted = uploaded_excel_target_path(target_key, upload)
        return str(persisted)
    return None


def _legacy_target_args(form_values: dict[str, object]) -> list[str]:
    """Translate the legacy ``profile_mode``/``profile_key`` form values.

    Older callers (and a number of existing tests) submit form values
    built before the multiselect. They pass ``profile_mode`` of either
    ``Single profile`` or ``All profiles`` along with a ``profile_key``;
    we honour that shape verbatim.
    """
    if form_values.get("profile_mode") == "All profiles":
        return ["--all-profiles"]
    profile_key = str(form_values.get("profile_key") or "")
    if profile_key:
        return ["--profile", profile_key]
    return []


def _configured_profiles(form_values: dict[str, object]) -> list[str]:
    """Return the list of profiles known to the Streamlit session."""
    config_path = str(form_values.get("_config_path") or "state/config.yaml")
    try:
        from src.core.config.config import load_config
    except Exception:
        return []
    try:
        app_config = load_config(Path(config_path))
    except Exception:
        return []
    return list(app_config.profiles.keys())


def _order_debug_args(form_values: dict[str, object]) -> list[str]:
    """Return debug and mode CLI arguments."""
    args = []
    if form_values["debug_browser"]:
        args.append("--debug-browser")
    if form_values.get("resume"):
        args.append("--resume")
    if form_values.get("match_only"):
        args.append("--match-only")
    return args


def _order_execution_args(form_values: dict[str, object]) -> list[str]:
    """Return execution mode CLI arguments."""
    return ["--execution-mode", _order_execution_mode(form_values)]


def _order_worker_args(form_values: dict[str, object]) -> list[str]:
    """Return item workers CLI arguments."""
    from .streamlit_order_form import _int_form_value
    item_workers = _int_form_value(form_values, "item_workers", 1)
    return ["--item-workers", str(item_workers)]


def _order_discount_args(form_values: dict[str, object]) -> list[str]:
    """Return discount-related CLI arguments."""
    from .streamlit_order_form import _float_form_value
    args = []
    if form_values.get("highest_discount"):
        args.extend(["--warehouse-mode", "max_discount"])
    min_discount = _float_form_value(form_values, "min_discount_percent", 0.0)
    if min_discount > 0:
        args.extend(["--min-discount-percent", f"{min_discount:g}"])
    prevented = str(form_values.get("prevented_items_excel") or "")
    if prevented:
        args.extend(["--prevented-items-excel", prevented])
    return args


def _order_item_range_args(form_values: dict[str, object]) -> list[str]:
    """Return item range (start/end) CLI arguments."""
    from .streamlit_order_form import _int_form_value
    args = []
    start_item = _int_form_value(form_values, "start_item", 1)
    if start_item > 1:
        args.extend(["--start-item", str(start_item)])
    end_item = _int_form_value(form_values, "end_item", 0)
    if end_item > 0:
        args.extend(["--end-item", str(end_item)])
    return args


def _matching_risk_command_args(form_values: dict[str, object]) -> list[str]:
    """Return CLI arguments for safe or aggressive matching policy."""
    return [
        "--matching-risk-policy",
        str(form_values.get("matching_risk_policy") or "safe"),
        "--flagged-match-action",
        str(form_values.get("flagged_match_action") or "manual-review-only"),
    ]


def _order_execution_mode(form_values: dict[str, object]) -> str:
    """Return the fastest safe execution mode for the requested order run."""
    mode = str(form_values.get("execution_mode", "auto") or "auto")
    if form_values.get("match_only") and mode == "auto":
        return "api"
    return mode


__all__ = [
    "order_command",
    "_order_base_command",
    "_order_profile_args",
    "_order_debug_args",
    "_order_execution_args",
    "_order_worker_args",
    "_order_discount_args",
    "_order_item_range_args",
    "_matching_risk_command_args",
    "_order_execution_mode",
]
