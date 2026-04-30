"""User tools — list/get/create/update/delete agents and admins."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


_RoleName = Literal[
    "admin",
    "agent",
    "basic-agent",
    "bot",
    "internal-agent",
    "lite-agent",
    "observer-agent",
]


def register_user_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def list_users(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        email: Annotated[str | None, Field(description="Filter by exact email.")] = None,
        external_id: Annotated[str | None, Field(description="Filter by external ID.")] = None,
        search: Annotated[str | None, Field(description="Free-text search.")] = None,
        available_first: Annotated[
            bool | None, Field(description="Prioritise available users.")
        ] = None,
        roles: Annotated[
            list[str] | None, Field(description="Filter by role names.")
        ] = None,
        order_by: Annotated[
            str | None,
            Field(description="Sort order, e.g. 'name:asc', 'created_datetime:desc'."),
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/users",
                drop_none(
                    {
                        "cursor": cursor,
                        "limit": limit,
                        "email": email,
                        "external_id": external_id,
                        "search": search,
                        "available_first": available_first,
                        "roles": roles,
                        "order_by": order_by,
                    }
                ),
            )
        )

    registrar.tool(
        "gorgias_list_users",
        description="GET /api/users — Paginated user list.",
        handler=list_users,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_user(
        id: Annotated[
            int,
            Field(description="User ID. 0 = currently authenticated user.", ge=0),
        ],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/users/{id}"))

    registrar.tool(
        "gorgias_get_user",
        description="GET /api/users/{id} — Single user. id=0 returns the caller.",
        handler=get_user,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def create_user(
        email: Annotated[str, Field(description="Login email.")],
        name: Annotated[str, Field(description="Full name.")],
        role: Annotated[
            dict[str, Any],
            Field(description="Role: {name: 'admin' | 'agent' | ...}."),
        ],
        firstname: Annotated[str | None, Field(description="First name.")] = None,
        lastname: Annotated[str | None, Field(description="Last name.")] = None,
        active: Annotated[bool | None, Field(description="Can log in (default true).")] = None,
        bio: Annotated[str | None, Field(description="Short bio.")] = None,
        country: Annotated[str | None, Field(description="ISO 3166-1 alpha-2.")] = None,
        external_id: Annotated[str | None, Field(description="External system ID.")] = None,
        language: Annotated[
            Literal["fr", "en"] | None,
            Field(description="UI locale (Gorgias-restricted to fr/en)."),
        ] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Arbitrary metadata.")
        ] = None,
        timezone: Annotated[str | None, Field(description="IANA timezone.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "email": email,
                "name": name,
                "role": role,
                "firstname": firstname,
                "lastname": lastname,
                "active": active,
                "bio": bio,
                "country": country,
                "external_id": external_id,
                "language": language,
                "meta": meta,
                "timezone": timezone,
            }
        )
        return await safe(client.post("/api/users", body))

    registrar.tool(
        "gorgias_create_user",
        description="POST /api/users — Create a new user (agent or admin).",
        handler=create_user,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def update_user(
        id: Annotated[int, Field(description="User ID. 0 = caller.", ge=0)],
        bio: Annotated[str | None, Field(description="Bio.")] = None,
        country: Annotated[str | None, Field(description="ISO 3166-1 alpha-2.")] = None,
        email: Annotated[
            str | None,
            Field(description="Email (requires password_confirmation when changing)."),
        ] = None,
        external_id: Annotated[str | None, Field(description="External ID.")] = None,
        language: Annotated[
            Literal["fr", "en"] | None, Field(description="UI locale.")
        ] = None,
        meta: Annotated[
            dict[str, Any] | None, Field(description="Replaces meta entirely.")
        ] = None,
        name: Annotated[str | None, Field(description="Full name.")] = None,
        new_password: Annotated[str | None, Field(description="New password.")] = None,
        old_password: Annotated[
            str | None, Field(description="Current password (required for change).")
        ] = None,
        password_confirmation: Annotated[
            str | None, Field(description="Current password (required to change email).")
        ] = None,
        role: Annotated[
            dict[str, Any] | None, Field(description="Role: {name}.")
        ] = None,
        firstname: Annotated[str | None, Field(description="First name.")] = None,
        lastname: Annotated[str | None, Field(description="Last name.")] = None,
        active: Annotated[bool | None, Field(description="Can log in.")] = None,
        timezone: Annotated[str | None, Field(description="IANA timezone.")] = None,
        two_fa_code: Annotated[str | None, Field(description="2FA code, if required.")] = None,
    ) -> dict[str, Any]:
        body = drop_none(
            {
                "bio": bio,
                "country": country,
                "email": email,
                "external_id": external_id,
                "language": language,
                "meta": meta,
                "name": name,
                "new_password": new_password,
                "old_password": old_password,
                "password_confirmation": password_confirmation,
                "role": role,
                "firstname": firstname,
                "lastname": lastname,
                "active": active,
                "timezone": timezone,
                "two_fa_code": two_fa_code,
            }
        )
        return await safe(client.put(f"/api/users/{id}", body))

    registrar.tool(
        "gorgias_update_user",
        description="PUT /api/users/{id} — Partial update. id=0 updates the caller.",
        handler=update_user,
        annotations={
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )

    async def delete_user(
        id: Annotated[int, Field(description="User ID to delete.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/users/{id}"))

    registrar.tool(
        "gorgias_delete_user",
        description=(
            "DELETE /api/users/{id} — Permanently delete a user. The Gorgias API "
            "does not expose a bulk delete on /api/users."
        ),
        handler=delete_user,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
