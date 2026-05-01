"""Smart ticket detail — single ticket with auto-paginated message thread.

Returns a clean, projected view (chronologically sorted, internal-note flagged)
optimised for LLM consumption. Use `gorgias_get_ticket` for the raw API
response when you need the full ticket payload.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.cache import fetch_all_pages
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.errors import GorgiasApiError, sanitise_error_for_llm
from gorgias_mcp_server.projection import (
    project_message,
    project_ticket,
    sort_messages_chronologically,
)


_DEFAULT_MAX_MESSAGES = 1000
_HARD_CAP_MAX_MESSAGES = 5000


def register_smart_ticket_detail_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def smart_get_ticket(
        id: Annotated[int, Field(description="Ticket ID.", ge=1)],
        max_messages: Annotated[
            int | None,
            Field(
                description=(
                    f"Max messages to fetch (default {_DEFAULT_MAX_MESSAGES}, "
                    f"hard cap {_HARD_CAP_MAX_MESSAGES}). Tickets exceeding the "
                    "cap return truncated=true."
                ),
                ge=1,
                le=_HARD_CAP_MAX_MESSAGES,
            ),
        ] = None,
    ) -> dict[str, Any]:
        message_cap = max_messages or _DEFAULT_MAX_MESSAGES

        try:
            ticket_raw, messages_result = await asyncio.gather(
                client.get(f"/api/tickets/{id}"),
                fetch_all_pages(
                    client,
                    f"/api/tickets/{id}/messages",
                    max_items=message_cap,
                ),
            )
        except Exception as err:  # noqa: BLE001 — mirrors safeHandler intent
            safe_error = sanitise_error_for_llm(err)
            hint = "Failed to retrieve ticket details. Verify the ticket ID is correct."
            if isinstance(err, GorgiasApiError):
                if err.status_code == 404:
                    hint = f"Ticket #{id} does not exist. Verify the ticket ID."
                elif err.status_code == 429:
                    hint = (
                        f"Rate limited by Gorgias API. "
                        f"Retry after {err.retry_after} seconds."
                        if err.retry_after
                        else "Rate limited by Gorgias API. Please wait before retrying."
                    )
            return {"error": safe_error, "_hint": hint}

        sorted_messages = sort_messages_chronologically(messages_result.items)
        projected_messages = [project_message(m) for m in sorted_messages]
        ticket = project_ticket(ticket_raw, len(projected_messages))

        note_count = sum(1 for m in projected_messages if m.isInternalNote)
        truncated = messages_result.truncated

        hint = f'Ticket #{ticket.id}: "{ticket.subject or "(no subject)"}". '
        if truncated:
            hint += (
                f"PARTIAL CONVERSATION — {len(projected_messages)} message(s) shown "
                f"(oldest first), but the ticket has more messages than the cap of "
                f"{message_cap}. If you need the full history, retry with a higher "
                f"max_messages (up to {_HARD_CAP_MAX_MESSAGES}). "
            )
        else:
            hint += (
                f"{len(projected_messages)} message(s) shown chronologically "
                "(oldest first). "
            )
        hint += (
            "Present as a threaded conversation — show sender name, whether agent "
            "or customer, and message text. "
        )
        if note_count > 0:
            hint += (
                f"{note_count} message(s) are internal notes (isInternalNote=true) "
                "— agent-to-agent and not seen by the customer. "
            )
        hint += f"Status: {ticket.status}, Priority: {ticket.priority}."

        result: dict[str, Any] = {
            "ticket": ticket.to_dict(),
            "messages": [m.to_dict() for m in projected_messages],
            "_hint": hint,
        }
        if truncated:
            result["truncated"] = True
            result["truncatedReason"] = f"max_messages cap of {message_cap} reached"
            result["pagesFetched"] = messages_result.pages_fetched
        return result

    registrar.tool(
        "gorgias_smart_get_ticket",
        description=(
            "Retrieve a ticket with its full conversation thread, projected to a "
            "clean format optimised for LLM consumption. Auto-paginates messages up "
            f"to max_messages (default {_DEFAULT_MAX_MESSAGES}). Long conversations "
            "return truncated=true. Messages sorted chronologically (oldest first). "
            "Use gorgias_smart_search to find tickets first; for raw API data use "
            "gorgias_get_ticket."
        ),
        handler=smart_get_ticket,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
