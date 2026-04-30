"""Tag tools — CRUD plus bulk delete and merge."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_OrderBy = Literal[
    "created_datetime:asc",
    "created_datetime:desc",
    "name:asc",
    "name:desc",
    "usage:asc,name:asc",
    "usage:desc,name:desc",
]


def register_tag_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_tags(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None,
            Field(description="Per-page (default 30).", ge=1, le=100),
        ] = None,
        order_by: Annotated[_OrderBy | None, Field(description="Sort order.")] = None,
        search: Annotated[
            str | None, Field(description="Case-insensitive name search.")
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/tags",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "search": search,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_tags",
        description="GET /api/tags — List all tags with optional filtering.",
        handler=list_tags,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_tag(
        id: Annotated[int, Field(description="Tag ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/tags/{id}"))

    registrar.tool(
        "gorgias_get_tag",
        description="GET /api/tags/{id} — Single tag.",
        handler=get_tag,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_tag(
        name: Annotated[
            str,
            Field(description="Tag name (case-sensitive).", min_length=1, max_length=256),
        ],
        description: Annotated[
            str | None,
            Field(description="Description (max 1024).", max_length=1024),
        ] = None,
        decoration: Annotated[
            dict[str, Any] | None,
            Field(description="Visual styling: {color: '#F58D86'}."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {"name": name, "description": description, "decoration": decoration}
        )
        return await safe(client.post("/api/tags", body))

    registrar.tool(
        "gorgias_create_tag",
        description="POST /api/tags — Create a tag.",
        handler=create_tag,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_tag(
        id: Annotated[int, Field(description="Tag ID.", ge=1)],
        name: Annotated[
            str | None,
            Field(description="New name.", min_length=1, max_length=256),
        ] = None,
        description: Annotated[
            str | None, Field(description="New description.", max_length=1024)
        ] = None,
        decoration: Annotated[
            dict[str, Any] | None,
            Field(description="Decoration: {color}. null to clear."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {"name": name, "description": description, "decoration": decoration}
        )
        return await safe(client.put(f"/api/tags/{id}", body))

    registrar.tool(
        "gorgias_update_tag",
        description="PUT /api/tags/{id} — Update a tag.",
        handler=update_tag,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_tag(
        id: Annotated[int, Field(description="Tag ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/tags/{id}"))

    registrar.tool(
        "gorgias_delete_tag",
        description=(
            "DELETE /api/tags/{id} — Permanent delete. Views using this tag are "
            "deactivated. Tags used in macros/rules cannot be deleted."
        ),
        handler=delete_tag,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_tags(
        ids: Annotated[
            list[int], Field(description="Tag IDs to delete.", min_length=1)
        ],
    ) -> dict[str, Any]:
        return await safe(client.delete("/api/tags", {"ids": ids}))

    registrar.tool(
        "gorgias_delete_tags",
        description="DELETE /api/tags — Bulk delete.",
        handler=delete_tags,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    async def merge_tags(
        destination_tag_id: Annotated[
            int, Field(description="Destination (kept after merge).", ge=1)
        ],
        source_tags_ids: Annotated[
            list[int],
            Field(description="Source tag IDs (deleted after merge).", min_length=1),
        ],
    ) -> dict[str, Any]:
        return await safe(
            client.put(
                f"/api/tags/{destination_tag_id}/merge",
                {"source_tags_ids": source_tags_ids},
            )
        )

    registrar.tool(
        "gorgias_merge_tags",
        description=(
            "PUT /api/tags/{destination_tag_id}/merge — Merge sources into "
            "destination; sources are deleted."
        ),
        handler=merge_tags,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )
