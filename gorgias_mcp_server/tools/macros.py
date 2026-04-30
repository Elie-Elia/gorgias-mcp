"""Macro tools — list/get/create/update/delete and bulk archive/unarchive."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_OrderBy = Literal[
    "name:asc",
    "name:desc",
    "created_datetime:asc",
    "created_datetime:desc",
    "updated_datetime:asc",
    "updated_datetime:desc",
    "usage:asc",
    "usage:desc",
    "relevance:asc",
    "relevance:desc",
    "language:asc",
    "language:desc",
]

_Intent = Literal[
    "discount/request",
    "exchange/request",
    "exchange/status",
    "feedback",
    "order/damaged",
    "order/cancel",
    "order/change",
    "order/wrong",
    "other/no_reply",
    "other/question",
    "other/thanks",
    "product/recommendation",
    "product/question",
    "refund/request",
    "refund/status",
    "return/request",
    "return/status",
    "shipping/change",
    "shipping/delivery-issue",
    "shipping/policy",
    "shipping/status",
    "stock/request",
    "subscription/cancel",
    "subscription/change",
]


def register_macro_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_macros(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None,
            Field(description="Per-page (default 30, max 100).", ge=1, le=100),
        ] = None,
        order_by: Annotated[
            _OrderBy | None,
            Field(description="Sort order. 'relevance' requires ticket_id."),
        ] = None,
        search: Annotated[str | None, Field(description="Search filter.")] = None,
        tags: Annotated[list[str] | None, Field(description="Filter by tags.")] = None,
        languages: Annotated[
            list[str] | None, Field(description="Filter by ISO 639-1 codes.")
        ] = None,
        ticket_id: Annotated[
            int | None,
            Field(description="Order by relevance to this ticket.", ge=1),
        ] = None,
        message_id: Annotated[
            int | None,
            Field(description="Refine relevance using this message.", ge=1),
        ] = None,
        number_predictions: Annotated[
            int | None,
            Field(description="Number of relevant macros to surface (default 0)."),
        ] = None,
        archived: Annotated[
            bool | None,
            Field(description="Filter by archived status (default false)."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/macros",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "order_by": order_by,
                        "search": search,
                        "tags": tags,
                        "languages": languages,
                        "ticket_id": ticket_id,
                        "message_id": message_id,
                        "number_predictions": number_predictions,
                        "archived": archived,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_macros",
        description=(
            "GET /api/macros — List canned-response macros with filtering by "
            "search, tags, language, archived, and ticket relevance."
        ),
        handler=list_macros,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_macro(
        id: Annotated[int, Field(description="Macro ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/macros/{id}"))

    registrar.tool(
        "gorgias_get_macro",
        description="GET /api/macros/{id} — Single macro with all its actions.",
        handler=get_macro,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_macro(
        name: Annotated[str, Field(description="Macro name.")],
        actions: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Actions: [{name, title, arguments, type?, description?}]."
                )
            ),
        ] = None,
        external_id: Annotated[
            str | None, Field(description="External system ID.")
        ] = None,
        intent: Annotated[
            _Intent | None,
            Field(description="Intended use case (predefined intents)."),
        ] = None,
        language: Annotated[
            str | None, Field(description="ISO 639-1 (e.g. 'en', 'fr').")
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "actions": actions,
                "external_id": external_id,
                "intent": intent,
                "language": language,
            }
        )
        return await safe(client.post("/api/macros", body))

    registrar.tool(
        "gorgias_create_macro",
        description="POST /api/macros — Create a canned-response macro.",
        handler=create_macro,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_macro(
        id: Annotated[int, Field(description="Macro ID.", ge=1)],
        name: Annotated[str | None, Field(description="New name.")] = None,
        actions: Annotated[
            list[dict[str, Any]] | None,
            Field(description="REPLACES the actions array."),
        ] = None,
        external_id: Annotated[str | None, Field(description="External ID.")] = None,
        intent: Annotated[_Intent | None, Field(description="Intent.")] = None,
        language: Annotated[str | None, Field(description="ISO 639-1.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "actions": actions,
                "external_id": external_id,
                "intent": intent,
                "language": language,
            }
        )
        return await safe(client.put(f"/api/macros/{id}", body))

    registrar.tool(
        "gorgias_update_macro",
        description=(
            "PUT /api/macros/{id} — Partial update. Including 'actions' replaces "
            "the entire actions array."
        ),
        handler=update_macro,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_macro(
        id: Annotated[int, Field(description="Macro ID to delete.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/macros/{id}"))

    registrar.tool(
        "gorgias_delete_macro",
        description=(
            "DELETE /api/macros/{id} — Permanent delete. Macros in active rules "
            "return 409."
        ),
        handler=delete_macro,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def archive_macros(
        ids: Annotated[
            list[int],
            Field(description="Macro IDs (1–30).", min_length=1, max_length=30),
        ],
    ) -> dict[str, Any]:
        return await safe(client.put("/api/macros/archive", {"ids": ids}))

    registrar.tool(
        "gorgias_archive_macros",
        description="PUT /api/macros/archive — Bulk archive (max 30).",
        handler=archive_macros,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "destructiveHint": True,
            "openWorldHint": True,
        },
    )

    async def unarchive_macros(
        ids: Annotated[
            list[int],
            Field(description="Macro IDs (1–30).", min_length=1, max_length=30),
        ],
    ) -> dict[str, Any]:
        return await safe(client.put("/api/macros/unarchive", {"ids": ids}))

    registrar.tool(
        "gorgias_unarchive_macros",
        description="PUT /api/macros/unarchive — Bulk unarchive (max 30).",
        handler=unarchive_macros,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
