"""Credential-handling tests for scripts/llm_to_obsidian.py.

These cover the rule that a key is only ever sent to the endpoint of the provider it belongs to:
Pi's saved OpenAI/OpenRouter keys must never end up in a request to another provider's API.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "media-transcribe" / "scripts" / "llm_to_obsidian.py"
spec = importlib.util.spec_from_file_location("llm_to_obsidian", SCRIPT)
l2o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(l2o)

LLM_ENV = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "DEEPSEEK_API_KEY", "OPENAI_API_KEY",
           "OPENROUTER_API_KEY", "OLLAMA_API_KEY")


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in LLM_ENV}
    env.update(extra)
    return mock.patch.dict(os.environ, env, clear=True)


class ProviderMappingTest(unittest.TestCase):
    def test_known_endpoints(self):
        self.assertEqual(l2o.provider_of("https://api.deepseek.com"), "deepseek")
        self.assertEqual(l2o.provider_of("https://api.openai.com/v1"), "openai")
        self.assertEqual(l2o.provider_of("https://openrouter.ai/api"), "openrouter")

    def test_unknown_and_local_endpoints(self):
        self.assertIsNone(l2o.provider_of("https://example.com/v1"))
        self.assertTrue(l2o.is_local_endpoint("http://localhost:11434/v1"))
        self.assertTrue(l2o.is_local_endpoint("http://127.0.0.1:1234/v1"))
        self.assertFalse(l2o.is_local_endpoint("https://api.deepseek.com"))


class PiAuthTest(unittest.TestCase):
    def _home_with(self, payload):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        auth = Path(tmp.name) / ".pi" / "agent" / "auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_text(json.dumps(payload), encoding="utf-8")
        return tmp.name

    def test_only_the_matching_provider_key_is_returned(self):
        home = self._home_with({"openrouter": {"key": "sk-or-secret"}})
        with mock.patch.dict(os.environ, {"HOME": home}):
            self.assertIsNone(l2o.key_from_pi_auth("deepseek"))
            self.assertIsNone(l2o.key_from_pi_auth("openai"))
            self.assertEqual(l2o.key_from_pi_auth("openrouter"), "sk-or-secret")

    def test_no_provider_no_key(self):
        home = self._home_with({"deepseek": {"key": "sk-deepseek"}})
        with mock.patch.dict(os.environ, {"HOME": home}):
            self.assertIsNone(l2o.key_from_pi_auth(None))


class ResolveLlmTest(unittest.TestCase):
    def _home_with(self, payload):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        auth = Path(tmp.name) / ".pi" / "agent" / "auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_text(json.dumps(payload), encoding="utf-8")
        return tmp.name

    def test_openai_endpoint_never_receives_a_foreign_key(self):
        """The reported issue: only an OpenRouter key saved, DeepSeek is the default endpoint."""
        home = self._home_with({"openrouter": {"key": "sk-or-secret"}})
        with clean_env(HOME=home):
            key, base_url, model, *_ = l2o.resolve_llm({})
            self.assertEqual(base_url, "https://api.deepseek.com")
            self.assertIsNone(key, "an OpenRouter key must not be used for the DeepSeek endpoint")

    def test_matching_saved_key_is_used(self):
        home = self._home_with({"deepseek": {"key": "sk-deepseek"}, "openrouter": {"key": "sk-or"}})
        with clean_env(HOME=home):
            key, base_url, model, *_ = l2o.resolve_llm({})
            self.assertEqual(key, "sk-deepseek")
            self.assertEqual(model, "deepseek-chat")

    def test_openai_endpoint_uses_openai_key_and_asks_for_a_model(self):
        home = self._home_with({"openai": {"key": "sk-openai"}, "deepseek": {"key": "sk-deepseek"}})
        with clean_env(HOME=home, OPENAI_API_KEY="sk-openai"):
            key, base_url, model, *_ = l2o.resolve_llm({"llm": {"provider": "openai"}})
            self.assertEqual(base_url, "https://api.openai.com")
            self.assertEqual(key, "sk-openai")
            self.assertEqual(model, "", "no default model should be invented for OpenAI")

    def test_local_endpoint_needs_no_key(self):
        with clean_env(HOME=tempfile.mkdtemp()):
            key, base_url, model, *_ = l2o.resolve_llm(
                {"llm": {"baseUrl": "http://localhost:11434/v1", "model": "qwen3:8b"}}
            )
            self.assertEqual(key, "local")
            self.assertEqual(model, "qwen3:8b")

    def test_explicit_env_key_is_respected(self):
        with clean_env(HOME=tempfile.mkdtemp(), LLM_API_KEY="sk-explicit"):
            key, *_ = l2o.resolve_llm({})
            self.assertEqual(key, "sk-explicit")


if __name__ == "__main__":
    unittest.main()
