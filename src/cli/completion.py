"""Shell tab-completion for the PharmaSupplyBot CLI.

Generates shell-completion scripts for bash, zsh, and fish from the
**same** :func:`build_parser` that powers the runtime CLI. This is
the single source of truth: adding a new subcommand or flag is
picked up here automatically — no second list to maintain.

Quick start for the operator::

    # bash
    eval "$(python run.py --show-completion bash)"

    # zsh
    eval "$(python run.py --show-completion zsh)"

    # fish
    python run.py --show-completion fish | source

Why a dedicated module rather than a vendored argcomplete?
    * Zero new dependency (argcomplete is great but adds install
      weight and an import-time side effect on every CLI run).
    * The CLI has a small, stable surface (5 subcommands × ~30
      flags) — hand-rolled completion is <200 lines, easy to audit.
    * Choices are surfaced for enum-like flags (``--execution-mode``,
      ``--ai-verify-policy``) which the simple ``argcomplete`` would
      also need explicit configuration to discover.

Design notes:
    * Output is a self-contained shell script. No external files,
      no temp dirs, no permissions. ``eval`` is the contract.
    * The completion function queries the **same parser** for
      subcommand names and flag choices, so the script can never
      drift out of sync with the real CLI.
    * We deliberately do **not** complete positional values
      (Excel paths, profile keys) — those are not enumerable, and
      completing them from the filesystem is a slippery slope
      (which dir? which depth?).
"""

from __future__ import annotations

import argparse
import shlex
from typing import Iterable

# Supported shell targets. The error path is reported separately.
SUPPORTED_SHELLS = ("bash", "zsh", "fish")


# ─────────────────────────── Public API ─────────────────────────────


def emit_completion(shell: str) -> str:
    """Return the completion script for ``shell`` (bash | zsh | fish).

    Raises :class:`ValueError` on an unsupported shell name so the
    caller (``run.py``) can convert to a typed ``ValidationError``
    with exit code 5.
    """
    shell = shell.lower().strip()
    if shell not in SUPPORTED_SHELLS:
        raise ValueError(
            f"Unknown shell '{shell}'. Supported: {', '.join(SUPPORTED_SHELLS)}"
        )
    if shell == "bash":
        return _bash_script()
    if shell == "zsh":
        return _zsh_script()
    return _fish_script()


# ─────────────────────────── Parser introspection ───────────────────


def _get_parser() -> argparse.ArgumentParser:
    """Import the parser lazily so completion loading does not pull in
    the whole CLI (Playwright, network, etc.) at ``eval`` time.

    We also avoid running the parser's setup at import by deferring
    until this function is actually called.
    """
    from src.cli.parsers.cli_parser import build_parser

    return build_parser()


def _subcommands(parser: argparse.ArgumentParser) -> list[str]:
    """Return the registered subcommand names (e.g. ``['order', 'auth']``)."""
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and len(choices) > 0:
            return sorted(choices.keys())
    return []


def _flags_for_subcommand(
    parser: argparse.ArgumentParser, sub_name: str
) -> list[argparse.Action]:
    """Return the argparse actions for a specific subcommand, in
    declaration order (which is the order shown in ``--help``).
    """
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and sub_name in choices:
            sub = choices[sub_name]
            # Skip the implicit 'help' action — not useful to complete.
            return [a for a in sub._actions if a.dest != "help"]
    return []


def _flag_tokens(action: argparse.Action) -> list[str]:
    """Return the flag strings a user might type: long + short forms."""
    tokens: list[str] = []
    for opt in action.option_strings:
        tokens.append(opt)
    return tokens


def _choice_values(action: argparse.Action) -> list[str] | None:
    """Return the enum-like choices for an action, or None if it has none."""
    choices = getattr(action, "choices", None)
    if isinstance(choices, (list, tuple)) and all(
        isinstance(c, str) for c in choices
    ):
        return list(choices)
    return None


# ─────────────────────────── bash ───────────────────────────────────


def _bash_script() -> str:
    """Generate a bash completion script.

    Strategy:
      * Register ``_pharmabot_completion`` for the exact command
        name ``python run.py``. Operators who use the ``pharmabot``
        entry point (future) will need to re-eval; documented in
        the script header.
      * Walk the current COMP_WORDS to decide what to complete:
          - no subcommand yet → suggest subcommand names
          - subcommand present + a flag with choices → suggest the choices
          - subcommand present + a partial flag → suggest flag tokens
          - else → suggest all available flag tokens
    """
    parser = _get_parser()
    sub_names = _subcommands(parser)
    # Pre-compute the per-subcommand flag map at script-emit time
    # (the script itself runs in the shell, which can't introspect Python).
    per_sub: dict[str, list[tuple[list[str], list[str] | None]]] = {}
    for sub in sub_names:
        entries: list[tuple[list[str], list[str] | None]] = []
        for action in _flags_for_subcommand(parser, sub):
            tokens = _flag_tokens(action)
            choices = _choice_values(action)
            if tokens and choices:
                entries.append((tokens, choices))
            elif tokens:
                entries.append((tokens, None))
        per_sub[sub] = entries

    # Top-level (non-subcommand) flags, if any. In our case the
    # main parser has only --log-level/--quiet/--json-logs, but we
    # surface them anyway so the script is generic.
    top_level_flags: list[tuple[list[str], list[str] | None]] = []
    for action in parser._actions:
        if action.dest == "cmd":
            continue  # subparsers action
        tokens = _flag_tokens(action)
        choices = _choice_values(action)
        if tokens:
            top_level_flags.append((tokens, choices))

    return _BASH_TEMPLATE.render(
        sub_names=sub_names,
        per_sub=per_sub,
        top_level_flags=top_level_flags,
    )


# ─────────────────────────── zsh ────────────────────────────────────


def _zsh_script() -> str:
    parser = _get_parser()
    sub_names = _subcommands(parser)
    per_sub: dict[str, list[tuple[list[str], list[str] | None]]] = {}
    for sub in sub_names:
        entries: list[tuple[list[str], list[str] | None]] = []
        for action in _flags_for_subcommand(parser, sub):
            tokens = _flag_tokens(action)
            choices = _choice_values(action)
            if tokens and choices:
                entries.append((tokens, choices))
            elif tokens:
                entries.append((tokens, None))
        per_sub[sub] = entries

    return _ZSH_TEMPLATE.render(
        sub_names=sub_names,
        per_sub=per_sub,
    )


# ─────────────────────────── fish ───────────────────────────────────


def _fish_script() -> str:
    parser = _get_parser()
    sub_names = _subcommands(parser)
    per_sub: dict[str, list[tuple[list[str], list[str] | None]]] = {}
    for sub in sub_names:
        entries: list[tuple[list[str], list[str] | None]] = []
        for action in _flags_for_subcommand(parser, sub):
            tokens = _flag_tokens(action)
            choices = _choice_values(action)
            if tokens and choices:
                entries.append((tokens, choices))
            elif tokens:
                entries.append((tokens, None))
        per_sub[sub] = entries

    return _FISH_TEMPLATE.render(
        sub_names=sub_names,
        per_sub=per_sub,
    )


# ─────────────────────────── Templates ──────────────────────────────
# Plain f-strings (not jinja2) — keeps the import cost zero for an
# operator who just wants to ``eval`` something small.

_BASH_TEMPLATE_HEADER = """\
# bash completion for the PharmaSupplyBot CLI
# -----------------------------------------
# Install (one time per shell):
#   eval "$(python run.py --show-completion bash)"
#
# Or persist it in ~/.bashrc.
#
# Notes:
#   * This completes `python run.py ...`. If you install the future
#     `pharmabot` entry point, re-eval with that command name.
#   * The set of subcommands and flags is read from build_parser()
#     at generation time, so a CLI update requires re-eval.

_pharmabot_completion() {
    local cur prev words cword
    _init_completion || return

    # The user-typed tokens; COMP_WORDS[0]=python, [1]=run.py.
    # We look at offset 2+ for the subcommand.
    local offset=2
    local cmd=""
    local i
    for ((i = offset; i < cword; i++)); do
        local w="${words[i]}"
        if [[ "$w" != -* && -n "$w" ]]; then
            cmd="$w"
            break
        fi
    done
"""

_BASH_TEMPLATE_FOOTER = """\
} && \\
complete -F _pharmabot_completion python
"""


def _render_bash_subcommand_block(
    sub: str, entries: list[tuple[list[str], list[str] | None]]
) -> str:
    """Emit the bash branch that handles one subcommand's completions."""
    if not entries:
        return ""
    flag_tokens: list[str] = []
    # Map from flag token → list of valid choices (empty list means no choices)
    choice_groups: list[tuple[str, list[str]]] = []
    for tokens, choices in entries:
        flag_tokens.extend(tokens)
        if choices:
            for t in tokens:
                choice_groups.append((t, list(choices)))
    flag_str = " ".join(shlex.quote(t) for t in flag_tokens)
    if choice_groups:
        # Two completion paths for enum flags:
        #   --flag <TAB>          → previous token is the flag, cur is empty
        #   --flag=<partial>      → cur contains '='; we strip the prefix
        # We unify them via "what the user's typed-after-flag is",
        # which is either $cur (when $cur starts with the flag + '=')
        # or empty (when the previous token is the flag and cur is blank).
        choice_cases = []
        for t, choices in choice_groups:
            values = " ".join(shlex.quote(c) for c in choices)
            choice_cases.append(
                f'        if [[ "$prev" == "{t}" || "${{cur%%=*}}" == "{t}" ]]; then\n'
                f'            local stripped="${{cur#*=}}"\n'
                f'            COMPREPLY=($(compgen -W "{values}" -- "$stripped"))\n'
                f'            return 0\n'
                f'        fi\n'
            )
        choice_block = "\n".join(choice_cases)
    else:
        choice_block = ""
    return f"""\
    if [[ "$cmd" == "{sub}" ]]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=($(compgen -W "{flag_str}" -- "$cur"))
{choice_block}
            return 0
        fi
        return 0
    fi
"""


def _bash_script_impl(parser: argparse.ArgumentParser) -> str:
    """Render the bash script. Exposed for unit testing only."""
    sub_names = _subcommands(parser)
    per_sub: dict[str, list[tuple[list[str], list[str] | None]]] = {}
    for sub in sub_names:
        entries: list[tuple[list[str], list[str] | None]] = []
        for action in _flags_for_subcommand(parser, sub):
            tokens = _flag_tokens(action)
            choices = _choice_values(action)
            if tokens and choices:
                entries.append((tokens, choices))
            elif tokens:
                entries.append((tokens, None))
        per_sub[sub] = entries

    blocks = [
        _BASH_TEMPLATE_HEADER,
        '    if [[ -z "$cmd" ]]; then',
        '        COMPREPLY=($(compgen -W "' + " ".join(shlex.quote(s) for s in sub_names) + '" -- "$cur"))',
        '        return 0',
        '    fi',
    ]
    for sub in sub_names:
        blocks.append(_render_bash_subcommand_block(sub, per_sub[sub]))
    blocks.append(_BASH_TEMPLATE_FOOTER)
    return "\n".join(blocks)


# Replace the simpler template with the real renderer.
def _bash_script() -> str:
    return _bash_script_impl(_get_parser())


# ─────────────────────────── zsh template ───────────────────────────


_ZSH_TEMPLATE = """\
# zsh completion for the PharmaSupplyBot CLI
# -----------------------------------------
# Install (one time per shell):
#   eval "$(python run.py --show-completion zsh)"
# Or save to a file in $fpath and run `compinit`.
#
# Note: completion matches the literal command `python run.py ...`.

#compdef python
_pharmabot_completion() {{
    local -a subcommands
    subcommands=(
{sub_names_block}
    )

    local -a flags
    flags=(
{flags_block}
    )

    _arguments -s \\
        '1: :->cmd' \\
        '*:: :->args'

    case $state in
        cmd)
            _describe 'command' subcommands
            ;;
        args)
            # After the subcommand, complete flag tokens.
            _describe 'flag' flags
            ;;
    esac
}}
compdef _pharmabot_completion python
"""


def _zsh_script_impl(parser: argparse.ArgumentParser) -> str:
    """Render the zsh script. Exposed for unit testing only."""
    sub_names = _subcommands(parser)
    per_sub: dict[str, list[tuple[list[str], list[str] | None]]] = {}
    for sub in sub_names:
        entries: list[tuple[list[str], list[str] | None]] = []
        for action in _flags_for_subcommand(parser, sub):
            tokens = _flag_tokens(action)
            choices = _choice_values(action)
            if tokens and choices:
                entries.append((tokens, choices))
            elif tokens:
                entries.append((tokens, None))
        per_sub[sub] = entries

    sub_names_block = "\n".join(f"        '{s}:subcommand'" for s in sub_names)
    # Aggregate all flags from all subcommands (zsh's _arguments can
    # show them all; deeper filtering requires per-cmd context, which
    # we keep simple for the first cut).
    all_flag_lines: list[str] = []
    for sub in sub_names:
        for tokens, choices in per_sub[sub]:
            for t in tokens:
                if choices:
                    desc = f"[{'|'.join(choices)}]"
                else:
                    desc = ""
                all_flag_lines.append(f"        '{t}{{{desc}}}'")
    flags_block = "\n".join(all_flag_lines) if all_flag_lines else "        '(no flags)'"
    return _ZSH_TEMPLATE.format(
        sub_names_block=sub_names_block,
        flags_block=flags_block,
    )


def _zsh_script() -> str:
    return _zsh_script_impl(_get_parser())


# ─────────────────────────── fish template ──────────────────────────


_FISH_TEMPLATE = """\
# fish completion for the PharmaSupplyBot CLI
# -------------------------------------------
# Install (one time per shell):
#   python run.py --show-completion fish | source
# Or save to ~/.config/fish/completions/python.fish

# Subcommands
{sub_blocks}

# Flags (sparse: all flags, prefixed by -- or -)
{flag_blocks}
"""


def _fish_script_impl(parser: argparse.ArgumentParser) -> str:
    """Render the fish script. Exposed for unit testing only."""
    sub_names = _subcommands(parser)
    per_sub: dict[str, list[tuple[list[str], list[str] | None]]] = {}
    for sub in sub_names:
        entries: list[tuple[list[str], list[str] | None]] = []
        for action in _flags_for_subcommand(parser, sub):
            tokens = _flag_tokens(action)
            choices = _choice_values(action)
            if tokens and choices:
                entries.append((tokens, choices))
            elif tokens:
                entries.append((tokens, None))
        per_sub[sub] = entries

    sub_blocks = "\n".join(
        f"complete -c python -n '__fish_use_subcommand' -a '{s}'" for s in sub_names
    )
    flag_lines: list[str] = []
    for sub in sub_names:
        for tokens, choices in per_sub[sub]:
            for t in tokens:
                cond = f"__fish_seen_subcommand_from {sub}"
                if choices:
                    for c in choices:
                        flag_lines.append(
                            f"complete -c python -n '{cond} and __fish_seen_argument {t}' -a '{c}'"
                        )
                else:
                    flag_lines.append(
                        f"complete -c python -n '{cond}' -l '{t.lstrip('-')}'"
                    )
    flag_blocks = "\n".join(flag_lines) if flag_lines else "# (no flags)"
    return _FISH_TEMPLATE.format(
        sub_blocks=sub_blocks,
        flag_blocks=flag_blocks,
    )


def _fish_script() -> str:
    return _fish_script_impl(_get_parser())


# Keep the names referenced in __all__ for tests/importers.
_emit_bash = _bash_script
_emit_zsh = _zsh_script
_emit_fish = _fish_script


__all__ = [
    "SUPPORTED_SHELLS",
    "emit_completion",
    "_subcommands",
    "_flags_for_subcommand",
    "_flag_tokens",
    "_choice_values",
    "_bash_script_impl",
    "_zsh_script_impl",
    "_fish_script_impl",
]
