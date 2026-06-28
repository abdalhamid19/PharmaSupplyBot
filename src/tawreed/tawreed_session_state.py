"""Session state management for Tawreed authentication."""

from pathlib import Path


def auth_temp_state_path(state_path: Path) -> Path:
    """Return the temporary path used while validating a newly captured auth session."""
    return state_path.with_name(f"{state_path.stem}.tmp{state_path.suffix}")


def save_session_state(context, state_path: Path, is_intermediate: bool) -> None:
    """Persist the current browser storage state to disk."""
    try:
        context.storage_state(path=str(state_path))
        if is_intermediate:
            print(f"Saved intermediate session state: {state_path}")
    except Exception:
        pass


def promote_session_state(temp_state_path: Path, final_state_path: Path) -> None:
    """Replace the final saved session state with a validated temporary capture."""
    final_state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_state_path.replace(final_state_path)


def discard_session_state(state_path: Path) -> None:
    """Delete one temporary or invalid saved session state without surfacing cleanup errors."""
    try:
        state_path.unlink(missing_ok=True)
    except Exception:
        pass
