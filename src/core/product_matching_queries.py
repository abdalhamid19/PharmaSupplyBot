"""Search query generation for product matching."""

from .product_matching_helpers import normalize_text, unique_non_empty, MAX_SEARCH_QUERY_VARIANTS
from .search_query_templates import category_queries
from .utils.excel import Item


def search_queries_for_item(item: Item) -> list[str]:
    """Build ordered search queries from the Excel item name and code."""
    name = str(item.name or "").strip()
    normalized_name = normalize_text(name)
    tokens = name.split()
    normalized_tokens = normalized_name.split()
    queries = category_queries(name)
    queries.extend(_priority_search_queries(name, normalized_name, tokens, normalized_tokens))
    queries.extend(_fallback_search_queries(item.code, tokens, normalized_tokens))
    return unique_non_empty(queries)[:MAX_SEARCH_QUERY_VARIANTS]


def _priority_search_queries(name, normalized_name, tokens, normalized_tokens):
    """Return high-signal full-name and leading-token query variants."""
    return [
        name, normalized_name,
        " ".join(tokens[:4]), " ".join(normalized_tokens[:4]),
        " ".join(tokens[:3]), " ".join(normalized_tokens[:3]),
        " ".join(tokens[:2]), " ".join(normalized_tokens[:2]),
        tokens[0] if tokens else "", normalized_tokens[0] if normalized_tokens else ""
    ]


def _fallback_search_queries(code, tokens, normalized_tokens):
    """Return extra bounded fallback queries when priority variants do not match."""
    return _token_window_queries(normalized_tokens or tokens, window_size=2)


def _token_window_queries(tokens, window_size):
    """Return contiguous token-window query variants."""
    if len(tokens) <= window_size or not tokens:
        return []
    brand = tokens[0]
    return [f"{brand} {' '.join(tokens[i:i+window_size])}" for i in range(1, len(tokens) - window_size + 1)]
