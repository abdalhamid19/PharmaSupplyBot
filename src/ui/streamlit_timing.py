"""Timing-report helpers for Streamlit order summaries."""

from __future__ import annotations

import pandas as pd


def elapsed_seconds_values(rows: list[dict[str, str]]) -> list[float]:
    """Return parsed total elapsed seconds from rows that have the field populated."""
    return numeric_field_values(rows, "elapsed_seconds")


def match_elapsed_seconds_values(rows: list[dict[str, str]]) -> list[float]:
    """Return parsed matching-only elapsed seconds from rows that have the field populated."""
    return numeric_field_values(rows, "match_elapsed_seconds")


def numeric_field_values(rows: list[dict[str, str]], field_name: str) -> list[float]:
    """Return parsed float values from one populated summary field."""
    values: list[float] = []
    for row in rows:
        raw_value = str(row.get(field_name, "")).strip()
        if raw_value:
            values.append(float(raw_value))
    return values


def populated_elapsed_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return rows that include a populated total elapsed-seconds field."""
    return [row for row in rows if str(row.get("elapsed_seconds", "")).strip()]


def timing_breakdown(rows: list[dict[str, str]]) -> pd.DataFrame:
    """Return the compact timing summary dataframe for one row set."""
    elapsed_values = elapsed_seconds_values(rows)
    match_values = match_elapsed_seconds_values(rows)
    return pd.DataFrame(
        [
            _timing_metric("Average total seconds", average_value(elapsed_values)),
            _timing_metric("Average match seconds", average_value(match_values)),
            _timing_metric("Max total seconds", max(elapsed_values)),
            _timing_metric("Min total seconds", min(elapsed_values)),
        ]
    )


def average_value(values: list[float]) -> float:
    """Return the average value, or zero when the list is empty."""
    return round(sum(values) / len(values), 3) if values else 0.0


def _timing_metric(metric: str, value: float) -> dict[str, object]:
    """Return one timing summary row."""
    return {"metric": metric, "value": round(value, 3)}


def top_slowest_rows(rows: list[dict[str, str]]) -> pd.DataFrame:
    """Return the slowest summary rows, sorted by total elapsed seconds."""
    top_rows = sorted(
        populated_elapsed_rows(rows),
        key=lambda row: float(row["elapsed_seconds"]),
        reverse=True,
    )[:15]
    dataframe = pd.DataFrame(top_rows)
    columns = [
        "item_code",
        "item_name",
        "status",
        "elapsed_seconds",
        "match_elapsed_seconds",
        "matched_product_name",
    ]
    visible = [column for column in columns if column in dataframe.columns]
    return dataframe[visible] if visible else dataframe
