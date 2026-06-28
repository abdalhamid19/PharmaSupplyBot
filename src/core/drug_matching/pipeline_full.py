"""Full pipeline execution method for MatchPipeline."""

import pandas as pd

from .pipeline_helpers import _manual_review_path


class PipelineFullMixin:
    """Full pipeline execution method for MatchPipeline."""

    async def run_full(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
        output_path: str | None = None,
        skip_ai: bool = False,
    ) -> pd.DataFrame:
        """Run the complete pipeline."""
        self.load_data(drugs_path, tawreed_path)
        self.run_matching()
        if not skip_ai:
            await self.run_ai_verification()
            await self.run_ai_search_unmatched()
            await self.run_ai_review()
        saved_path = self.save(output_path)
        self.save_manual_review(_manual_review_path(saved_path))
        self.print_stats()
        return self._matching._results
