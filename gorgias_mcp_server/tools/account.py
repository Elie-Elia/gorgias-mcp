"""Account tools — retrieve and manage account-level settings."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


def register_account_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def retrieve_account() -> dict[str, Any]:
        return await safe(client.get("/api/account"))

    registrar.tool(
        "gorgias_retrieve_account",
        description=(
            "GET /api/account — Retrieve your account information. The account is "
            "determined by authentication credentials."
        ),
        handler=retrieve_account,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def list_account_settings(
        type: Annotated[
            str | None,
            Field(description="Filter by setting type (e.g. 'business-hours')."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get("/api/account/settings", drop_none({"type": type}))
        )

    registrar.tool(
        "gorgias_list_account_settings",
        description=(
            "GET /api/account/settings — List account settings. No pagination — all "
            "settings returned in a single response."
        ),
        handler=list_account_settings,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_account_setting(
        type: Annotated[
            str, Field(description="Setting type identifier (e.g. 'business-hours').")
        ],
        name: Annotated[str | None, Field(description="Human-readable name.")] = None,
        data: Annotated[
            dict[str, Any] | None,
            Field(description="Type-specific config payload."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none({"type": type, "name": name, "data": data})
        return await safe(client.post("/api/account/settings", body))

    registrar.tool(
        "gorgias_create_account_setting",
        description=(
            "POST /api/account/settings — Create a setting for the current account "
            "(business hours, satisfaction surveys, etc.)."
        ),
        handler=create_account_setting,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_account_setting(
        id: Annotated[int, Field(description="Setting ID.", ge=1)],
        type: Annotated[str, Field(description="Setting type (must match existing).")],
        name: Annotated[str | None, Field(description="Name. null to clear.")] = None,
        data: Annotated[
            dict[str, Any] | None,
            Field(description="Replaces existing data entirely."),
        ] = None,
    ) -> dict[str, Any]:
        body = drop_none({"type": type, "name": name, "data": data})
        return await safe(client.put(f"/api/account/settings/{id}", body))

    registrar.tool(
        "gorgias_update_account_setting",
        description=(
            "PUT /api/account/settings/{id} — Replace the configuration of an "
            "AccountSetting by ID."
        ),
        handler=update_account_setting,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
