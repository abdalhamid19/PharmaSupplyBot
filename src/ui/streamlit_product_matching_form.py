"""Product matching form handling for Streamlit."""

from __future__ import annotations

from .streamlit_excel_fields import existing_excel_path, uploaded_excel_file
from .streamlit_uploads import available_excel_options


def product_matching_form(app_config, default_profile: str | None) -> tuple[bool, dict]:
    """Return submitted state and product matching form values."""
    import streamlit as st
    
    with st.form("product_matching_form"):
        input_mode = st.radio(
            "Excel source", ["Existing file", "Upload file"], horizontal=True
        )
        excel_path = existing_excel_path(input_mode, available_excel_options())
        upload = uploaded_excel_file(input_mode)
        profile = st.selectbox(
            "Profile",
            list(app_config.profiles.keys()),
            index=_profile_index(app_config, default_profile),
        )
        limit = st.number_input("Item limit", min_value=0, max_value=100000, value=50)
        trace = st.checkbox("Trace", value=True)
        no_ai = st.checkbox("No AI", value=True)
        provider = st.selectbox(
            "AI provider", ["", "rotation", "groq", "opencode", "openrouter"]
        )
        model = st.text_input("AI model", value="")
        review_model = st.text_input("Review model", value="")
        concurrency = st.number_input("AI concurrency", min_value=1, max_value=20, value=5)
        submitted = st.form_submit_button("Run Product Matching")
    return bool(submitted), {
        "excel_path": excel_path,
        "upload": upload,
        "profile_key": profile,
        "limit": int(limit),
        "trace": bool(trace),
        "no_ai": bool(no_ai),
        "provider": str(provider),
        "model": str(model),
        "review_model": str(review_model),
        "concurrency": int(concurrency),
    }


def _profile_index(app_config, default_profile: str | None) -> int:
    profiles = list(app_config.profiles.keys())
    return profiles.index(default_profile) if default_profile in profiles else 0


__all__ = ["product_matching_form", "_profile_index"]
