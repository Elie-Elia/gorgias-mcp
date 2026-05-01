"""Reporting tools — low-level analytics statistics endpoint.

For LLM-friendly usage with auto-defaults, validation, and pagination, use
gorgias_smart_stats from tools.smart_stats instead.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_Scope = Literal[
    "tickets-closed",
    "tickets-created",
    "tickets-open",
    "tickets-replied",
    "one-touch-tickets",
    "zero-touch-tickets",
    "satisfaction-surveys",
    "resolution-time",
    "messages-sent",
    "first-response-time",
    "human-first-response-time",
    "response-time",
    "messages-per-ticket",
    "ticket-handle-time",
    "online-time",
    "tags",
    "auto-qa",
    "messages-received",
    "automation-rate",
    "workload-tickets",
    "automated-interactions",
    "ticket-fields",
    "voice-calls",
    "voice-agent-events",
    "ticket-sla",
    "knowledge-insights",
    "voice-calls-summary",
]


def register_reporting_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def retrieve_reporting_statistic(
        query: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Reporting query: {scope, filters, timezone, dimensions?, "
                    "measures?, time_dimensions?, order?}. scope determines "
                    "available dimensions/measures/filters."
                )
            ),
        ],
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None,
            Field(description="Per-page (default 30, max 10000).", ge=1, le=10000),
        ] = None,
    ) -> dict[str, Any]:
        query_params = drop_none({"cursor": cursor, "limit": limit})
        return await safe(
            client.post("/api/reporting/stats", {"query": query}, query_params)
        )

    registrar.tool(
        "gorgias_retrieve_reporting_statistic",
        description=(
            "POST /api/reporting/stats — Low-level reporting endpoint. For "
            "LLM-friendly usage with defaults and validation, use "
            "gorgias_smart_stats. Available scopes (27): tickets-closed, "
            "tickets-created, tickets-open, tickets-replied, one-touch-tickets, "
            "zero-touch-tickets, satisfaction-surveys, resolution-time, "
            "messages-sent, first-response-time, human-first-response-time, "
            "response-time, messages-per-ticket, ticket-handle-time, online-time, "
            "tags, auto-qa, messages-received, automation-rate, workload-tickets, "
            "automated-interactions, ticket-fields, voice-calls, voice-agent-events, "
            "ticket-sla, knowledge-insights, voice-calls-summary."
        ),
        handler=retrieve_reporting_statistic,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
