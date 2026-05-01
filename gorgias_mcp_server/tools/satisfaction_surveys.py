"""Satisfaction survey tools — CSAT survey CRUD."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


def register_satisfaction_survey_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def list_satisfaction_surveys(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[int | None, Field(description="Per-page (default 30).")] = None,
        order_by: Annotated[
            str | None, Field(description="Sort, e.g. 'created_datetime:desc'.")
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/satisfaction-surveys",
                drop_none(
                    {"cursor": cursor, "limit": limit, "order_by": order_by}
                ),
            )
        )

    registrar.tool(
        "gorgias_list_satisfaction_surveys",
        description="GET /api/satisfaction-surveys — Paginated CSAT survey list.",
        handler=list_satisfaction_surveys,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_satisfaction_survey(
        id: Annotated[int, Field(description="Survey ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/satisfaction-surveys/{id}"))

    registrar.tool(
        "gorgias_get_satisfaction_survey",
        description="GET /api/satisfaction-surveys/{id} — Single survey.",
        handler=get_satisfaction_survey,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_satisfaction_survey(
        customer_id: Annotated[int, Field(description="Customer ID.", ge=1)],
        ticket_id: Annotated[
            int,
            Field(description="Ticket ID (only one survey per ticket).", ge=1),
        ],
        body_text: Annotated[
            str | None,
            Field(description="Customer comment (max 1000).", max_length=1000),
        ] = None,
        created_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Custom metadata.")
        ] = None,
        score: Annotated[
            int | None,
            Field(description="1–5 score.", ge=1, le=5),
        ] = None,
        scored_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        sent_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        should_send_datetime: Annotated[
            str | None,
            Field(description="ISO 8601. null prevents auto-send."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "customer_id": customer_id,
                "ticket_id": ticket_id,
                "body_text": body_text,
                "created_datetime": created_datetime,
                "meta": meta,
                "score": score,
                "scored_datetime": scored_datetime,
                "sent_datetime": sent_datetime,
                "should_send_datetime": should_send_datetime,
            }
        )
        return await safe(client.post("/api/satisfaction-surveys", body))

    registrar.tool(
        "gorgias_create_satisfaction_survey",
        description="POST /api/satisfaction-surveys — Create a CSAT survey.",
        handler=create_satisfaction_survey,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_satisfaction_survey(
        id: Annotated[int, Field(description="Survey ID.", ge=1)],
        customer_id: Annotated[int, Field(description="Customer ID (PUT replaces).", ge=1)],
        ticket_id: Annotated[int, Field(description="Ticket ID (PUT replaces).", ge=1)],
        created_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        body_text: Annotated[
            str | None, Field(description="Comment (max 1000).", max_length=1000)
        ] = None,
        meta: Annotated[dict[str, Any] | None, Field(description="Metadata.")] = None,
        score: Annotated[int | None, Field(description="1–5.", ge=1, le=5)] = None,
        scored_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        sent_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
        should_send_datetime: Annotated[str | None, Field(description="ISO 8601.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "customer_id": customer_id,
                "ticket_id": ticket_id,
                "created_datetime": created_datetime,
                "body_text": body_text,
                "meta": meta,
                "score": score,
                "scored_datetime": scored_datetime,
                "sent_datetime": sent_datetime,
                "should_send_datetime": should_send_datetime,
            }
        )
        return await safe(client.put(f"/api/satisfaction-surveys/{id}", body))

    registrar.tool(
        "gorgias_update_satisfaction_survey",
        description=(
            "PUT /api/satisfaction-surveys/{id} — Full-replacement update. "
            "Re-send customer_id and ticket_id."
        ),
        handler=update_satisfaction_survey,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
