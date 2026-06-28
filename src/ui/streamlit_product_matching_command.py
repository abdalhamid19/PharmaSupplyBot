"""Product matching command building for Streamlit."""

from __future__ import annotations

from pathlib import Path


def product_matching_command(
    config_path: Path, values: dict, excel_path: Path, output_path: Path
) -> list[str]:
    """Return CLI arguments for one product matching run."""
    command = [
        "match-products", "--config", str(config_path),
        "--profile", str(values["profile_key"]),
        "--excel", str(excel_path), "--output", str(output_path),
        "--limit", str(values["limit"]),
        "--concurrency", str(values["concurrency"]),
    ]
    if values["trace"]:
        command.append("--trace")
    if values["no_ai"]:
        command.append("--no-ai")
    command.extend(_optional_arg("--provider", values["provider"]))
    command.extend(_optional_arg("--model", values["model"]))
    command.extend(_optional_arg("--review-model", values["review_model"]))
    return command


def _optional_arg(name: str, value: object) -> list[str]:
    text = str(value or "").strip()
    return [name, text] if text else []


__all__ = ["product_matching_command", "_optional_arg"]
