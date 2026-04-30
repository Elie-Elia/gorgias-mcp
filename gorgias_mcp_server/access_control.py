"""Access-level filtering for the Gorgias MCP Server.

Mirrors benpalmer1's three-tier model:
- "readonly": only read/search/list tools (annotation `read_only_hint=True`)
- "agent": readonly + tools needed for support agent workflows
- "admin": every tool registered

Tools call `register_if_allowed(...)` instead of registering directly. The
registrar checks the requested access level and silently skips tools that
shouldn't be visible.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal


AccessLevel = Literal["readonly", "agent", "admin"]
VALID_ACCESS_LEVELS: frozenset[str] = frozenset({"readonly", "agent", "admin"})

# Write tools allowed in "agent" mode. These cover the typical CS chatbot
# workflow: reply to customers, update ticket state, manage tags, and update
# custom fields. No deletions, no account/rule/macro management.
AGENT_WRITE_TOOLS: frozenset[str] = frozenset(
    {
        "gorgias_create_ticket",
        "gorgias_update_ticket",
        "gorgias_create_message",
        "gorgias_update_message",
        "gorgias_add_ticket_tags",
        "gorgias_remove_ticket_tags",
        "gorgias_set_ticket_tags",
        "gorgias_update_ticket_field",
        "gorgias_update_ticket_fields",
        "gorgias_update_customer_field_value",
        "gorgias_update_customer_fields",
    }
)


def is_tool_allowed(
    name: str,
    annotations: dict[str, Any],
    level: AccessLevel,
) -> bool:
    """Decide whether `name` should be registered at the given access level."""
    if level == "admin":
        return True
    if annotations.get("readOnlyHint") is True:
        return True
    if level == "agent":
        return name in AGENT_WRITE_TOOLS
    return False


def parse_access_level(raw: str | None) -> AccessLevel:
    """Validate and normalise the GORGIAS_ACCESS_LEVEL value.

    Defaults to "admin" when unset (matches benpalmer1's behaviour and the
    default expected by callers that don't opt in to filtering).
    """
    if not raw:
        return "admin"
    cleaned = raw.strip().lower()
    if cleaned in VALID_ACCESS_LEVELS:
        return cleaned  # type: ignore[return-value]
    valid = ", ".join(sorted(VALID_ACCESS_LEVELS))
    raise ValueError(f'Invalid GORGIAS_ACCESS_LEVEL="{raw}". Valid values: {valid}')


@dataclass
class AccessFilterStats:
    registered: int = 0
    skipped: int = 0
    skipped_names: list[str] = field(default_factory=list)


class ToolRegistrar:
    """Helper used by tool modules to declare tools subject to access filtering.

    Wraps a FastMCP server. Tool modules call `registrar.tool(name, ..., handler)`
    instead of `@mcp.tool()` directly so the registrar can decide whether to
    actually register it based on the active access level.
    """

    def __init__(self, mcp: Any, level: AccessLevel) -> None:
        self._mcp = mcp
        self._level = level
        self.stats = AccessFilterStats()

    @property
    def level(self) -> AccessLevel:
        return self._level

    def tool(
        self,
        name: str,
        *,
        description: str,
        handler: Callable[..., Any],
        annotations: dict[str, Any] | None = None,
    ) -> None:
        ann = annotations or {}
        if not is_tool_allowed(name, ann, self._level):
            self.stats.skipped += 1
            self.stats.skipped_names.append(name)
            return

        # FastMCP introspects the handler's signature for the input schema.
        # We rename it so MCP exposes the tool under the Gorgias-namespaced
        # name even though the underlying Python function may have a
        # collision-free local name.
        handler.__name__ = name
        handler.__doc__ = description
        # Pass annotations through if the FastMCP version supports it.
        try:
            self._mcp.tool(
                name=name, description=description, annotations=ann
            )(handler)
        except TypeError:
            # Older FastMCP without annotations kwarg — register without.
            self._mcp.tool(name=name, description=description)(handler)
        self.stats.registered += 1
