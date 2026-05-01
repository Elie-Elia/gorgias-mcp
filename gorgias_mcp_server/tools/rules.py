"""Rule tools — automation rule CRUD plus priority batch update."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


def register_rule_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_rules(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 100).", ge=1, le=100)
        ] = None,
        order_by: Annotated[
            Literal["created_datetime:asc", "created_datetime:desc"] | None,
            Field(description="Sort."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/rules",
                drop_none(
                    {"cursor": cursor, "limit": limit, "order_by": order_by}
                ),
            )
        )

    registrar.tool(
        "gorgias_list_rules",
        description="GET /api/rules — Cursor-paginated rule list.",
        handler=list_rules,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_rule(
        id: Annotated[int, Field(description="Rule ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/rules/{id}"))

    registrar.tool(
        "gorgias_get_rule",
        description="GET /api/rules/{id} — Single automation rule.",
        handler=get_rule,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_rule(
        name: Annotated[str, Field(description="Rule name.")],
        code: Annotated[str, Field(description="JavaScript rule logic.")],
        code_ast: Annotated[
            dict[str, Any] | None,
            Field(description="ESTree AST (auto-generated from code if omitted)."),
        ] = None,
        description: Annotated[str | None, Field(description="Description.")] = None,
        event_types: Annotated[
            str | None,
            Field(
                description=(
                    "Comma-separated triggers: ticket-created, ticket-updated, "
                    "ticket-message-created, ticket-assigned, ticket-self-unsnoozed, "
                    "satisfaction-survey-responded."
                )
            ),
        ] = None,
        priority: Annotated[int | None, Field(description="Higher runs first.")] = None,
        deactivated_datetime: Annotated[
            str | None,
            Field(description="ISO 8601 to create deactivated."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "code": code,
                "code_ast": code_ast,
                "description": description,
                "event_types": event_types,
                "priority": priority,
                "deactivated_datetime": deactivated_datetime,
            }
        )
        return await safe(client.post("/api/rules", body))

    registrar.tool(
        "gorgias_create_rule",
        description=(
            "POST /api/rules — Create an automation rule with JavaScript logic and "
            "event triggers."
        ),
        handler=create_rule,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_rule(
        id: Annotated[int, Field(description="Rule ID.", ge=1)],
        name: Annotated[str | None, Field(description="Rule name.")] = None,
        code: Annotated[str | None, Field(description="JavaScript rule logic.")] = None,
        code_ast: Annotated[
            dict[str, Any] | None, Field(description="ESTree AST.")
        ] = None,
        description: Annotated[str | None, Field(description="Description.")] = None,
        event_types: Annotated[str | None, Field(description="Comma-separated triggers.")] = None,
        priority: Annotated[int | None, Field(description="Execution priority.")] = None,
        deactivated_datetime: Annotated[
            str | None,
            Field(description="ISO 8601. null to reactivate."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "name": name,
                "code": code,
                "code_ast": code_ast,
                "description": description,
                "event_types": event_types,
                "priority": priority,
                "deactivated_datetime": deactivated_datetime,
            }
        )
        return await safe(client.put(f"/api/rules/{id}", body))

    registrar.tool(
        "gorgias_update_rule",
        description="PUT /api/rules/{id} — Partial update of an automation rule.",
        handler=update_rule,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_rule(
        id: Annotated[int, Field(description="Rule ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/rules/{id}"))

    registrar.tool(
        "gorgias_delete_rule",
        description="DELETE /api/rules/{id} — Permanently delete a rule.",
        handler=delete_rule,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def update_rules_priorities(
        priorities: Annotated[
            list[dict[str, Any]],
            Field(
                description="Array of {id, priority} pairs.",
                min_length=1,
            ),
        ],
    ) -> dict[str, Any]:
        # The Gorgias API expects {priorities: [...]}, NOT a bare array.
        return await safe(
            client.post("/api/rules/priorities", {"priorities": priorities})
        )

    registrar.tool(
        "gorgias_update_rules_priorities",
        description="POST /api/rules/priorities — Batch update rule execution priorities.",
        handler=update_rules_priorities,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
