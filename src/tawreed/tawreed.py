"""Playwright automation for product search and Tawreed ordering."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

from playwright.sync_api import sync_playwright

from ..core.cart_removal_items import CartRemovalItem
from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.matching_models import MatchDecision
from ..core.order_ai_matching import OrderAiDecisionService, OrderAiSettings
from ..core.utils.excel import Item
from .selectors import _selectors
from .tawreed_api import TawreedApiUnavailable
from .tawreed_artifacts import append_csv_artifact
from .tawreed_auth_flow import TawreedAuthFlow
from .tawreed_cart_flow import TawreedCartFlow
from .tawreed_constants import PRODUCTS_PAGE_ROUTE
from .tawreed_dialogs import close_visible_dialogs
from .tawreed_match_logs import OrderResultSummary
from .tawreed_order_flow import TawreedOrderFlow
from .tawreed_order_exceptions import _SkipItem, _NoResultsItem
from .tawreed_order_run_artifacts import append_order_ai_trace_artifacts
from .tawreed_search_logic import require_product_match
from .tawreed_session import open_order_page
from .tawreed_timing import record_timing

# Import for backward compatibility with tests
from .tawreed_artifacts import dump_artifacts
from .tawreed_dialogs import visible_overlay_diagnostics
from .tawreed_match_only_summary import append_match_only_summary


class TawreedBot:
    """Coordinate Tawreed authentication, product matching, and order placement."""

    def __init__(
        self,
        config: AppConfig,
        profile_key: str,
        profile: ProfileConfig,
        state_path: Path,
        debug_browser: bool = False,
        stop_flag_path: Path | None = None,
        fast_search: bool = False,
        summary_label_suffix: str | None = None,
        match_only: bool = False,
        order_ai_settings: OrderAiSettings | None = None,
        execution_mode: str = "browser",
        matching_risk_policy: str = "safe",
        flagged_match_action: str = "manual-review-only",
        auth_lock=None,
        worker_id: int | None = None,
    ):
        """Create a bot instance bound to one Tawreed profile and saved session state.

        Args:
            auth_lock: Optional multiprocessing.Lock for coordinating auth refresh.
            worker_id: Optional worker ID for multi-worker logging.
        """
        self.config = config
        self.profile_key = profile_key
        self.profile = profile
        self.state_path = state_path
        self.debug_browser = debug_browser
        self.stop_flag_path = stop_flag_path
        self.fast_search = fast_search
        self.summary_label_suffix = summary_label_suffix
        self.match_only = match_only
        self.order_ai_settings = order_ai_settings or OrderAiSettings()
        self.execution_mode = execution_mode
        self.matching_risk_policy = matching_risk_policy
        self.flagged_match_action = flagged_match_action
        self.auth_lock = auth_lock
        self.worker_id = worker_id
        self.order_ai_service = self._build_order_ai_service()
        self.selectors = _selectors(config)
        self.skip_item_exception = _SkipItem
        self.no_results_exception = _NoResultsItem
        self._reset_last_item_state()

        # Initialize flow handlers
        self.auth_flow = TawreedAuthFlow(self)
        self.order_flow = TawreedOrderFlow(self)
        self.cart_flow = TawreedCartFlow(self)

    def log(self, message: str) -> None:
        """Print a profile-scoped diagnostic message."""
        print(_console_safe(f"[{self.profile_key}] {message}"))

    def _reset_last_item_state(self) -> None:
        """Reset internal state tracking for the next item to be processed."""
        pending_timings = getattr(self, "_pending_item_timings", {})
        self.last_match_decision: MatchDecision | None = None
        self.last_match_elapsed_seconds = 0.0
        self.last_searched_queries: list[str] = []
        self.last_selected_discount_percent = ""
        self.last_selected_store_name = ""
        self.last_ordered_total_qty = 0
        self.last_order_ai_outcome = None
        self.last_item_timings: dict[str, float] = dict(pending_timings)
        self._pending_item_timings = {}

    def _build_order_ai_service(self):
        """Return the optional live-order AI decision service."""
        if not self.order_ai_settings.enabled:
            return None
        return OrderAiDecisionService(self.order_ai_settings)

    def _try_api_order(self, items: Iterable[Item]) -> bool:
        """Run API order flow or return False when browser fallback should handle it."""
        if not self._api_enabled():
            return False
        from .tawreed_api_flow import place_order_with_api

        return self._run_api_or_fallback("order", lambda: place_order_with_api(self, items))

    def _try_api_match_only(self, items: Iterable[Item]) -> bool:
        """Run API match-only flow or return False when browser fallback should handle it."""
        if not self._api_enabled():
            return False
        from .tawreed_api_flow import match_items_only_with_api

        return self._run_api_or_fallback(
            "match-only", lambda: match_items_only_with_api(self, items)
        )

    def _try_api_cart_removal(self, items: Iterable[CartRemovalItem]) -> bool:
        """Run API cart removal or return False when browser fallback should handle it."""
        if not self._api_enabled():
            return False
        from .tawreed_api_flow import remove_cart_items_with_api

        return self._run_api_or_fallback(
            "cart-removal", lambda: remove_cart_items_with_api(self, items)
        )

    def _api_enabled(self) -> bool:
        """Return whether this bot should try the API backend before the browser."""
        return self.execution_mode in {"api", "auto"}

    def _ensure_valid_auth(self) -> None:
        """Verify token is valid or refresh authentication automatically."""
        self.auth_flow.ensure_valid_auth()

    def _run_api_or_fallback(self, label: str, operation) -> bool:
        """Run one API operation and decide whether browser fallback may continue."""
        try:
            operation()
            self.log(f"{label} completed with Tawreed API backend.")
            return True
        except TawreedApiUnavailable as error:
            if self.execution_mode == "api":
                raise
            self.log(f"{label} API unavailable; falling back to browser: {error}")
            return False

    def resolve_order_ai_decision(
        self, item: Item, decision: MatchDecision
    ) -> MatchDecision:
        """Apply opt-in AI verification/search and persist trace rows."""
        if not self.order_ai_service:
            return decision
        outcome = self.order_ai_service.resolve(item, decision)
        self.last_order_ai_outcome = outcome
        self._record_order_ai_rows(item, outcome)
        self.last_match_decision = outcome.decision
        return outcome.decision

    def _record_order_ai_rows(self, item: Item, outcome) -> None:
        """Append live-order AI trace and manual-review rows."""
        row = self._order_ai_trace_row(item, outcome)
        append_csv_artifact(self.profile_key, "matching_trace", [row])
        append_order_ai_trace_artifacts(
            self.profile_key, item, outcome, self.summary_label_suffix
        )

    def _order_ai_trace_row(self, item: Item, outcome) -> dict[str, object]:
        """Return one trace-compatible row for the AI order decision."""
        match = outcome.decision.best_match
        return {
            "phase": "order_ai",
            "item_code": item.code,
            "item_name": item.name,
            "item_qty": item.qty,
            "final_status": outcome.status,
            "final_reason": outcome.reason,
            **self._order_ai_candidate_fields(match, outcome),
            "selection_reason": outcome.reason,
        }

    def _order_ai_candidate_fields(self, match, outcome) -> dict[str, object]:
        """Return candidate columns for one AI trace row."""
        candidate = match.data if match else {}
        return {
            "candidate_rank": "",
            "candidate_name_en": candidate.get("productNameEn", ""),
            "candidate_name_ar": candidate.get("productName", ""),
            "candidate_id": candidate.get("storeProductId", ""),
            "candidate_score": round(outcome.confidence, 6),
            "accepted": bool(match and not outcome.manual_review),
            "accepted_reason": outcome.status,
            "rejection_reason": outcome.reason if outcome.manual_review else "",
            "query": match.query if match else "",
            "row_index": match.row_index if match else "",
        }

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        self.auth_flow.auth_interactive(wait_seconds)

    def auth_headless(self, wait_seconds: int = 120) -> None:
        """Run a headless login attempt and persist session state when credentials succeed."""
        self.auth_flow.auth_headless(wait_seconds)

    def _headless_auth_error(self) -> Exception:
        """Return the explicit auth failure used when hosted login never leaves the login page."""
        return self.auth_flow._headless_auth_error()

    def place_order_from_items(self, items: Iterable[Item]) -> None:
        """Place an order by processing each item from the provided iterable."""
        self.order_flow.place_order_from_items(items)

    def match_items_only(self, items: Iterable[Item]) -> None:
        """Match Tawreed products for each item without adding anything to the cart."""
        self.order_flow.match_items_only(items)

    def remove_cart_items(self, items: Iterable[CartRemovalItem]) -> None:
        """Remove the requested items from Tawreed carts."""
        self.cart_flow.remove_cart_items(items)

    def _stop_before_item(self, item: Item) -> bool:
        """Return True and print a diagnostic when a run should stop before an item."""
        if not self._stop_requested():
            return False
        print(
            f"[{self.profile_key}] Stop requested before item {item.code} / {item.name}."
        )
        return True

    def _stop_requested(self) -> bool:
        """Return whether an external stop request has been written for this run."""
        return bool(self.stop_flag_path and self.stop_flag_path.exists())

    def _products_page_url(self) -> str:
        """Return the direct Tawreed products page URL for faster order startup."""
        if "#/" in self.config.base_url:
            origin, _ = self.config.base_url.split("#/", 1)
            return f"{origin}{PRODUCTS_PAGE_ROUTE}"
        return self.config.base_url

    def _record_pending_item_timing(self, key: str, elapsed_seconds: float) -> None:
        """Attach one setup timing bucket to the next processed item."""
        pending = getattr(self, "_pending_item_timings", {})
        pending[key] = float(pending.get(key, 0.0)) + max(0.0, float(elapsed_seconds))
        self._pending_item_timings = pending

    # Delegation methods for backward compatibility with tests
    def _skip_status(self, reason: str) -> str:
        """Return the structured summary status for one skipped item."""
        return self.order_flow._skip_status(reason)

    def _build_item_summary(self, status: str, reason: str, elapsed: float, match_elapsed: float):
        """Build a compact summary object from the current bot state."""
        return self.order_flow._build_item_summary(status, reason, elapsed, match_elapsed)

    def _order_surface_ready(self, page) -> bool:
        """Return whether the products ordering surface is already interactive."""
        return self.order_flow._order_surface_ready(page)

    def _process_single_item(self, page, item):
        """Add one item or save artifacts when a technical failure happens."""
        return self.order_flow._process_single_item(page, item)

    def _process_single_match_only_item(self, page, item):
        """Match one item without running any add-to-cart action."""
        return self.order_flow._process_single_match_only_item(page, item)

    def _prepare_order_page(self, page):
        """Open the site and navigate to the ordering surface for item processing."""
        return self.order_flow._prepare_order_page(page)

    def _process_items(self, page, items):
        """Process each requested Excel item on the current order page."""
        return self.order_flow._process_items(page, items)

    def _is_products_page(self, page):
        """Return whether the current page is Tawreed's products ordering page."""
        return self.order_flow._is_products_page(page)

    def _record_item_summary(self, item, status, reason, elapsed_seconds, match_elapsed_seconds):
        """Append one execution-summary row for the processed item."""
        return self.order_flow._record_item_summary(item, status, reason, elapsed_seconds, match_elapsed_seconds)

    def _match_item_only(self, page, item):
        """Run Tawreed matching for one item without opening the cart dialog."""
        return self.order_flow._match_item_only(page, item)

    def _run_match_only_session(self, page, items):
        """Prepare Tawreed and process item matching without cart actions."""
        return self.order_flow._run_match_only_session(page, items)

    def _add_item(self, page, item):
        """Add one item using either the products-page flow or the legacy configured flow."""
        return self.order_flow._add_item(page, item)


def _console_safe(text: str) -> str:
    """Return text that can be printed on cp1252 Windows consoles without crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")
