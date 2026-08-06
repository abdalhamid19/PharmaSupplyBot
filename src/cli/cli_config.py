"""User-level CLI configuration: ``~/.pharmabotrc`` and ``--preset``.

This module is intentionally small and dependency-light. It supports
two complementary conveniences on top of ``argparse``:

1. **User config file** — a YAML file (``~/.pharmabotrc`` globally,
   ``./.pharmabotrc`` per-project) that supplies *defaults* for any
   flag the operator did not pass on the command line. CLI flags
   always win, so this is purely a "fill the blanks" mechanism.
2. **Presets** — named groups of flags under the top-level ``presets:``
   key. The user selects one with ``--preset <name>``; the preset
   values are merged *under* the CLI args (so anything typed on the
   command line still overrides).

Precedence (highest to lowest)::

    CLI args > --preset > ./.pharmabotrc > ~/.pharmabotrc > built-in defaults

The module never raises on a missing or malformed file. The philosophy
is: "the user's hands must not be forced" — bad config falls back
to argparse's built-in defaults, with a one-line warning logged so
the operator knows their file was ignored.

Why YAML and not TOML/JSON? Because the project's main
``config.example.yaml`` is already YAML, and PyYAML is a transitive
dependency of the project (``python-dotenv`` pulls it in for some
distros, and ``requirements.txt`` lists it explicitly). Zero new
dependencies.
"""

from __future__ import annotations

import logging
import os
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ─────────────────────────── Public constants ───────────────────────────

#: Global user config path (in the operator's home directory).
GLOBAL_CONFIG_PATH = Path.home() / ".pharmabotrc"

#: Project-local override (committed or gitignored as the team prefers).
LOCAL_CONFIG_PATH = Path(".pharmabotrc")


# ─────────────────────────── Load + merge ─────────────────────────────


def load_user_config() -> dict[str, Any]:
    """Load and merge ``~/.pharmabotrc`` with ``./.pharmabotrc``.

    Local (project-level) config wins over global. Missing files are
    not errors. A malformed file logs a warning and returns the
    successfully-parsed layer (or ``{}``).

    Returns a dict with two top-level keys when files are present::

        {
            "default": { "--profile": "wardany", "--config": "state/config.yaml" },
            "presets": {
                "quick-dry-run": { "--match-only": True, "--limit": 20, ... },
                ...
            },
        }
    """
    merged: dict[str, Any] = {"default": {}, "presets": {}}

    # Global first, local overrides
    for path in (GLOBAL_CONFIG_PATH, LOCAL_CONFIG_PATH):
        data = _read_yaml_safe(path)
        if not data:
            continue
        if isinstance(data.get("default"), dict):
            merged["default"].update(data["default"])
        if isinstance(data.get("presets"), dict):
            merged["presets"].update(data["presets"])
        logger.debug("loaded user config from %s", path)

    return merged


def list_presets(config: dict[str, Any] | None = None) -> list[str]:
    """Return the names of all available presets, sorted."""
    if config is None:
        config = load_user_config()
    return sorted((config.get("presets") or {}).keys())


def get_preset(name: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a preset's flag dict, or an empty dict if the name is unknown.

    A missing preset is **not** an error here — the caller (``run.py``)
    is responsible for deciding what to do (warn, list alternatives,
    or hard-fail). This keeps ``get_preset`` testable in isolation.
    """
    if config is None:
        config = load_user_config()
    presets = config.get("presets") or {}
    preset = presets.get(name)
    if not isinstance(preset, dict):
        return {}
    return dict(preset)


# ─────────────────────────── Preset application ────────────────────────


def apply_preset(
    parser: ArgumentParser | None,
    args: Namespace,
    preset_name: str | None,
) -> Namespace:
    """Apply a named preset to ``args`` *underneath* the explicit CLI values.

    Algorithm:
        1. Resolve the preset dict (empty if ``preset_name`` is falsy).
        2. For each ``--flag: value`` in the preset, override ``args``
           *only if* the user did not pass it explicitly on the CLI.

    "Did not pass explicitly" is detected by ``_was_passed()``, which
    uses argparse's ``default`` sentinel: any value that still equals
    the parser's declared default is treated as "not set by the user".
    This is the standard argparse idiom and is reliable for the
    action types used by this CLI (``store_true``, ``store_const``,
    ``store``, ``append``).
    """
    if not preset_name:
        return args

    config = load_user_config()
    preset = get_preset(preset_name, config)
    if not preset:
        available = list_presets(config)
        hint = (
            f"Available presets: {', '.join(available)}"
            if available
            else "No presets defined. Add a 'presets:' section to ~/.pharmabotrc."
        )
        # We raise here so run.py can convert to ValidationError + exit 5
        raise ValueError(f"Unknown preset '{preset_name}'. {hint}")

    logger.info("applying preset: %s", preset_name)
    for flag, value in preset.items():
        if not _was_passed(parser, args, flag):
            setattr(args, _dest_for_flag(flag), value)
            logger.debug("preset %s: %s = %r", preset_name, flag, value)

    return args


# ─────────────────────────── Defaults injection ────────────────────────


def inject_defaults(parser: ArgumentParser | None, args: Namespace) -> Namespace:
    """Fill any unset CLI argument from the user-config ``default`` block.

    This runs *after* ``parse_args()`` and *before* the command
    handler. It must never override a value the user typed on the
    command line — see ``_was_passed`` for the heuristic.
    """
    config = load_user_config()
    defaults = config.get("default") or {}
    if not defaults:
        return args

    logger.debug("injecting %d default(s) from user config", len(defaults))
    for flag, value in defaults.items():
        if not _was_passed(parser, args, flag):
            setattr(args, _dest_for_flag(flag), value)
            logger.debug("default %s = %r", flag, value)

    return args


# ─────────────────────────── Internals ────────────────────────────────


def _read_yaml_safe(path: Path) -> dict[str, Any] | None:
    """Read YAML, returning ``None`` on any failure (logged, not raised)."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError) as exc:
        logger.warning(
            "could not read user config %s: %s (continuing with no override)",
            path,
            exc,
        )
        return None
    if not isinstance(data, dict):
        logger.warning(
            "user config %s is not a YAML mapping (got %s); ignoring",
            path,
            type(data).__name__,
        )
        return None
    return data


def _dest_for_flag(flag: str) -> str:
    """Convert ``--excel`` → ``excel``. Tolerates a single leading dash."""
    return flag.lstrip("-").replace("-", "_")


def _was_passed(
    parser_or_flag: Any,
    args_or_current: Any,
    flag_or_default: str | Any = None,
) -> bool:
    """Return True if the user (or a preset) supplied ``flag`` with a non-default value.

    Three calling conventions are supported:

    * **New (parser-agnostic)**: ``_was_passed(flag: str, current: Any, default: Any)``
      — caller resolves the current value and declared default, helper does the
      equality check. Works with Typer, argparse, or any source of defaults.

    * **Legacy (argparse-only)**: ``_was_passed(parser, args, flag: str)``
      — helper inspects argparse internals to resolve ``current`` + ``default``.

    * **Typer-aware shim**: ``_was_passed(None, args, flag: str)`` — ``parser`` is
      optional. When ``None``, ``args._typer_defaults`` (set by the Typer app's
      ``_collect_defaults``) supplies the declared defaults.

    The legacy + shim forms are kept so existing call sites in ``apply_preset``
    and ``inject_defaults`` (which receive an ``ArgumentParser | None`` and a
    ``Namespace``) keep working unchanged.
    """
    # Legacy argparse path: positional args are (parser, args, flag)
    # (parser can be None for the Typer sidecar path.)
    if (
        (parser_or_flag is None or isinstance(parser_or_flag, ArgumentParser))
        and isinstance(args_or_current, Namespace)
        and isinstance(flag_or_default, str)
    ):
        return _was_passed_argparse(parser_or_flag, args_or_current, flag_or_default)

    # New parser-agnostic path: positional args are (flag, current, default)
    flag = parser_or_flag
    current = args_or_current
    default = flag_or_default
    if isinstance(default, bool):
        return bool(current) and not bool(default)
    return current != default


def _was_passed_argparse(
    parser: ArgumentParser | None, args: Namespace, flag: str
) -> bool:
    """Resolve ``current`` + ``default`` for ``flag`` and delegate to :func:`_was_passed`.

    Two resolver paths:

    1. **Typer sidecar** (preferred when ``parser`` is ``None``): read
       ``args._typer_defaults`` (a ``dict[str, Any]`` snapshot of declared
       Typer parameter defaults).
    2. **argparse introspection** (when a parser is supplied): walk
       ``parser._actions`` and the selected subparser's ``_actions`` to find
       the matching ``Action`` and read its ``.default``.
    """
    import argparse  # local to keep import cost down on hot path

    dest = _dest_for_flag(flag)

    # Typer sidecar: snapshot of declared defaults lives on the namespace.
    typer_defaults = getattr(args, "_typer_defaults", None)
    if isinstance(typer_defaults, dict) and dest in typer_defaults:
        current = getattr(args, dest, None)
        default = typer_defaults[dest]
        return _was_passed(flag, current, default)

    # No argparse parser to introspect (Typer sidecar path with no defaults).
    if parser is None:
        return True  # unknown to Typer sidecar — treat as already-set.

    # Pure argparse introspection.
    action = _find_action_in_selected_subparser(parser, args, dest)
    if action is None:
        # Flag unknown to this parser — treat as already-set so we
        # don't pollute ``args`` with garbage. Caller will see a
        # different error from argparse downstream.
        return True
    current = getattr(args, dest, None)
    default = _action_default(action)
    # For store_true actions, the user passing the flag flips it to True.
    # So if current is True and default is False, the user set it.
    if isinstance(action, argparse._StoreTrueAction):
        return bool(current) and not bool(default)
    return current != default


def _find_action_in_selected_subparser(
    parser: ArgumentParser, args: Namespace, dest: str
):
    """Find the argparse action for ``dest`` on the selected subparser.

    argparse's ``parser._subparsers`` is an ``_ArgumentGroup`` (not a
    list) and exposes the per-subcommand parsers as a ``choices``
    mapping on the subparser action itself. We pull the right one
    via ``getattr(args, 'cmd', None)`` (the dest of the subparser
    action — set by ``add_subparsers(dest='cmd')`` in the main parser).
    """
    # First try the main parser (top-level flags like --profile, --config)
    for action in parser._actions:
        if action.dest == dest:
            return action

    # Then try the selected subparser, if any
    sub = _get_selected_subparser(parser, args)
    if sub is not None:
        for action in sub._actions:
            if action.dest == dest:
                return action
    return None


def _get_selected_subparser(parser: ArgumentParser, args: Namespace):
    """Return the subparser chosen by ``args.cmd``, or None."""
    # The subparsers action is registered on the main parser; its
    # .choices dict maps subcommand name → subparser.
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and len(choices) > 0:
            selected_name = getattr(args, "cmd", None)
            if selected_name and selected_name in choices:
                return choices[selected_name]
    return None


def _action_default(action) -> Any:
    """Return the declared default for an argparse action, normalising ``None``."""
    default = getattr(action, "default", None)
    if default is None:
        # ``store_true`` / ``store_false`` default to False implicitly
        import argparse as _a

        if isinstance(action, _a._StoreTrueAction):
            return False
        if isinstance(action, _a._StoreFalseAction):
            return True
    return default


# ─────────────────────────── Self-check helper ────────────────────────


def describe_sources() -> dict[str, Any]:
    """Diagnostic: report which config files exist and what they'd contribute.

    Used by ``run.py`` for the one-time "loaded config from ..." log
    line on first run, and by tests.
    """
    return {
        "global_path": str(GLOBAL_CONFIG_PATH),
        "global_exists": GLOBAL_CONFIG_PATH.exists(),
        "local_path": str(LOCAL_CONFIG_PATH.resolve())
        if LOCAL_CONFIG_PATH.exists()
        else str(LOCAL_CONFIG_PATH),
        "local_exists": LOCAL_CONFIG_PATH.exists(),
        "config": load_user_config(),
    }


__all__ = [
    "GLOBAL_CONFIG_PATH",
    "LOCAL_CONFIG_PATH",
    "load_user_config",
    "list_presets",
    "get_preset",
    "apply_preset",
    "inject_defaults",
    "describe_sources",
]
