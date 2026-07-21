"""Tests for the domain exception hierarchy."""

from __future__ import annotations

import pytest

from src.core.errors import (
    APIUnavailableError,
    ArtifactError,
    AuthError,
    ConfigError,
    ExecutionModeError,
    PharmaSupplyError,
    ValidationError,
)


@pytest.mark.parametrize(
    "cls,expected_code",
    [
        (PharmaSupplyError, 1),
        (ConfigError, 2),
        (AuthError, 3),
        (APIUnavailableError, 4),
        (ValidationError, 5),
        (ArtifactError, 6),
        (ExecutionModeError, 7),
    ],
)
def test_exit_codes_are_stable(cls: type[PharmaSupplyError], expected_code: int) -> None:
    """Lock in exit codes so external scripts can rely on them."""
    assert cls().exit_code == expected_code
    assert cls("x").exit_code == expected_code


def test_all_classes_inherit_from_base() -> None:
    for cls in (ConfigError, AuthError, APIUnavailableError,
                ValidationError, ArtifactError, ExecutionModeError):
        assert issubclass(cls, PharmaSupplyError)
        assert cls is not PharmaSupplyError


def test_str_includes_message_only_when_no_context() -> None:
    err = ValidationError("bad input")
    assert str(err) == "bad input"


def test_str_includes_profile_when_provided() -> None:
    err = AuthError("expired", profile="wardany")
    text = str(err)
    assert "expired" in text
    assert "profile=wardany" in text


def test_str_includes_hint_when_provided() -> None:
    err = ConfigError("missing field", hint="set FOO in .env")
    text = str(err)
    assert "missing field" in text
    assert "hint=set FOO in .env" in text


def test_attributes_stored_on_instance() -> None:
    err = APIUnavailableError("timeout", profile="p1", hint="retry later")
    assert err.message == "timeout"
    assert err.profile == "p1"
    assert err.hint == "retry later"


def test_default_message_is_class_name() -> None:
    err = PharmaSupplyError()
    assert err.message == "PharmaSupplyError"


def test_can_be_raised_and_caught_as_base() -> None:
    with pytest.raises(PharmaSupplyError) as info:
        raise ValidationError("nope")
    assert isinstance(info.value, ValidationError)
    assert info.value.exit_code == 5