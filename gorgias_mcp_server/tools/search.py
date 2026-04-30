"""Low-level Gorgias search tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import safe


_SearchType = Literal[
    "agent",
    "customer",
    "customer_profile",
    "customer_channel",
    "customer_channel_email",
    "customer_channel_phone",
    "customers_by_phone",
    "integration",
    "team",
    "tag",
]


def register_search_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def search(
        type: Annotated[
            _SearchType,
            Field(description="Resource category to search."),
        ],
        query: Annotated[
            str,
            Field(
                description=(
                    "Search query. Empty string returns recent/all of the type."
                )
            ),
        ] = "",
        size: Annotated[
            int | None,
            Field(description="Max results (default 10, max 50).", ge=1, le=50),
        ] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"type": type, "query": query}
        if size is not None:
            body["size"] = size
        return await safe(client.search(body))  # type: ignore[arg-type]

    registrar.tool(
        "gorgias_search",
        description=(
            "POST /api/search — Search agents/customers/teams/tags/integrations by "
            "text. For ticket search, use gorgias_smart_search instead. Result is "
            "always a flat array (the client unwraps {data:[...]} responses)."
        ),
        handler=search,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
