"""Custom field tools — definition CRUD for Ticket and Customer fields."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_ObjectType = Literal["Ticket", "Customer"]
_DataType = Literal["text", "number", "boolean"]
_ManagedType = Literal[
    "contact_reason",
    "product",
    "resolution",
    "ai_intent",
    "ai_outcome",
    "ai_sales",
    "ai_discount",
    "ai_journey",
    "managed_sentiment",
    "call_status",
]


def register_custom_field_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def list_custom_fields(
        object_type: Annotated[
            _ObjectType,
            Field(description="Entity type: 'Ticket' or 'Customer'."),
        ],
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        order_by: Annotated[
            Literal["priority:asc", "priority:desc"] | None,
            Field(description="Sort. Default priority:desc."),
        ] = None,
        search: Annotated[str | None, Field(description="Substring filter on name.")] = None,
        archived: Annotated[
            bool | None, Field(description="True returns only archived fields.")
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/custom-fields",
                drop_none(
                    {
                        "object_type": object_type,
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "search": search,
                        "archived": archived,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_custom_fields",
        description="GET /api/custom-fields — Cursor-paginated custom field definitions.",
        handler=list_custom_fields,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_custom_field(
        id: Annotated[int, Field(description="Custom field ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/custom-fields/{id}"))

    registrar.tool(
        "gorgias_get_custom_field",
        description="GET /api/custom-fields/{id} — Single custom field definition.",
        handler=get_custom_field,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_custom_field(
        object_type: Annotated[_ObjectType, Field(description="Entity type.")],
        label: Annotated[
            str,
            Field(description="Display name (1–255).", min_length=1, max_length=255),
        ],
        definition: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Definition: {data_type: 'text'|'number'|'boolean', "
                    "input_settings: {input_type, ...}}."
                )
            ),
        ],
        description: Annotated[
            str | None, Field(description="Description (max 1024).", max_length=1024)
        ] = None,
        external_id: Annotated[str | None, Field(description="External system ID.")] = None,
        priority: Annotated[
            int | None,
            Field(description="Display order (0–5000, lower first).", ge=0, le=5000),
        ] = None,
        required: Annotated[bool | None, Field(description="Required field flag.")] = None,
        managed_type: Annotated[
            _ManagedType | None,
            Field(description="Managed type classification."),
        ] = None,
        deactivated_datetime: Annotated[
            str | None,
            Field(description="ISO 8601 to deactivate at creation."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "object_type": object_type,
                "label": label,
                "definition": definition,
                "description": description,
                "external_id": external_id,
                "priority": priority,
                "required": required,
                "managed_type": managed_type,
                "deactivated_datetime": deactivated_datetime,
            }
        )
        return await safe(client.post("/api/custom-fields", body))

    registrar.tool(
        "gorgias_create_custom_field",
        description=(
            "POST /api/custom-fields — Create a custom field. data_type "
            "discriminator drives input_settings shape."
        ),
        handler=create_custom_field,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_custom_field(
        id: Annotated[int, Field(description="Custom field ID.", ge=1)],
        object_type: Annotated[_ObjectType, Field(description="Entity type (required).")],
        label: Annotated[
            str,
            Field(description="Display name (required).", min_length=1, max_length=255),
        ],
        definition: Annotated[
            dict[str, Any],
            Field(description="Definition object (required)."),
        ],
        description: Annotated[
            str | None, Field(description="Description (max 1024).", max_length=1024)
        ] = None,
        external_id: Annotated[str | None, Field(description="External system ID.")] = None,
        priority: Annotated[
            int | None, Field(description="Display order.", ge=0, le=5000)
        ] = None,
        required: Annotated[bool | None, Field(description="Required flag.")] = None,
        managed_type: Annotated[
            _ManagedType | None,
            Field(description="Managed type classification."),
        ] = None,
        deactivated_datetime: Annotated[
            str | None,
            Field(description="ISO 8601 to deactivate. null to reactivate."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "object_type": object_type,
                "label": label,
                "definition": definition,
                "description": description,
                "external_id": external_id,
                "priority": priority,
                "required": required,
                "managed_type": managed_type,
                "deactivated_datetime": deactivated_datetime,
            }
        )
        return await safe(client.put(f"/api/custom-fields/{id}", body))

    registrar.tool(
        "gorgias_update_custom_field",
        description=(
            "PUT /api/custom-fields/{id} — Update a custom field. object_type, "
            "label, definition are required even if unchanged."
        ),
        handler=update_custom_field,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def bulk_update_custom_fields(
        fields: Annotated[
            list[dict[str, Any]],
            Field(
                description="Array of field updates; each requires id.",
                min_length=1,
            ),
        ],
    ) -> dict[str, Any]:
        return await safe(client.put("/api/custom-fields", fields))

    registrar.tool(
        "gorgias_bulk_update_custom_fields",
        description=(
            "PUT /api/custom-fields — Bulk update multiple custom fields in a "
            "single request."
        ),
        handler=bulk_update_custom_fields,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
