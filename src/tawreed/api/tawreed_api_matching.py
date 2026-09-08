"""Compatibility shim for the retired Tawreed API matching module.

The implementation lives in :mod:`tawreed_api_flow_matching`. This legacy
path remains available for the current caller that imports the predicate here.
"""

from .tawreed_api_flow_matching import _has_only_non_orderable_candidates


__all__ = ["_has_only_non_orderable_candidates"]
