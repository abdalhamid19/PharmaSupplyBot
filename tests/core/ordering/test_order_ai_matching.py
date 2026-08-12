"""Tests for live-order AI matching decisions."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from src.core.drug_matching.config import APIConfig
from src.core.matching_types import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
    SearchMatch,
)
from src.core.ordering.order_ai_matching import (
    OrderAiDecisionService,
    OrderAiSettings,
    _close_verifier,
    _no_verifier_outcome,
)
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


# ---------------------------------------------------------------------------
# Regression tests for the NoneType-session crash encountered during the
# SMALL_TEST bench run (opencode/big-pickle). The original code did:
#     await verifier._session.close()
# unconditionally in the close path, which raised AttributeError whenever the
# verifier had no session (factory failure, missing API key, bad config). The
# fixed module makes _close_verifier safe for every shape and degrades the
# service to ai_skipped when the verifier cannot be built.
# ---------------------------------------------------------------------------


class _RecordingSession:
    """Async context manager-ish session that records close() calls."""

    def __init__(self) -> None:
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1


class _VerifierWithSession:
    """Verifier exposing a real, closeable _session attribute."""

    def __init__(self) -> None:
        self._session = _RecordingSession()


class _VerifierWithSessionNone:
    """Verifier whose _session attribute exists but is None (no key)."""

    _session = None


class _VerifierRaisingClose:
    """Verifier whose async close() raises; _close_verifier must swallow."""

    _session = None

    async def close(self) -> None:
        raise RuntimeError("boom from close()")


class _VerifierWithBrokenSession:
    """Verifier whose _session.close() raises — must not crash the flow."""

    def __init__(self) -> None:
        class _Broken:
            async def close(self) -> None:
                raise RuntimeError("session boom")

        self._session = _Broken()


class CloseVerifierTests(unittest.IsolatedAsyncioTestCase):
    """_close_verifier must never propagate exceptions from cleanup."""

    async def test_close_verifier_with_none_is_safe(self) -> None:
        """None verifier must be a no-op (regression: was crashing the flow)."""
        # If this raises, the test fails. There is no observable side-effect to assert.
        await _close_verifier(None)

    async def test_close_verifier_with_session_none_is_safe(self) -> None:
        """verifier._session == None must not crash close_verifier."""
        await _close_verifier(_VerifierWithSessionNone())

    async def test_close_verifier_swallows_close_exception(self) -> None:
        """An exception from verifier.close() must not escape the finally block."""
        await _close_verifier(_VerifierRaisingClose())

    async def test_close_verifier_closes_real_session(self) -> None:
        """When _session is a real closeable, close_verifier must call session.close()."""
        verifier = _VerifierWithSession()
        await _close_verifier(verifier)
        self.assertEqual(verifier._session.close_calls, 1)

    async def test_close_verifier_prefers_explicit_close_method(self) -> None:
        """If the verifier defines its own async close(), that wins over _session."""

        class _VerifierWithOwnClose:
            def __init__(self) -> None:
                self._session = _RecordingSession()
                self.close_calls = 0

            async def close(self) -> None:
                self.close_calls += 1

        verifier = _VerifierWithOwnClose()
        await _close_verifier(verifier)
        self.assertEqual(verifier.close_calls, 1)
        # _session.close() must NOT have been called because close() won.
        self.assertEqual(verifier._session.close_calls, 0)

    async def test_close_verifier_swallows_session_close_exception(self) -> None:
        """If _session.close() raises, the flow must still continue."""
        await _close_verifier(_VerifierWithBrokenSession())


class NoVerifierOutcomeTests(unittest.TestCase):
    """_no_verifier_outcome should degrade gracefully."""

    def test_no_verifier_outcome_with_no_best_match_marks_manual_review(self) -> None:
        decision = MatchDecision(best_match=None, diagnostics=[], final_reason="api_match")
        outcome = _no_verifier_outcome(decision)
        self.assertEqual(outcome.status, "ai_skipped")
        self.assertEqual(outcome.reason, "no_verifier")
        self.assertTrue(outcome.manual_review)
        self.assertEqual(outcome.confidence, 0.0)

    def test_no_verifier_outcome_with_existing_match_is_not_manual_review(self) -> None:
        match = SearchMatch("Panadol", 0, 92.0, {"storeProductId": "s1"})
        decision = MatchDecision(best_match=match, diagnostics=[], final_reason="api_match")
        outcome = _no_verifier_outcome(decision)
        self.assertEqual(outcome.status, "ai_skipped")
        self.assertEqual(outcome.reason, "no_verifier")
        self.assertFalse(outcome.manual_review)


class ServiceNoVerifierFactoryTests(unittest.TestCase):
    """OrderAiDecisionService.resolve must not raise when the verifier factory fails."""

    def test_factory_raises_returns_ai_skipped_outcome(self) -> None:
        """If the factory cannot build a verifier, resolve() returns ai_skipped/no_verifier."""

        def _bad_factory(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("no api key / config invalid")

        settings = OrderAiSettings(
            enabled=True,
            api_config=APIConfig(api_key="key", api_keys=("key",)),
        )
        service = OrderAiDecisionService(settings, _bad_factory)
        decision = MatchDecision(best_match=None, diagnostics=[], final_reason="api_match")
        outcome = service.resolve(item=None, decision=decision)  # type: ignore[arg-type]
        self.assertEqual(outcome.status, "ai_skipped")
        self.assertEqual(outcome.reason, "no_verifier")
        self.assertTrue(outcome.manual_review)

    def test_factory_raises_with_existing_match_keeps_decision(self) -> None:
        """When factory raises but the decision already has a best_match, do not flip to manual review."""

        def _bad_factory(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("factory boom")

        settings = OrderAiSettings(
            enabled=True,
            api_config=APIConfig(api_key="key", api_keys=("key",)),
        )
        service = OrderAiDecisionService(settings, _bad_factory)
        match = SearchMatch("Panadol", 0, 92.0, {"storeProductId": "s1"})
        decision = MatchDecision(best_match=match, diagnostics=[], final_reason="api_match")
        outcome = service.resolve(item=None, decision=decision)  # type: ignore[arg-type]
        self.assertEqual(outcome.status, "ai_skipped")
        self.assertEqual(outcome.reason, "no_verifier")
        # Existing deterministic match must stay usable (not forced to manual review).
        self.assertFalse(outcome.manual_review)
        self.assertIsNotNone(outcome.decision.best_match)


class ServiceResolveAsyncCleanupTests(unittest.IsolatedAsyncioTestCase):
    """The async resolve path must call _close_verifier on every code path."""

    async def test_resolve_order_ai_failure_closes_verifier_anyway(self) -> None:
        """Even if resolve_order_ai raises, the verifier must be closed."""
        close_calls = {"n": 0}

        class _V:
            def __init__(self, *a: Any, **k: Any) -> None:
                pass

            async def close(self) -> None:
                close_calls["n"] += 1

        # Build a service whose resolve_order_ai raises.
        from src.core import order_ai_flow as flow_mod

        original = flow_mod.resolve_order_ai

        async def _boom(*_a: Any, **_k: Any) -> Any:
            raise RuntimeError("resolve_order_ai boom")

        flow_mod.resolve_order_ai = _boom  # type: ignore[assignment]
        try:
            settings = OrderAiSettings(
                enabled=True,
                api_config=APIConfig(api_key="key", api_keys=("key",)),
            )
            service = OrderAiDecisionService(settings, _V)
            decision = MatchDecision(best_match=None, diagnostics=[], final_reason="api_match")
            # resolve() runs the async path inside _run_async; we expect the
            # exception to be re-raised by _run_async, but the verifier must
            # still have been closed during the finally block.
            with self.assertRaises(RuntimeError):
                service.resolve(item=None, decision=decision)  # type: ignore[arg-type]
            self.assertEqual(
                close_calls["n"],
                1,
                "verifier.close() must run exactly once even when resolve_order_ai raises",
            )
        finally:
            flow_mod.resolve_order_ai = original  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
