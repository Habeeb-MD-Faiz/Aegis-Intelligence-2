"""
Credential custody.

This is the load-bearing idea of the whole system.

A proxy an agent can route around is a suggestion. A proxy that holds the only
credential is a wall. Agents never receive an API key or a wallet key — they
submit an intent, and if policy allows it, AEGIS makes the outbound call
itself using a secret the agent has never seen.

That is what makes the guard non-optional. There is no "bypass AEGIS and pay
the provider directly" path, because the agent has nothing to pay with.

Secrets are loaded from the environment as AEGIS_CREDENTIAL_<PROVIDER> and are
never returned over the API — `describe()` reports only whether a credential
is held.
"""

import os
from typing import Dict, Optional


_PREFIX = "AEGIS_CREDENTIAL_"


def _normalize(provider: str) -> str:
    """
    "Alpha Vantage" -> "ALPHA_VANTAGE"
    """

    return (
        provider.strip()
        .upper()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
    )


def _load() -> Dict[str, str]:
    """
    Read every configured provider credential from the environment.
    """

    vault: Dict[str, str] = {}

    for key, value in os.environ.items():
        if not key.startswith(_PREFIX):
            continue

        provider = key[len(_PREFIX):]

        if provider and value:
            vault[provider] = value

    return vault


_vault: Dict[str, str] = _load()


def reload_vault() -> None:
    """
    Re-read credentials from the environment (used by tests and the demo).
    """

    global _vault
    _vault = _load()


def has_credential(provider: str) -> bool:
    return _normalize(provider) in _vault


def get_credential(provider: str) -> Optional[str]:
    """
    Return the secret for a provider.

    Only the guard calls this, and only after a payment has been authorized.
    The value is never serialized into a response, a log line, or the ledger.
    """

    return _vault.get(_normalize(provider))


def describe() -> Dict[str, bool]:
    """
    Safe-to-expose view of the vault: which providers we hold a secret for,
    never the secrets themselves.
    """

    return {provider: True for provider in sorted(_vault)}


def redact(text: str) -> str:
    """
    Defensive scrub for anything we are about to log or persist.

    If a provider response echoes our own credential back at us, it must not
    end up in the audit trail.
    """

    if not text:
        return text

    scrubbed = text

    for secret in _vault.values():
        if secret and secret in scrubbed:
            scrubbed = scrubbed.replace(secret, "[REDACTED]")

    return scrubbed
