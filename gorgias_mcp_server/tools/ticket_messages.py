"""Ticket message tools — list/get/create/update/delete messages on tickets."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_Channel = Literal[
    "aircall",
    "api",
    "chat",
    "contact_form",
    "email",
    "facebook",
    "facebook-mention",
    "facebook-messenger",
    "facebook-recommendations",
    "help-center",
    "instagram-ad-comment",
    "instagram-comment",
    "instagram-direct-message",
    "instagram-mention",
    "internal-note",
    "phone",
    "sms",
    "twitter",
    "twitter-direct-message",
    "whatsapp",
    "yotpo-review",
]

_Via = Literal[
    "aircall",
    "api",
    "chat",
    "contact_form",
    "email",
    "facebook",
    "facebook-mention",
    "facebook-messenger",
    "facebook-recommendations",
    "form",
    "gorgias_chat",
    "help-center",
    "helpdesk",
    "instagram",
    "instagram-ad-comment",
    "instagram-comment",
    "instagram-direct-message",
    "instagram-mention",
    "internal-note",
    "offline_capture",
    "phone",
    "rule",
    "self_service",
    "shopify",
    "sms",
    "twilio",
    "twitter",
    "twitter-direct-message",
    "whatsapp",
    "yotpo",
    "yotpo-review",
    "zendesk",
]


def register_ticket_message_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    # --- List Ticket Messages (deprecated, per-ticket) ---
    async def list_ticket_messages(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/tickets/{ticket_id}/messages"))

    registrar.tool(
        "gorgias_list_ticket_messages",
        description=(
            "GET /api/tickets/{ticket_id}/messages — Raw messages for a ticket. "
            "Prefer gorgias_smart_get_ticket for a clean projected view, or "
            "gorgias_list_messages with a ticket_id filter for pagination."
        ),
        handler=list_ticket_messages,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- List Messages (cross-ticket, paginated) ---
    async def list_messages(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None,
            Field(description="Max per page (default 30, max 100).", ge=1, le=100),
        ] = None,
        order_by: Annotated[
            Literal["created_datetime:asc", "created_datetime:desc"] | None,
            Field(description="Sort order. Default: created_datetime:desc."),
        ] = None,
        ticket_id: Annotated[
            int | None,
            Field(description="Filter to a single ticket's messages.", ge=1),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/messages",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "ticket_id": ticket_id,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_messages",
        description=(
            "GET /api/messages — Cross-ticket message list with cursor pagination."
        ),
        handler=list_messages,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Get Message ---
    async def get_message(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        id: Annotated[int, Field(description="Message ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/tickets/{ticket_id}/messages/{id}"))

    registrar.tool(
        "gorgias_get_message",
        description="GET /api/tickets/{ticket_id}/messages/{id} — Single message.",
        handler=get_message,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    # --- Create Message ---
    async def create_message(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        channel: Annotated[
            _Channel,
            Field(description="Send channel. Use 'internal-note' for agent-only notes."),
        ],
        from_agent: Annotated[
            bool,
            Field(description="True if sent by your company (agent), false if customer."),
        ],
        via: Annotated[_Via, Field(description="How the message is sent.")],
        action: Annotated[
            Literal["force", "retry", "cancel"] | None,
            Field(description="Failure recovery: 'force', 'retry', or 'cancel'."),
        ] = None,
        body_text: Annotated[str | None, Field(description="Plain-text body.")] = None,
        body_html: Annotated[str | None, Field(description="HTML body.")] = None,
        subject: Annotated[str | None, Field(description="Subject (mainly email).")] = None,
        public: Annotated[
            bool | None,
            Field(description="Visible to customers. False for internal notes."),
        ] = None,
        message_id: Annotated[str | None, Field(description="External message ID.")] = None,
        external_id: Annotated[
            str | None, Field(description="Foreign system ID (max 255).", max_length=255)
        ] = None,
        integration_id: Annotated[
            int | None, Field(description="Integration ID.", ge=1)
        ] = None,
        sent_datetime: Annotated[
            str | None,
            Field(description="ISO 8601. Provide to import as already-sent."),
        ] = None,
        created_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        deleted_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        failed_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        opened_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        stripped_text: Annotated[
            str | None, Field(description="Plain-text without signatures/quotes.")
        ] = None,
        stripped_html: Annotated[
            str | None, Field(description="HTML without signatures/quotes.")
        ] = None,
        stripped_signature: Annotated[str | None, Field(description="Signature.")] = None,
        mention_ids: Annotated[
            list[int] | None,
            Field(description="User IDs to mention (internal notes only)."),
        ] = None,
        source: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Routing: {type, from: {address, name}, to: [...], cc: [...], bcc: [...], extra}."
                )
            ),
        ] = None,
        sender: Annotated[
            dict[str, Any] | None,
            Field(description="Originator: {id?, email?, name?, ...}."),
        ] = None,
        receiver: Annotated[
            dict[str, Any] | None,
            Field(description="Primary recipient: {id?, email?, name?, ...}."),
        ] = None,
        attachments: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Attachments: [{url, name, content_type, size?, public?, extra?}]."),
        ] = None,
        headers: Annotated[
            dict[str, Any] | None, Field(description="Email headers as key-value pairs.")
        ] = None,
        macros: Annotated[
            list[dict[str, Any]] | None, Field(description="Macros to apply: [{id}].")
        ] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Custom metadata.")
        ] = None,
        last_sending_error: Annotated[
            dict[str, Any] | None,
            Field(description="Sending error details: {error}."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "channel": channel,
                "from_agent": from_agent,
                "via": via,
                "body_text": body_text,
                "body_html": body_html,
                "subject": subject,
                "public": public,
                "message_id": message_id,
                "external_id": external_id,
                "integration_id": integration_id,
                "sent_datetime": sent_datetime,
                "created_datetime": created_datetime,
                "deleted_datetime": deleted_datetime,
                "failed_datetime": failed_datetime,
                "opened_datetime": opened_datetime,
                "stripped_text": stripped_text,
                "stripped_html": stripped_html,
                "stripped_signature": stripped_signature,
                "mention_ids": mention_ids,
                "source": source,
                "sender": sender,
                "receiver": receiver,
                "attachments": attachments,
                "headers": headers,
                "macros": macros,
                "meta": meta,
                "last_sending_error": last_sending_error,
            }
        )
        query = {"action": action} if action else None
        return await safe(
            client.post(f"/api/tickets/{ticket_id}/messages", body, query)
        )

    registrar.tool(
        "gorgias_create_message",
        description=(
            "POST /api/tickets/{ticket_id}/messages — Create a message on an existing "
            "ticket. Three modes: (1) send to customer (omit sent_datetime); (2) "
            "import already-sent (provide sent_datetime); (3) internal note "
            "(channel='internal-note', public=false)."
        ),
        handler=create_message,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    # --- Update Message ---
    async def update_message(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        id: Annotated[int, Field(description="Message ID.", ge=1)],
        channel: Annotated[_Channel, Field(description="Channel.")],
        from_agent: Annotated[bool, Field(description="From-agent flag.")],
        via: Annotated[_Via, Field(description="Via.")],
        action: Annotated[
            Literal["force", "retry", "cancel"] | None,
            Field(description="Recovery policy for failed external action."),
        ] = None,
        public: Annotated[bool | None, Field(description="Public flag.")] = None,
        body_html: Annotated[str | None, Field(description="HTML body.")] = None,
        body_text: Annotated[str | None, Field(description="Plain-text body.")] = None,
        external_id: Annotated[str | None, Field(description="External ID.")] = None,
        integration_id: Annotated[
            int | None, Field(description="Integration ID.", ge=1)
        ] = None,
        failed_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        message_id: Annotated[str | None, Field(description="External msg ID.")] = None,
        receiver: Annotated[
            dict[str, Any] | None, Field(description="Receiver object.")
        ] = None,
        sender: Annotated[
            dict[str, Any] | None, Field(description="Sender object.")
        ] = None,
        sent_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        source: Annotated[
            dict[str, Any] | None, Field(description="Routing object.")
        ] = None,
        subject: Annotated[str | None, Field(description="Subject.")] = None,
        mention_ids: Annotated[
            list[int] | None, Field(description="Mentioned user IDs.")
        ] = None,
        attachments: Annotated[
            list[dict[str, Any]] | None, Field(description="Attachments.")
        ] = None,
        headers: Annotated[
            dict[str, Any] | None, Field(description="Headers.")
        ] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Metadata.")
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "channel": channel,
                "from_agent": from_agent,
                "via": via,
                "public": public,
                "body_html": body_html,
                "body_text": body_text,
                "external_id": external_id,
                "integration_id": integration_id,
                "failed_datetime": failed_datetime,
                "message_id": message_id,
                "receiver": receiver,
                "sender": sender,
                "sent_datetime": sent_datetime,
                "source": source,
                "subject": subject,
                "mention_ids": mention_ids,
                "attachments": attachments,
                "headers": headers,
                "meta": meta,
            }
        )
        query = {"action": action} if action else None
        return await safe(
            client.put(f"/api/tickets/{ticket_id}/messages/{id}", body, query)
        )

    registrar.tool(
        "gorgias_update_message",
        description=(
            "PUT /api/tickets/{ticket_id}/messages/{id} — Update an existing ticket "
            "message. channel, from_agent, via are required."
        ),
        handler=update_message,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    # --- Delete Message ---
    async def delete_message(
        ticket_id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        id: Annotated[int, Field(description="Message ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/tickets/{ticket_id}/messages/{id}"))

    registrar.tool(
        "gorgias_delete_message",
        description=(
            "DELETE /api/tickets/{ticket_id}/messages/{id} — Permanently delete a "
            "message. The parent ticket is unaffected."
        ),
        handler=delete_message,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
