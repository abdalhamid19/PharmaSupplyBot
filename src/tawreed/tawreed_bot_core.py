"""Core TawreedBot class initialization and state management."""

from __future__ import annotations

from pathlib import Path

from ..core.config.config_models import AppConfig, ProfileConfig
from ..core.matching_models import MatchDecision
from ..core.order_ai_matching import OrderAiDecisionService, OrderAiSettings
from ..core.utils.excel import Item
from .selectors import _selectors
from .tawreed_auth_flow import TawreedAuthFlow
from .tawreed_cart_flow import TawreedCartFlow
from .tawreed_order_flow import TawreedOrderFlow
from .tawreed_order_exceptions import _SkipItem, _NoResultsItem


def _console_safe(text: str) -> str:
    """Return text that can be printed on cp1252 Windows consoles without crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")


__all__ = ["TawreedBotCore", "_console_safe"]


class TawreedBotCore:
    """Core TawreedBot initialization and state management."""

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

    def log(self, message: str) -> None:
        """Print a profile-scoped diagnostic message."""
        print(_console_safe(f"[{self.profile_key}] {message}"))
