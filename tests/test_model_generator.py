"""
Tests for ModelGenerator — verifies deterministic generation params for all providers.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestModelGeneratorDeterminism:
    """Verify that all providers are configured for deterministic output."""

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.OllamaChatGenerator")
    def test_ollama_defaults_to_zero_temperature(self, mock_ollama_cls, mock_config):
        mock_config.return_value = {
            "code_analyzer": {"active_generator": "ollama"},
            "generators": {"ollama": {"url": "http://localhost:11434", "model": "llama3"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        mg = ModelGenerator("code_analyzer")
        mg.get_generator()

        gen_kwargs = mock_ollama_cls.call_args.kwargs["generation_kwargs"]
        assert gen_kwargs["temperature"] == 0

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.OllamaChatGenerator")
    def test_ollama_respects_explicit_temperature(self, mock_ollama_cls, mock_config):
        mock_config.return_value = {
            "code_analyzer": {"active_generator": "ollama"},
            "generators": {"ollama": {"url": "http://localhost:11434", "model": "llama3"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        mg = ModelGenerator("code_analyzer", temperature=0.5)
        mg.get_generator()

        gen_kwargs = mock_ollama_cls.call_args.kwargs["generation_kwargs"]
        assert gen_kwargs["temperature"] == 0.5

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.OllamaChatGenerator")
    def test_ollama_passes_seed(self, mock_ollama_cls, mock_config):
        mock_config.return_value = {
            "code_analyzer": {"active_generator": "ollama"},
            "generators": {"ollama": {"url": "http://localhost:11434", "model": "llama3"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        mg = ModelGenerator("code_analyzer", seed=42)
        mg.get_generator()

        gen_kwargs = mock_ollama_cls.call_args.kwargs["generation_kwargs"]
        assert gen_kwargs["seed"] == 42

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.GoogleGenAIChatGenerator")
    def test_gemini_has_deterministic_defaults(self, mock_gemini_cls, mock_config):
        mock_config.return_value = {
            "doc_creator": {"active_generator": "gemini"},
            "generators": {"gemini": {"url": "https://gen.googleapis.com", "model": "gemini-2.5-flash"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        mg = ModelGenerator("doc_creator")
        mg.get_generator()

        gen_kwargs = mock_gemini_cls.call_args.kwargs["generation_kwargs"]
        assert gen_kwargs["temperature"] == 0
        assert gen_kwargs["top_p"] == 0.1
        assert gen_kwargs["response_mime_type"] == "application/json"
        assert gen_kwargs["thinking_budget"] == 0

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.GoogleGenAIChatGenerator")
    def test_gemini_passes_response_schema(self, mock_gemini_cls, mock_config):
        mock_config.return_value = {
            "doc_creator": {"active_generator": "gemini"},
            "generators": {"gemini": {"url": "https://gen.googleapis.com", "model": "gemini-2.5-flash"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        mg = ModelGenerator("doc_creator", format_schema=schema)
        mg.get_generator()

        gen_kwargs = mock_gemini_cls.call_args.kwargs["generation_kwargs"]
        assert gen_kwargs["response_schema"] == schema

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.GoogleGenAIChatGenerator")
    def test_gemini_passes_seed_when_provided(self, mock_gemini_cls, mock_config):
        mock_config.return_value = {
            "doc_creator": {"active_generator": "gemini"},
            "generators": {"gemini": {"url": "https://gen.googleapis.com", "model": "gemini-2.5-flash"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        mg = ModelGenerator("doc_creator", seed=42)
        mg.get_generator()

        gen_kwargs = mock_gemini_cls.call_args.kwargs["generation_kwargs"]
        assert gen_kwargs["seed"] == 42

    @patch("src.utils.modelGenerator.load_config")
    @patch("src.utils.modelGenerator.GoogleGenAIChatGenerator")
    def test_gemini_no_seed_when_not_provided(self, mock_gemini_cls, mock_config):
        mock_config.return_value = {
            "doc_creator": {"active_generator": "gemini"},
            "generators": {"gemini": {"url": "https://gen.googleapis.com", "model": "gemini-2.5-flash"}},
        }
        from src.utils.modelGenerator import ModelGenerator

        mg = ModelGenerator("doc_creator")
        mg.get_generator()

        gen_kwargs = mock_gemini_cls.call_args.kwargs["generation_kwargs"]
        assert "seed" not in gen_kwargs
