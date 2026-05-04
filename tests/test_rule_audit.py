import unittest

from tools import rule_audit


class RuleAuditTests(unittest.TestCase):
    def test_unexpected_violations_filters_known_baseline(self) -> None:
        violations = [
            "src/excel.py:file_lines:141",
            "src/new_module.py:file_lines:101",
        ]

        unexpected = rule_audit.unexpected_violations(violations)

        self.assertEqual(unexpected, ["src/new_module.py:file_lines:101"])

    def test_baseline_violations_returns_only_known_debt(self) -> None:
        violations = [
            "src/excel.py:file_lines:141",
            "src/new_module.py:file_lines:101",
        ]

        remaining = rule_audit.baseline_violations(violations)

        self.assertEqual(remaining, ["src/excel.py:file_lines:141"])

    def test_violation_key_ignores_improving_measured_values(self) -> None:
        self.assertEqual(
            rule_audit.violation_key("src/excel.py:file_lines:141"),
            "src/excel.py:file_lines",
        )
        self.assertEqual(
            rule_audit.violation_key("src/tawreed.py:95:function_lines:_auth:49"),
            "src/tawreed.py:95:function_lines:_auth",
        )


if __name__ == "__main__":
    unittest.main()
