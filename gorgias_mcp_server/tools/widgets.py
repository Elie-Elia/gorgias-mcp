"""Widget tools — sidebar widget CRUD."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_OrderBy = Literal[
    "created_datetime:asc",
    "created_datetime:desc",
    "order:asc",
    "order:desc",
]

_Type = Literal[
    "bigcommerce",
    "custom",
    "customer_external_data",
    "http",
    "magento2",
    "recharge",
    "shopify",
    "smile",
    "standalone",
    "yotpo",
    "klaviyo",
    "stripe",
    "woocommerce",
]


def register_widget_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_widgets(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[_OrderBy | None, Field(description="Sort.")] = None,
        integration_id: Annotated[
            int | None, Field(description="Filter by integration.", ge=1)
        ] = None,
        app_id: Annotated[str | None, Field(description="Filter by 3rd-party app ID.")] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/widgets",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "integration_id": integration_id,
                        "app_id": app_id,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_widgets",
        description="GET /api/widgets — Cursor-paginated sidebar widget list.",
        handler=list_widgets,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_widget(
        id: Annotated[int, Field(description="Widget ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/widgets/{id}"))

    registrar.tool(
        "gorgias_get_widget",
        description="GET /api/widgets/{id} — Single widget definition.",
        handler=get_widget,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_widget(
        template: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Render template: {type:'wrapper', widgets:[{path,type,title,widgets?}]}."
                )
            ),
        ],
        type: Annotated[_Type, Field(description="Widget data source type.")],
        context: Annotated[
            Literal["ticket", "customer", "user"] | None,
            Field(description="UI context (default 'ticket'). 'user' is deprecated."),
        ] = None,
        order: Annotated[
            int | None,
            Field(description="Display order (lower first, default 0).", ge=0),
        ] = None,
        integration_id: Annotated[
            int | None,
            Field(description="HTTP integration ID (type=http).", ge=0),
        ] = None,
        app_id: Annotated[
            str | None,
            Field(description="3rd-party app ID (type=customer_external_data)."),
        ] = None,
        deactivated_datetime: Annotated[
            str | None, Field(description="ISO 8601 to deactivate at creation.")
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "template": template,
                "type": type,
                "context": context,
                "order": order,
                "integration_id": integration_id,
                "app_id": app_id,
                "deactivated_datetime": deactivated_datetime,
            }
        )
        return await safe(client.post("/api/widgets", body))

    registrar.tool(
        "gorgias_create_widget",
        description="POST /api/widgets — Create a sidebar widget.",
        handler=create_widget,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_widget(
        id: Annotated[int, Field(description="Widget ID.", ge=1)],
        context: Annotated[
            Literal["ticket", "customer", "user"] | None,
            Field(description="UI context."),
        ] = None,
        deactivated_datetime: Annotated[
            str | None,
            Field(description="ISO 8601. null to reactivate."),
        ] = None,
        integration_id: Annotated[
            int | None, Field(description="Integration ID.", ge=0)
        ] = None,
        app_id: Annotated[str | None, Field(description="3rd-party app ID.")] = None,
        order: Annotated[int | None, Field(description="Display order.", ge=0)] = None,
        template: Annotated[
            dict[str, Any] | None,
            Field(description="Template (replaces existing entirely)."),
        ] = None,
        type: Annotated[_Type | None, Field(description="Widget type.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "context": context,
                "deactivated_datetime": deactivated_datetime,
                "integration_id": integration_id,
                "app_id": app_id,
                "order": order,
                "template": template,
                "type": type,
            }
        )
        return await safe(client.put(f"/api/widgets/{id}", body))

    registrar.tool(
        "gorgias_update_widget",
        description="PUT /api/widgets/{id} — Update widget. template fully replaces.",
        handler=update_widget,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_widget(
        id: Annotated[int, Field(description="Widget ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/widgets/{id}"))

    registrar.tool(
        "gorgias_delete_widget",
        description="DELETE /api/widgets/{id} — Permanently delete a widget.",
        handler=delete_widget,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )
