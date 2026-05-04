"""Main page composition for the Streamlit GUI."""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from ..core.config.config import load_config
from .streamlit_auth import render_auth_tab
from .streamlit_order import render_order_tab
from .streamlit_overview import render_overview
from .streamlit_prevented_items import render_prevented_items_tab
from .streamlit_remove_cart import render_remove_cart_tab
from .streamlit_results import render_results_tab
from .streamlit_shared import APP_TITLE, FALLBACK_CONFIG_PATH, resolved_streamlit_config_path, sidebar_config_path


def main() -> None:
    """Render the Streamlit application."""
    load_dotenv()
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Tawreed authentication, order execution, and result review from one UI.")
    app_config, config_path = loaded_app_config()
    default_profile = first_profile_key(app_config)
    render_main_tabs(app_config, default_profile, config_path)


def loaded_app_config():
    """Return the loaded application config and its selected path, or stop on failure."""
    selected_config_path = sidebar_config_path()
    config_path = resolved_streamlit_config_path(selected_config_path)
    try:
        app_config = load_config(config_path)
    except Exception as error:
        st.error(f"Could not load config: {error}")
        st.stop()
    st.sidebar.success(f"Loaded config: `{config_path}`")
    maybe_warn_fallback_config(selected_config_path, config_path)
    return app_config, config_path


def maybe_warn_fallback_config(selected_config_path, loaded_config_path) -> None:
    """Warn when Streamlit falls back from config.yaml to config.example.yaml."""
    if selected_config_path == loaded_config_path:
        return
    if loaded_config_path != FALLBACK_CONFIG_PATH:
        return
    st.warning(
        "Using `config.example.yaml` because `config.yaml` was not found. "
        "Provide a real `config.yaml` for production settings."
    )


def first_profile_key(app_config) -> str | None:
    """Return the first configured profile key when available."""
    profile_options = list(app_config.profiles.keys())
    return profile_options[0] if profile_options else None


def render_main_tabs(app_config, default_profile: str | None, config_path) -> None:
    """Render the main Streamlit tabs."""
    overview_tab, auth_tab, order_tab, prevented_items_tab, remove_cart_tab, results_tab = st.tabs(
        ["Overview", "Auth", "Order", "Prevented items", "Remove cart items", "Results"]
    )
    with overview_tab:
        render_overview(app_config)
    with auth_tab:
        render_auth_tab(app_config, default_profile, config_path)
    with order_tab:
        render_order_tab(app_config, default_profile, config_path)
    with prevented_items_tab:
        render_prevented_items_tab()
    with remove_cart_tab:
        render_remove_cart_tab(app_config, default_profile, config_path)
    with results_tab:
        render_results_tab(default_profile)
