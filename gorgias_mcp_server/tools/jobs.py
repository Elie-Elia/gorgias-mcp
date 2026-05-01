"""Job tools — async background job CRUD."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_Status = Literal[
    "pending",
    "scheduled",
    "running",
    "done",
    "cancel_requested",
    "canceled",
    "errored",
    "fatal_errored",
]

_Type = Literal[
    "applyMacro",
    "deleteTicket",
    "exportTicket",
    "exportMacro",
    "importMacro",
    "updateTicket",
    "exportTicketDrilldown",
    "exportConvertCampaignSalesDrilldown",
]


def register_job_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_jobs(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[int | None, Field(description="Per-page (default 30).")] = None,
        order_by: Annotated[
            Literal["created_datetime:asc", "created_datetime:desc"] | None,
            Field(description="Sort."),
        ] = None,
        status: Annotated[_Status | None, Field(description="Filter by status.")] = None,
        type: Annotated[_Type | None, Field(description="Filter by job type.")] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/jobs",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "status": status,
                        "type": type,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_jobs",
        description=(
            "GET /api/jobs — Cursor-paginated background job list. Ordered by "
            "created_datetime descending."
        ),
        handler=list_jobs,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_job(
        id: Annotated[int, Field(description="Job ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/jobs/{id}"))

    registrar.tool(
        "gorgias_get_job",
        description=(
            "GET /api/jobs/{id} — Single job with status, params, info (progress), "
            "and timestamps."
        ),
        handler=get_job,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_job(
        type: Annotated[_Type, Field(description="Job type.")],
        params: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Type-specific config. applyMacro: {macro_id, ticket_ids?, "
                    "view_id?, view?, apply_and_close?}. updateTicket: {updates, ...}. "
                    "importMacro: {url}. exportTicket: {ticket_ids? or view?, ...}."
                )
            ),
        ],
        scheduled_datetime: Annotated[
            str | None,
            Field(description="ISO 8601, max 60 minutes future. null = immediate."),
        ] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Arbitrary metadata.")
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "type": type,
                "params": params,
                "scheduled_datetime": scheduled_datetime,
                "meta": meta,
            }
        )
        return await safe(client.post("/api/jobs", body))

    registrar.tool(
        "gorgias_create_job",
        description=(
            "POST /api/jobs — Create an async background job (bulk macro apply, "
            "ticket exports, imports, etc.)."
        ),
        handler=create_job,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_job(
        id: Annotated[int, Field(description="Job ID.", ge=1)],
        meta: Annotated[
            dict[str, Any] | None, Field(description="Metadata.")
        ] = None,
        params: Annotated[
            dict[str, Any] | None, Field(description="Job parameters.")
        ] = None,
        scheduled_datetime: Annotated[
            str | None, Field(description="ISO 8601 schedule.")
        ] = None,
        status: Annotated[
            _Status | None, Field(description="Transition status.")
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "meta": meta,
                "params": params,
                "scheduled_datetime": scheduled_datetime,
                "status": status,
            }
        )
        return await safe(client.put(f"/api/jobs/{id}", body))

    registrar.tool(
        "gorgias_update_job",
        description="PUT /api/jobs/{id} — Update meta, params, schedule, or status.",
        handler=update_job,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def cancel_job(
        id: Annotated[int, Field(description="Job ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/jobs/{id}"))

    registrar.tool(
        "gorgias_cancel_job",
        description=(
            "DELETE /api/jobs/{id} — Cancel a job. Already-applied changes are not "
            "reverted."
        ),
        handler=cancel_job,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
