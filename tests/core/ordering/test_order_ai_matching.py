"""Tests for live-order AI matching decisions."""

from __future__ import annotations

import unittest

from src.core.drug_matching.config import APIConfig
from src.core.matching_types import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
    SearchMatch,
)
from src.core.ordering.order_ai_matching import OrderAiDecisionService, OrderAiSettings
from src.core.utils.excel import Item


class FakeVerifier:
    """Minimal async verifier used by order AI tests."""

    verify_result = {"is_correct": True, "reason": "ok", "confidence": 0.95}
    search_result = None
    review_result = {"is_correct": True, "reason": "review ok", "confidence": 0.99}

    def __init__(self, *_args, **_kwargs):
        pass

    async def verify_one(self, *_args, **_kwargs):
        return dict(self.verify_result)

    async def find_better_match(self, *_args, **_kwargs):
        return dict(self.search_result) if self.search_result else None

    async def review_one(self, *_args, **_kwargs):
        return dict(self.review_result)

    async def close(self):
        return None


class OrderAiMatchingTests(unittest.TestCase):
    """Validate active order AI accept/reject behavior."""

    def setUp(self) -> None:
        FakeVerifier.verify_result = {"is_correct": True, "reason": "ok", "confidence": 0.95}
        FakeVerifier.search_result = None
        FakeVerifier.review_result = {"is_correct": True, "reason": "review ok", "confidence": 0.99}

    def test_no_api_key_keeps_deterministic_match(self) -> None:
        """AI without credentials is traced but does not block an existing match."""
        outcome = self._service(APIConfig()).resolve(self._item(), self._decision(True))
        self.assertEqual(outcome.status, "ai_skipped")
        self.assertIsNotNone(outcome.decision.best_match)
        self.assertFalse(outcome.manual_review)

    def test_no_api_key_without_match_goes_to_manual_review(self) -> None:
        """AI without credentials cannot invent a match."""
        outcome = self._service(APIConfig()).resolve(self._item(), self._decision(False))
        self.assertEqual(outcome.status, "ai_skipped")
        self.assertTrue(outcome.manual_review)

    def test_verify_accepts_high_confidence_match(self) -> None:
        """High-confidence AI verification keeps the deterministic match active."""
        outcome = self._service(self._api()).resolve(self._item(), self._decision(True))
        self.assertEqual(outcome.status, "ai_verified")
        self.assertIsNotNone(outcome.decision.best_match)
        self.assertEqual(outcome.verify_result["reason"], "ok")

    def test_reject_moves_to_manual_review_when_search_fails(self) -> None:
        """Rejected deterministic match blocks active ordering without AI replacement."""
        FakeVerifier.verify_result = {"is_correct": False, "reason": "mismatch", "confidence": 0.9}
        outcome = self._service(self._api()).resolve(self._item(), self._decision(True))
        self.assertTrue(outcome.manual_review)
        self.assertEqual(outcome.status, "ai_rejected")
        self.assertEqual(outcome.verify_result["reason"], "mismatch")

    def test_ai_search_can_accept_replacement(self) -> None:
        """AI search can select a candidate when deterministic matching has no winner."""
        FakeVerifier.search_result = {
            "record": self._record(),
            "score": 91.0,
            "reason": "better",
            "confidence": 0.96,
        }
        outcome = self._service(self._api()).resolve(self._item(), self._decision(False))
        self.assertEqual(outcome.status, "ai_search_accepted")
        self.assertEqual(outcome.decision.best_match.score, 91.0)
        self.assertEqual(outcome.search_result["reason"], "better")

    def test_ai_search_rejects_missing_store_id(self) -> None:
        """AI search cannot select a candidate that is not orderable."""
        record = self._record()
        record["store_product_id"] = ""
        record["_raw"] = {"productNameEn": "Panadol Advance", "availableQuantity": 5}
        FakeVerifier.search_result = {
            "record": record,
            "score": 91.0,
            "reason": "better",
            "confidence": 0.96,
        }
        outcome = self._service(self._api()).resolve(self._item(), self._decision(False))
        self.assertEqual(outcome.status, "ai_rejected")
        self.assertTrue(outcome.manual_review)
        self.assertIn("missing storeProductId", outcome.reason)

    def test_ai_search_rejects_component_mismatch(self) -> None:
        """AI search cannot override local component safety."""
        record = self._record()
        record["product_name_en"] = "ASPIRIN 100 MG 30 TAB"
        record["_raw"] = {
            "productNameEn": "ASPIRIN 100 MG 30 TAB",
            "storeProductId": "s2",
            "availableQuantity": 5,
        }
        FakeVerifier.search_result = {
            "record": record,
            "score": 91.0,
            "reason": "better",
            "confidence": 0.96,
        }
        outcome = self._service(self._api()).resolve(self._item(), self._decision(False))
        self.assertEqual(outcome.status, "ai_rejected")
        self.assertTrue(outcome.manual_review)
        self.assertIn("component mismatch", outcome.reason)

    def test_verify_does_not_override_local_safety(self) -> None:
        """AI verification cannot keep a deterministic match missing orderable id."""
        decision = self._decision(True)
        decision.best_match.data.pop("storeProductId")
        outcome = self._service(self._api()).resolve(self._item(), decision)
        self.assertEqual(outcome.status, "ai_rejected")
        self.assertTrue(outcome.manual_review)
        self.assertEqual(outcome.verify_result["reason"], "local_safety: missing storeProductId")

    def test_review_rejection_blocks_ai_selection(self) -> None:
        """A review model disagreement forces manual review."""
        FakeVerifier.search_result = {
            "record": self._record(),
            "score": 91.0,
            "reason": "better",
            "confidence": 0.96,
        }
        FakeVerifier.review_result = {
            "is_correct": False,
            "reason": "review reject",
            "confidence": 0.99,
        }
        outcome = self._service(self._api(review_model="review")).resolve(
            self._item(), self._decision(False)
        )
        self.assertEqual(outcome.status, "ai_review_rejected")
        self.assertTrue(outcome.manual_review)
        self.assertEqual(outcome.review_result["reason"], "review reject")

    def test_low_confidence_agreeing_review_keeps_verified_match(self) -> None:
        """An agreeing review confirms a verified match even below review threshold."""
        FakeVerifier.review_result = {
            "is_correct": True,
            "reason": "same product",
            "confidence": 0.90,
        }
        outcome = self._service(self._api(review_model="review")).resolve(
            self._item(), self._decision(True)
        )
        self.assertEqual(outcome.status, "ai_verified")
        self.assertFalse(outcome.manual_review)
        self.assertIsNotNone(outcome.decision.best_match)

    def test_low_confidence_agreeing_review_keeps_search_replacement(self) -> None:
        """An agreeing review confirms an AI search replacement below review threshold."""
        FakeVerifier.search_result = {
            "record": self._record(),
            "score": 91.0,
            "reason": "better",
            "confidence": 0.96,
        }
        FakeVerifier.review_result = {
            "is_correct": True,
            "reason": "same product",
            "confidence": 0.90,
        }
        outcome = self._service(self._api(review_model="review")).resolve(
            self._item(), self._decision(False)
        )
        self.assertEqual(outcome.status, "ai_search_accepted")
        self.assertFalse(outcome.manual_review)
        self.assertIsNotNone(outcome.decision.best_match)

    def _service(self, api_config):
        settings = OrderAiSettings(enabled=True, api_config=api_config)
        return OrderAiDecisionService(settings, FakeVerifier)

    @staticmethod
    def _api(review_model: str = "") -> APIConfig:
        return APIConfig(api_key="key", api_keys=("key",), review_model=review_model)

    @staticmethod
    def _item() -> Item:
        return Item("1", "Panadol Advance", 1)

    def _decision(self, with_match: bool) -> MatchDecision:
        match = SearchMatch("Panadol", 0, 92.0, self._candidate()) if with_match else None
        return MatchDecision(match, [self._diagnostic()], "test")

    def _diagnostic(self):
        return CandidateMatchDiagnostic(
            "Panadol", 0, 92.0, (92, 0, 0, 0, 0, 0), True, "ok", "",
            MatchScoreBreakdown(0, 0, 0, 0, 0, 0, 0, 0, 92),
            self._candidate(),
        )

    @staticmethod
    def _candidate():
        return {"productNameEn": "Panadol Advance", "storeProductId": "s1", "availableQuantity": 5}

    def _record(self):
        return {
            "product_name_en": "Panadol Advance",
            "store_product_id": "s1",
            "_raw": self._candidate(),
            "_query": "Panadol",
            "_row_index": 0,
        }


if __name__ == "__main__":
    unittest.main()
