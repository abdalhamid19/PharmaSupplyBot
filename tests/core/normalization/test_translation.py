from __future__ import annotations

import unittest
from unittest.mock import patch

from src.core.normalization import translation


class _CachedTranslations:
    def get_many(self, cleaned_names: list[str]) -> dict[str, str]:
        return {
            translation.normalize_key_for_lru(name): f"EN:{name}"
            for name in cleaned_names
        }


class TranslationBatchTests(unittest.TestCase):
    def test_cached_only_cleans_each_input_once(self) -> None:
        names = ["  دواء  ", " ", "دواء", "دواء آخر"]

        with (
            patch.object(translation, "_clean", wraps=translation._clean) as clean,
            patch.object(
                translation, "_persistent", return_value=_CachedTranslations()
            ),
        ):
            translations = translation.ar_to_en_many_cached_only(names)

        self.assertEqual(clean.call_count, len(names))
        self.assertEqual(
            translations,
            {
                "  دواء  ": "EN:دواء",
                "دواء": "EN:دواء",
                "دواء آخر": "EN:دواء آخر",
            },
        )


if __name__ == "__main__":
    unittest.main()
