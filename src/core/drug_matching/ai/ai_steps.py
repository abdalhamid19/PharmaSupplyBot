"""AI verification and search steps - coordinator module.

This module provides the main interface for AI operations and delegates
to specialized modules:
- ai_verify.py: AI verification logic
- ai_search.py: AI search logic  
- ai_review.py: AI review logic
"""

from __future__ import annotations

import logging

from ..config import MatchingConfig, APIConfig
from ..indexing.indexer import DrugIndex
from .ai_verify import run_ai_verification
from .ai_search import run_ai_search
from .ai_review import run_ai_review

logger = logging.getLogger("pharmasupplybot.matching")

# Re-export main functions for backward compatibility
__all__ = [
    "run_ai_verification",
    "run_ai_search", 
    "run_ai_review",
]
