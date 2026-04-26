import unittest
from types import SimpleNamespace

from src.tawreed_session import SessionInvalidError, ensure_logged_in


class _FakePage:
    def __init__(self, ready_visible: bool, marker_visible: bool, login_visible: bool):
        self._ready_visible = ready_visible
        self._marker_visible = marker_visible
        self._login_visible = login_visible

    def wait_for_load_state(self, state: str) -> None:
        return None

    def locator(self, selector: str):
        return _FakeLocator(selector, self)


class _FakeLocator:
    def __init__(self, selector: str, page: _FakePage):
        self.selector = selector
        self.page = page

    @property
    def first(self):
        return self

    def wait_for(self, timeout: int = 0) -> None:
        is_ready_selector = self.selector == "#ready"
        is_marker_selector = self.selector == "#marker"
        if is_ready_selector and self.page._ready_visible:
            return None
        if is_marker_selector and self.page._marker_visible:
            return None
        raise RuntimeError("not visible")

    def is_visible(self, timeout: int = 0) -> bool:
        if self.selector in {"#email", "#password"}:
            return self.page._login_visible
        return False


class TawreedSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selectors = SimpleNamespace(
            login_email="#email",
            login_password="#password",
            logged_in_marker="#marker",
        )

    def test_valid_ready_surface_passes(self) -> None:
        page = _FakePage(ready_visible=True, marker_visible=False, login_visible=False)
        ensure_logged_in(page, self.selectors, timeout_ms=5000, ready_selector="#ready")

    def test_login_page_raises_clear_error(self) -> None:
        page = _FakePage(ready_visible=False, marker_visible=False, login_visible=True)
        with self.assertRaises(SessionInvalidError) as context:
            ensure_logged_in(page, self.selectors, timeout_ms=5000, ready_selector="#ready")
        self.assertIn("login page", str(context.exception))

    def test_unknown_surface_raises_page_not_ready_error(self) -> None:
        page = _FakePage(ready_visible=False, marker_visible=False, login_visible=False)
        with self.assertRaises(SessionInvalidError) as context:
            ensure_logged_in(page, self.selectors, timeout_ms=5000, ready_selector="#ready")
        self.assertIn("expected order surface", str(context.exception))


if __name__ == "__main__":
    unittest.main()
