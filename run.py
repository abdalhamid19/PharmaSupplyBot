from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.config import load_config
from src.excel import load_items_from_excel
from src.tawreed import TawreedBot


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    p.add_argument("--profile", default=None, help="Profile key from config.yaml (e.g. wardany)")
    p.add_argument("--all-profiles", action="store_true", help="Run for all profiles in config.yaml")


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(prog="PharmaSupplyBot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_auth = sub.add_parser("auth", help="Manual login once, save session state")
    _add_common_args(p_auth)
    p_auth.add_argument(
        "--wait-seconds",
        type=int,
        default=600,
        help="How long to keep browser open waiting for login detection",
    )

    p_order = sub.add_parser("order", help="Create orders from Excel (no human interaction)")
    _add_common_args(p_order)
    p_order.add_argument("--excel", required=True, help="Path to Excel file in input/")
    p_order.add_argument("--limit", type=int, default=0, help="Limit number of items (0 = no limit)")

    args = parser.parse_args()

    config_path = Path(args.config)
    cfg = load_config(config_path)

    profiles = cfg.profiles_to_run(profile=args.profile, all_profiles=args.all_profiles)

    state_dir = Path("state")
    state_dir.mkdir(parents=True, exist_ok=True)

    if args.cmd == "auth":
        for profile_key, profile in profiles:
            bot = TawreedBot(cfg=cfg, profile_key=profile_key, profile=profile, state_path=state_dir / f"{profile_key}.json")
            bot.auth_interactive(wait_seconds=int(args.wait_seconds))
        return 0

    if args.cmd == "order":
        excel_path = Path(args.excel)
        items = load_items_from_excel(excel_path, cfg.excel, limit=args.limit)
        if not items:
            print("No items found from Excel (after filtering).")
            return 0

        for profile_key, profile in profiles:
            state_path = state_dir / f"{profile_key}.json"
            if not state_path.exists():
                raise SystemExit(
                    f"Missing saved session state for profile '{profile_key}'. "
                    f"Run: py run.py auth --profile {profile_key}"
                )

            bot = TawreedBot(cfg=cfg, profile_key=profile_key, profile=profile, state_path=state_path)
            bot.place_order_from_items(items)
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())

