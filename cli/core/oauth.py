"""
OAuth browser-based authentication flow.

Used for providers that support OAuth2 (e.g., Google Cloud / Vertex AI).
Spins up a temporary local HTTP server to capture the authorization callback,
then exchanges the code for access/refresh tokens.
"""

import http.server
import json
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth authorization code from the redirect."""

    authorization_code: str | None = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.authorization_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            body = (
                "<html><body>"
                "<h2>Authentication successful</h2>"
                "<p>You can close this tab and return to your terminal.</p>"
                "</body></html>"
            )
            self.wfile.write(body.encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authentication failed</h2></body></html>")

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress server request logs to keep terminal clean."""
        pass


def start_oauth_flow(
    auth_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    scopes: str,
    redirect_port: int = 8080,
) -> dict[str, Any] | None:
    """
    Run a full OAuth2 authorization code flow.

    1. Opens the browser to the provider's consent page
    2. Captures the authorization code via local redirect
    3. Exchanges code for access + refresh tokens

    Returns the token response dict, or None on failure.
    """
    redirect_uri = f"http://localhost:{redirect_port}/callback"
    OAuthCallbackHandler.authorization_code = None

    # Build authorization URL
    login_params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
    })
    login_url = f"{auth_url}?{login_params}"

    # Start local server and open browser
    server_address = ("localhost", redirect_port)
    httpd = http.server.HTTPServer(server_address, OAuthCallbackHandler)
    webbrowser.open(login_url)

    # Wait for the single callback request
    httpd.handle_request()
    httpd.server_close()

    code = OAuthCallbackHandler.authorization_code
    if not code:
        return None

    # Exchange code for tokens
    token_data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=token_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        return None


def save_tokens(tokens: dict[str, Any], path: Path) -> None:
    """Persist OAuth tokens to a file (chmod 600)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2))
    path.chmod(0o600)


def load_tokens(path: Path) -> dict[str, Any] | None:
    """Load previously saved OAuth tokens."""
    if not path.exists():
        return None
    return json.loads(path.read_text())
