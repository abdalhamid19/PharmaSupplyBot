"""Playwright automation for product search and Tawreed ordering."""

from __future__ import annotations

from .tawreed_bot_core import TawreedBotCore, _console_safe
from .tawreed_bot_api import TawreedBotApi
from .tawreed_bot_order_ai import TawreedBotOrderAi
from .tawreed_bot_methods import TawreedBotMethods


class TawreedBot(TawreedBotCore, TawreedBotApi, TawreedBotOrderAi, TawreedBotMethods):
    """Coordinate Tawreed authentication, product matching, and order placement."""
    pass


# Import for backward compatibility with tests
from .tawreed_artifacts import dump_artifacts
from .tawreed_dialogs import visible_overlay_diagnostics
from .tawreed_match_only_summary import append_match_only_summary
