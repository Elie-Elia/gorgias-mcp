"""Gorgias MCP Server entry point.

Boots a FastMCP server, instantiates the Gorgias HTTP client from environment
credentials, applies access-level filtering, and registers every Gorgias tool
group. Runs on Gumstack via GumstackHost in production, or via streamable-HTTP
locally when ENVIRONMENT=local.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from mcp.gumstack import GumstackHost
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from gorgias_mcp_server.access_control import ToolRegistrar, parse_access_level
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.tools.account import register_account_tools
from gorgias_mcp_server.tools.custom_fields import register_custom_field_tools
from gorgias_mcp_server.tools.customers import register_customer_tools
from gorgias_mcp_server.tools.events import register_event_tools
from gorgias_mcp_server.tools.files import register_file_tools
from gorgias_mcp_server.tools.integrations import register_integration_tools
from gorgias_mcp_server.tools.jobs import register_job_tools
from gorgias_mcp_server.tools.macros import register_macro_tools
from gorgias_mcp_server.tools.reporting import register_reporting_tools
from gorgias_mcp_server.tools.rules import register_rule_tools
from gorgias_mcp_server.tools.satisfaction_surveys import (
    register_satisfaction_survey_tools,
)
from gorgias_mcp_server.tools.search import register_search_tools
from gorgias_mcp_server.tools.smart_search import register_smart_search_tools
from gorgias_mcp_server.tools.smart_stats import register_smart_stats_tools
from gorgias_mcp_server.tools.smart_ticket_detail import (
    register_smart_ticket_detail_tools,
)
from gorgias_mcp_server.tools.tags import register_tag_tools
from gorgias_mcp_server.tools.teams import register_team_tools
from gorgias_mcp_server.tools.ticket_messages import register_ticket_message_tools
from gorgias_mcp_server.tools.tickets import register_ticket_tools
from gorgias_mcp_server.tools.users import register_user_tools
from gorgias_mcp_server.tools.views import register_view_tools
from gorgias_mcp_server.tools.voice_calls import register_voice_call_tools
from gorgias_mcp_server.tools.widgets import register_widget_tools
from gorgias_mcp_server.utils.auth import get_credentials


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", 8000))

mcp = FastMCP("Gorgias MCP Server", host="0.0.0.0", port=PORT)


@mcp.custom_route("/health_check", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _bootstrap() -> ToolRegistrar:
    creds = get_credentials()
    domain = creds["domain"]
    email = creds["email"]
    api_key = creds["api_key"]

    if not (domain and email and api_key):
        missing = ", ".join(
            name
            for name, value in (
                ("GORGIAS_DOMAIN", domain),
                ("GORGIAS_EMAIL", email),
                ("GORGIAS_API_KEY", api_key),
            )
            if not value
        )
        raise RuntimeError(
            f"Missing required Gorgias credentials: {missing}. "
            f"Set them in your environment or .env file."
        )

    raw_level = creds.get("access_level") or os.environ.get("GORGIAS_ACCESS_LEVEL")
    if not (raw_level or "").strip():
        logger.warning(
            "GORGIAS_ACCESS_LEVEL not set — defaulting to 'admin' (all tools "
            "including destructive operations). Set GORGIAS_ACCESS_LEVEL=readonly "
            "or =agent for restricted access."
        )
    level = parse_access_level(raw_level)

    client = GorgiasClient(domain=domain, email=email, api_key=api_key)
    registrar = ToolRegistrar(mcp, level)

    # Core ticket / customer / messaging surface
    register_ticket_tools(registrar, client)
    register_ticket_message_tools(registrar, client)
    register_customer_tools(registrar, client)
    register_macro_tools(registrar, client)
    register_search_tools(registrar, client)
    register_tag_tools(registrar, client)
    register_user_tools(registrar, client)
    register_view_tools(registrar, client)

    # Admin / operational
    register_account_tools(registrar, client)
    register_custom_field_tools(registrar, client)
    register_event_tools(registrar, client)
    register_file_tools(registrar, client)
    register_integration_tools(registrar, client)
    register_job_tools(registrar, client)
    register_reporting_tools(registrar, client)
    register_rule_tools(registrar, client)
    register_satisfaction_survey_tools(registrar, client)
    register_team_tools(registrar, client)
    register_voice_call_tools(registrar, client)
    register_widget_tools(registrar, client)

    # Smart layer (intelligence helpers built on the basic tools)
    register_smart_search_tools(registrar, client)
    register_smart_ticket_detail_tools(registrar, client)
    register_smart_stats_tools(registrar, client)

    logger.info(
        "Gorgias MCP server ready (access_level=%s, registered=%d, skipped=%d)",
        level,
        registrar.stats.registered,
        registrar.stats.skipped,
    )
    return registrar


def main() -> None:
    load_dotenv()
    _bootstrap()

    if os.environ.get("ENVIRONMENT") != "local":
        host = GumstackHost(mcp)
        host.run(host="0.0.0.0", port=PORT)
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
