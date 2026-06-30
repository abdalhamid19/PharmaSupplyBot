"""Drug name normalization and parsing module.

This module contains all normalization-related functionality split into
submodules for better organization:
- normalizer_constants: Constants for drug name normalization
- normalizer_parsing: Drug name parsing and component extraction
- normalizer_matching: Drug component matching and compatibility
"""

from .normalizer import *  # noqa: F401, F403

__all__ = []
