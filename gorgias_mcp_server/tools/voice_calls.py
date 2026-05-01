"""Voice call tools — read-only access to calls, events, and recordings."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import drop_none, safe


def register_voice_call_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def list_voice_calls(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        ticket_id: Annotated[
            int | None, Field(description="Filter by ticket.", ge=1)
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/phone/voice-calls",
                drop_none(
                    {"cursor": cursor, "limit": limit, "ticket_id": ticket_id}
                ),
            )
        )

    registrar.tool(
        "gorgias_list_voice_calls",
        description="GET /api/phone/voice-calls — Cursor-paginated voice calls.",
        handler=list_voice_calls,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_voice_call(
        id: Annotated[int, Field(description="Voice call ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/phone/voice-calls/{id}"))

    registrar.tool(
        "gorgias_get_voice_call",
        description="GET /api/phone/voice-calls/{id} — Single voice call.",
        handler=get_voice_call,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def list_voice_call_events(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        call_id: Annotated[
            int | None, Field(description="Filter by call ID.", ge=1)
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/phone/voice-call-events",
                drop_none(
                    {"cursor": cursor, "limit": limit, "call_id": call_id}
                ),
            )
        )

    registrar.tool(
        "gorgias_list_voice_call_events",
        description="GET /api/phone/voice-call-events — Cursor-paginated call events.",
        handler=list_voice_call_events,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_voice_call_event(
        id: Annotated[int, Field(description="Event ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/phone/voice-call-events/{id}"))

    registrar.tool(
        "gorgias_get_voice_call_event",
        description="GET /api/phone/voice-call-events/{id} — Single voice call event.",
        handler=get_voice_call_event,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def list_voice_call_recordings(
        cursor: Annotated[str | None, Field(description="Pagination cursor.")] = None,
        limit: Annotated[
            int | None, Field(description="Per-page (default 30).", ge=1, le=100)
        ] = None,
        call_id: Annotated[
            int | None, Field(description="Filter by call ID.", ge=1)
        ] = None,
    ) -> dict[str, Any]:
        return await safe(
            client.get(
                "/api/phone/voice-call-recordings",
                drop_none(
                    {"cursor": cursor, "limit": limit, "call_id": call_id}
                ),
            )
        )

    registrar.tool(
        "gorgias_list_voice_call_recordings",
        description=(
            "GET /api/phone/voice-call-recordings — Cursor-paginated recordings/voicemails."
        ),
        handler=list_voice_call_recordings,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def get_voice_call_recording(
        id: Annotated[int, Field(description="Recording ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.get(f"/api/phone/voice-call-recordings/{id}"))

    registrar.tool(
        "gorgias_get_voice_call_recording",
        description="GET /api/phone/voice-call-recordings/{id} — Single recording.",
        handler=get_voice_call_recording,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )

    async def delete_voice_call_recording(
        id: Annotated[int, Field(description="Recording ID.", ge=1)],
    ) -> dict[str, Any]:
        return await safe(client.delete(f"/api/phone/voice-call-recordings/{id}"))

    registrar.tool(
        "gorgias_delete_voice_call_recording",
        description=(
            "DELETE /api/phone/voice-call-recordings/{id} — Permanently delete a "
            "recording or voicemail."
        ),
        handler=delete_voice_call_recording,
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
