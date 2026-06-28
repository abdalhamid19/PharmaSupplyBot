"""Dialog handling for Tawreed order summaries."""

import time

from .tawreed_dialogs import close_visible_dialogs
from .tawreed_timing import record_timing


class SummaryDialogHandler:
    """Handles dialog closing and timing for summary recording."""

    def __init__(self, bot):
        self.bot = bot

    def close_visible_dialogs_timed(self, page) -> None:
        """Close visible dialogs and accumulate the item-level wait cost."""
        started_at = time.perf_counter()
        close_visible_dialogs(page)
        record_timing(self.bot, "dialog_close_seconds", time.perf_counter() - started_at)
