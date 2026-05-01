"""Domain knowledge for the Gorgias reporting / statistics API.

Encodes hard-won knowledge about scope→time-dimension mappings, default
measures, valid dimensions, broken scopes, mandatory filters, and dimension
aliases. Mirrors `src/reporting-knowledge.ts` from benpalmer1.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


_YYYYMMDD = re.compile(r"^\d{4}-\d{2}-\d{2}$")


SCOPE_TIME_DIMENSION: dict[str, str] = {
    "tickets-created": "createdDatetime",
    "tickets-closed": "closedDatetime",
    "tickets-open": "createdDatetime",
    "tickets-replied": "createdDatetime",
    "one-touch-tickets": "closedDatetime",
    "zero-touch-tickets": "closedDatetime",
    "satisfaction-surveys": "createdDatetime",
    "resolution-time": "createdDatetime",
    "messages-sent": "sentDatetime",
    "first-response-time": "firstAgentMessageDatetime",
    "human-first-response-time": "firstAgentMessageDatetime",
    "response-time": "sentDatetime",
    "messages-per-ticket": "createdDatetime",
    "ticket-handle-time": "createdDatetime",
    "online-time": "timestamp",
    # Live API requires "timestamp", not "createdDatetime" (verified 2026-04-14)
    "tags": "timestamp",
    "auto-qa": "closedDatetime",
    "messages-received": "sentDatetime",
    "automation-rate": "createdDatetime",
    "workload-tickets": "createdDatetime",
    "automated-interactions": "createdDatetime",
    "ticket-fields": "createdDatetime",
    "voice-calls": "createdDatetime",
    "voice-agent-events": "timestamp",
    "ticket-sla": "anchorDatetime",
    "knowledge-insights": "createdDatetime",
    "voice-calls-summary": "createdDatetime",
}

SCOPE_DEFAULT_MEASURES: dict[str, list[str]] = {
    "tickets-created": ["ticketCount"],
    "tickets-closed": ["ticketCount"],
    "tickets-open": ["ticketCount"],
    "tickets-replied": ["ticketCount"],
    "one-touch-tickets": ["ticketCount"],
    "zero-touch-tickets": ["ticketCount"],
    "satisfaction-surveys": [
        "averageSurveyScore",
        "scoredSurveysCount",
        "responseRate",
    ],
    "resolution-time": ["medianResolutionTime"],
    "messages-sent": ["messagesCount"],
    "first-response-time": ["medianFirstResponseTime"],
    "human-first-response-time": ["medianFirstResponseTime"],
    "response-time": ["medianResponseTime"],
    "messages-per-ticket": ["averageMessagesCount"],
    "ticket-handle-time": ["averageHandleTime"],
    "online-time": ["onlineTime"],
    "tags": ["ticketCount"],
    "auto-qa": ["averageRatingScore"],
    "messages-received": ["messagesCount"],
    "automation-rate": [
        "automationRate",
        "automatedTicketCount",
        "ticketCount",
    ],
    "workload-tickets": ["ticketCount"],
    "automated-interactions": ["automatedInteractions"],
    "ticket-fields": ["ticketCount"],
    "voice-calls": ["voiceCallsCount"],
    "voice-agent-events": ["voiceAgentEventsCount"],
    "ticket-sla": ["ticketCount"],
    "knowledge-insights": ["viewsCount", "clicksCount"],
    "voice-calls-summary": ["voiceCallsCount", "totalDuration"],
}

# "teamId" is NOT a valid dimension despite older docs; verified 2026-04-14.
SCOPE_VALID_DIMENSIONS: dict[str, list[str]] = {
    "tickets-created": ["agentId", "channel", "integrationId", "storeId"],
    "tickets-closed": ["agentId", "channel", "integrationId", "storeId"],
    "tickets-open": ["agentId", "channel", "integrationId", "storeId"],
    "tickets-replied": ["agentId", "channel", "integrationId", "storeId"],
    "one-touch-tickets": ["agentId", "channel", "integrationId", "storeId"],
    "zero-touch-tickets": ["channel", "integrationId", "storeId"],
    "satisfaction-surveys": ["agentId", "channel", "integrationId", "storeId"],
    "resolution-time": ["agentId", "channel", "integrationId", "storeId"],
    "messages-sent": ["agentId", "channel", "integrationId", "storeId"],
    "first-response-time": ["agentId", "channel", "integrationId", "storeId"],
    "human-first-response-time": ["agentId", "channel", "integrationId", "storeId"],
    "response-time": ["agentId", "channel", "integrationId", "storeId"],
    "messages-per-ticket": ["agentId", "channel", "integrationId", "storeId"],
    "ticket-handle-time": ["agentId", "channel", "integrationId", "storeId"],
    "online-time": ["agentId"],
    "tags": ["tagId"],
    "auto-qa": [
        "agentId",
        "channel",
        "integrationId",
        "storeId",
        "categoryName",
    ],
    "messages-received": ["channel", "integrationId", "storeId"],
    "automation-rate": ["channel", "integrationId", "storeId"],
    "workload-tickets": ["agentId"],
    "automated-interactions": [
        "eventType",
        "channel",
        "integrationId",
        "storeId",
    ],
    "ticket-fields": ["customFieldValue"],
    "voice-calls": ["agentId", "integrationId", "phoneNumberId", "queueId"],
    "voice-agent-events": ["agentId", "integrationId"],
    "ticket-sla": ["status"],
    "knowledge-insights": [],
    "voice-calls-summary": [
        "agentId",
        "integrationId",
        "phoneNumberId",
        "queueId",
    ],
}

# LLM-friendly aliases. None values mark dimensions that are NOT valid.
DIMENSION_ALIASES: dict[str, str | None] = {
    "agent": "agentId",
    "team": None,
    "tag": "tagId",
    "store": "storeId",
    "integration": "integrationId",
    "policy": None,
    "phone": "phoneNumberId",
    "queue": "queueId",
    "category": "categoryName",
    "field": "customFieldValue",
    "event": "eventType",
}

BROKEN_SCOPES: dict[str, str] = {
    "automation-rate": "This scope consistently returns server errors from the Gorgias API",
    "online-time": "This scope consistently returns server errors from the Gorgias API",
    "voice-calls": "This scope consistently returns server errors from the Gorgias API",
    "voice-agent-events": "This scope consistently returns server errors from the Gorgias API",
    "voice-calls-summary": "This scope consistently returns server errors from the Gorgias API",
}

SCOPE_REQUIRED_FILTERS: dict[str, dict[str, str]] = {
    "ticket-fields": {
        "filter_member": "customFieldId",
        "description": (
            "The 'ticket-fields' scope requires a 'customFieldId' filter "
            "specifying which custom field to analyse"
        ),
    },
}

TIME_BASED_SCOPES: frozenset[str] = frozenset(
    {
        "first-response-time",
        "human-first-response-time",
        "response-time",
        "resolution-time",
        "ticket-handle-time",
    }
)

MAX_PERIOD_DAYS = 366


def kebab_to_camel_case(s: str) -> str:
    segments = s.split("-")
    if not segments:
        return s
    head, *tail = segments
    return head + "".join(seg[:1].upper() + seg[1:] for seg in tail)


def humanise_key(key: str) -> str:
    out_parts: list[str] = []
    for segment in key.split("."):
        spaced: list[str] = []
        for ch in segment:
            if ch.isupper():
                spaced.append(" ")
                spaced.append(ch)
            else:
                spaced.append(ch)
        spaced_str = "".join(spaced).strip()
        words = [w for w in spaced_str.split(" ") if w]
        out_parts.append(" ".join(w[:1].upper() + w[1:] for w in words))
    return " ".join(out_parts)


def period_length_days(start_date: str, end_date: str) -> int:
    """Inclusive length in whole days between two YYYY-MM-DD dates."""
    start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (end - start).days + 1


def adjust_end_date_for_exclusive(date_str: str) -> str:
    """Return date_str + 1 day (Gorgias reporting filters end-exclusive)."""
    if not _YYYYMMDD.match(date_str):
        raise ValueError(f"Expected date in YYYY-MM-DD format, got: '{date_str}'")
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as err:
        raise ValueError(f"Invalid date: '{date_str}'") from err
    bumped = date + timedelta(days=1)
    return bumped.strftime("%Y-%m-%d")
