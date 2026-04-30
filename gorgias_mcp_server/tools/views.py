"""View tools — saved-view CRUD plus item listing and ad-hoc search."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_ListOrderBy = Literal[
    "created_datetime:asc",
    "created_datetime:desc",
]

_ItemOrderBy = Literal[
    "created_datetime:asc",
    "created_datetime:desc",
    "updated_datetime:asc",
    "updated_datetime:desc",
    "last_message_datetime:asc",
    "last_message_datetime:desc",
    "last_received_message_datetime:asc",
    "last_received_message_datetime:desc",
    "closed_datetime:asc",
    "closed_datetime:desc",
    "snooze_datetime:asc",
    "snooze_datetime:desc",
    "priority:asc",
    "priority:desc",
]

_FieldName = Literal[
    "id",
    "details",
    "tags",
    "customer",
    "last_message",
    "name",
    "email",
    "created",
    "updated",
    "assignee",
    "assignee_team",
    "channel",
    "closed",
    "language",
    "last_received_message",
    "integrations",
    "snooze",
    "status",
    "subject",
    "priority",
]


def register_view_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_views(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[_ListOrderBy | None, Field(description="Sort.")] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/views",
                drop_none(
                    {"cursor": cursor, "limit": limit, "order_by": order_by}
                ),
            )
        )

    registrar.tool(
        "gorgias_list_views",
        description=(
            "GET /api/views — List saved views. Template variables in filters "
            "are resolved against the authenticated user."
        ),
        handler=list_views,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_view(
        id: Annotated[int, Field(description="View ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/views/{id}"))

    registrar.tool(
        "gorgias_get_view",
        description="GET /api/views/{id} — Single view.",
        handler=get_view,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_view(
        name: Annotated[str | None, Field(description="View name.")] = None,
        type: Annotated[
            Literal["ticket-list"] | None,
            Field(description="Object type. Only 'ticket-list' is supported."),
        ] = None,
        visibility: Annotated[
            Literal["public", "shared", "private"] | None,
            Field(description="Access level."),
        ] = None,
        decoration: Annotated[
            dict[str, Any] | None,
            Field(description="UI decoration: {emoji?}."),
        ] = None,
        fields: Annotated[
            list[_FieldName] | None,
            Field(description="Ticket attributes shown as columns."),
        ] = None,
        filters: Annotated[
            str | None,
            Field(
                description=(
                    "JS-style filter expression e.g. eq(ticket.status, 'open')."
                )
            ),
        ] = None,
        order_by: Annotated[
            str | None, Field(description="Sort attribute (default updated_datetime).")
        ] = None,
        order_dir: Annotated[
            Literal["asc", "desc"] | None, Field(description="Sort direction.")
        ] = None,
        search: Annotated[str | None, Field(description="Free-text filter.")] = None,
        section_id: Annotated[
            int | None, Field(description="View section ID.", ge=1)
        ] = None,
        shared_with_teams: Annotated[
            list[int] | None,
            Field(description="Team IDs (max 100).", max_length=100),
        ] = None,
        shared_with_users: Annotated[
            list[int] | None,
            Field(description="User IDs (max 100).", max_length=100),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "type": type,
                "visibility": visibility,
                "decoration": decoration,
                "fields": fields,
                "filters": filters,
                "order_by": order_by,
                "order_dir": order_dir,
                "search": search,
                "section_id": section_id,
                "shared_with_teams": shared_with_teams,
                "shared_with_users": shared_with_users,
            }
        )
        return await safe(client.post("/api/views", body))

    registrar.tool(
        "gorgias_create_view",
        description="POST /api/views — Create a saved view.",
        handler=create_view,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_view(
        id: Annotated[int, Field(description="View ID.", ge=1)],
        name: Annotated[str | None, Field(description="View name.")] = None,
        type: Annotated[
            Literal["ticket-list"] | None, Field(description="Object type.")
        ] = None,
        visibility: Annotated[
            Literal["public", "shared", "private"] | None,
            Field(description="Access level."),
        ] = None,
        decoration: Annotated[
            dict[str, Any] | None,
            Field(description="Decoration. null to remove."),
        ] = None,
        fields: Annotated[
            list[_FieldName] | None,
            Field(description="Column attributes."),
        ] = None,
        filters: Annotated[str | None, Field(description="Filter expression.")] = None,
        order_by: Annotated[str | None, Field(description="Sort attribute.")] = None,
        order_dir: Annotated[
            Literal["asc", "desc"] | None, Field(description="Sort direction.")
        ] = None,
        search: Annotated[str | None, Field(description="Free-text filter.")] = None,
        section_id: Annotated[
            int | None, Field(description="Section ID.", ge=1)
        ] = None,
        shared_with_teams: Annotated[
            list[int] | None,
            Field(description="Team IDs (max 100).", max_length=100),
        ] = None,
        shared_with_users: Annotated[
            list[int] | None,
            Field(description="User IDs (max 100).", max_length=100),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "type": type,
                "visibility": visibility,
                "decoration": decoration,
                "fields": fields,
                "filters": filters,
                "order_by": order_by,
                "order_dir": order_dir,
                "search": search,
                "section_id": section_id,
                "shared_with_teams": shared_with_teams,
                "shared_with_users": shared_with_users,
            }
        )
        return await safe(client.put(f"/api/views/{id}", body))

    registrar.tool(
        "gorgias_update_view",
        description="PUT /api/views/{id} — Update a saved view.",
        handler=update_view,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_view(
        id: Annotated[int, Field(description="View ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/views/{id}"))

    registrar.tool(
        "gorgias_delete_view",
        description="DELETE /api/views/{id} — Delete a saved view (system views excluded).",
        handler=delete_view,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def list_view_items(
        view_id: Annotated[int, Field(description="View ID.", ge=1)],
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        direction: Annotated[
            Literal["prev", "next"] | None,
            Field(description="Pagination direction."),
        ] = None,
        ignored_item: Annotated[
            int | None, Field(description="Ticket ID to exclude.", ge=1)
        ] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[
            _ItemOrderBy | None, Field(description="Sort attribute.")
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                f"/api/views/{view_id}/items",
                drop_none(
                    {
                        "cursor": cursor,
                        "direction": direction,
                        "ignored_item": ignored_item,
                        "limit": limit,
                        "order_by": order_by,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_view_items",
        description="GET /api/views/{view_id}/items — Tickets in a saved view.",
        handler=list_view_items,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def search_view_items(
        view_id: Annotated[
            int, Field(description="View ID. 0 = ad-hoc query.", ge=0)
        ],
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        direction: Annotated[
            Literal["prev", "next"] | None,
            Field(description="Pagination direction."),
        ] = None,
        ignored_item: Annotated[
            int | None, Field(description="Ticket ID to exclude.", ge=1)
        ] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[
            _ItemOrderBy | None, Field(description="Sort attribute.")
        ] = None,
        view: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Inline view config: {category?, fields?, filters?, order_by?, "
                    "order_dir?, search?, type?}."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        query = drop_none(
            {
                "cursor": cursor,
                "direction": direction,
                "ignored_item": ignored_item,
                "limit": limit,
                "order_by": order_by,
            }
        )
        body = drop_none({"view": view})
        return await safe(client.put(f"/api/views/{view_id}/items", body, query))

    registrar.tool(
        "gorgias_search_view_items",
        description=(
            "PUT /api/views/{view_id}/items — Search with inline view config. "
            "Use view_id=0 for ad-hoc queries."
        ),
        handler=search_view_items,
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
