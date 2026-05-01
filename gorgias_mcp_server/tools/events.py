"""Event tools — read-only system event log access."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_ObjectType = Literal[
    "Account",
    "Macro",
    "Tag",
    "Customer",
    "Team",
    "View",
    "Widget",
    "User",
    "TicketMessage",
    "Ticket",
    "Rule",
    "Integration",
    "SatisfactionSurvey",
]


def register_event_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_events(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[
            Literal["created_datetime:asc", "created_datetime:desc"] | None,
            Field(description="Sort. Default created_datetime:desc."),
        ] = None,
        object_id: Annotated[
            int | None, Field(description="Filter by associated object ID.", ge=1)
        ] = None,
        object_type: Annotated[
            _ObjectType | None,
            Field(description="Filter by associated object type (object_id required when set)."),
        ] = None,
        user_ids: Annotated[
            list[int] | None,
            Field(description="Filter by triggering user IDs."),
        ] = None,
        types: Annotated[
            list[str] | None,
            Field(description="Filter by event type names (e.g. 'ticket-created')."),
        ] = None,
        created_datetime: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Date range comparators: {gt?, gte?, lt?, lte?} as ISO 8601."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        # Flatten created_datetime into bracket-notation params, e.g. created_datetime[gte]=...
        query: dict[str, Any] = drop_none(
            {
                "cursor": cursor,
                "limit": limit,
                "order_by": order_by,
                "object_id": object_id,
                "object_type": object_type,
                "user_ids": user_ids,
                "types": types,
            }
        )
        if created_datetime:
            for op, val in created_datetime.items():
                if val is not None:
                    query[f"created_datetime[{op}]"] = val
        return await safe(client.get("/api/events", query))

    registrar.tool(
        "gorgias_list_events",
        description=(
            "GET /api/events — Cursor-paginated event log, ordered by creation. "
            "Filter by object, user, event type, or datetime range."
        ),
        handler=list_events,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_event(
        id: Annotated[int, Field(description="Event ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/events/{id}"))

    registrar.tool(
        "gorgias_get_event",
        description="GET /api/events/{id} — Single event (read-only system log entry).",
        handler=get_event,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
