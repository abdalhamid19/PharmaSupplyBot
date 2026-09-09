from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

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

    def test_many_uses_normalized_cache_keys_before_provider(self) -> None:
        cache = Mock()
        cache.get_many.return_value = {
            translation.normalize_key_for_lru("Ø¯ÙˆØ§Ø¡ Ø¢Ø®Ø±"): "Cached English"
        }

        with (
            patch.object(translation, "_persistent", return_value=cache),
            patch.object(translation, "_call_cohere_batch") as batch,
        ):
            translations = translation.ar_to_en_many(["Ø¯ÙˆØ§Ø¡  Ø¢Ø®Ø±"])

        self.assertEqual(translations, {"Ø¯ÙˆØ§Ø¡ Ø¢Ø®Ø±": "Cached English"})
        batch.assert_not_called()

    def test_many_sends_at_most_fifty_names_per_provider_call(self) -> None:
        names = [f"Ø¯ÙˆØ§Ø¡ {index}" for index in range(51)]
        cache = Mock()
        cache.get_many.return_value = {}

        def translate_batch(model: str, chunk: list[str]) -> list[str]:
            return [f"EN:{name}" for name in chunk]

        with (
            patch.object(translation, "_persistent", return_value=cache),
            patch.object(
                translation, "_call_cohere_batch", side_effect=translate_batch
            ) as batch,
        ):
            translations = translation.ar_to_en_many(names)

        self.assertEqual(len(translations), 51)
        self.assertEqual([len(args[0][1]) for args in batch.call_args_list], [50, 1])

    def test_many_does_not_make_per_item_fallback_calls(self) -> None:
        names = ["Ø¯ÙˆØ§Ø¡ 1", "Ø¯ÙˆØ§Ø¡ 2"]
        cache = Mock()
        cache.get_many.return_value = {}

        with (
            patch.object(translation, "_persistent", return_value=cache),
            patch.object(
                translation, "_call_cohere_batch", return_value=[None, "EN:2"]
            ),
            patch.object(translation, "_call_cohere") as single,
        ):
            translations = translation.ar_to_en_many(names)

        self.assertEqual(translations, {"Ø¯ÙˆØ§Ø¡ 1": "", "Ø¯ÙˆØ§Ø¡ 2": "EN:2"})
        single.assert_not_called()


class _FakeCohereClient:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def chat(self, **_kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(message=SimpleNamespace(content=outcome))


class TranslationProviderFailoverTests(unittest.TestCase):
    def setUp(self) -> None:
        translation._reset_provider_state()

    def tearDown(self) -> None:
        translation._reset_provider_state()

    def test_monthly_quota_failure_moves_batch_to_next_key(self) -> None:
        first = _FakeCohereClient(
            RuntimeError("429: limited to 1000 API calls / month")
        )
        second = _FakeCohereClient("1. PANADOL 30 TABLETS")

        with (
            patch.dict(
                "os.environ",
                {"COHERE_API_KEY_1": "first", "COHERE_API_KEY_2": "second"},
                clear=True,
            ),
            patch.object(translation, "_get_client", side_effect=[first, second]),
        ):
            result = translation._call_cohere_batch("model", ["بانادول 30 قرص"])

        self.assertEqual(result, ["PANADOL 30 TABLETS"])
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)

    def test_per_minute_failure_retries_same_key(self) -> None:
        client = _FakeCohereClient(
            RuntimeError("limited to 20 API calls / minute"),
            "1. PANADOL",
        )

        with (
            patch.dict("os.environ", {"COHERE_API_KEY_1": "first"}, clear=True),
            patch.object(translation, "_get_client", return_value=client),
            patch.object(translation.time, "sleep") as sleep,
        ):
            result = translation._call_cohere_batch("model", ["بانادول"])

        self.assertEqual(result, ["PANADOL"])
        self.assertEqual(client.calls, 2)
        sleep.assert_called_once_with(1.0)

    def test_repeated_per_minute_failure_does_not_switch_key(self) -> None:
        first = _FakeCohereClient(
            RuntimeError("limited to 20 API calls / minute"),
            RuntimeError("limited to 20 API calls / minute"),
        )
        second = _FakeCohereClient("1. SHOULD NOT RUN")

        with (
            patch.dict(
                "os.environ",
                {"COHERE_API_KEY_1": "first", "COHERE_API_KEY_2": "second"},
                clear=True,
            ),
            patch.object(translation, "_get_client", side_effect=[first, second]),
            patch.object(translation.time, "sleep"),
        ):
            result = translation._call_cohere_batch("model", ["بانادول"])

        self.assertEqual(result, [None])
        self.assertEqual(first.calls, 2)
        self.assertEqual(second.calls, 0)

    def test_all_terminal_keys_leave_batch_untranslated(self) -> None:
        first = _FakeCohereClient(RuntimeError("maximum billing reached"))
        second = _FakeCohereClient(RuntimeError("invalid api token"))

        with (
            patch.dict(
                "os.environ",
                {"COHERE_API_KEY_1": "first", "COHERE_API_KEY_2": "second"},
                clear=True,
            ),
            patch.object(translation, "_get_client", side_effect=[first, second]),
        ):
            result = translation._call_cohere_batch("model", ["اسم غير معروف"])
            quota_dead = translation.provider_status()["quota_dead"]

        self.assertEqual(result, [None])
        self.assertTrue(quota_dead)

    def test_open_breaker_prevents_batch_network_calls(self) -> None:
        client = _FakeCohereClient("1. SHOULD NOT RUN")
        with (
            patch.dict("os.environ", {"COHERE_API_KEY_1": "first"}, clear=True),
            patch.object(translation, "_get_client", return_value=client),
            patch.object(translation._breaker, "allow", return_value=False),
        ):
            result = translation._call_cohere_batch("model", ["بانادول"])

        self.assertEqual(result, [None])
        self.assertEqual(client.calls, 0)

    def test_transient_failure_does_not_consume_second_key(self) -> None:
        first = _FakeCohereClient(RuntimeError("temporary upstream failure"))
        second = _FakeCohereClient("1. SHOULD NOT RUN")
        with (
            patch.dict(
                "os.environ",
                {"COHERE_API_KEY_1": "first", "COHERE_API_KEY_2": "second"},
                clear=True,
            ),
            patch.object(translation, "_get_client", side_effect=[first, second]),
        ):
            result = translation._call_cohere_batch("model", ["بانادول"])

        self.assertEqual(result, [None])
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 0)


class TranslationCachePersistenceTests(unittest.TestCase):
    def test_provider_results_are_persisted_and_reused(self) -> None:
        entries: dict[str, str] = {}
        models: list[str] = []

        class MemoryCache:
            def get_many(self, names: list[str]) -> dict[str, str]:
                return {
                    translation.normalize_key_for_lru(name): entries[
                        translation.normalize_key_for_lru(name)
                    ]
                    for name in names
                    if translation.normalize_key_for_lru(name) in entries
                }

            def put_many(self, values: dict[str, str], model: str) -> int:
                for name, value in values.items():
                    entries[translation.normalize_key_for_lru(name)] = value
                models.append(model)
                return len(values)

        name = "un cached medicine"
        cache = MemoryCache()
        with (
            patch.object(translation, "_persistent", return_value=cache),
            patch.object(
                translation,
                "_call_cohere_batch",
                return_value=["NEW MEDICINE"],
            ) as batch,
        ):
            first = translation.ar_to_en_many([name])
            second = translation.ar_to_en_many([name])

        self.assertEqual(first, {name: "NEW MEDICINE"})
        self.assertEqual(second, first)
        batch.assert_called_once()
        self.assertEqual(models, [translation._configured_model()])


if __name__ == "__main__":
    unittest.main()
