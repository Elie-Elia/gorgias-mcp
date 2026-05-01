# Gorgias MCP Server (Python / Gumstack)

A Python port of [benpalmer1/Gorgias-MCP-Server](https://github.com/benpalmer1/Gorgias-MCP-Server) (Node/TypeScript) that runs on the [Gumstack](https://www.gumloop.com/mcp) MCP hosting platform and integrates natively with Gumloop workflows.

The original benpalmer1 server is excellent — clean architecture, well-documented tool surface, careful API safety. This port preserves all of that while swapping the language/runtime so the server can be deployed via Gumstack's Python template.

## What this exposes

**109 tools across 19 modules** covering the full Gorgias REST API surface.

### Core ticketing
- `tools/tickets.py` — list/get/create/update/delete tickets, plus tag and custom-field operations
- `tools/ticket_messages.py` — list/get/create/update/delete messages on tickets (the agent-reply path)
- `tools/customers.py` — full customer CRUD plus merge, channels, custom field values
- `tools/macros.py` — canned-response macros incl. relevance ranking
- `tools/search.py` — low-level Gorgias resource search
- `tools/tags.py` — tag CRUD + bulk delete + merge
- `tools/users.py` — user/agent CRUD (`id=0` returns the caller)
- `tools/views.py` — saved-view CRUD plus item listing and ad-hoc `view_id=0` queries

### Admin / operational
- `tools/account.py`, `tools/custom_fields.py`, `tools/events.py`, `tools/files.py`, `tools/integrations.py`, `tools/jobs.py`, `tools/reporting.py`, `tools/rules.py`, `tools/satisfaction_surveys.py`, `tools/teams.py`, `tools/voice_calls.py`, `tools/widgets.py`

### Smart layer (LLM-friendly helpers built on the basic tools)
- **`gorgias_smart_search`** — intelligent ticket finder with 8-strategy auto-detection (email, ticket ID, order reference, view name, customer name, topic keyword, generic query → recents, keyword fallback). Includes a curated ecommerce-keyword set for AU/UK/US carriers, payment methods, returns, and complaints.
- **`gorgias_smart_get_ticket`** — single ticket plus its full conversation thread, projected to a clean LLM-friendly format and chronologically sorted, with auto-pagination over the messages endpoint.
- **`gorgias_smart_stats`** — reporting wrapper with auto-default measures, dimension alias resolution, broken-scope guardrails, agent-name resolution, and bounded auto-pagination.

## Architecture

Same shape as benpalmer1's original, ported to Python:

```
gorgias_mcp_server/
├── server.py              # FastMCP entry; wires GumstackHost + tool registration
├── client.py              # Async httpx client with SSRF allowlist + 429 retry + jitter
├── access_control.py      # readonly / agent / admin tiers + ToolRegistrar
├── errors.py              # GorgiasError, GorgiasApiError, sanitise_error_for_llm
├── cache.py               # TTL cache, fetch_all_pages, per-client reference data
├── fuzzy_match.py         # Levenshtein with the 7-tier scoring ladder
├── projection.py          # Clean ProjectedTicket / ProjectedMessage shapes
├── reporting_knowledge.py # Scope→time-dimension, default measures, valid dims, ...
├── tools/                 # 19 tool modules (see above)
└── utils/auth.py          # Reads GORGIAS_DOMAIN/EMAIL/API_KEY/ACCESS_LEVEL from env
```

### Safety properties preserved from the TypeScript original

- **SSRF allowlist** — domain validation only accepts `*.gorgias.com` hosts; rejects `http://`, whitespace, trailing dots, empty domains.
- **429 handling** — capped exponential backoff, honours `Retry-After`, jitter to spread retry storms.
- **JSON detection** — vendor `+json` content types accepted (`application/vnd.api+json`, `application/problem+json`).
- **LLM-safe errors** — every tool wraps API calls in a sanitiser that strips Bearer tokens, JWTs, basic auth, vendor API keys (Stripe `sk_*`, GitHub `ghp_*`, Slack `xox*`, etc.), customer emails, SQL statements, file paths, and internal IPs before the message reaches the model.
- **Per-client cache scoping** — reference data (tags, teams, custom fields, views, users) is cached per-client so multi-tenant deployments never leak between accounts.

### Access tiers

Set `GORGIAS_ACCESS_LEVEL` to control which tools are registered:

| Level | What's exposed |
|-------|----------------|
| `readonly` | Only list/get/search tools. Safe for any analytics-only bot. |
| `agent` | `readonly` plus the typical CS-chatbot write surface: create/update tickets, send messages, add/remove/set tags, update ticket and customer custom field values. No deletions. |
| `admin` *(default)* | Everything, including destructive operations. |

The agent-write allowlist is in [`access_control.py`](gorgias_mcp_server/access_control.py).

## Deploying on Gumstack

This is the primary use case. Push to GitHub, point your Gumstack server at the repo, set the four env vars below in Gumstack's environment, and Gumstack's `GumstackHost` (already wired in `server.py`) takes care of the rest.

Required environment variables:

```
GORGIAS_DOMAIN=your-subdomain         # or full domain / URL
GORGIAS_EMAIL=admin@yourcompany.com   # the REST API user
GORGIAS_API_KEY=...                   # Settings → REST API → Generate
GORGIAS_ACCESS_LEVEL=agent            # readonly | agent | admin
```

`config.yaml` declares every tool name so Gumloop picks them up automatically.

## Local development

```bash
# Install uv if you don't have it
brew install uv

# Install deps
uv sync

# Copy and edit .env
cp env.example .env
# fill in GORGIAS_DOMAIN / EMAIL / API_KEY

# Run the server (streamable-HTTP transport)
ENVIRONMENT=local ./run.sh
```

## What's NOT ported

- **File upload** (`gorgias_upload_file`) — the Gorgias upload endpoint requires `multipart/form-data` and the JSON-only client cannot satisfy it. The tool registers but returns a structured error explaining the limitation. Mirrors benpalmer1's behaviour. Use the Gorgias web UI for uploads.

## Known upstream limitation

`gorgias_smart_search`'s keyword path uses Gorgias's own view-search endpoint (`PUT /api/views/0/items`), which has been observed to return `202 Accepted` (async) without polling support in the underlying API. Free-text keyword queries that aren't matched by the topic-keyword set may return empty results until Gorgias adds polling. Fix requires async polling support in the upstream API itself.

## Credits

- Original Node/TypeScript implementation: [benpalmer1/Gorgias-MCP-Server](https://github.com/benpalmer1/Gorgias-MCP-Server) — MIT licensed. All Gorgias API knowledge, tool descriptions, the smart layer design, the access-tier model, and most error-handling logic come from there.
- Gumstack template: scaffolded by [Gumloop](https://www.gumloop.com/mcp).
- Python port maintained by [@Elie-Elia](https://github.com/Elie-Elia) for Casa Di Lumo customer-support workflows.

## License

MIT (matches the upstream original).
