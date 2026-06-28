"""Main order summary recorder class."""

from __future__ import annotations

from .tawreed_summary_builder import SummaryBuilder
from .tawreed_summary_status import SummaryStatus
from .tawreed_summary_dialog import SummaryDialogHandler


class OrderSummaryRecorderBase:
    """Base class for order summary recorder."""

    def __init__(self, bot):
        """Initialize summary recorder with bot instance."""
        self.bot = bot
        self._summary_builder = SummaryBuilder(bot)
        self._status = SummaryStatus(bot)
        self._dialog_handler = SummaryDialogHandler(bot)
