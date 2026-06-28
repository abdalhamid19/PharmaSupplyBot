"""AI verification and search methods for MatchPipeline."""

import pandas as pd


class PipelineAIMixin:
    """AI verification and search methods for MatchPipeline."""

    async def run_ai_verification(self) -> pd.DataFrame:
        """AI verification of matches below threshold."""
        if self._ai is None:
            raise RuntimeError("Call load_data() first")
        return await self._ai.run_ai_verification()

    async def run_ai_search_unmatched(self) -> pd.DataFrame:
        """AI searches for matches among unmatched items."""
        if self._ai is None:
            raise RuntimeError("Call load_data() first")
        return await self._ai.run_ai_search_unmatched()

    async def run_ai_review(self) -> pd.DataFrame:
        """AI review: second model cross-verifies low-confidence AI decisions."""
        if self._ai is None:
            raise RuntimeError("Call load_data() first")
        return await self._ai.run_ai_review()
