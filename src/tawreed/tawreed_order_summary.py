"""Order summary and recording logic for Tawreed order processing."""

from __future__ import annotations

from .tawreed_order_summary_main import OrderSummaryRecorderBase
from .tawreed_order_summary_success import OrderSummaryRecorderSuccessMixin
from .tawreed_order_summary_failure import OrderSummaryRecorderFailureMixin
from .tawreed_order_summary_builders import OrderSummaryRecorderBuildersMixin


class OrderSummaryRecorder(
    OrderSummaryRecorderBase,
    OrderSummaryRecorderSuccessMixin,
    OrderSummaryRecorderFailureMixin,
    OrderSummaryRecorderBuildersMixin,
):
    """Handles recording of order summaries and match-only summaries."""
    pass


__all__ = ["OrderSummaryRecorder"]
