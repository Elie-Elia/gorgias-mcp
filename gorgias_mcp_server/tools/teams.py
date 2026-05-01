"""Team tools — team CRUD plus membership management."""

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
]


def register_team_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_teams(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[_OrderBy | None, Field(description="Sort.")] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/teams",
                drop_none({"cursor": cursor, "limit": limit, "order_by": order_by}),
            )
        )

    registrar.tool(
        "gorgias_list_teams",
        description="GET /api/teams — Paginated team list.",
        handler=list_teams,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_team(
        id: Annotated[int, Field(description="Team ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/teams/{id}"))

    registrar.tool(
        "gorgias_get_team",
        description="GET /api/teams/{id} — Single team with members.",
        handler=get_team,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_team(
        name: Annotated[str, Field(description="Team name.", min_length=1)],
        description: Annotated[str | None, Field(description="Description.")] = None,
        decoration: Annotated[
            dict[str, Any] | None,
            Field(description="UI decoration: {emoji?}."),
        ] = None,
        members: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Members: [{id, name?, email?, meta?}]."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "description": description,
                "decoration": decoration,
                "members": members,
            }
        )
        return await safe(client.post("/api/teams", body))

    registrar.tool(
        "gorgias_create_team",
        description="POST /api/teams — Create a team for auto-assignment.",
        handler=create_team,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_team(
        id: Annotated[int, Field(description="Team ID.", ge=1)],
        name: Annotated[
            str | None, Field(description="Team name.", min_length=1)
        ] = None,
        description: Annotated[str | None, Field(description="Description.")] = None,
        decoration: Annotated[
            dict[str, Any] | None,
            Field(description="Decoration. null to remove."),
        ] = None,
        members: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Replaces ALL members when provided."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "description": description,
                "decoration": decoration,
                "members": members,
            }
        )
        return await safe(client.put(f"/api/teams/{id}", body))

    registrar.tool(
        "gorgias_update_team",
        description="PUT /api/teams/{id} — Update team. Members replaces existing list.",
        handler=update_team,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_team(
        id: Annotated[int, Field(description="Team ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/teams/{id}"))

    registrar.tool(
        "gorgias_delete_team",
        description=(
            "DELETE /api/teams/{id} — Permanently delete a team. Tickets lose their "
            "team assignment."
        ),
        handler=delete_team,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )
