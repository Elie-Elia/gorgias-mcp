"""Ticket tools for the Gorgias MCP Server.

Mirrors benpalmer1/Gorgias-MCP-Server's tools/tickets.ts:
    list, get, create, update, delete, list/add/remove/set tags,
    list/update/bulk-update/delete custom field values.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_OrderByTickets = Literal[
    "created_datetime:asc",
    "created_datetime:desc",
    "updated_datetime:asc",
    "updated_datetime:desc",
]


def register_ticket_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    # --- List Tickets ---
    async def list_tickets(
        order_by: Annotated[
            _OrderByTickets | None,
            Field(description="Sort order for tickets. Default: 'created_datetime:desc'."),
        ] = None,
        cursor: Annotated[
            str | None,
            Field(description="Pagination cursor from a previous response."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Max tickets per page (default 30, max 100).", ge=1, le=100),
        ] = None,
        customer_id: Annotated[
            int | None,
            Field(description="Filter to a single customer's tickets.", ge=1),
        ] = None,
        external_id: Annotated[
            str | None,
            Field(description="Filter by external ID."),
        ] = None,
        view_id: Annotated[
            int | None,
            Field(description="Filter by saved view ID.", ge=1),
        ] = None,
        rule_id: Annotated[
            int | None,
            Field(description="Filter by rule ID.", ge=1),
        ] = None,
        ticket_ids: Annotated[
            list[int] | None,
            Field(description="Specific ticket IDs to retrieve (max 100).", max_length=100),
        ] = None,
        trashed: Annotated[
            bool | None,
            Field(description="Whether to include trashed tickets (default true)."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/tickets",
                drop_none(
                    {
                        "order_by": order_by,
                        "cursor": cursor,
                        "limit": limit,
                        "customer_id": customer_id,
                        "external_id": external_id,
                        "view_id": view_id,
                        "rule_id": rule_id,
                        "ticket_ids": ticket_ids,
                        "trashed": trashed,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_tickets",
        description=(
            "GET /api/tickets — Paginated list of raw ticket data. For intelligent "
            "search with auto-detection of emails, names, views, and keywords, use "
            "gorgias_smart_search instead. Supports filtering by customer, external "
            "ID, view, rule, specific ticket IDs, and whether to include trashed "
            "tickets. Cursor-based pagination."
        ),
        handler=list_tickets,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Get Ticket ---
    async def get_ticket(
        id: Annotated[int, Field(description="The unique ID of the ticket.", ge=1)],
        relationships: Annotated[
            list[Literal["custom_fields"]] | None,
            Field(description="Related objects to include. Currently 'custom_fields' is documented."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                f"/api/tickets/{id}",
                drop_none({"relationships": relationships}),
            )
        )

    registrar.tool(
        "gorgias_get_ticket",
        description=(
            "GET /api/tickets/{id} — Retrieve a single ticket's raw API response. "
            "For an LLM-optimised view with chronologically sorted messages, use "
            "gorgias_smart_get_ticket instead."
        ),
        handler=get_ticket,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Create Ticket ---
    async def create_ticket(
        via: Annotated[
            str,
            Field(
                description=(
                    "How the first message was received or sent. Common values: "
                    "'api', 'email', 'helpdesk', 'chat', 'sms', 'phone', "
                    "'facebook-messenger', 'instagram-direct-message', 'whatsapp'."
                )
            ),
        ],
        messages: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    "Array of message objects (1–500). Each message requires "
                    "channel (string), from_agent (boolean), via (string). Optional: "
                    "body_text, body_html, public, subject, sender, receiver, source, "
                    "attachments, integration_id, message_id, external_id, "
                    "created_datetime, sent_datetime, headers, meta, mention_ids."
                ),
                min_length=1,
                max_length=500,
            ),
        ],
        channel: Annotated[
            str | None,
            Field(description="Channel used to initiate the conversation."),
        ] = None,
        subject: Annotated[
            str | None,
            Field(description="Subject of the ticket (max 998 chars).", max_length=998),
        ] = None,
        status: Annotated[
            Literal["open", "closed"] | None,
            Field(description="Status of the ticket. Default: 'open'."),
        ] = None,
        priority: Annotated[
            Literal["critical", "high", "normal", "low"] | None,
            Field(description="Priority of the ticket. Default: 'normal'."),
        ] = None,
        customer: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Customer associated with the ticket: {id?, email?, name?}."
                )
            ),
        ] = None,
        assignee_user: Annotated[
            dict[str, Any] | None,
            Field(description="User assigned to the ticket: {id}."),
        ] = None,
        assignee_team: Annotated[
            dict[str, Any] | None,
            Field(description="Team assigned to the ticket: {id}."),
        ] = None,
        tags: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Tags for the ticket: [{name, decoration?: {color?}}]."
                )
            ),
        ] = None,
        custom_fields: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Custom field values: [{id, value}]."),
        ] = None,
        external_id: Annotated[
            str | None,
            Field(description="External ID (max 255 chars).", max_length=255),
        ] = None,
        from_agent: Annotated[
            bool | None,
            Field(description="Whether first message was sent by your company."),
        ] = None,
        language: Annotated[
            str | None,
            Field(description="ISO 639-1 language code. Auto-detected if unset."),
        ] = None,
        spam: Annotated[
            bool | None,
            Field(description="Whether the ticket is spam. Default: false."),
        ] = None,
        meta: Annotated[
            dict[str, Any] | None,
            Field(description="Arbitrary metadata key-value pairs."),
        ] = None,
        created_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        opened_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        closed_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        trashed_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        snooze_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        updated_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "via": via,
                "messages": messages,
                "channel": channel,
                "subject": subject,
                "status": status,
                "priority": priority,
                "customer": customer,
                "assignee_user": assignee_user,
                "assignee_team": assignee_team,
                "tags": tags,
                "custom_fields": custom_fields,
                "external_id": external_id,
                "from_agent": from_agent,
                "language": language,
                "spam": spam,
                "meta": meta,
                "created_datetime": created_datetime,
                "opened_datetime": opened_datetime,
                "closed_datetime": closed_datetime,
                "trashed_datetime": trashed_datetime,
                "snooze_datetime": snooze_datetime,
                "updated_datetime": updated_datetime,
            }
        )
        return await safe(client.post("/api/tickets", body))

    registrar.tool(
        "gorgias_create_ticket",
        description=(
            "POST /api/tickets — Create a new support ticket. Requires 'via' and at "
            "least one message. Each message must include channel, from_agent, via."
        ),
        handler=create_ticket,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    # --- Update Ticket ---
    async def update_ticket(
        id: Annotated[int, Field(description="Ticket ID to update.", ge=1)],
        status: Annotated[Literal["open", "closed"] | None, Field(description="Status.")] = None,
        priority: Annotated[
            Literal["critical", "high", "normal", "low"] | None,
            Field(description="Priority."),
        ] = None,
        subject: Annotated[
            str | None, Field(description="Subject (max 998).", max_length=998)
        ] = None,
        channel: Annotated[str | None, Field(description="Channel.")] = None,
        via: Annotated[str | None, Field(description="Via.")] = None,
        assignee_user: Annotated[
            dict[str, Any] | None,
            Field(description="Assigned user: {id}. Send {id: null} to unassign."),
        ] = None,
        assignee_team: Annotated[
            dict[str, Any] | None,
            Field(description="Assigned team: {id}. Send {id: null} to unassign."),
        ] = None,
        customer: Annotated[
            dict[str, Any] | None,
            Field(description="Linked customer: {id?, email?, name?}."),
        ] = None,
        tags: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "REPLACES all tags. Use add/remove/set ticket tag tools instead."
                )
            ),
        ] = None,
        custom_fields: Annotated[
            list[dict[str, Any]] | None,
            Field(description="REPLACES custom field values: [{id, value}]."),
        ] = None,
        spam: Annotated[bool | None, Field(description="Spam flag.")] = None,
        from_agent: Annotated[bool | None, Field(description="From agent flag.")] = None,
        language: Annotated[str | None, Field(description="ISO 639-1.")] = None,
        external_id: Annotated[
            str | None, Field(description="External ID (max 255).", max_length=255)
        ] = None,
        meta: Annotated[dict[str, Any] | None, Field(description="Metadata.")] = None,
        snooze_datetime: Annotated[
            str | None, Field(description="ISO 8601. null to cancel snooze.")
        ] = None,
        closed_datetime: Annotated[
            str | None, Field(description="ISO 8601. Setting closes the ticket.")
        ] = None,
        trashed_datetime: Annotated[
            str | None, Field(description="ISO 8601. null to restore from trash.")
        ] = None,
        opened_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        updated_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        last_message_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        last_received_message_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "status": status,
                "priority": priority,
                "subject": subject,
                "channel": channel,
                "via": via,
                "assignee_user": assignee_user,
                "assignee_team": assignee_team,
                "customer": customer,
                "tags": tags,
                "custom_fields": custom_fields,
                "spam": spam,
                "from_agent": from_agent,
                "language": language,
                "external_id": external_id,
                "meta": meta,
                "snooze_datetime": snooze_datetime,
                "closed_datetime": closed_datetime,
                "trashed_datetime": trashed_datetime,
                "opened_datetime": opened_datetime,
                "updated_datetime": updated_datetime,
                "last_message_datetime": last_message_datetime,
                "last_received_message_datetime": last_received_message_datetime,
            }
        )
        return await safe(client.put(f"/api/tickets/{id}", body))

    registrar.tool(
        "gorgias_update_ticket",
        description=(
            "PUT /api/tickets/{id} — Update an existing ticket. Only provided fields "
            "are changed. NOTE: 'tags' and 'custom_fields' fully REPLACE existing values; "
            "use the dedicated tag/field tools for additive changes."
        ),
        handler=update_ticket,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Delete Ticket ---
    async def delete_ticket(
        id: Annotated[int, Field(description="Ticket ID to permanently delete.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/tickets/{id}"))

    registrar.tool(
        "gorgias_delete_ticket",
        description=(
            "DELETE /api/tickets/{id} — Permanently delete a ticket. Irreversible. "
            "Consider trashed_datetime via Update Ticket for soft-delete."
        ),
        handler=delete_ticket,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    # --- List Ticket Tags ---
    async def list_ticket_tags(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/tickets/{ticket_id}/tags"))

    registrar.tool(
        "gorgias_list_ticket_tags",
        description=(
            "GET /api/tickets/{ticket_id}/tags — List all tags currently associated "
            "with a ticket. Returns {data: [...]}."
        ),
        handler=list_ticket_tags,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Add Ticket Tags ---
    async def add_ticket_tags(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        ids: Annotated[
            list[int] | None,
            Field(description="Tag IDs to add."),
        ] = None,
        names: Annotated[
            list[str] | None,
            Field(description="Tag names to add (case-sensitive)."),
        ] = None,
    ) -> dict[str, Any]:
        if not (ids or names):
            return {"error": "At least one of 'ids' or 'names' must be provided."}
        body = drop_none({"ids": ids, "names": names})
        return await safe(client.post(f"/api/tickets/{ticket_id}/tags", body))

    registrar.tool(
        "gorgias_add_ticket_tags",
        description=(
            "POST /api/tickets/{ticket_id}/tags — Additively add tags by ID or name. "
            "Existing tags are preserved."
        ),
        handler=add_ticket_tags,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    # --- Set Ticket Tags ---
    async def set_ticket_tags(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        ids: Annotated[list[int] | None, Field(description="Tag IDs to set.")] = None,
        names: Annotated[list[str] | None, Field(description="Tag names to set.")] = None,
    ) -> dict[str, Any]:
        body = drop_none({"ids": ids, "names": names})
        return await safe(client.put(f"/api/tickets/{ticket_id}/tags", body))

    registrar.tool(
        "gorgias_set_ticket_tags",
        description=(
            "PUT /api/tickets/{ticket_id}/tags — Replace ALL tags on a ticket. Send "
            "an empty body to clear all tags."
        ),
        handler=set_ticket_tags,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    # --- Remove Ticket Tags ---
    async def remove_ticket_tags(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        ids: Annotated[list[int] | None, Field(description="Tag IDs to remove.")] = None,
        names: Annotated[list[str] | None, Field(description="Tag names to remove.")] = None,
    ) -> dict[str, Any]:
        if not (ids or names):
            return {"error": "At least one of 'ids' or 'names' must be provided."}
        body = drop_none({"ids": ids, "names": names})
        return await safe(client.delete(f"/api/tickets/{ticket_id}/tags", body))

    registrar.tool(
        "gorgias_remove_ticket_tags",
        description=(
            "DELETE /api/tickets/{ticket_id}/tags — Remove specific tags from a "
            "ticket. Other tags remain."
        ),
        handler=remove_ticket_tags,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    # --- List Ticket Custom Field Values ---
    async def list_ticket_fields(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/tickets/{ticket_id}/custom-fields"))

    registrar.tool(
        "gorgias_list_ticket_fields",
        description=(
            "GET /api/tickets/{ticket_id}/custom-fields — List custom field values on "
            "a ticket. Returns {data: [...]}; each item has field, prediction, value."
        ),
        handler=list_ticket_fields,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Update Single Ticket Custom Field Value ---
    async def update_ticket_field(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        id: Annotated[int, Field(description="Custom field DEFINITION ID.", ge=1)],
        definition_id: Annotated[
            int,
            Field(description="Custom field definition ID sent in the body. Usually equal to path id.", ge=1),
        ],
        value: Annotated[
            Any,
            Field(description="New value. Type matches the field's data_type. null to clear."),
        ],
    ) -> dict[str, Any]:
        return await safe(
            client.put(
                f"/api/tickets/{ticket_id}/custom-fields/{id}",
                {"id": definition_id, "value": value},
            )
        )

    registrar.tool(
        "gorgias_update_ticket_field",
        description=(
            "PUT /api/tickets/{ticket_id}/custom-fields/{id} — Update a single "
            "custom field value on a ticket."
        ),
        handler=update_ticket_field,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Bulk Update Ticket Custom Field Values ---
    async def update_ticket_fields(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        fields: Annotated[
            list[dict[str, Any]],
            Field(
                description="Array of [{id, value}] field updates.",
                min_length=1,
            ),
        ],
    ) -> dict[str, Any]:
        return await safe(
            client.put(f"/api/tickets/{ticket_id}/custom-fields", fields)
        )

    registrar.tool(
        "gorgias_update_ticket_fields",
        description=(
            "PUT /api/tickets/{ticket_id}/custom-fields — Bulk update custom field "
            "values on a ticket."
        ),
        handler=update_ticket_fields,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Delete Ticket Custom Field Value ---
    async def delete_ticket_field(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        id: Annotated[int, Field(description="Custom field DEFINITION ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(
            client.delete(f"/api/tickets/{ticket_id}/custom-fields/{id}")
        )

    registrar.tool(
        "gorgias_delete_ticket_field",
        description=(
            "DELETE /api/tickets/{ticket_id}/custom-fields/{id} — Remove a custom "
            "field value from a ticket."
        ),
        handler=delete_ticket_field,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )
