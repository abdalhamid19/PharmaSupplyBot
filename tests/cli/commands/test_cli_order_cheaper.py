"""Tests for the winner reconciliation logic in cli_order.

The cross-source winner pass (``_reconcile_cross_source_winners`` /
``_cheaper``) keeps the cheapest ``purchase_price`` row as the unique
winner per item. Excel target rows carry retail price (the price the
pharmacy sells to the end customer) and have a NULL ``purchase_price``
because the Excel catalog never provides the pharmacy's purchase cost.

Because retail vs wholesale are different semantic classes, Excel
target rows must never displace a Tawreed row from the winner spot —
the comparison would be apples-to-oranges. These tests lock in that
contract so future refactors cannot silently break it.
"""

from __future__ import annotations

from unittest import TestCase

from src.cli.commands.cli_order import _cheaper


class TestCheaperNeverLetsExcelTargetWinOverTawreed(TestCase):
    """Excel target rows are reference-only and must not outcompete Tawreed."""

    def test_excel_target_does_not_beat_tawreed_with_price(self) -> None:
        """An Excel target row never beats a Tawreed row that has a price.

        Even when the Excel target has a 100% ``discount_percent``, it
        must not win over a Tawreed row carrying a real ``purchase_price``
        because the numbers live in different semantic classes.
        """
        tawreed = {
            "source": "tawreed",
            "purchase_price": 100.0,
            "discount_percent": 10.0,
        }
        excel = {
            "source": "excel_target",
            "purchase_price": None,
            "discount_percent": 100.0,
        }
        self.assertFalse(_cheaper(excel, tawreed))

    def test_tawreed_stays_winner_against_excel_with_lower_discount(self) -> None:
        """Tawreed with a non-null price always beats Excel target.

        ``_cheaper`` answers "is candidate better than current?".
        Passing Tawreed-as-candidate against Excel-as-current should
        return True so Tawreed takes over when its price is recorded.
        """
        tawreed = {
            "source": "tawreed",
            "purchase_price": 50.0,
            "discount_percent": 0,
        }
        excel = {
            "source": "excel_target",
            "purchase_price": None,
            "discount_percent": 80.0,
        }
        self.assertTrue(_cheaper(tawreed, excel))

    def test_excel_target_wins_when_only_excel_present(self) -> None:
        """When the item has only Excel target rows, the highest discount wins.

        This preserves the legacy fallback for runs without any Tawreed
        matches so the operator still sees a non-empty winner.
        """
        cheap = {
            "source": "excel_target",
            "purchase_price": None,
            "discount_percent": 50.0,
        }
        expensive = {
            "source": "excel_target",
            "purchase_price": None,
            "discount_percent": 10.0,
        }
        self.assertTrue(_cheaper(cheap, expensive))
        self.assertFalse(_cheaper(expensive, cheap))

    def test_tawreed_to_tawreed_still_uses_price(self) -> None:
        """Pure Tawreed-vs-Tawreed behaviour is unchanged: cheapest wins."""
        cheap = {
            "source": "tawreed",
            "purchase_price": 50.0,
            "discount_percent": 0,
        }
        pricey = {
            "source": "tawreed",
            "purchase_price": 100.0,
            "discount_percent": 0,
        }
        self.assertTrue(_cheaper(cheap, pricey))
        self.assertFalse(_cheaper(pricey, cheap))

    def test_tawreed_takes_over_when_excel_has_no_price(self) -> None:
        """Tawreed with NULL price still beats Excel target (source rule).

        The source-based rule says a Tawreed row always wins over an
        Excel target row, regardless of the price values. This keeps
        the cross-source comparison apples-to-apples.
        """
        tawreed_null = {
            "source": "tawreed",
            "purchase_price": None,
            "discount_percent": 5.0,
        }
        excel_null = {
            "source": "excel_target",
            "purchase_price": None,
            "discount_percent": 50.0,
        }
        # Tawreed beats Excel even though Excel has a higher discount.
        self.assertTrue(_cheaper(tawreed_null, excel_null))
        # And the converse: Excel never beats Tawreed.
        self.assertFalse(_cheaper(excel_null, tawreed_null))


class TestCheaperSourceNormalization(TestCase):
    """Source field can arrive with slight formatting variants.

    ``run_item_stores.source`` historically has carried both
    ``excel_target`` and ``excel-target`` strings depending on the
    writer that produced the row. The comparator must normalise so a
    future refactor doesn't accidentally let an Excel row outrank
    Tawreed because of a typo.
    """

    def test_excel_target_with_dashed_source_still_blocked(self) -> None:
        """Even if ``source`` reads ``excel-target``, the row must lose."""
        tawreed = {
            "source": "tawreed",
            "purchase_price": 10.0,
            "discount_percent": 0,
        }
        excel_dashed = {
            "source": "excel-target",
            "purchase_price": None,
            "discount_percent": 50.0,
        }
        self.assertFalse(_cheaper(excel_dashed, tawreed))