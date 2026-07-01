import unittest
from typing import Any
from src.core.matching_types import CandidateMatchDiagnostic, MatchScoreBreakdown, MatchDecision
from src.core.matching.matching_risk import aggressive_review_decision
from src.core.config.config_models import MatchingConfig

class MatchingRiskTests(unittest.TestCase):
    def test_aggressive_review_decision_requires_brand_token(self) -> None:
        # Create a breakdown
        breakdown = MatchScoreBreakdown(
            sequence_score=15.0,
            overlap_score=0.8,
            numeric_overlap=1.0,
            exact_bonus=0.0,
            availability_bonus=0.0,
            critical_penalty=0.0,
            extra_token_penalty=0.0,
            semantic_penalty=0.0,
            total_score=15.0
        )
        
        # Test 1: Candidate with a completely different brand (e.g. DOLIPRANE vs CETAL)
        diag_diff = CandidateMatchDiagnostic(
            query="DOLIPRANE 500MG 20 TAB",
            row_index=1,
            score=15.0,
            sort_key=(15.0, 0, 0.8, 0, 0, 0),
            accepted=False,
            accepted_reason="",
            rejection_reason="different_brand",
            breakdown=breakdown,
            candidate={"storeProductId": "s1", "productNameEn": "CETAL 500MG 20 TAB"}
        )
        
        decision_diff = MatchDecision(best_match=None, diagnostics=[diag_diff], final_reason="no winner")
        
        # With default config (require_identity_token_for_flag=True), it should reject
        cfg = MatchingConfig(require_identity_token_for_flag=True)
        res_diff = aggressive_review_decision(decision_diff, cfg)
        self.assertIsNone(res_diff)
        
        # With config require_identity_token_for_flag=False, it should allow it
        cfg_disabled = MatchingConfig(require_identity_token_for_flag=False)
        res_diff_disabled = aggressive_review_decision(decision_diff, cfg_disabled)
        self.assertIsNotNone(res_diff_disabled)
        self.assertEqual(res_diff_disabled.best_match.data["productNameEn"], "CETAL 500MG 20 TAB")

        # Test 2: Candidate with same brand (e.g. ZOVIRAX 10% vs ZOVIRAX 5%)
        diag_same = CandidateMatchDiagnostic(
            query="ZOVIRAX CREAM 10%",
            row_index=1,
            score=15.0,
            sort_key=(15.0, 0, 0.8, 0, 0, 0),
            accepted=False,
            accepted_reason="",
            rejection_reason="different_dosage",
            breakdown=breakdown,
            candidate={"storeProductId": "s2", "productNameEn": "ZOVIRAX CREAM 5%"}
        )
        
        decision_same = MatchDecision(best_match=None, diagnostics=[diag_same], final_reason="no winner")
        res_same = aggressive_review_decision(decision_same, cfg)
        self.assertIsNotNone(res_same)
        self.assertEqual(res_same.best_match.data["productNameEn"], "ZOVIRAX CREAM 5%")

if __name__ == "__main__":
    unittest.main()
