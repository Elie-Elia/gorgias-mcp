"""Smart search — intelligent ticket finder with intent auto-detection.

Strategy ladder (auto mode): email → ticket ID (numeric) → order reference
(letters+digits) → generic-query recent → view fuzzy match → customer name
fuzzy match → topic-keyword search → keyword full-text search.

Set `search_type` explicitly to skip auto-detection.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import Field

from gorgias_mcp_server.access_control import ToolRegistrar
from gorgias_mcp_server.cache import get_reference_data
from gorgias_mcp_server.client import GorgiasClient
from gorgias_mcp_server.errors import GorgiasApiError, sanitise_error_for_llm
from gorgias_mcp_server.fuzzy_match import fuzzy_match_name
from gorgias_mcp_server.projection import project_ticket


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TICKET_ID_PATTERN = re.compile(
    r"^#(\d+)$|^(\d{4,})$|^ticket\s*#?\s*(\d+)$", re.IGNORECASE
)

_GENERIC_QUERIES: frozenset[str] = frozenset(
    {
        "tickets",
        "ticket",
        "support",
        "all",
        "recent",
        "latest",
        "show",
        "find",
        "list",
        "get",
        "help",
        "issues",
    }
)

# Ecommerce topic keywords — optimised for AU, US & UK terminology.
# All entries lowercase, alphanumeric only. Multi-word terms are stored as
# their bigram-collapsed form (e.g. "giftcard", "applepay").
_TOPIC_KEYWORDS: frozenset[str] = frozenset(
    {
        # Shipping & delivery
        "shipping", "ship", "shipped", "delivery", "deliver", "delivered",
        "dispatch", "despatched", "despatch", "dispatched",
        "freight", "courier", "express", "overnight", "standard",
        "tracking", "tracked", "transit", "customs", "duty", "import",
        "post", "postage", "postal", "parcel", "package",
        "signature", "signed", "redelivery", "redirect",
        "depot", "warehouse", "fulfillment", "fulfilment",
        "auspost", "startrack", "sendle", "aramex",
        "expresspost", "safedrop", "atl",
        "evri", "hermes", "dpd", "yodel", "parcelforce",
        "freepost", "collectplus",
        "usps", "ups", "fedex", "dhl",
        "priority", "ground",
        "pickup", "collect", "collection", "curbside", "bopis",
        # WISMO
        "wismo", "eta", "delay", "delayed", "late", "lost", "missing",
        "stolen", "status", "overdue",
        # Returns / refunds / exchanges
        "refund", "refunded", "refundable", "return", "returned", "returns",
        "exchange", "exchanged", "rma", "replacement",
        "warranty", "guarantee", "restocking", "label",
        "prepaid", "creditnote",
        "layby", "cooling", "reject", "rejection",
        # Order lifecycle
        "order", "orders", "reorder",
        "cancel", "cancellation", "cancelled", "canceled",
        "backorder", "backordered", "preorder",
        "confirmation", "confirmed",
        # Product issues
        "damaged", "broken", "defective", "faulty", "cracked",
        "wrong", "incorrect", "expired", "recalled",
        "sizing", "size", "fit", "colour", "color", "quality",
        "stock", "restock", "inventory",
        "dodgy", "rubbish", "knackered",
        # Payment & billing
        "billing", "payment", "invoice", "receipt",
        "charge", "charged", "overcharged", "chargeback",
        "discount", "coupon", "promo", "promotion", "code", "sale",
        "giftcard", "voucher",
        "installment", "installments", "surcharge",
        "debit", "credit",
        "afterpay", "zip", "humm", "latitudepay", "bpay", "eftpos", "openpay",
        "clearpay", "klarna", "laybuy", "bacs",
        "affirm", "sezzle", "shoppay", "applepay", "venmo", "cashapp",
        "paypal",
        "tax", "gst", "vat", "abn", "taxexempt",
        # Account & subscription
        "subscription", "unsubscribe", "account", "login", "password",
        "hacked", "hack",
        # Complaint & escalation
        "complaint", "escalate", "escalation", "urgent", "feedback",
        "compensation", "goodwill", "manager", "supervisor",
        "accc", "acl",
        "ombudsman", "statutory",
        "bbb", "ftc",
        "trading",
        # Fraud
        "fraud", "fraudulent", "scam", "dispute",
        "unauthorised", "unauthorized", "authorised",
        # Promotions / loyalty
        "bogo", "clearance", "rewards", "reward", "loyalty", "referral",
        # Address
        "address",
        # UK consumer law
        "satisfactory",
        # Bigram compounds
        "storecredit", "freeshipping", "returnlabel", "returnshipping",
        "pricematch", "priceadjustment", "flashsale", "blackfriday",
        "cybermonday",
        "royalmail", "firstclass", "secondclass", "specialdelivery",
        "safeplace", "clickandcollect", "clickcollect",
        "outofstock", "zipay", "zippay",
        "coolingoff", "consumerrights", "fitforpurpose",
        "tradingstandards", "fairtrading", "section75",
        "salestax", "pobox",
        "identitytheft", "creditcard", "debitcard",
        "australiapost",
    }
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")
_QUOTES_RE = re.compile(r"['`‘’]")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalise_token(raw: str) -> str:
    cleaned = _QUOTES_RE.sub("", raw.lower())
    return _NON_ALNUM_RE.sub("", cleaned)


def _query_matches_topic_keyword(query: str) -> bool:
    raw = _WHITESPACE_RE.split(query.lower())
    tokens = [t for t in (_normalise_token(r) for r in raw) if t]

    if any(t in _TOPIC_KEYWORDS for t in tokens):
        return True

    for i in range(len(tokens) - 1):
        bigram = tokens[i] + tokens[i + 1]
        if bigram in _TOPIC_KEYWORDS:
            return True
    return False


def _extract_order_ref(query: str) -> str | None:
    trimmed = query.strip()
    stripped = re.sub(r"^order\s*#?\s*", "", trimmed, flags=re.IGNORECASE)
    ref = stripped.lstrip("#")

    has_letter = bool(re.search(r"[a-z]", ref, re.IGNORECASE))
    has_digit = bool(re.search(r"\d", ref))

    if has_letter and has_digit and len(ref) >= 3:
        return ref
    if trimmed.startswith("#") and has_letter and len(ref) >= 3:
        return ref
    return None


def _apply_client_filters(
    tickets: list[dict[str, Any]],
    *,
    status: str | None,
    start_date: str | None,
    end_date: str | None,
    requested_limit: int,
) -> dict[str, Any]:
    pre = len(tickets)
    filtered = tickets

    if status:
        filtered = [t for t in filtered if t.get("status") == status]

    if start_date:
        start_ms = datetime.fromisoformat(start_date).replace(
            tzinfo=timezone.utc
        ).timestamp() * 1000
        filtered = [
            t
            for t in filtered
            if _to_ms(t.get("created_datetime")) >= start_ms
        ]

    if end_date:
        end_dt = datetime.fromisoformat(end_date + "T23:59:59.999").replace(
            tzinfo=timezone.utc
        )
        end_ms = end_dt.timestamp() * 1000
        filtered = [
            t for t in filtered if _to_ms(t.get("created_datetime")) <= end_ms
        ]

    return {
        "tickets": filtered,
        "preFilterCount": pre,
        "postFilterCount": len(filtered),
        "droppedCount": pre - len(filtered),
        "apiWindowExhausted": pre >= requested_limit,
    }


def _to_ms(iso: str | None) -> float:
    if not iso:
        return float("inf")
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return float("inf")


def _has_client_filters(
    *, status: str | None, start_date: str | None, end_date: str | None
) -> bool:
    return bool(status or start_date or end_date)


def _build_response(
    *,
    tickets: list[Any],
    search_strategy: str,
    hint: str,
    filter_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final_hint = hint
    if filter_result and filter_result["droppedCount"] > 0:
        final_hint += (
            f" Note: {filter_result['droppedCount']} of {filter_result['preFilterCount']} "
            "rows were dropped by client-side filters (status/date)."
        )
        if filter_result["apiWindowExhausted"]:
            final_hint += (
                " The API window was at the requested limit, so more matching tickets "
                "may exist beyond this page — narrow the query or raise the limit."
            )

    payload: dict[str, Any] = {
        "tickets": [t.to_dict() if hasattr(t, "to_dict") else t for t in tickets],
        "totalFound": len(tickets),
        "searchStrategy": search_strategy,
        "_hint": final_hint,
    }
    if filter_result:
        payload["preFilterCount"] = filter_result["preFilterCount"]
        payload["postFilterCount"] = filter_result["postFilterCount"]
    return payload


async def _view_search(
    client: GorgiasClient, search_term: str, limit: int
) -> list[dict[str, Any]]:
    """Server-side full-text search using the Gorgias view search endpoint."""
    response = await client.put(
        "/api/views/0/items",
        {"view": {"search": search_term, "type": "ticket-list"}},
        {"limit": limit},
    )
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, list):
            return data
    return []


async def _search_by_email(
    client: GorgiasClient,
    email: str,
    args: dict[str, Any],
    limit: int,
) -> dict[str, Any]:
    customers_response = await client.get(
        "/api/customers", {"email": email, "limit": 1}
    )
    data = (
        customers_response.get("data", [])
        if isinstance(customers_response, dict)
        else []
    )
    customer = data[0] if data else None
    if not customer:
        return _build_response(
            tickets=[],
            search_strategy="email",
            hint="No customer found with this email.",
        )

    tickets_response = await client.get(
        "/api/tickets", {"customer_id": customer["id"], "limit": limit}
    )
    raw_tickets = (
        tickets_response.get("data", [])
        if isinstance(tickets_response, dict)
        else []
    )
    filter_result = _apply_client_filters(
        raw_tickets,
        status=args.get("status"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        requested_limit=limit,
    )
    projected = [project_ticket(t) for t in filter_result["tickets"]]

    return _build_response(
        tickets=projected,
        search_strategy="email",
        hint=(
            f"Found {len(projected)} ticket(s) for customer {email}. Use "
            "gorgias_smart_get_ticket to see full conversation details."
        ),
        filter_result=(
            filter_result if _has_client_filters(**_filter_args(args)) else None
        ),
    )


async def _search_by_order_number(
    client: GorgiasClient,
    order_ref: str,
    original_query: str,
    args: dict[str, Any],
    limit: int,
) -> dict[str, Any]:
    tickets = await _view_search(client, original_query, limit)
    filter_result = _apply_client_filters(
        tickets,
        status=args.get("status"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        requested_limit=limit,
    )
    projected = [project_ticket(t) for t in filter_result["tickets"][:limit]]

    if projected:
        hint = (
            f"Found {len(projected)} ticket(s) matching order reference "
            f"'{order_ref}'. Use gorgias_smart_get_ticket to see full details."
        )
    else:
        hint = (
            f"No tickets found matching order reference '{order_ref}'. The order "
            "number may not appear in any ticket subjects or messages. Try "
            "searching by the customer's email instead."
        )

    return _build_response(
        tickets=projected,
        search_strategy="order_number",
        hint=hint,
        filter_result=(
            filter_result if _has_client_filters(**_filter_args(args)) else None
        ),
    )


async def _get_ticket_by_id(
    client: GorgiasClient, ticket_id: int
) -> dict[str, Any]:
    ticket = await client.get(f"/api/tickets/{ticket_id}")
    return _build_response(
        tickets=[project_ticket(ticket)],
        search_strategy="ticket_id",
        hint=(
            f"Retrieved ticket #{ticket_id}. Use gorgias_smart_get_ticket for "
            "full conversation including messages."
        ),
    )


async def _fetch_recent_tickets(
    client: GorgiasClient, args: dict[str, Any], limit: int
) -> dict[str, Any]:
    response = await client.get(
        "/api/tickets",
        {"limit": limit, "order_by": "created_datetime:desc"},
    )
    raw_tickets = response.get("data", []) if isinstance(response, dict) else []
    filter_result = _apply_client_filters(
        raw_tickets,
        status=args.get("status"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        requested_limit=limit,
    )
    projected = [project_ticket(t) for t in filter_result["tickets"]]

    return _build_response(
        tickets=projected,
        search_strategy="recent",
        hint=(
            f"Showing {len(projected)} most recent tickets. Use status, "
            "start_date, end_date to filter. Use gorgias_smart_get_ticket for "
            "full details."
        ),
        filter_result=(
            filter_result if _has_client_filters(**_filter_args(args)) else None
        ),
    )


async def _search_by_view(
    client: GorgiasClient, query: str, args: dict[str, Any], limit: int
) -> dict[str, Any] | None:
    ref_data = await get_reference_data(client)
    matches = fuzzy_match_name(
        query, ref_data.views, lambda v: (v or {}).get("name", ""), 65
    )
    if not matches:
        return None

    match = matches[0]
    view = match.item
    view_name = (view or {}).get("name", "unknown")
    view_id = (view or {}).get("id")

    response = await client.get(f"/api/views/{view_id}/items", {"limit": limit})
    raw_tickets = response.get("data", []) if isinstance(response, dict) else []
    filter_result = _apply_client_filters(
        raw_tickets,
        status=args.get("status"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        requested_limit=limit,
    )
    projected = [project_ticket(t) for t in filter_result["tickets"]]

    return _build_response(
        tickets=projected,
        search_strategy="view",
        hint=(
            f"Showing tickets from view '{view_name}'. Use gorgias_smart_get_ticket "
            "for details."
        ),
        filter_result=(
            filter_result if _has_client_filters(**_filter_args(args)) else None
        ),
    )


async def _search_by_customer_name(
    client: GorgiasClient, query: str, args: dict[str, Any], limit: int
) -> dict[str, Any] | None:
    customers = await client.search({"type": "customer", "query": query, "size": 10})
    if not isinstance(customers, list):
        customers = []
    matches = fuzzy_match_name(
        query,
        customers,
        lambda c: (c or {}).get("name", "") or (c or {}).get("email", ""),
        40,
    )
    if not matches:
        return None

    best = matches[0].item
    customer_id = (best or {}).get("id")
    label = (best or {}).get("name") or (best or {}).get("email") or "unknown"

    tickets_response = await client.get(
        "/api/tickets", {"customer_id": customer_id, "limit": limit}
    )
    raw_tickets = (
        tickets_response.get("data", [])
        if isinstance(tickets_response, dict)
        else []
    )
    filter_result = _apply_client_filters(
        raw_tickets,
        status=args.get("status"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        requested_limit=limit,
    )
    projected = [project_ticket(t) for t in filter_result["tickets"]]

    return _build_response(
        tickets=projected,
        search_strategy="customer_name",
        hint=(
            f"Found {len(projected)} ticket(s) for customer '{label}'. Use "
            "gorgias_smart_get_ticket to see full conversation details."
        ),
        filter_result=(
            filter_result if _has_client_filters(**_filter_args(args)) else None
        ),
    )


async def _search_by_keyword(
    client: GorgiasClient, query: str, args: dict[str, Any], limit: int
) -> dict[str, Any]:
    tickets = await _view_search(client, query, limit)
    filter_result = _apply_client_filters(
        tickets,
        status=args.get("status"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        requested_limit=limit,
    )
    projected = [project_ticket(t) for t in filter_result["tickets"][:limit]]

    if projected:
        hint = (
            f"Found {len(projected)} ticket(s) matching '{query}'. Use "
            "gorgias_smart_get_ticket to see full conversation details."
        )
    else:
        hint = (
            f"No tickets found matching '{query}'. Try different keywords or "
            "search by customer email."
        )

    return _build_response(
        tickets=projected,
        search_strategy="keyword",
        hint=hint,
        filter_result=(
            filter_result if _has_client_filters(**_filter_args(args)) else None
        ),
    )


def _filter_args(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": args.get("status"),
        "start_date": args.get("start_date"),
        "end_date": args.get("end_date"),
    }


def register_smart_search_tools(
    registrar: ToolRegistrar, client: GorgiasClient
) -> None:

    async def smart_search(
        query: Annotated[
            str,
            Field(
                description=(
                    "Search query. Meaning depends on search_type. For 'auto' "
                    "(default) the tool detects intent (email, ticket ID, order "
                    "number, customer name, view, or topic keyword)."
                )
            ),
        ],
        search_type: Annotated[
            Literal[
                "auto",
                "order_number",
                "ticket_id",
                "email",
                "customer_name",
                "keyword",
                "view",
            ]
            | None,
            Field(description="Explicit search strategy. Default 'auto'."),
        ] = None,
        status: Annotated[
            Literal["open", "closed"] | None,
            Field(description="Filter by ticket status (client-side)."),
        ] = None,
        start_date: Annotated[
            str | None,
            Field(description="ISO date YYYY-MM-DD: only tickets created on/after."),
        ] = None,
        end_date: Annotated[
            str | None,
            Field(description="ISO date YYYY-MM-DD: only tickets created on/before."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Max tickets (default 30, max 100).", ge=1, le=100),
        ] = None,
    ) -> dict[str, Any]:
        q = query.strip()
        result_limit = limit or 30
        st = search_type or "auto"
        args: dict[str, Any] = {
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
        }

        try:
            # ----- Explicit search type -----
            if st == "order_number":
                ref = q.lstrip("#")
                return await _search_by_order_number(
                    client, ref, q, args, result_limit
                )

            if st == "ticket_id":
                cleaned = q.lstrip("#")
                try:
                    tid = int(cleaned)
                except ValueError:
                    return _build_response(
                        tickets=[],
                        search_strategy="ticket_id",
                        hint=f"'{query}' is not a valid Gorgias ticket ID.",
                    )
                return await _get_ticket_by_id(client, tid)

            if st == "email":
                return await _search_by_email(client, q, args, result_limit)

            if st == "customer_name":
                result = await _search_by_customer_name(client, q, args, result_limit)
                return result or _build_response(
                    tickets=[],
                    search_strategy="customer_name",
                    hint=f"No customer found matching '{query}'.",
                )

            if st == "keyword":
                return await _search_by_keyword(client, q, args, result_limit)

            if st == "view":
                result = await _search_by_view(client, q, args, result_limit)
                return result or _build_response(
                    tickets=[],
                    search_strategy="view",
                    hint=f"No view found matching '{query}'.",
                )

            # ----- Auto-detection ladder -----

            # Strategy 1: email
            if _EMAIL_PATTERN.match(q):
                return await _search_by_email(client, q, args, result_limit)

            # Strategy 2: ticket ID (skip when date filters are present)
            has_date_filter = bool(start_date or end_date)
            ticket_id_match = _TICKET_ID_PATTERN.match(q)
            if ticket_id_match and not has_date_filter:
                tid_str = (
                    ticket_id_match.group(1)
                    or ticket_id_match.group(2)
                    or ticket_id_match.group(3)
                )
                # Pure-numeric queries can be either ticket IDs or order
                # numbers (e.g. Casa Di Lumo's #14134, #14699). Try ticket
                # ID; on 404, fall back to keyword search so order numbers
                # also work.
                try:
                    return await _get_ticket_by_id(client, int(tid_str))
                except GorgiasApiError as err:
                    if err.status_code == 404 or "does not exist" in str(err):
                        return await _search_by_keyword(
                            client, q, args, result_limit
                        )
                    raise

            # Strategy 3: order/reference number
            order_ref = _extract_order_ref(q)
            if order_ref:
                return await _search_by_order_number(
                    client, order_ref, q, args, result_limit
                )

            # Strategy 4: generic query → recent tickets
            if q.lower() in _GENERIC_QUERIES:
                return await _fetch_recent_tickets(client, args, result_limit)

            # Strategy 5: view fuzzy match
            view_result = await _search_by_view(client, q, args, result_limit)
            if view_result is not None:
                return view_result

            # Strategy 6: topic keyword → keyword search.
            # Promoted ABOVE customer-name fuzzy match — words like
            # "tracking", "shipping", "refund" were being misclassified as
            # customer names because fuzzy_match_name's threshold is loose.
            if _query_matches_topic_keyword(q):
                return await _search_by_keyword(client, q, args, result_limit)

            # Strategy 7: customer name fuzzy match
            customer_result = await _search_by_customer_name(
                client, q, args, result_limit
            )
            if customer_result is not None:
                return customer_result

            # Strategy 8: keyword fallback
            return await _search_by_keyword(client, q, args, result_limit)
        except Exception as err:  # noqa: BLE001
            return {
                "error": sanitise_error_for_llm(err),
                "_hint": (
                    "Search failed. Try a more specific query or use the direct "
                    "API tools."
                ),
            }

    registrar.tool(
        "gorgias_smart_search",
        description=(
            "Intelligent search across tickets, customers, and views. Set "
            "search_type when intent is clear; auto-detection handles emails, topic "
            "keywords, view names, customer names, and ticket IDs. Order numbers "
            "use Gorgias server-side full-text search across subjects, messages, "
            "and metadata. Use gorgias_smart_get_ticket to view full conversations."
        ),
        handler=smart_search,
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
