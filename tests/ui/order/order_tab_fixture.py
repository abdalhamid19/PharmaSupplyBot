"""Standalone Streamlit test fixture for the Order tab.

Used by ``tests/ui/order/test_run_target_excel_target.py`` so the
test runner can import the Order tab widgets without touching
``streamlit_app.py`` (which mounts the full app).
"""

from pathlib import Path

from src.core.config.config_models import (
    AppConfig,
    DatabaseConfig,
    ExcelConfig,
    ExcelTargetConfig,
    MatchingConfig,
    ProfileConfig,
    RuntimeConfig,
)
from src.ui.order.streamlit_order import render_order_tab

CONFIG = AppConfig(
    base_url="",
    excel=ExcelConfig(code_col="كود", name_col="إسم الصنف", qty_col="كمية النقص"),
    profiles={
        "wardany": ProfileConfig(
            display_name="Wardany",
            pharmacy_switch={"enabled": False, "pharmacy_name": ""},
        )
    },
    excel_targets={
        "alnasr": ExcelTargetConfig(
            name_col="صنف",
            price_col="سعر",
            discount_col="الخصم",
            display_name="صيدلية النصر",
            sheet="",
            header_row=0,
            enabled=True,
        )
    },
    selectors={},
    warehouse_strategy={},
    matching=MatchingConfig(),
    runtime=RuntimeConfig(),
    database=DatabaseConfig(),
)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Order tab fixture", layout="wide")
    render_order_tab(CONFIG, "wardany", Path("state/config.yaml"))


if __name__ == "__main__":
    main()