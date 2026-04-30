"""Async HTTP client for the Gorgias REST API.

Ports the safety properties of benpalmer1/Gorgias-MCP-Server's TS client:
- SSRF allowlist (only *.gorgias.com hosts)
- Rejects http://, whitespace, trailing-dot, empty domain inputs
- Basic auth via email + API key
- Retry on 429 with Retry-After or capped exponential backoff + jitter
- Per-request timeout
- Vendor JSON content-type detection
"""

from __future__ import annotations

import asyncio
import base64
import random
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from gorgias_mcp_server.errors import GorgiasApiError


_ALLOWED_HOST_SUFFIX = ".gorgias.com"
_REQUEST_TIMEOUT_SECONDS = 30.0
_MAX_RETRY_AFTER_SECONDS = 60
_JSON_CONTENT_TYPE_RE = re.compile(
    r"\bapplication/(?:[\w.+-]+\+)?json\b", re.IGNORECASE
)


def _assert_gorgias_host(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host != "gorgias.com" and not host.endswith(_ALLOWED_HOST_SUFFIX):
        raise ValueError(
            f'Domain not on allowlist: hostname "{host}" is not a *.gorgias.com address.'
        )


def _build_base_url(domain: str) -> str:
    d = domain.strip()
    if not d:
        raise ValueError("Domain must not be empty.")
    if re.search(r"\s", d):
        raise ValueError("Domain must not contain whitespace.")
    if d.endswith("."):
        raise ValueError("Domain must not end with a trailing dot.")
    if d.startswith("http://"):
        raise ValueError(
            "Insecure http:// URLs are not allowed. Use https:// instead."
        )

    if d.startswith("https://"):
        parsed = urlparse(d)
        resolved = f"{parsed.scheme}://{parsed.netloc}"
        _assert_gorgias_host(resolved)
        return resolved

    while d.endswith("/"):
        d = d[:-1]
    if d.endswith("/api"):
        d = d[:-4]
    while d.endswith("/"):
        d = d[:-1]

    if "." in d:
        resolved = f"https://{d}"
        _assert_gorgias_host(resolved)
        return resolved

    return f"https://{d}.gorgias.com"


class GorgiasClient:
    """Thin async wrapper over httpx for Gorgias REST endpoints."""

    def __init__(self, *, domain: str, email: str, api_key: str) -> None:
        if not (domain and email and api_key):
            missing = ", ".join(
                name
                for name, value in (
                    ("GORGIAS_DOMAIN", domain),
                    ("GORGIAS_EMAIL", email),
                    ("GORGIAS_API_KEY", api_key),
                )
                if not value
            )
            raise ValueError(f"Missing required Gorgias credentials: {missing}")

        self._base_url = _build_base_url(domain)
        token = base64.b64encode(f"{email}:{api_key}".encode()).decode()
        self._auth_header = f"Basic {token}"

    @staticmethod
    def _coerce_query(
        query: dict[str, Any] | None,
    ) -> list[tuple[str, str]] | None:
        if not query:
            return None
        params: list[tuple[str, str]] = []
        for key, value in query.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                for item in value:
                    if item is None:
                        continue
                    if isinstance(item, dict):
                        raise ValueError(
                            f'Query parameter "{key}" array element must be a scalar (got dict)'
                        )
                    params.append((key, str(item)))
            elif isinstance(value, dict):
                raise ValueError(
                    f'Query parameter "{key}" must be a scalar or array of scalars (got dict)'
                )
            else:
                params.append((key, str(value)))
        return params

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any = None,
    ) -> Any:
        url = urljoin(self._base_url + "/", path.lstrip("/"))
        params = self._coerce_query(query)

        headers: dict[str, str] = {
            "Authorization": self._auth_header,
            "Accept": "application/json",
        }
        json_body: Any = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            json_body = body

        max_retries = 3
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as http:
            response: httpx.Response | None = None
            for attempt in range(max_retries):
                response = await http.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
                if response.status_code != 429:
                    break

                if attempt < max_retries - 1:
                    retry_after_header = response.headers.get("Retry-After")
                    header_seconds: float | None = None
                    if retry_after_header:
                        try:
                            header_seconds = float(retry_after_header)
                        except ValueError:
                            header_seconds = None

                    exp_backoff = min(2**attempt, _MAX_RETRY_AFTER_SECONDS)
                    if header_seconds is not None and header_seconds > 0:
                        base_seconds = min(header_seconds, _MAX_RETRY_AFTER_SECONDS)
                    else:
                        base_seconds = exp_backoff
                    jitter = random.random() * 0.25
                    await asyncio.sleep(base_seconds + jitter)

            assert response is not None  # mypy: at least one iteration ran

            call_limit = response.headers.get("X-Gorgias-Account-Api-Call-Limit")
            retry_after = response.headers.get("Retry-After")

            if response.status_code == 429:
                raise GorgiasApiError(
                    f"Rate limited by Gorgias API. Retry after {retry_after or 'unknown'} seconds. "
                    f"Usage: {call_limit or 'unknown'}",
                    429,
                    rate_limited=True,
                    retry_after=retry_after,
                )

            if not (200 <= response.status_code < 300):
                try:
                    error_body = response.text
                except Exception:
                    error_body = "(could not read response body)"
                raise GorgiasApiError(
                    f"Gorgias API error {response.status_code} {response.reason_phrase}: {error_body}",
                    response.status_code,
                )

            content_length = response.headers.get("content-length")
            if (
                response.status_code in (202, 204)
                or content_length == "0"
            ):
                return {
                    "success": True,
                    "status": response.status_code,
                    "message": (
                        f"Operation accepted ({response.status_code} {response.reason_phrase})"
                    ),
                }

            content_type = response.headers.get("content-type", "")
            if _JSON_CONTENT_TYPE_RE.search(content_type):
                text = response.text
                if not text:
                    return {
                        "success": True,
                        "status": response.status_code,
                        "message": (
                            f"Empty body ({response.status_code} {response.reason_phrase})"
                        ),
                    }
                try:
                    return response.json()
                except ValueError:
                    return {"content": text}

            return {"content": response.text}

    async def get(
        self, path: str, query: dict[str, Any] | None = None
    ) -> Any:
        return await self.request("GET", path, query=query)

    async def post(
        self,
        path: str,
        body: Any = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request("POST", path, query=query, body=body)

    async def put(
        self,
        path: str,
        body: Any = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request("PUT", path, query=query, body=body)

    async def delete(
        self,
        path: str,
        body: Any = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request("DELETE", path, query=query, body=body)

    async def search(self, body: Any) -> list[Any]:
        """POST /api/search — handles both array and {data: [...]} shapes."""
        result = await self.post("/api/search", body)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and isinstance(result.get("data"), list):
            return result["data"]
        raise GorgiasApiError(
            f"Unexpected search response shape: expected array or {{data: [...]}}, "
            f"got {type(result).__name__}",
            0,
        )
