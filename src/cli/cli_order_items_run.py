"""Item running logic for Tawreed ordering."""

from __future__ import annotations

import argparse
from typing import Iterable

from ..core.config.config_models import AppConfig
from ..core.utils.excel import Item
from ..tawreed.tawreed import TawreedBot
from .cli_order_single import run_profile_order, run_profile_match_only
from .cli_order_items import match_only


def run_profile_items(
    app_config: AppConfig,
    profile_key: str,
    bot: TawreedBot,
    items: Iterable[Item],
    args: argparse.Namespace,
) -> None:
    """Run one profile through the requested order mode."""
    if match_only(args):
        run_profile_match_only(app_config.base_url, profile_key, bot, items)
        return
    run_profile_order(app_config.base_url, profile_key, bot, items)
