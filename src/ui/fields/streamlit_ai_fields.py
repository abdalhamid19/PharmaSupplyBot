"""AI matching fields for Streamlit order form."""

import streamlit as st


def ai_matching_fields() -> dict[str, object]:
    """Return Streamlit controls for live-order AI matching."""
    with st.expander("🤖 AI Matching (Advanced)", expanded=False):
        enabled = st.checkbox("Enable AI matching", value=False)
        values = _ai_provider_fields()
        values.update(_ai_policy_fields())
        values.update(matching_risk_fields())
    return {"enable_order_ai": bool(enabled), **values}


def matching_risk_fields() -> dict[str, object]:
    """Return Streamlit controls for matching risk policy."""
    with st.expander("⚙️ Matching Risk (Advanced)", expanded=False):
        policy = st.selectbox("Risk policy", ["aggressive", "safe"], index=0)
        action = st.selectbox(
            "Flagged match action",
            ["manual-review-only", "add-to-cart"],
            index=0,
        )
    return {
        "matching_risk_policy": str(policy),
        "flagged_match_action": str(action),
    }


def _ai_provider_fields() -> dict[str, object]:
    provider = st.selectbox(
        "Provider",
        ["openrouter", "rotation", "opencode", "groq", "github", "custom"],
        index=0,
    )
    return {
        "ai_provider": str(provider),
        "ai_model": str(st.text_input("Model", value="")),
        "ai_review_model": str(st.text_input("Review model", value="")),
        "ai_concurrency": int(st.number_input("AI concurrency", min_value=1, value=5)),
    }


def _ai_policy_fields() -> dict[str, object]:
    verify_policy = st.selectbox("Verify policy", ["score", "all"], index=0)
    search_policy = st.selectbox(
        "Search policy", ["review-candidates", "safe", "expanded"], index=0
    )
    accept_conf = st.number_input("Accept confidence", value=0.9, step=0.01)
    review_threshold = st.number_input("Review threshold", value=0.95, step=0.01)
    return {
        "ai_verify_policy": str(verify_policy),
        "ai_search_policy": str(search_policy),
        "ai_accept_confidence": float(accept_conf),
        "ai_review_threshold": float(review_threshold),
    }
