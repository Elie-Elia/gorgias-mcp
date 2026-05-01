"""TTL caching and pagination helpers for Gorgias reference data.

Caches are scoped per `GorgiasClient` instance via `WeakValueDictionary`-style
identity keying so multi-tenant deployments never leak data between clients.
Reference data endpoints are fully paginated (cursor-based, 100 per page) so
accounts with more than 100 tags/views/users/etc. are not silently truncated.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from gorgias_mcp_server.client import GorgiasClient


CACHE_TTL_SECONDS = 10 * 60  # 10 minutes
_PAGE_LIMIT = 100


@dataclass
class _CacheEntry:
    value: Any
    timestamp: float


class TtlCache:
    """In-memory TTL cache with single-key eviction on read."""

    def __init__(self, ttl_seconds: float = CACHE_TTL_SECONDS) -> None:
        self._entries: dict[str, _CacheEntry] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry.timestamp >= self._ttl:
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._entries[key] = _CacheEntry(value=value, timestamp=time.monotonic())

    def clear(self) -> None:
        self._entries.clear()


@dataclass
class FetchAllPagesResult:
    items: list[Any]
    pages_fetched: int
    truncated: bool


@dataclass
class ReferenceData:
    tags: list[Any] = field(default_factory=list)
    teams: list[Any] = field(default_factory=list)
    custom_fields: list[Any] = field(default_factory=list)
    views: list[Any] = field(default_factory=list)
    users: list[Any] = field(default_factory=list)


async def fetch_all_pages(
    client: GorgiasClient,
    endpoint: str,
    *,
    page_limit: int = _PAGE_LIMIT,
    max_items: int | None = None,
) -> FetchAllPagesResult:
    """Fetch every page of a cursor-paginated endpoint.

    Handles both standard {data, meta} responses and plain-array endpoints
    (e.g. /api/teams when paged manually).
    """
    items: list[Any] = []
    cursor: str | None = None
    pages_fetched = 0
    truncated = False
    cap = max_items if max_items is not None else float("inf")

    while True:
        params: dict[str, Any] = {"limit": page_limit}
        if cursor:
            params["cursor"] = cursor

        response = await client.get(endpoint, params)
        pages_fetched += 1

        # Plain-array endpoints (no cursor)
        if isinstance(response, list):
            items.extend(response)
            break

        body = response if isinstance(response, dict) else {}
        data = body.get("data")
        if isinstance(data, list):
            for item in data:
                if len(items) >= cap:
                    truncated = True
                    break
                items.append(item)

        if truncated:
            break

        meta = body.get("meta") or {}
        raw_cursor = meta.get("next_cursor")
        if raw_cursor is None or str(raw_cursor) == "":
            break
        cursor = str(raw_cursor)

    return FetchAllPagesResult(
        items=items, pages_fetched=pages_fetched, truncated=truncated
    )


async def _fetch_all_pages_flat(
    client: GorgiasClient, endpoint: str
) -> list[Any]:
    return (await fetch_all_pages(client, endpoint)).items


# Per-client caches keyed by id(client). We use WeakValueDictionary for
# in-flight promises so they can be garbage-collected once awaited.
_reference_data_caches: dict[int, TtlCache] = {}
_reference_data_inflight: dict[int, asyncio.Future[ReferenceData]] = {}
_users_caches: dict[int, TtlCache] = {}
_users_inflight: dict[int, asyncio.Future[list[Any]]] = {}

_REFERENCE_DATA_KEY = "referenceData"
_USERS_CACHE_KEY = "users"


async def get_reference_data(client: GorgiasClient) -> ReferenceData:
    """Fetch and cache the full reference dataset (tags, teams, fields, views, users)."""
    client_key = id(client)
    cache = _reference_data_caches.setdefault(client_key, TtlCache())

    cached = cache.get(_REFERENCE_DATA_KEY)
    if cached is not None:
        return cached

    inflight = _reference_data_inflight.get(client_key)
    if inflight is not None:
        return await inflight

    loop = asyncio.get_event_loop()
    future: asyncio.Future[ReferenceData] = loop.create_future()
    _reference_data_inflight[client_key] = future

    try:
        tags, teams, custom_fields, views, users = await asyncio.gather(
            _fetch_all_pages_flat(client, "/api/tags"),
            _fetch_all_pages_flat(client, "/api/teams"),
            _fetch_all_pages_flat(
                client, "/api/custom-fields?object_type=Ticket"
            ),
            _fetch_all_pages_flat(client, "/api/views"),
            _fetch_all_pages_flat(client, "/api/users"),
        )
        result = ReferenceData(
            tags=tags,
            teams=teams,
            custom_fields=custom_fields,
            views=views,
            users=users,
        )
        cache.set(_REFERENCE_DATA_KEY, result)
        future.set_result(result)
        return result
    except Exception as exc:
        future.set_exception(exc)
        raise
    finally:
        _reference_data_inflight.pop(client_key, None)


async def get_cached_users(client: GorgiasClient) -> list[Any]:
    """Fetch and cache the full users list for ID→name resolution."""
    client_key = id(client)
    cache = _users_caches.setdefault(client_key, TtlCache())

    cached = cache.get(_USERS_CACHE_KEY)
    if cached is not None:
        return cached

    inflight = _users_inflight.get(client_key)
    if inflight is not None:
        return await inflight

    loop = asyncio.get_event_loop()
    future: asyncio.Future[list[Any]] = loop.create_future()
    _users_inflight[client_key] = future

    try:
        users = await _fetch_all_pages_flat(client, "/api/users")
        cache.set(_USERS_CACHE_KEY, users)
        future.set_result(users)
        return users
    except Exception as exc:
        future.set_exception(exc)
        raise
    finally:
        _users_inflight.pop(client_key, None)
