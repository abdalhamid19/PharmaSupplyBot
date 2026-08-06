"""Unit tests for the Typer→argparse.Namespace shim."""

from __future__ import annotations

from argparse import Namespace

from typer import Context

from src.cli.cli_runner import ns_from_ctx


def _make_ctx(
    *,
    params: dict | None = None,
    obj: dict | None = None,
) -> Context:
    """Construct a bare Typer Context without invoking its constructor.

    Typer's ``Context.__init__`` requires a real ``Command`` instance;
    our ``ns_from_ctx`` only reads ``ctx.params`` and ``ctx.obj``, so
    we can attach those attributes directly via ``__new__`` for testing.
    """
    ctx = Context.__new__(Context)
    ctx.params = params
    ctx.obj = obj
    return ctx


def test_ns_from_ctx_promotes_top_level_options() -> None:
    ctx = _make_ctx(
        params={"excel": "data.xlsx", "profile": "wardany"},
        obj={"quiet": True, "log_level": "DEBUG", "json_logs": False},
    )

    ns = ns_from_ctx(ctx, cmd="order")

    assert isinstance(ns, Namespace)
    assert ns.cmd == "order"
    assert ns.excel == "data.xlsx"
    assert ns.profile == "wardany"
    assert ns.quiet is True
    assert ns.log_level == "DEBUG"
    assert ns.json_logs is False


def test_ns_from_ctx_handles_missing_obj() -> None:
    ctx = _make_ctx(params={"profile": "default"}, obj=None)

    ns = ns_from_ctx(ctx, cmd="auth")

    assert ns.cmd == "auth"
    assert ns.profile == "default"
    assert ns.quiet is False  # default
    assert ns.log_level == "INFO"  # default
    assert ns.json_logs is False


def test_ns_from_ctx_empty_params_still_attaches_cmd() -> None:
    ctx = _make_ctx(params={}, obj=None)

    ns = ns_from_ctx(ctx, cmd="auth")

    assert ns.cmd == "auth"
    assert isinstance(ns, Namespace)


def test_ns_from_ctx_preserves_format_flag() -> None:
    ctx = _make_ctx(params={"excel": "data.xlsx", "format": "json"}, obj=None)

    ns = ns_from_ctx(ctx, cmd="order")

    assert ns.format == "json"


def test_ns_from_ctx_none_params_safe() -> None:
    ctx = _make_ctx(params=None, obj=None)

    ns = ns_from_ctx(ctx, cmd="auth")

    # When params is None, only the global attrs + cmd are set; no per-subcommand
    # attrs leak into the namespace. Handlers read getattr(args, "foo") safely.
    assert ns.cmd == "auth"
    assert not hasattr(ns, "profile") or ns.profile is None


def test_ns_from_ctx_promotes_rich_logs_flag() -> None:
    ctx = _make_ctx(
        params={"profile": "default"},
        obj={"quiet": False, "rich_logs": True, "json_logs": False},
    )

    ns = ns_from_ctx(ctx, cmd="auth")

    assert ns.rich_logs is True
