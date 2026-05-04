import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from src.core.config.config_factory import build_runtime_config
from src.tawreed.tawreed_checkout import confirm_order


class TawreedCheckoutTests(unittest.TestCase):
    def test_runtime_submit_order_defaults_to_false(self) -> None:
        runtime = build_runtime_config({})
        self.assertFalse(runtime.submit_order)

    def test_confirm_order_skips_submission_when_disabled(self) -> None:
        bot = SimpleNamespace(
            profile_key="wardany",
            config=SimpleNamespace(runtime=SimpleNamespace(submit_order=False)),
            selectors=SimpleNamespace(confirm_order_button="button"),
        )
        page = object()
        output = io.StringIO()

        with redirect_stdout(output):
            confirm_order(bot, page)

        self.assertIn("manual human review", output.getvalue())


if __name__ == "__main__":
    unittest.main()
