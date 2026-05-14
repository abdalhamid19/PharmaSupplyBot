"""Aggressive matching bridge for Tawreed search flow."""

from __future__ import annotations

from ..core.matching_risk import aggressive_review_decision
from ..core.order_ai_matching import OrderAiOutcome
from ..core.utils.excel import Item
from .tawreed_match_acceptance import available_quantity


def aggressive_review_result(bot, item: Item, decision, require_available: bool):
    """Return or stage a flagged aggressive match when the run opted into it."""
    if getattr(bot, "matching_risk_policy", "safe") != "aggressive":
        return None
    flagged_decision = aggressive_review_decision(decision)
    if not flagged_decision or not flagged_decision.best_match:
        return None
    _record_flagged_decision(bot, flagged_decision)
    _reject_unavailable_flagged_match(bot, item, flagged_decision, require_available)
    if bot.match_only or getattr(bot, "flagged_match_action", "") == "add-to-cart":
        match = flagged_decision.best_match
        return match, match.query
    raise bot.skip_item_exception("Aggressive matching requires manual review.")


def _record_flagged_decision(bot, decision) -> None:
    match = decision.best_match
    bot.last_match_decision = decision
    bot.last_order_ai_outcome = OrderAiOutcome(
        decision, "aggressive_review_required", decision.final_reason, match.score, True,
    )


def _reject_unavailable_flagged_match(
    bot, item: Item, decision, require_available: bool
) -> None:
    match = decision.best_match
    if require_available and available_quantity(match.data) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )
