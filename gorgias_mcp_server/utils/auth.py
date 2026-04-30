"""Credential helpers for the Gorgias MCP Server."""

import os


def get_credentials() -> dict[str, str]:
    """Return Gorgias credentials from the local environment.

    Auth type is `none` in `config.yaml`, so the developer (you) provides the
    credentials via environment variables. The server reads them at boot.
    """
    return {
        "domain": os.environ.get("GORGIAS_DOMAIN", ""),
        "email": os.environ.get("GORGIAS_EMAIL", ""),
        "api_key": os.environ.get("GORGIAS_API_KEY", ""),
        "access_level": os.environ.get("GORGIAS_ACCESS_LEVEL", "").strip().lower(),
    }
