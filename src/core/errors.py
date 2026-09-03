"""Domain exception hierarchy for PharmaSupplyBot.

Every error that bubbles up to the CLI layer should be a subclass of
:class:`PharmaSupplyError`. This gives us:

* A single catch site in ``run.main()`` that converts exceptions to
  proper exit codes.
* Predictable ``exit_code`` per error category (useful for CI / scripts).
* Better ``logger.exception()`` records because the exception type itself
  encodes the failure category.

Exit code conventions (kept stable for external scripts):

    0    success
    1    generic / unexpected
    2    configuration error
    3    authentication / session error
    4    network / API unavailable
    5    validation / user input error
    6    artifact / file I/O error
    7    execution mode / runtime conflict
    99   unhandled exception
"""

from __future__ import annotations


class PharmaSupplyError(Exception):
    """Base class for all expected domain errors.

    Subclasses set ``exit_code`` to indicate how the CLI should exit.
    Carries optional structured context (``profile``, ``run_id``, ...)
    so that callers and loggers can correlate the failure.
    """

    exit_code: int = 1

    def __init__(
        self,
        message: str = "",
        *,
        profile: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.profile = profile
        self.hint = hint

    def __str__(self) -> str:  # pragma: no cover - trivial
        parts = [self.message]
        if self.profile:
            parts.append(f"profile={self.profile}")
        if self.hint:
            parts.append(f"hint={self.hint}")
        return " | ".join(parts)


# ─────────────────────────── Configuration ───────────────────────────


class ConfigError(PharmaSupplyError):
    """The application config is missing, malformed, or inconsistent."""

    exit_code = 2


# ─────────────────────────── Authentication ──────────────────────────


class AuthError(PharmaSupplyError):
    """The Playwright storage state is missing, expired, or unusable."""

    exit_code = 3


# ─────────────────────────── Network / API ───────────────────────────


class APIUnavailableError(PharmaSupplyError):
    """A required external API is unreachable or returns a fatal error."""

    exit_code = 4


# ─────────────────────────── Validation ──────────────────────────────


class ValidationError(PharmaSupplyError):
    """User-supplied input is missing required fields or violates a rule."""

    exit_code = 5


# ─────────────────────────── I/O / artifacts ─────────────────────────


class ArtifactError(PharmaSupplyError):
    """Reading or writing an artifact file (xlsx, csv, json, ...) failed."""

    exit_code = 6


# ─────────────────────────── Execution mode ──────────────────────────


class ExecutionModeError(PharmaSupplyError):
    """The chosen execution mode conflicts with the current state."""

    exit_code = 7


__all__ = [
    "PharmaSupplyError",
    "ConfigError",
    "AuthError",
    "APIUnavailableError",
    "ValidationError",
    "ArtifactError",
    "ExecutionModeError",
]