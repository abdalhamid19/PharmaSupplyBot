"""Main page composition for the Streamlit GUI."""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from .config import load_config
from .streamlit_auth import render_auth_tab
from .streamlit_order import render_order_tab
from .streamlit_overview import render_overview
from .streamlit_results import render_results_tab
from .streamlit_shared import APP_TITLE, sidebar_config_path


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
    config_path = sidebar_config_path()
    try:
        app_config = load_config(config_path)
    except Exception as error:
        st.error(f"Could not load config: {error}")
        st.stop()
    st.sidebar.success(f"Loaded config: `{config_path}`")
    return app_config, config_path


def first_profile_key(app_config) -> str | None:
    """Return the first configured profile key when available."""
    profile_options = list(app_config.profiles.keys())
    return profile_options[0] if profile_options else None


def render_main_tabs(app_config, default_profile: str | None, config_path) -> None:
    """Render the main Streamlit tabs."""
    overview_tab, auth_tab, order_tab, results_tab = st.tabs(
        ["Overview", "Auth", "Order", "Results"]
    )
    with overview_tab:
        render_overview(app_config)
    with auth_tab:
        render_auth_tab(app_config, default_profile)
    with order_tab:
        render_order_tab(app_config, default_profile, config_path)
    with results_tab:
        render_results_tab(default_profile)
