"""
Tests for security concern analysis in endpoint documentation.

Verifies that:
1. The docCreator prompt includes security analysis instructions
2. LLM responses with security concerns in descriptions are correctly parsed/saved
3. Fallback documentation does NOT include non-standard keys (OpenAPI compliant)
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch
from haystack.dataclasses import Document

from src.components.DocumentationCreator import DocumentationCreator
from src.utils.llm_json_handler import LLMJsonHandler
from prompts import doc_creator_prompt


class TestSecurityPrompt:
    """Verify the prompt instructs the LLM to include security analysis."""

    def test_prompt_contains_security_analysis_section(self):
        """The prompt template must have a SECURITY ANALYSIS section."""
        prompt_text = doc_creator_prompt.template
        assert "SECURITY" in prompt_text.upper(), \
            "Prompt must contain security analysis instructions"

    def test_prompt_mentions_common_security_concerns(self):
        """The prompt should mention typical API security risks."""
        prompt_text = doc_creator_prompt.template.lower()
        security_keywords = ["http", "token", "auth", "injection", "credential"]
        found = [kw for kw in security_keywords if kw in prompt_text]
        assert len(found) >= 3, \
            f"Prompt should mention at least 3 security keywords, found: {found}"

    def test_prompt_instructs_description_embedding(self):
        """Security concerns should be embedded in the description field."""
        prompt_text = doc_creator_prompt.template.lower()
        assert "description" in prompt_text, \
            "Prompt must instruct embedding security info in the description"


class TestSecurityInDocumentation:
    """Verify that generated documentation includes security analysis in description."""

    def test_save_outputs_preserves_description_with_security(self):
        """Swagger output must include description with security warnings (CommonMark)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(DocumentationCreator, '__init__', lambda self: None):
                creator = DocumentationCreator()
                creator.output_dir = tmpdir

                documentation = {
                    "method": "post",
                    "path": "/auth/login",
                    "swagger": {
                        "summary": "User login",
                        "description": (
                            "Authenticates a user with email and password.\n\n"
                            "---\n"
                            "**Security Concerns:**\n"
                            "- **HIGH** — Endpoint uses HTTP instead of HTTPS\n"
                            "- **MEDIUM** — No rate limiting detected\n"
                        ),
                        "parameters": [],
                        "responses": {
                            "200": {"description": "Login successful"},
                            "401": {"description": "Invalid credentials"}
                        },
                        "security": []
                    }
                }

                saved = creator._save_outputs("login", documentation, {
                    "method_type": "POST",
                    "method_path": "/auth/login"
                })

                with open(saved["swagger"]) as f:
                    data = json.load(f)

                # Security info should be in description, not custom keys
                assert "Security Concerns" in data["description"]
                assert "HTTP instead of HTTPS" in data["description"]
                # Ensure no non-standard keys exist at top level of swagger
                allowed_keys = {
                    "summary", "description", "operationId", "parameters",
                    "requestBody", "responses", "security", "tags",
                    "deprecated", "callbacks", "servers", "externalDocs",
                    "method", "path"  # our injected keys for merger
                }
                for key in data:
                    assert key in allowed_keys, \
                        f"Non-standard OpenAPI key found: '{key}'"


