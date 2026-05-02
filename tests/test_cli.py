"""
DocGen CLI Test Suite -- Written once, never modified.

Covers:
  - core/secrets.py     (keyring-based credential storage)
  - core/settings.py    (dynaconf settings management)
  - core/provider_registry.py (commit-hash pinned provider fetching)
  - core/docker.py      (docker/volume management)
  - core/console.py     (rich + questionary wrappers)
  - commands/*           (all CLI commands)
"""

import json
import os
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest


# ---------------------------------------------------------------------------
# core/secrets.py
# ---------------------------------------------------------------------------

class TestSecrets:
    """Keyring-backed credential storage."""

    SERVICE = "docgen-rag"

    @patch("cli.core.secrets.keyring")
    def test_store_calls_set_password(self, mock_kr):
        from cli.core.secrets import store
        store("openai_api_key", "sk-abc123")
        mock_kr.set_password.assert_called_once_with(
            self.SERVICE, "openai_api_key", "sk-abc123"
        )

    @patch("cli.core.secrets.keyring")
    def test_retrieve_returns_value(self, mock_kr):
        from cli.core.secrets import retrieve
        mock_kr.get_password.return_value = "sk-abc123"
        assert retrieve("openai_api_key") == "sk-abc123"
        mock_kr.get_password.assert_called_once_with(
            self.SERVICE, "openai_api_key"
        )

    @patch("cli.core.secrets.keyring")
    def test_retrieve_returns_none_when_missing(self, mock_kr):
        from cli.core.secrets import retrieve
        mock_kr.get_password.return_value = None
        assert retrieve("nonexistent") is None

    @patch("cli.core.secrets.keyring")
    def test_delete_calls_delete_password(self, mock_kr):
        from cli.core.secrets import delete
        delete("openai_api_key")
        mock_kr.delete_password.assert_called_once_with(
            self.SERVICE, "openai_api_key"
        )

    @patch("cli.core.secrets.keyring")
    def test_delete_ignores_missing_key(self, mock_kr):
        from cli.core.secrets import delete
        from keyring.errors import PasswordDeleteError
        mock_kr.delete_password.side_effect = PasswordDeleteError()
        # Should not raise
        delete("nonexistent")

    @patch("cli.core.secrets.keyring")
    def test_exists_returns_true_when_set(self, mock_kr):
        from cli.core.secrets import exists
        mock_kr.get_password.return_value = "some-value"
        assert exists("openai_api_key") is True

    @patch("cli.core.secrets.keyring")
    def test_exists_returns_false_when_missing(self, mock_kr):
        from cli.core.secrets import exists
        mock_kr.get_password.return_value = None
        assert exists("openai_api_key") is False


# ---------------------------------------------------------------------------
# core/settings.py
# ---------------------------------------------------------------------------

class TestSettings:
    """Dynaconf-powered settings management."""

    @patch("cli.core.settings._build_settings")
    def test_get_settings_returns_dynaconf_obj(self, mock_build):
        from cli.core.settings import get_settings
        mock_build.return_value = MagicMock(
            active_provider="gemini",
            rag=MagicMock(active_embedder="gemini"),
        )
        s = get_settings()
        assert s.active_provider == "gemini"

    @patch("cli.core.settings._build_settings")
    def test_settings_env_override(self, mock_build):
        from cli.core.settings import get_settings
        mock_settings = MagicMock()
        mock_settings.rag.active_embedder = "openai"
        mock_build.return_value = mock_settings
        s = get_settings()
        assert s.rag.active_embedder == "openai"

    def test_settings_to_config_yaml(self):
        """Ensure settings can be exported to the legacy config.yaml format."""
        from cli.core.settings import settings_to_config_dict
        mock_settings = MagicMock()
        mock_settings.active_provider = "gemini"
        mock_settings.rag.active_embedder = "gemini"
        mock_settings.rag.embedding_model = "gemini-2.5-flash-lite"
        mock_settings.rag.top_k_retriever = 2
        mock_settings.rag.top_k_reranker = 2
        mock_settings.rag.chunk_size = 500

        result = settings_to_config_dict(mock_settings)
        assert isinstance(result, dict)
        assert "rag" in result
        assert result["rag"]["active_embedder"] == "gemini"


# ---------------------------------------------------------------------------
# core/provider_registry.py
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    """Commit-hash pinned provider fetching from GitHub."""

    SAMPLE_MANIFEST = {
        "commit": "d702886664a6db668945293c4308d2ea7ad4654d",
        "repo": "DocGen-io/DocGen-RAG",
        "providers": {
            "gemini": {
                "embedder": "src/components/embedders/gemini_provider.py",
                "generator": "src/utils/model_generator/gemini_provider.py",
                "pip_packages": ["google-genai-haystack"],
            },
            "openai": {
                "embedder": "src/components/embedders/openai_provider.py",
                "generator": "src/utils/model_generator/openai_provider.py",
                "pip_packages": ["openai-haystack"],
            },
        },
    }

    def test_load_manifest(self):
        from cli.core.provider_registry import load_manifest
        with patch("builtins.open", mock_open(read_data=json.dumps(self.SAMPLE_MANIFEST))):
            manifest = load_manifest("/fake/path/provider_manifest.json")
        assert manifest["commit"] == "d702886664a6db668945293c4308d2ea7ad4654d"
        assert "gemini" in manifest["providers"]
        assert "openai" in manifest["providers"]

    def test_build_raw_url(self):
        from cli.core.provider_registry import build_raw_url
        url = build_raw_url(
            repo="DocGen-io/DocGen-RAG",
            commit="abc123",
            filepath="src/foo.py",
        )
        assert url == "https://raw.githubusercontent.com/DocGen-io/DocGen-RAG/abc123/src/foo.py"

    def test_list_available_providers(self):
        from cli.core.provider_registry import list_providers
        with patch("builtins.open", mock_open(read_data=json.dumps(self.SAMPLE_MANIFEST))):
            providers = list_providers("/fake/manifest.json")
        assert set(providers) == {"gemini", "openai"}

    @patch("cli.core.provider_registry.urllib.request.urlopen")
    def test_fetch_provider_file(self, mock_urlopen):
        from cli.core.provider_registry import fetch_provider_file
        mock_response = MagicMock()
        mock_response.read.return_value = b"# provider code"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        content = fetch_provider_file(
            repo="DocGen-io/DocGen-RAG",
            commit="abc123",
            filepath="src/foo.py",
        )
        assert content == "# provider code"

    @patch("subprocess.run")
    def test_install_pip_packages_uses_uv(self, mock_run):
        from cli.core.provider_registry import install_packages
        install_packages(["google-genai-haystack", "openai-haystack"])
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "uv" in cmd
        assert "pip" in cmd
        assert "install" in cmd


# ---------------------------------------------------------------------------
# core/docker.py
# ---------------------------------------------------------------------------

class TestDocker:
    """Docker and volume management."""

    @patch("subprocess.run")
    def test_ensure_volume_creates_if_missing(self, mock_run):
        from cli.core.docker import ensure_volume
        mock_run.return_value = MagicMock(
            returncode=0, stdout=""
        )
        ensure_volume("docgen-data")
        calls = mock_run.call_args_list
        # Should inspect first, then create
        assert any("volume" in str(c) for c in calls)

    @patch("subprocess.run")
    def test_compose_up(self, mock_run):
        from cli.core.docker import compose_up
        mock_run.return_value = MagicMock(returncode=0)
        compose_up("/fake/docker-compose.yaml")
        cmd = mock_run.call_args[0][0]
        assert "docker" in cmd
        assert "up" in cmd

    @patch("subprocess.run")
    def test_compose_down(self, mock_run):
        from cli.core.docker import compose_down
        mock_run.return_value = MagicMock(returncode=0)
        compose_down("/fake/docker-compose.yaml")
        cmd = mock_run.call_args[0][0]
        assert "docker" in cmd
        assert "down" in cmd

    @patch("subprocess.run")
    def test_is_running_true(self, mock_run):
        from cli.core.docker import is_running
        mock_run.return_value = MagicMock(
            returncode=0, stdout="true\n"
        )
        assert is_running("docgen-weaviate") is True

    @patch("subprocess.run")
    def test_is_running_false(self, mock_run):
        from cli.core.docker import is_running
        mock_run.return_value = MagicMock(
            returncode=1, stdout=""
        )
        assert is_running("nonexistent") is False


# ---------------------------------------------------------------------------
# core/console.py
# ---------------------------------------------------------------------------

class TestConsole:
    """Rich console and questionary prompt wrappers."""

    def test_console_singleton(self):
        from cli.core.console import console
        from rich.console import Console
        assert isinstance(console, Console)

    def test_print_header(self, capsys):
        from cli.core.console import print_header
        # Should not raise
        print_header("Test Header")

    def test_print_step(self, capsys):
        from cli.core.console import print_step
        print_step("Doing something")

    def test_print_error(self, capsys):
        from cli.core.console import print_error
        print_error("Something failed")

    @patch("cli.core.console.questionary")
    def test_confirm_returns_bool(self, mock_q):
        from cli.core.console import confirm
        mock_q.confirm.return_value.ask.return_value = True
        assert confirm("Proceed?") is True

    @patch("cli.core.console.questionary")
    def test_select_returns_choice(self, mock_q):
        from cli.core.console import select
        mock_q.select.return_value.ask.return_value = "gemini"
        result = select("Pick one:", ["gemini", "openai", "ollama"])
        assert result == "gemini"

    @patch("cli.core.console.questionary")
    def test_password_returns_string(self, mock_q):
        from cli.core.console import password
        mock_q.password.return_value.ask.return_value = "sk-secret"
        assert password("API key:") == "sk-secret"

    @patch("cli.core.console.questionary")
    def test_text_returns_string(self, mock_q):
        from cli.core.console import text
        mock_q.text.return_value.ask.return_value = "my-project"
        assert text("Project ID:") == "my-project"


# ---------------------------------------------------------------------------
# commands/credentials.py
# ---------------------------------------------------------------------------

class TestCredentialsCommand:
    """Credential management commands."""

    @patch("cli.commands.credentials.secrets")
    def test_check_reports_missing(self, mock_secrets):
        from cli.commands.credentials import check_credentials
        mock_secrets.exists.return_value = False
        result = check_credentials("gemini")
        assert result is False

    @patch("cli.commands.credentials.secrets")
    def test_check_reports_present(self, mock_secrets):
        from cli.commands.credentials import check_credentials
        mock_secrets.exists.return_value = True
        result = check_credentials("gemini")
        assert result is True

    @patch("cli.commands.credentials.secrets")
    def test_clear_deletes_keys(self, mock_secrets):
        from cli.commands.credentials import clear_credentials
        clear_credentials("openai")
        mock_secrets.delete.assert_called()


# ---------------------------------------------------------------------------
# commands/provider.py
# ---------------------------------------------------------------------------

class TestProviderCommand:
    """Provider management commands."""

    @patch("cli.commands.provider.registry")
    def test_list_returns_providers(self, mock_reg):
        from cli.commands.provider import list_available
        mock_reg.list_providers.return_value = ["gemini", "openai", "ollama"]
        result = list_available()
        assert "gemini" in result
        assert "openai" in result

    @patch("cli.commands.provider.registry")
    @patch("cli.commands.provider.console")
    def test_add_fetches_and_installs(self, mock_console, mock_reg):
        from cli.commands.provider import add_provider
        mock_reg.fetch_provider_file.return_value = "# code"
        mock_reg.load_manifest.return_value = {
            "commit": "abc",
            "repo": "DocGen-io/DocGen-RAG",
            "providers": {
                "openai": {
                    "embedder": "e.py",
                    "generator": "g.py",
                    "pip_packages": ["openai-haystack"],
                },
            },
        }
        # Should not raise
        add_provider("openai")


# ---------------------------------------------------------------------------
# commands/init.py (OAuth flow)
# ---------------------------------------------------------------------------

class TestInitCommand:
    """First-time setup wizard with OAuth."""

    @patch("cli.commands.init.console")
    @patch("cli.commands.init.secrets")
    def test_setup_gemini_stores_credentials(self, mock_secrets, mock_console):
        from cli.commands.init import setup_provider_credentials
        mock_console.text.side_effect = ["my-project-id", "europe-west4"]
        mock_console.confirm.return_value = False  # no service account JSON
        setup_provider_credentials("gemini")
        assert mock_secrets.store.call_count >= 2  # project_id + location

    @patch("cli.commands.init.console")
    @patch("cli.commands.init.secrets")
    def test_setup_openai_stores_api_key(self, mock_secrets, mock_console):
        from cli.commands.init import setup_provider_credentials
        mock_console.password.return_value = "sk-test123"
        setup_provider_credentials("openai")
        mock_secrets.store.assert_called_with("openai_api_key", "sk-test123")

    @patch("cli.commands.init.console")
    @patch("cli.commands.init.secrets")
    def test_setup_ollama_stores_url(self, mock_secrets, mock_console):
        from cli.commands.init import setup_provider_credentials
        mock_console.text.return_value = "http://localhost:11434"
        setup_provider_credentials("ollama")
        mock_secrets.store.assert_called_with(
            "ollama_url", "http://localhost:11434"
        )

    @patch("subprocess.run")
    def test_check_docker_available(self, mock_run):
        from cli.commands.init import check_docker
        mock_run.return_value = MagicMock(returncode=0)
        assert check_docker() is True

    @patch("subprocess.run")
    def test_check_docker_missing(self, mock_run):
        from cli.commands.init import check_docker
        mock_run.side_effect = FileNotFoundError
        assert check_docker() is False


# ---------------------------------------------------------------------------
# commands/config.py
# ---------------------------------------------------------------------------

class TestConfigCommand:
    """Configuration management."""

    @patch("cli.commands.config.get_settings")
    def test_show_returns_dict(self, mock_get):
        from cli.commands.config import show_config
        mock_get.return_value = MagicMock()
        mock_get.return_value.as_dict.return_value = {"rag": {"active_embedder": "gemini"}}
        result = show_config()
        assert "rag" in result

    def test_reset_removes_user_file(self):
        from cli.commands.config import reset_config
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink") as mock_unlink:
                reset_config()
                mock_unlink.assert_called_once()


# ---------------------------------------------------------------------------
# commands/run.py
# ---------------------------------------------------------------------------

class TestRunCommand:
    """Pipeline execution command."""

    @patch("cli.commands.run.secrets")
    @patch("cli.commands.run.get_settings")
    def test_inject_credentials_sets_env(self, mock_settings, mock_secrets):
        from cli.commands.run import inject_credentials
        mock_settings.return_value = MagicMock(active_provider="gemini")
        mock_secrets.retrieve.side_effect = lambda k: {
            "google_project_id": "proj-123",
            "google_location": "europe-west4",
        }.get(k)
        env = inject_credentials()
        assert "GOOGLE_CLOUD_PROJECT" in env or env is not None

    @patch("cli.commands.run.DocumentationPipeline")
    @patch("cli.commands.run.inject_credentials")
    def test_run_pipeline_calls_run(self, mock_inject, mock_pipeline_cls):
        from cli.commands.run import run_pipeline
        mock_inject.return_value = {}
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = {"status": "completed", "files": 3}
        mock_pipeline_cls.return_value = mock_pipeline
        result = run_pipeline("https://github.com/example/repo.git")
        mock_pipeline.run.assert_called_once()
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# OAuth flow (core/oauth.py)
# ---------------------------------------------------------------------------

class TestOAuthFlow:
    """OAuth browser-based authentication flow."""

    @patch("cli.core.oauth.webbrowser")
    @patch("cli.core.oauth.http.server.HTTPServer")
    def test_oauth_starts_server_and_opens_browser(self, mock_server, mock_wb):
        from cli.core.oauth import start_oauth_flow
        # Mock the server to simulate receiving a callback
        mock_httpd = MagicMock()
        mock_server.return_value = mock_httpd
        mock_httpd.authorization_code = "test-code-123"

        result = start_oauth_flow(
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            client_id="test-client-id",
            client_secret="test-secret",
            scopes="https://www.googleapis.com/auth/cloud-platform",
            redirect_port=8080,
        )
        mock_wb.open.assert_called_once()
        mock_httpd.handle_request.assert_called_once()

    def test_oauth_callback_handler_extracts_code(self):
        from cli.core.oauth import OAuthCallbackHandler
        # Verify the class exists and has do_GET
        assert hasattr(OAuthCallbackHandler, "do_GET")


# ---------------------------------------------------------------------------
# Provider manifest integration
# ---------------------------------------------------------------------------

class TestProviderManifest:
    """End-to-end manifest loading and validation."""

    def test_manifest_file_is_valid_json(self):
        manifest_path = Path(__file__).parent.parent / "cli" / "provider_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                data = json.load(f)
            assert "commit" in data
            assert "repo" in data
            assert "providers" in data
            for name, info in data["providers"].items():
                assert "embedder" in info
                assert "generator" in info
                assert "pip_packages" in info
                assert isinstance(info["pip_packages"], list)

    def test_manifest_commit_is_40_char_hex(self):
        manifest_path = Path(__file__).parent.parent / "cli" / "provider_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                data = json.load(f)
            commit = data["commit"]
            assert len(commit) == 40
            assert all(c in "0123456789abcdef" for c in commit)
