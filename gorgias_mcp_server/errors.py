"""Gorgias-specific exceptions and an LLM-safe error sanitiser.

The sanitiser strips credentials, tokens, internal paths, PII, and other
sensitive data from arbitrary error messages before they're returned to a
model. Mirrors the protections in benpalmer1's TypeScript implementation.
"""

from __future__ import annotations

import re
from typing import Any


class GorgiasError(Exception):
    """Base error for the Gorgias MCP server."""

    def __init__(self, message: str, cause: Any = None) -> None:
        super().__init__(message)
        self.cause = cause


class GorgiasApiError(GorgiasError):
    """Raised when the Gorgias HTTP API returns a non-2xx response."""

    def __init__(
        self,
        message: str,
        status_code: int | None,
        *,
        rate_limited: bool = False,
        retry_after: str | None = None,
        cause: Any = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.status_code = status_code
        self.rate_limited = rate_limited
        self.retry_after = retry_after


_GENERIC_MESSAGE = "An internal error occurred"
_MAX_CAUSE_DEPTH = 5

# Patterns are applied in order; earlier (more specific) patterns win.
_REDACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Bearer\s+\S+", re.IGNORECASE), "[REDACTED]"),
    (re.compile(r"Basic\s+[A-Za-z0-9+/=]{8,}", re.IGNORECASE), "[REDACTED]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[REDACTED]"),
    (
        re.compile(r"(?:postgres|mysql|mongodb|redis)://\S+", re.IGNORECASE),
        "[REDACTED]",
    ),
    (
        re.compile(
            r"(?:api[_-]?key|api[_-]?secret|access[_-]?key|password|token|secret|client[_-]?secret)\s*=\s*[^&\s;]+",
            re.IGNORECASE,
        ),
        "[REDACTED]",
    ),
    (re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"), "[REDACTED]"),
    (re.compile(r"\bpk_(?:live|test)_[A-Za-z0-9]{16,}\b"), "[REDACTED]"),
    (re.compile(r"\bwhsec_[A-Za-z0-9]{16,}\b"), "[REDACTED]"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[REDACTED]"),
    (re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"), "[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "[REDACTED]"),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (re.compile(r"\bSELECT\s+[\w\s,*().`\"]+\s+FROM\s+\w[\s\S]*?;"), "[REDACTED]"),
    (re.compile(r"\bINSERT\s+INTO\s+\w[\s\S]*?;"), "[REDACTED]"),
    (re.compile(r"\bUPDATE\s+\w+\s+SET\s+[\s\S]*?;"), "[REDACTED]"),
    (re.compile(r"\bDELETE\s+FROM\s+\w[\s\S]*?;"), "[REDACTED]"),
    (re.compile(r"[A-Za-z]:\\[\w\\. -]+"), "[REDACTED]"),
    (re.compile(r"\\\\[A-Za-z0-9._-]+\\[^\s]+"), "[REDACTED]"),
    (
        re.compile(
            r"(^|\s)(/(?:Users|home|var|tmp|etc|root|proc|sys|opt|srv|mnt|private)/\S+)",
            re.MULTILINE,
        ),
        r"\1[REDACTED]",
    ),
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[REDACTED]"),
    (re.compile(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b"), "[REDACTED]"),
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "[REDACTED]"),
    (re.compile(r"\b127\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "[REDACTED]"),
    (re.compile(r"\b169\.254\.\d{1,3}\.\d{1,3}\b"), "[REDACTED]"),
    (re.compile(r"(?<![A-Za-z0-9:])::1(?![A-Za-z0-9:])"), "[REDACTED]"),
    (re.compile(r"\bfe80::[0-9a-fA-F:]+\b"), "[REDACTED]"),
    (re.compile(r"\bfc[0-9a-fA-F]{2}::[0-9a-fA-F:]+\b"), "[REDACTED]"),
    (re.compile(r"\bfd[0-9a-fA-F]{2}::[0-9a-fA-F:]+\b"), "[REDACTED]"),
]


def _extract_full_message(error: Any) -> str:
    """Walk an exception's `__cause__` chain, joining each message."""
    parts: list[str] = []
    seen: set[int] = set()
    current: Any = error
    depth = 0

    while current is not None and depth < _MAX_CAUSE_DEPTH and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, BaseException):
            parts.append(str(current))
            current = current.__cause__ or getattr(current, "cause", None)
        elif isinstance(current, str):
            parts.append(current)
            break
        elif hasattr(current, "message") and isinstance(current.message, str):
            parts.append(current.message)
            break
        else:
            parts.append(str(current))
            break
        depth += 1

    return " | caused by: ".join(p for p in parts if p)


def sanitise_error_for_llm(error: Any) -> str:
    """Return an LLM-safe error string with credentials/PII redacted."""
    message = _extract_full_message(error)

    for pattern, replacement in _REDACTION_PATTERNS:
        message = pattern.sub(replacement, message)

    message = re.sub(r"\n{3,}", "\n\n", message).strip()
    return message or _GENERIC_MESSAGE
