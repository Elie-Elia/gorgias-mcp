"""File tools — file download (upload is non-functional, JSON-only client)."""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools._helpers import safe


_PATH_SAFE_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_RESOURCE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
_HAS_ALPHANUM_RE = re.compile(r"[a-zA-Z0-9]")


def register_file_tools(registrar: ToolRegistrar, client: GorgiasClient) -> None:

    async def upload_file(
        name: Annotated[str, Field(description="Filename label.")],
        url: Annotated[str, Field(description="URL of the file to reference.")],
    ) -> dict[str, Any]:
        # Mirrors benpalmer's behaviour: the upload endpoint requires
        # multipart/form-data, which our JSON-only HTTP client does not
        # support. Return a structured error instead of attempting a
        # request that would always fail.
        return {
            "error": (
                "File upload requires multipart/form-data which is not supported by "
                "this MCP server's JSON-only client. Use the Gorgias web interface "
                "or a multipart-capable HTTP client for file uploads."
            ),
            "_hint": (
                "This endpoint cannot be used through the MCP server. Upload files "
                "through the Gorgias UI or call the Gorgias API directly."
            ),
        }

    registrar.tool(
        "gorgias_upload_file",
        description=(
            "POST /api/upload — NOT FUNCTIONAL: Gorgias upload requires "
            "multipart/form-data which this JSON-only client does not support. "
            "Use the Gorgias web UI or a multipart-capable client instead."
        ),
        handler=upload_file,
        annotations={"readOnlyHint": False, "openWorldHint": True},
    )

    async def download_file(
        file_type: Annotated[
            str,
            Field(description="File type segment (e.g. 'attachments')."),
        ],
        domain_hash: Annotated[
            str,
            Field(description="Domain hash segment from the attachment URL."),
        ],
        resource_name: Annotated[
            str,
            Field(description="Resource filename (e.g. 'package-damaged.png')."),
        ],
    ) -> dict[str, Any]:
        # Validate path segments to prevent traversal / injection. Keep
        # parity with the regex protections in benpalmer's TS version.
        if not _PATH_SAFE_RE.match(file_type):
            return {"error": "file_type must be alphanumeric, hyphens, or underscores."}
        if not _PATH_SAFE_RE.match(domain_hash):
            return {"error": "domain_hash must be alphanumeric, hyphens, or underscores."}
        if not _RESOURCE_NAME_RE.match(resource_name):
            return {"error": "resource_name contains disallowed characters."}
        if not _HAS_ALPHANUM_RE.search(resource_name):
            return {"error": "resource_name must contain at least one alphanumeric character."}
        if ".." in resource_name:
            return {"error": "resource_name must not contain consecutive dots (path traversal)."}

        return await safe(
            client.get(f"/api/{file_type}/download/{domain_hash}/{resource_name}")
        )

    registrar.tool(
        "gorgias_download_file",
        description=(
            "GET /api/{file_type}/download/{domain_hash}/{resource_name} — Download a "
            "private Gorgias file. Path segments come from an attachment URL."
        ),
        handler=download_file,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
