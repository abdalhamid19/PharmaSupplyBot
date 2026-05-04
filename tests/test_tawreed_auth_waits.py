import unittest
from pathlib import Path

from src.tawreed.tawreed_auth_waits import wait_for_login_detection


class _FakePage:
    def __init__(self, url: str, marker_visible: bool, login_visible: bool):
        self.url = url
        self.marker_visible = marker_visible
        self.login_visible = login_visible

    def locator(self, selector: str):
        return _FakeLocator(self, selector)


class _FakeLocator:
    def __init__(self, page: _FakePage, selector: str):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    def wait_for(self, timeout: int = 0) -> None:
        if self.selector == "#marker" and self.page.marker_visible:
            return None
        raise RuntimeError("not visible")

    def is_visible(self, timeout: int = 0) -> bool:
        if self.selector in {"#email", "#password"}:
            return self.page.login_visible
        return False


class TawreedAuthWaitsTests(unittest.TestCase):
    def test_wait_for_login_detection_exits_when_marker_appears(self) -> None:
        page = _FakePage("https://seller.tawreed.io/#/login", marker_visible=True, login_visible=True)
        detected = wait_for_login_detection(
            page,
            context=object(),
            wait_seconds=10,
            login_email_selector="#email",
            login_password_selector="#password",
            logged_in_marker="#marker",
            state_path=Path("state/wardany.json"),
            save_session_state=lambda *_args, **_kwargs: None,
        )
        self.assertTrue(detected)

    def test_wait_for_login_detection_exits_when_login_form_disappears(self) -> None:
        page = _FakePage("https://seller.tawreed.io/#/login", marker_visible=False, login_visible=False)
        detected = wait_for_login_detection(
            page,
            context=object(),
            wait_seconds=10,
            login_email_selector="#email",
            login_password_selector="#password",
            logged_in_marker="#marker",
            state_path=Path("state/wardany.json"),
            save_session_state=lambda *_args, **_kwargs: None,
        )
        self.assertTrue(detected)

    def test_wait_for_login_detection_exits_when_route_leaves_login(self) -> None:
        page = _FakePage("https://seller.tawreed.io/#/home", marker_visible=False, login_visible=True)
        detected = wait_for_login_detection(
            page,
            context=object(),
            wait_seconds=10,
            login_email_selector="#email",
            login_password_selector="#password",
            logged_in_marker="#marker",
            state_path=Path("state/wardany.json"),
            save_session_state=lambda *_args, **_kwargs: None,
        )
        self.assertTrue(detected)

    def test_wait_for_login_detection_skips_intermediate_saves_when_disabled(self) -> None:
        page = _FakePage("https://seller.tawreed.io/#/login", marker_visible=False, login_visible=True)
        save_calls = []
        detected = wait_for_login_detection(
            page,
            context=object(),
            wait_seconds=1,
            login_email_selector="#email",
            login_password_selector="#password",
            logged_in_marker="#marker",
            state_path=Path("state/wardany.json"),
            save_session_state=lambda *_args, **_kwargs: save_calls.append("saved"),
            save_intermediate=False,
        )
        self.assertFalse(detected)
        self.assertEqual(save_calls, [])


if __name__ == "__main__":
    unittest.main()
