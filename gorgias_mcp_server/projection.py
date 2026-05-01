"""LLM-friendly projections of Gorgias ticket and message objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProjectedTicket:
    id: int
    subject: str | None
    excerpt: str | None
    status: str
    priority: str
    channel: str | None
    customerEmail: str | None
    customerName: str | None
    assigneeName: str | None
    assigneeTeam: str | None
    tags: list[str] = field(default_factory=list)
    messagesCount: int = 0
    createdAt: str | None = None
    lastMessageAt: str | None = None
    closedAt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectedMessage:
    id: int
    fromAgent: bool
    isInternalNote: bool
    senderName: str | None
    senderEmail: str | None
    text: str | None
    channel: str | None
    createdAt: str | None
    intents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    return None


def project_ticket(
    ticket: dict[str, Any], actual_message_count: int | None = None
) -> ProjectedTicket:
    customer = ticket.get("customer") or {}
    assignee_user = ticket.get("assignee_user") or {}
    assignee_team = ticket.get("assignee_team") or {}
    tags_raw = ticket.get("tags") or []

    tags: list[str] = []
    for tag in tags_raw:
        if isinstance(tag, dict) and tag.get("name") is not None:
            cleaned = str(tag["name"]).strip()
            if cleaned:
                tags.append(cleaned)

    return ProjectedTicket(
        id=ticket["id"],
        subject=ticket.get("subject"),
        excerpt=ticket.get("excerpt"),
        status=ticket.get("status", ""),
        priority=ticket.get("priority", ""),
        channel=ticket.get("channel"),
        customerEmail=customer.get("email"),
        customerName=_strip(customer.get("name")),
        assigneeName=_strip(assignee_user.get("name")),
        assigneeTeam=_strip(assignee_team.get("name")),
        tags=tags,
        messagesCount=(
            actual_message_count
            if actual_message_count is not None
            else ticket.get("messages_count", 0)
        ),
        createdAt=ticket.get("created_datetime"),
        lastMessageAt=ticket.get("last_message_datetime"),
        closedAt=ticket.get("closed_datetime"),
    )


def project_message(message: dict[str, Any]) -> ProjectedMessage:
    sender = message.get("sender") or {}
    intents_raw = message.get("intents") or []

    intents: list[str] = []
    if isinstance(intents_raw, list):
        for intent in intents_raw:
            if isinstance(intent, dict) and intent.get("name") is not None:
                cleaned = str(intent["name"]).strip()
                if cleaned:
                    intents.append(cleaned)

    return ProjectedMessage(
        id=message["id"],
        fromAgent=bool(message.get("from_agent", False)),
        isInternalNote=message.get("public") is False,
        senderName=_strip(sender.get("name")),
        senderEmail=sender.get("email"),
        text=message.get("stripped_text") or message.get("body_text"),
        channel=message.get("channel"),
        createdAt=message.get("created_datetime"),
        intents=intents,
    )


def sort_messages_chronologically(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a copy of `messages` ordered by `created_datetime` ascending.

    Messages without a `created_datetime` sort to the end (mirrors benpalmer's
    +Infinity fallback).
    """
    def key(msg: dict[str, Any]) -> tuple[int, str]:
        ts = msg.get("created_datetime")
        if ts is None:
            return (1, "")
        return (0, ts)

    return sorted(messages, key=key)
