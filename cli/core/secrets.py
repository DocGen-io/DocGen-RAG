"""
Secure credential storage via the OS keyring.

All sensitive data (API keys, tokens, project IDs) is stored in the operating
system's native credential manager -- never in plaintext files.

Supported backends:
  - macOS: Keychain
  - Linux: SecretService (GNOME Keyring / KWallet)
  - Windows: Credential Manager
"""

import keyring
from keyring.errors import PasswordDeleteError

SERVICE = "docgen-rag"


def store(key: str, value: str) -> None:
    """Save a credential to the OS keyring."""
    keyring.set_password(SERVICE, key, value)


def retrieve(key: str) -> str | None:
    """Read a credential from the OS keyring. Returns None if not found."""
    return keyring.get_password(SERVICE, key)


def delete(key: str) -> None:
    """Remove a credential from the OS keyring. No-op if missing."""
    try:
        keyring.delete_password(SERVICE, key)
    except PasswordDeleteError:
        pass


def exists(key: str) -> bool:
    """Check whether a credential exists in the keyring."""
    return keyring.get_password(SERVICE, key) is not None
