"""Shared helpers used by every Gorgias tool module."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from gorgias_mcp_server.errors import sanitise_error_for_llm


def drop_none(d: dict[str, Any]) -> dict[str, Any]:
    """Strip keys with None values from a dict before sending to the API."""
    return {k: v for k, v in d.items() if v is not None}


async def safe(coro: Awaitable[Any]) -> dict[str, Any]:
    """Run an awaited API call and convert exceptions into a clean error dict.

    Mirrors benpalmer1's `safeHandler` — guarantees every tool returns a
    structured response even on failure, and never leaks credentials or
    internal stack info to the LLM.
    """
    try:
        result = await coro
    except Exception as err:
        try:
            return {"error": sanitise_error_for_llm(err)}
        except Exception:
            return {"error": "An internal error occurred"}

    # Tools advertise `dict[str, Any]` returns, so wrap non-dict results
    # under "result" to match the schema FastMCP advertises.
    if isinstance(result, dict):
        return result
    return {"result": result}
