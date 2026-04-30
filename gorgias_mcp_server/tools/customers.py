"""Customer tools — list/get/create/update/delete customers and their fields."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_OrderBy = Literal[
    "created_datetime:asc",
    "created_datetime:desc",
    "updated_datetime:asc",
    "updated_datetime:desc",
]


def register_customer_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    # --- List Customers ---
    async def list_customers(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        email: Annotated[str | None, Field(description="Filter by primary email.")] = None,
        external_id: Annotated[str | None, Field(description="Filter by external ID.")] = None,
        language: Annotated[
            str | None, Field(description="Filter by ISO 639-1 language code.")
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Per-page limit (default 30, max 100).", ge=1, le=100),
        ] = None,
        name: Annotated[str | None, Field(description="Filter by full name.")] = None,
        order_by: Annotated[
            _OrderBy | None, Field(description="Sort order.")
        ] = None,
        timezone: Annotated[str | None, Field(description="IANA timezone filter.")] = None,
        view_id: Annotated[
            int | None, Field(description="Saved view ID.", ge=1)
        ] = None,
        channel_type: Annotated[
            str | None,
            Field(description="Channel type filter (e.g. email, phone, sms)."),
        ] = None,
        channel_address: Annotated[
            str | None,
            Field(description="Exact channel address (use with channel_type).", max_length=320),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/customers",
                drop_none(
                    {
                        "cursor": cursor,
                        "email": email,
                        "external_id": external_id,
                        "language": language,
                        "limit": limit,
                        "name": name,
                        "order_by": order_by,
                        "timezone": timezone,
                        "view_id": view_id,
                        "channel_type": channel_type,
                        "channel_address": channel_address,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_customers",
        description=(
            "GET /api/customers — Paginated customer list. Filter by email, "
            "external ID, name, language, timezone, view, or channel."
        ),
        handler=list_customers,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Get Customer ---
    async def get_customer(
        id: Annotated[int, Field(description="Customer ID.", ge=1)],
        relationships: Annotated[
            list[Literal["custom_fields"]] | None,
            Field(description="Pass ['custom_fields'] to include them."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                f"/api/customers/{id}",
                drop_none({"relationships": relationships}),
            )
        )

    registrar.tool(
        "gorgias_get_customer",
        description=(
            "GET /api/customers/{id} — Single customer including channels and "
            "integration data; pass relationships=['custom_fields'] for fields."
        ),
        handler=get_customer,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Create Customer ---
    async def create_customer(
        name: Annotated[str | None, Field(description="Full name.")] = None,
        firstname: Annotated[str | None, Field(description="First name.")] = None,
        lastname: Annotated[str | None, Field(description="Last name.")] = None,
        email: Annotated[
            str | None, Field(description="Primary email (max 320).", max_length=320)
        ] = None,
        external_id: Annotated[str | None, Field(description="External system ID.")] = None,
        language: Annotated[str | None, Field(description="ISO 639-1.")] = None,
        timezone: Annotated[str | None, Field(description="IANA timezone.")] = None,
        note: Annotated[str | None, Field(description="Internal note.")] = None,
        channels: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Contact channels: [{type, address, preferred?}]."
                )
            ),
        ] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Arbitrary metadata.")
        ] = None,
        custom_fields: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Custom field values: [{id, value}]."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "external_id": external_id,
                "language": language,
                "timezone": timezone,
                "note": note,
                "channels": channels,
                "meta": meta,
                "custom_fields": custom_fields,
            }
        )
        return await safe(client.post("/api/customers", body))

    registrar.tool(
        "gorgias_create_customer",
        description="POST /api/customers — Create a new customer. All fields optional.",
        handler=create_customer,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    # --- Update Customer ---
    async def update_customer(
        id: Annotated[int, Field(description="Customer ID.", ge=1)],
        name: Annotated[str | None, Field(description="Full name.")] = None,
        firstname: Annotated[str | None, Field(description="First name.")] = None,
        lastname: Annotated[str | None, Field(description="Last name.")] = None,
        email: Annotated[
            str | None, Field(description="Primary email.", max_length=320)
        ] = None,
        external_id: Annotated[str | None, Field(description="External ID.")] = None,
        language: Annotated[str | None, Field(description="ISO 639-1.")] = None,
        timezone: Annotated[str | None, Field(description="IANA timezone.")] = None,
        note: Annotated[str | None, Field(description="Internal note.")] = None,
        channels: Annotated[
            list[dict[str, Any]] | None,
            Field(description="REPLACES all channels: [{address, preferred, type}]."),
        ] = None,
        meta: Annotated[dict[str, Any] | None, Field(description="Metadata.")] = None,
        custom_fields: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Custom field values: [{id, value}]."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "firstname": firstname,
                "lastname": lastname,
                "email": email,
                "external_id": external_id,
                "language": language,
                "timezone": timezone,
                "note": note,
                "channels": channels,
                "meta": meta,
                "custom_fields": custom_fields,
            }
        )
        return await safe(client.put(f"/api/customers/{id}", body))

    registrar.tool(
        "gorgias_update_customer",
        description=(
            "PUT /api/customers/{id} — Partial update. Only provided fields change. "
            "channels REPLACES all existing channels when included."
        ),
        handler=update_customer,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Delete Customer ---
    async def delete_customer(
        id: Annotated[int, Field(description="Customer ID to delete.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/customers/{id}"))

    registrar.tool(
        "gorgias_delete_customer",
        description="DELETE /api/customers/{id} — Permanently delete one customer.",
        handler=delete_customer,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Bulk Delete Customers ---
    async def delete_customers(
        ids: Annotated[
            list[int],
            Field(description="Customer IDs to delete.", min_length=1),
        ],
    ) -> dict[str, Any]:
        return await safe(client.delete("/api/customers", {"ids": ids}))

    registrar.tool(
        "gorgias_delete_customers",
        description="DELETE /api/customers — Bulk delete customers.",
        handler=delete_customers,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Merge Customers ---
    async def merge_customers(
        source_id: Annotated[
            int,
            Field(description="Source customer (will be deleted after merge).", ge=1),
        ],
        target_id: Annotated[
            int,
            Field(description="Target customer (survives the merge).", ge=1),
        ],
        name: Annotated[str | None, Field(description="Set name on target.")] = None,
        email: Annotated[str | None, Field(description="Set email on target.")] = None,
        external_id: Annotated[str | None, Field(description="Set external_id.")] = None,
        note: Annotated[str | None, Field(description="Set note.")] = None,
        language: Annotated[str | None, Field(description="ISO 639-1.")] = None,
        timezone: Annotated[str | None, Field(description="IANA timezone.")] = None,
        channels: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Channels: [{address, type, preferred?}]."),
        ] = None,
        meta: Annotated[dict[str, Any] | None, Field(description="Metadata.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "email": email,
                "external_id": external_id,
                "note": note,
                "language": language,
                "timezone": timezone,
                "channels": channels,
                "meta": meta,
            }
        )
        return await safe(
            client.put(
                "/api/customers/merge",
                body,
                {"source_id": source_id, "target_id": target_id},
            )
        )

    registrar.tool(
        "gorgias_merge_customers",
        description=(
            "PUT /api/customers/merge — Merge source into target. 409 if both have "
            "data for the same integration."
        ),
        handler=merge_customers,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    # --- Set Customer Data ---
    async def set_customer_data(
        customer_id: Annotated[int, Field(description="Customer ID.", ge=1)],
        data: Annotated[
            Any,
            Field(description="Free-form JSON to store on the customer."),
        ],
        version: Annotated[
            str | None,
            Field(description="ISO 8601 for optimistic concurrency."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none({"data": data, "version": version})
        return await safe(client.put(f"/api/customers/{customer_id}/data", body))

    registrar.tool(
        "gorgias_set_customer_data",
        description=(
            "PUT /api/customers/{customer_id}/data — Replace customer data. "
            "Optional optimistic-concurrency 'version' is silently ignored when "
            "stored data is newer."
        ),
        handler=set_customer_data,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- List Customer Field Values ---
    async def list_customer_field_values(
        customer_id: Annotated[int, Field(description="Customer ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/customers/{customer_id}/custom-fields"))

    registrar.tool(
        "gorgias_list_customer_field_values",
        description=(
            "GET /api/customers/{customer_id}/custom-fields — Custom field values "
            "for a customer."
        ),
        handler=list_customer_field_values,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Update Single Customer Field Value ---
    async def update_customer_field_value(
        customer_id: Annotated[int, Field(description="Customer ID.", ge=1)],
        id: Annotated[int, Field(description="Custom field DEFINITION ID.", ge=1)],
        definition_id: Annotated[
            int,
            Field(description="Custom field definition ID echoed in body.", ge=1),
        ],
        value: Annotated[Any, Field(description="New value. null to clear.")],
    ) -> dict[str, Any]:
        return await safe(
            client.put(
                f"/api/customers/{customer_id}/custom-fields/{id}",
                {"id": definition_id, "value": value},
            )
        )

    registrar.tool(
        "gorgias_update_customer_field_value",
        description=(
            "PUT /api/customers/{customer_id}/custom-fields/{id} — Update one "
            "custom field value on a customer."
        ),
        handler=update_customer_field_value,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Bulk Update Customer Custom Field Values ---
    async def update_customer_fields(
        customer_id: Annotated[int, Field(description="Customer ID.", ge=1)],
        fields: Annotated[
            list[dict[str, Any]],
            Field(description="[{id, value}] field updates.", min_length=1),
        ],
    ) -> dict[str, Any]:
        return await safe(
            client.put(f"/api/customers/{customer_id}/custom-fields", fields)
        )

    registrar.tool(
        "gorgias_update_customer_fields",
        description=(
            "PUT /api/customers/{customer_id}/custom-fields — Bulk update custom "
            "field values on a customer."
        ),
        handler=update_customer_fields,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Delete Customer Field Value ---
    async def delete_customer_field_value(
        customer_id: Annotated[int, Field(description="Customer ID.", ge=1)],
        id: Annotated[int, Field(description="Custom field DEFINITION ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(
            client.delete(f"/api/customers/{customer_id}/custom-fields/{id}")
        )

    registrar.tool(
        "gorgias_delete_customer_field_value",
        description=(
            "DELETE /api/customers/{customer_id}/custom-fields/{id} — Remove a "
            "custom field value (definition is unaffected)."
        ),
        handler=delete_customer_field_value,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
