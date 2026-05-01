"""Integration tools — HTTP-type integration CRUD."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_OrderBy = Literal["created_datetime:asc", "created_datetime:desc"]


def register_integration_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def list_integrations(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[int | None, Field(description="Per-page (default 30).")] = None,
        order_by: Annotated[_OrderBy | None, Field(description="Sort.")] = None,
        type: Annotated[
            Literal["http"] | None,
            Field(description="Filter by integration type. Only 'http' is filterable."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/integrations",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "type": type,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_integrations",
        description="GET /api/integrations — Cursor-paginated integrations list.",
        handler=list_integrations,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_integration(
        id: Annotated[int, Field(description="Integration ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/integrations/{id}"))

    registrar.tool(
        "gorgias_get_integration",
        description="GET /api/integrations/{id} — Single integration with HTTP config.",
        handler=get_integration,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_integration(
        name: Annotated[str, Field(description="Integration name.")],
        type: Annotated[
            Literal["http"], Field(description="Only 'http' is creatable via REST.")
        ],
        description: Annotated[str | None, Field(description="Description.")] = None,
        http: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "HTTP config: {url, method, request_content_type, "
                    "response_content_type, form?, headers?, hmac_secret?, triggers?}. "
                    "triggers maps event names (ticket-created, ticket-updated, etc.) to bool."
                )
            ),
        ] = None,
        business_hours_id: Annotated[
            int | None,
            Field(description="Business hours ID (phone integrations).", ge=1),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "type": type,
                "description": description,
                "http": http,
                "business_hours_id": business_hours_id,
            }
        )
        return await safe(client.post("/api/integrations", body))

    registrar.tool(
        "gorgias_create_integration",
        description="POST /api/integrations — Create an HTTP integration.",
        handler=create_integration,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_integration(
        id: Annotated[int, Field(description="Integration ID.", ge=1)],
        name: Annotated[str, Field(description="Integration name (required).")],
        description: Annotated[str | None, Field(description="Description.")] = None,
        deactivated_datetime: Annotated[
            str | None,
            Field(description="ISO 8601 to deactivate. null to reactivate."),
        ] = None,
        http: Annotated[
            dict[str, Any] | None,
            Field(description="HTTP config (when type=http)."),
        ] = None,
        business_hours_id: Annotated[
            int | None,
            Field(description="Business hours ID.", ge=1),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "description": description,
                "deactivated_datetime": deactivated_datetime,
                "http": http,
                "business_hours_id": business_hours_id,
            }
        )
        return await safe(client.put(f"/api/integrations/{id}", body))

    registrar.tool(
        "gorgias_update_integration",
        description="PUT /api/integrations/{id} — Update integration (name required).",
        handler=update_integration,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_integration(
        id: Annotated[int, Field(description="Integration ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/integrations/{id}"))

    registrar.tool(
        "gorgias_delete_integration",
        description=(
            "DELETE /api/integrations/{id} — Delete an integration. Views using it "
            "will be deactivated. Cannot delete if used by rules/other integrations."
        ),
        handler=delete_integration,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )
