"""Smart stats — Gorgias reporting with auto-defaults, validation, and pagination.

Ports `src/tools/smart-stats.ts`. Wraps the low-level
`gorgias_retrieve_reporting_statistic` with:
- broken-scope guardrails
- required-filter checks (e.g. ticket-fields needs customFieldId)
- 366-day client-side date range validation
- dimension alias + kebab-case normalisation
- default measure / time-dimension selection per scope
- exclusive-end-date adjustment
- auto-pagination up to a row limit (with a 10-page safety cap)
- agentId → agentName resolution via cached users
- humanised column metadata for table rendering
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.cache import get_cached_users
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.errors import sanitise_error_for_llm
from gorgias_mcp_server.reporting_knowledge import (
    BROKEN_SCOPES,
    DIMENSION_ALIASES,
    MAX_PERIOD_DAYS,
    SCOPE_DEFAULT_MEASURES,
    SCOPE_REQUIRED_FILTERS,
    SCOPE_TIME_DIMENSION,
    SCOPE_VALID_DIMENSIONS,
    TIME_BASED_SCOPES,
    adjust_end_date_for_exclusive,
    humanise_key,
    kebab_to_camel_case,
    period_length_days,
)


def register_smart_stats_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def smart_stats(
        scope: Annotated[
            str,
            Field(
                description=(
                    "Reporting scope (e.g. 'tickets-created', 'first-response-time'). "
                    "See tool description for the full list by category."
                )
            ),
        ],
        start_date: Annotated[
            str,
            Field(
                description="Start date in YYYY-MM-DD format.",
                pattern=r"^\d{4}-\d{2}-\d{2}$",
            ),
        ],
        end_date: Annotated[
            str,
            Field(
                description="End date YYYY-MM-DD (inclusive; auto-adjusted for exclusive filter).",
                pattern=r"^\d{4}-\d{2}-\d{2}$",
            ),
        ],
        timezone: Annotated[
            str | None,
            Field(description="Timezone (default 'UTC')."),
        ] = None,
        granularity: Annotated[
            Literal["hour", "day", "week", "month", "none"] | None,
            Field(
                description=(
                    "Time grouping (default 'day'). Use 'none' for aggregate mode "
                    "to collapse the time axis when row counts would explode."
                )
            ),
        ] = None,
        dimensions: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Dimensions to group by. Aliases auto-resolved: 'agent'→agentId, "
                    "'tag'→tagId, 'store'→storeId, 'integration'→integrationId."
                )
            ),
        ] = None,
        measures: Annotated[
            list[str] | None,
            Field(description="Measures to return (defaults per scope if omitted)."),
        ] = None,
        filters: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Additional filter objects [{member, operator, values}]."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Max rows after auto-pagination (default 100, max 10000). "
                    "Prefer granularity='none' for very wide queries."
                ),
                ge=1,
                le=10000,
            ),
        ] = None,
        cursor: Annotated[
            str | None,
            Field(
                description=(
                    "Advanced: opaque cursor from a previous response's nextCursor. "
                    "Disables auto-pagination — caller drives the loop."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        try:
            tz = timezone or "UTC"
            granularity_value = granularity or "day"

            if scope in BROKEN_SCOPES:
                return {
                    "error": BROKEN_SCOPES[scope],
                    "scope": scope,
                    "_hint": (
                        f"The '{scope}' scope is known to be broken in the Gorgias API. "
                        "Try an alternative scope."
                    ),
                }

            if scope in SCOPE_REQUIRED_FILTERS:
                req = SCOPE_REQUIRED_FILTERS[scope]
                required_member = req["filter_member"]
                provided_filters = filters or []
                has_filter = any(
                    f.get("member") == required_member for f in provided_filters
                )
                if not has_filter:
                    return {
                        "error": req["description"],
                        "scope": scope,
                        "requiredFilter": required_member,
                        "_hint": (
                            f"Add a filter with member '{required_member}' to use "
                            f"the '{scope}' scope."
                        ),
                    }

            period_days = period_length_days(start_date, end_date)
            if period_days > MAX_PERIOD_DAYS:
                return {
                    "error": (
                        f"Requested date range is {period_days} days; the Gorgias "
                        f"reporting API limit is {MAX_PERIOD_DAYS} days."
                    ),
                    "scope": scope,
                    "requestedDays": period_days,
                    "maxDays": MAX_PERIOD_DAYS,
                    "_hint": (
                        f"Split the query into sub-ranges of {MAX_PERIOD_DAYS} days "
                        "or fewer and merge results client-side."
                    ),
                }

            # Resolve dimension aliases + kebab→camelCase normalisation
            resolved_dimensions: list[str] = []
            for raw in dimensions or []:
                camel = kebab_to_camel_case(raw)
                if camel in DIMENSION_ALIASES:
                    alias = DIMENSION_ALIASES[camel]
                    if alias is None:
                        continue  # invalid dimension — silently drop
                    resolved_dimensions.append(alias)
                else:
                    resolved_dimensions.append(camel)

            valid_dims = SCOPE_VALID_DIMENSIONS.get(scope)
            if valid_dims is not None:
                invalid_dims = [d for d in resolved_dimensions if d not in valid_dims]
                if invalid_dims:
                    return {
                        "error": (
                            f"Invalid dimensions for scope '{scope}': "
                            f"{', '.join(invalid_dims)}"
                        ),
                        "validDimensions": valid_dims,
                        "_hint": (
                            f"The '{scope}' scope supports these dimensions: "
                            f"{', '.join(valid_dims) if valid_dims else 'none'}"
                        ),
                    }

            chosen_measures = measures or SCOPE_DEFAULT_MEASURES.get(scope, [])
            time_dim_field = SCOPE_TIME_DIMENSION.get(scope, "createdDatetime")
            adjusted_end_date = adjust_end_date_for_exclusive(end_date)

            # The reporting API uses periodStart/periodEnd for date filters, not
            # the scope-specific time dimension names.
            date_filters = [
                {
                    "member": "periodStart",
                    "operator": "afterDate",
                    "values": [start_date],
                },
                {
                    "member": "periodEnd",
                    "operator": "beforeDate",
                    "values": [adjusted_end_date],
                },
            ]
            all_filters = [*date_filters, *(filters or [])]

            query: dict[str, Any] = {
                "scope": scope,
                "filters": all_filters,
                "timezone": tz,
                "measures": chosen_measures,
            }
            if resolved_dimensions:
                query["dimensions"] = resolved_dimensions
            if granularity_value != "none":
                query["time_dimensions"] = [
                    {"dimension": time_dim_field, "granularity": granularity_value}
                ]

            requested_limit = limit or 100
            page_size = min(requested_limit, 1000)
            safety_cap_pages = 10
            single_page_mode = cursor is not None

            rows: list[dict[str, Any]] = []
            pages_fetched = 0
            next_cursor: str | None = cursor
            safety_cap_reached = False

            while True:
                query_params: dict[str, Any] = {"limit": page_size}
                if next_cursor:
                    query_params["cursor"] = next_cursor

                page = await client.post(
                    "/api/reporting/stats", {"query": query}, query_params
                )
                pages_fetched += 1

                page_rows: list[dict[str, Any]]
                if isinstance(page, dict) and isinstance(page.get("data"), list):
                    page_rows = page["data"]
                elif isinstance(page, list):
                    page_rows = page
                else:
                    page_rows = []
                rows.extend(page_rows)

                upstream_cursor: str | None = None
                if isinstance(page, dict):
                    meta = page.get("meta") or {}
                    upstream_cursor = (
                        meta.get("next_cursor") or page.get("next_cursor")
                    )

                if single_page_mode:
                    next_cursor = upstream_cursor
                    break

                if not upstream_cursor:
                    next_cursor = None
                    break

                if len(rows) >= requested_limit:
                    next_cursor = upstream_cursor
                    break

                if pages_fetched >= safety_cap_pages:
                    safety_cap_reached = True
                    next_cursor = upstream_cursor
                    break

                next_cursor = upstream_cursor

            raw_row_count = len(rows)
            if not single_page_mode and len(rows) > requested_limit:
                rows = rows[:requested_limit]

            if safety_cap_reached:
                return {
                    "error": (
                        f"Reporting query exceeded the {safety_cap_pages}-page safety cap."
                    ),
                    "scope": scope,
                    "partialRowCount": len(rows),
                    "pagesFetched": pages_fetched,
                    "nextCursor": next_cursor,
                    "_hint": (
                        f"{len(rows)} rows fetched across {pages_fetched} pages, but "
                        f"more data is available upstream. Either: (1) re-issue with "
                        f"cursor='{next_cursor}' to continue, (2) coarsen 'granularity' "
                        f"(e.g. 'week' or 'month'), (3) use granularity='none' for an "
                        f"aggregate query, or (4) shorten the date range."
                    ),
                }

            null_measure_row_count = 0
            if chosen_measures:
                null_measure_row_count = sum(
                    1
                    for row in rows
                    if all(row.get(m) in (None,) for m in chosen_measures)
                )

            has_agent_dimension = "agentId" in resolved_dimensions
            if has_agent_dimension and rows:
                users = await get_cached_users(client)
                user_map: dict[int, str] = {}
                for u in users:
                    if not isinstance(u, dict):
                        continue
                    uid = u.get("id")
                    name = u.get("name")
                    if isinstance(uid, int) and isinstance(name, str):
                        user_map[uid] = name.strip()
                for row in rows:
                    agent_id = row.get("agentId")
                    if isinstance(agent_id, int):
                        row["agentName"] = user_map.get(agent_id, f"Agent {agent_id}")
                    else:
                        row["agentName"] = None

            columns: dict[str, str] = {}
            for row in rows:
                for key in row:
                    if key not in columns:
                        columns[key] = humanise_key(key)

            hint = (
                f"Returned {len(rows)} row(s) for scope '{scope}' from "
                f"{start_date} to {end_date}."
            )
            if len(rows) >= requested_limit:
                hint += (
                    f" WARNING: Results were capped at {requested_limit} rows and may "
                    "be truncated. To see more data: (1) shorten the date range; "
                    "(2) coarsen the granularity; (3) use granularity='none' for an "
                    "aggregate query; (4) REMOVE dimensions to reduce row cardinality; "
                    "(5) raise the limit (max 10000); (6) use cursor-based pagination."
                )
            if null_measure_row_count > 0:
                hint += (
                    f" {null_measure_row_count} row(s) have all-null measure values "
                    "(e.g. agents with zero activity). They are preserved so the LLM "
                    "can decide how to present them."
                )
            hint += " Present data in a table format."
            if has_agent_dimension:
                hint += " Agent names have been resolved from IDs."
            if scope in TIME_BASED_SCOPES:
                hint += " Time values are in seconds."
            hint += " Bold metric names for readability."

            return {
                "scope": scope,
                "dateRange": {"start": start_date, "end": end_date},
                "timezone": tz,
                "granularity": granularity_value,
                "columns": columns,
                "data": rows,
                "totalRows": len(rows),
                "rawRowCount": raw_row_count,
                "nullMeasureRowCount": null_measure_row_count,
                "pagesFetched": pages_fetched,
                "nextCursor": next_cursor,
                "_hint": hint,
            }
        except Exception as err:  # noqa: BLE001
            return {
                "error": sanitise_error_for_llm(err),
                "scope": scope,
                "_hint": (
                    f"Stats query failed for scope '{scope}'. Check that the "
                    "scope, date range, and dimensions are valid."
                ),
            }

    registrar.tool(
        "gorgias_smart_stats",
        description=(
            "Retrieve Gorgias analytics with automatic defaults, validation, "
            "post-processing, and auto-pagination.\n\n"
            "Scopes by category:\n"
            "Volume: tickets-created, tickets-closed, tickets-open, tickets-replied, "
            "one-touch-tickets, zero-touch-tickets, workload-tickets\n"
            "Performance: first-response-time, human-first-response-time, "
            "response-time, resolution-time, ticket-handle-time\n"
            "Quality: satisfaction-surveys, auto-qa\n"
            "Messages: messages-sent, messages-received, messages-per-ticket\n"
            "Automation: automation-rate, automated-interactions\n"
            "Breakdown: tags, ticket-fields\n"
            "Voice: voice-calls, voice-agent-events, voice-calls-summary\n"
            "Other: online-time, ticket-sla, knowledge-insights\n\n"
            "Broken scopes (return API errors): automation-rate, online-time, "
            "voice-calls, voice-agent-events, voice-calls-summary.\n\n"
            "Auto-pagination: fetches up to 'limit' rows (default 100, max 10000) "
            "across multiple upstream pages. For wide queries use granularity='none'. "
            "Date range capped at 366 days. Pass 'cursor' for manual page control. "
            "For raw access use gorgias_retrieve_reporting_statistic."
        ),
        handler=smart_stats,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
