"""DeskZero action API: the ops desk behind an eGain AI Agent for D2C brands.

Demo brand: Mayura Boutique (fictional). Every response is flat JSON with `result`
(a fixed word the eGain workflow branches on) and `message` (a sentence the agent
shows as-is). Parameters come from the query string or a JSON body.

Each request is triaged: answered automatically, filtered (policy says no, nobody
needs to be bothered), or escalated to the one team member who owns it, with the
email and WhatsApp alert that person would receive recorded in the outbox.
"""

import ipaddress
import json
import os
import re
import socket
import urllib.request
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import rules
from .store import _now, find_product, open_db, search_products, test_orders

app = FastAPI(title="DeskZero Actions", version="2.0.0",
              description="Actions for the DeskZero eGain AI Agent. Demo brand Mayura Boutique; all data fictional.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
db = open_db()
API_KEY = os.environ.get("ACTION_API_KEY", "")  # optional; off for the public demo (fictional data only)
WEB = Path(__file__).parent.parent / "web"


@app.middleware("http")
async def check_key(request: Request, call_next):
    if API_KEY and request.url.path.startswith("/v1/") and request.headers.get("x-api-key") != API_KEY:
        return JSONResponse({"result": "unauthorized", "message": "Missing or wrong API key."}, status_code=401)
    return await call_next(request)


async def params(request: Request) -> dict:
    data = dict(request.query_params)
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                data.update({k: v for k, v in body.items() if v not in (None, "")})
        except Exception:
            pass
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}


def to_int(v, default=None):
    try:
        return int(float(str(v).replace(",", "").replace("%", "").strip()))
    except (TypeError, ValueError):
        return default


def rupees(x: float) -> str:
    return f"₹{x:,.0f}"


def contact_line():
    c = rules.CONTACT
    return f"WhatsApp {c['whatsapp']} or email {c['email']} ({c['hours']})"


# ---------------------------------------------------------------- triage log + router

def log(kind: str, prefix: str, outcome: str, severity: str, team: str | None, summary: str,
        dedupe: str = "", **extra) -> dict:
    """Record one customer request and, if escalated, the alerts the owning team receives.

    outcome: auto_resolved | filtered | escalated | awaiting_team | human_takeover
    """
    rec = db.add(kind, prefix, dedupe, {"outcome": outcome, "status": outcome, "severity": severity,
                                         "team": team, "summary": summary, **extra})
    if team and not rec.get("repeat") and outcome in ("escalated", "awaiting_team", "human_takeover"):
        member = rules.TEAM[team]
        subject = f"[{severity.upper()}] {rec['id']}: {summary}"
        db.add("alert", "AL", "", {"channel": "email", "to": f"{member['name']} <{member['email']}>",
                                   "team": team, "subject": subject, "ref": rec["id"], "status": "sent (simulated)"})
        if severity in ("high", "urgent"):
            db.add("alert", "AL", "", {"channel": "whatsapp", "to": f"{member['name']} {member['whatsapp']}",
                                       "team": team, "subject": subject, "ref": rec["id"], "status": "sent (simulated)"})
    return rec


# ---------------------------------------------------------------- products

@app.api_route("/v1/products/search", methods=["GET", "POST"])
async def product_search(request: Request):
    p = await params(request)
    results, _, _ = search_products(p.get("query", ""), max_price=to_int(p.get("max_price")), limit=3)
    if not results:
        return {"result": "none", "count": 0,
                "message": "I couldn't find an in-stock piece matching that. Try another style or budget."}
    lines = [f"{i + 1}. {r['title']} - {rupees(r['price'])}" for i, r in enumerate(results)]
    return {"result": "found", "count": len(results), "message": "Here are the closest matches:\n" + "\n".join(lines)}


# ---------------------------------------------------------------- wholesale negotiation

@app.api_route("/v1/wholesale/quote", methods=["GET", "POST"])
async def wholesale_quote(request: Request):
    p = await params(request)
    qty = to_int(p.get("quantity"))
    asked = to_int(p.get("requested_discount"), 0) or 0
    buyer = p.get("buyer_name") or "Wholesale buyer"

    if not qty or qty <= 0:
        return {"result": "need_quantity", "message": "How many pieces would you like? Please send a number."}
    if qty < rules.WHOLESALE_MIN_PIECES:
        return {"result": "below_minimum",
                "message": f"Wholesale pricing starts at {rules.WHOLESALE_MIN_PIECES} pieces per design. For {qty} pieces, "
                           "please order on the website; first orders get 10% off with code FIRSTORDER."}

    product, candidates = find_product(p.get("product", ""))
    if not product:
        if candidates:
            opts = "; ".join(f"{c['title']} ({rupees(c['price'])})" for c in candidates)
            return {"result": "ambiguous", "message": f"Which design do you mean? Closest matches: {opts}."}
        return {"result": "not_found", "message": "I couldn't find that design in our catalogue. Please send the product name "
                                                  "as shown on the store."}
    if not product["available"]:
        alts, _, _ = search_products(" ".join(product["title"].split()[:3]), limit=2)
        alt = f" Similar in stock now: {alts[0]['title']} ({rupees(alts[0]['price'])})." if alts else ""
        rec = log("ticket", "TK", "escalated", "low", "orders", f"Restock request: {product['title']} x{qty} from {buyer}",
                  dedupe=f"restock:{product['id']}:{buyer}")
        return {"result": "out_of_stock", "reference": rec["id"],
                "message": f"{product['title']} is sold out right now, so I can't quote it. I've logged a restock request "
                           f"(reference {rec['id']}) with our orders team, and they'll message you as soon as it's back, "
                           f"usually within 2-3 weeks.{alt}"}

    tier = rules.tier_for(qty)
    unit = round(product["price"] * (100 - tier) / 100)
    total = unit * qty
    valid_until = (_now() + timedelta(days=rules.QUOTE_VALID_DAYS)).strftime("%d %b %Y")
    base = {"product": product["title"], "quantity": qty, "discount_percent": tier, "unit_price": unit,
            "total": total, "valid_until": valid_until}
    deal = f"{qty} x {product['title']} ({rupees(total)} at {tier}%)" + (f", asked {asked}%" if asked else "")

    # Tier 3: enterprise volume -> a person takes over.
    if qty >= rules.HUMAN_TAKEOVER_PIECES_FROM:
        rec = log("quote", "WQ", "human_takeover", "high", "sales", f"Enterprise deal: {deal} from {buyer}",
                  buyer=buyer, **base)
        lead = rules.TEAM["sales"]
        return {**base, "quote_id": rec["id"], "result": "human_takeover",
                "message": f"An order of {qty:,} pieces deserves a real conversation. I've handed this to {lead['name']}, our "
                           f"{lead['role']}, with everything you've told me (reference {rec['id']}). She'll take over on "
                           f"WhatsApp {lead['whatsapp']} within 30 minutes during working hours. For reference, our standard "
                           f"top tier is {tier}% off: {rupees(unit)} per piece."}

    # Tier 2: above the agent's authority -> "let me check with my team".
    if asked > rules.TEAM_CHECK_DISCOUNT_ABOVE or qty >= rules.TEAM_CHECK_PIECES_FROM:
        rec = log("quote", "WQ", "awaiting_team", "medium", "owner", f"Approval needed: {deal} from {buyer}",
                  buyer=buyer, requested_discount=asked, **base)
        return {**base, "quote_id": rec["id"], "result": "team_check",
                "message": f"Let me check with my team and get back to you. I've sent quote {rec['id']} for approval and "
                           f"you'll hear back within 2 working hours. What I can confirm right now is {tier}% off: "
                           f"{rupees(unit)} per piece, {rupees(total)} for {qty} pieces."}

    # Tier 1: within limits -> the agent closes it.
    nxt = rules.next_tier(qty)
    upsell = f" Add {nxt[0] - qty} more pieces to reach {nxt[0]} and unlock {nxt[1]}% off." if nxt else ""
    rec = log("quote", "WQ", "auto_resolved", "low", None, f"Auto quote: {deal} for {buyer}",
              buyer=buyer, requested_discount=asked, **base)
    if asked > tier:
        return {**base, "quote_id": rec["id"], "result": "counter_offer",
                "message": f"I can't do {asked}% at {qty} pieces, but I can do {tier}%: {rupees(unit)} per piece, "
                           f"{rupees(total)} total for {product['title']}.{upsell} Quote {rec['id']} is valid until {valid_until}."}
    return {**base, "quote_id": rec["id"], "result": "quote_issued",
            "message": f"Quote {rec['id']}: {qty} x {product['title']} at {tier}% off = {rupees(unit)} per piece, "
                       f"{rupees(total)} total (prices include GST).{upsell} Valid until {valid_until}."}


@app.get("/v1/quotes/{qid}")
def quote_lookup(qid: str):
    rec = db.get(qid.upper())
    if not rec or not rec["id"].startswith("WQ"):
        return {"result": "not_found", "message": "I couldn't find that quote number."}
    labels = {"auto_resolved": "issued", "awaiting_team": "waiting for the team's approval",
              "approved": "approved by the team", "declined": "declined; the standard tier still stands",
              "human_takeover": "with our wholesale sales lead"}
    return {"result": rec["status"], "message": f"Quote {rec['id']} is {labels.get(rec['status'], rec['status'])}."}


# ---------------------------------------------------------------- orders

def _order(p):
    oid = (p.get("order_id") or "").upper().replace("#", "").replace(" ", "")
    if oid and oid.isdigit():
        oid = "MB" + oid
    return oid, test_orders().get(oid)


def _verified(p):
    oid, o = _order(p)
    return oid, (o if o and p.get("phone_last4", "") == o["phone_last4"] else None)


@app.api_route("/v1/orders/status", methods=["GET", "POST"])
async def order_status(request: Request):
    p = await params(request)
    oid, o = _verified(p)
    if oid == "MB0000":
        return JSONResponse({"result": "error", "message": "Order system unavailable."}, status_code=503)
    if not o:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits. "
                                                  "Please check both."}
    if o["status"] == "processing":
        msg = f"Order {oid} ({o['item']}) is being packed and will ship within 1-3 business days."
    elif o["status"] == "shipped":
        eta = (o["placed"] + timedelta(days=o["eta_days"] + 2)).strftime("%d %b")
        msg = f"Order {oid} ({o['item']}) is on its way with {o['courier']}, tracking {o['awb']}, expected by {eta}."
    else:
        msg = f"Order {oid} ({o['item']}) was delivered on {o['delivered'].strftime('%d %b, %I:%M %p')}."
    log("ticket", "TK", "auto_resolved", "low", None, f"Order status {oid}: {o['status']}")
    return {"result": o["status"], "order_id": oid, "message": msg}


@app.api_route("/v1/orders/cancel", methods=["GET", "POST"])
async def order_cancel(request: Request):
    p = await params(request)
    oid, o = _verified(p)
    if not o:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits."}
    if o["status"] != "processing":
        log("ticket", "TK", "filtered", "low", None, f"Cancel refused {oid}: already {o['status']}")
        return {"result": "not_cancellable",
                "message": f"Order {oid} has already left our warehouse, so it can't be cancelled. If anything is wrong "
                           "when it arrives, I can help you report it."}
    rec = log("ticket", "TK", "auto_resolved", "low", None, f"Cancelled {oid} before dispatch", dedupe=f"cancel:{oid}")
    return {"result": "cancelled", "reference": rec["id"],
            "message": f"Done. Order {oid} is cancelled (reference {rec['id']}). Your refund goes to the original payment "
                       "method within 7-10 business days."}


@app.api_route("/v1/logistics/expedite", methods=["GET", "POST"])
async def expedite(request: Request):
    p = await params(request)
    oid, o = _verified(p)
    reason = p.get("reason", "customer asked for faster delivery")
    if not o:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits."}
    if o["status"] == "delivered":
        return {"result": "already_delivered", "message": f"Order {oid} has already been delivered."}
    if o["status"] == "processing":
        rec = log("ticket", "TK", "escalated", "medium", "orders", f"Priority dispatch request {oid}: {reason}",
                  dedupe=f"exp:{oid}")
        return {"result": "priority_dispatch_requested", "reference": rec["id"],
                "message": f"I've flagged order {oid} for priority packing (ticket {rec['id']}) and alerted our orders team. "
                           "I can't promise a date, but it will go out in the first batch it can."}
    courier_ticket = f"SWS-{70000 + len(db.list(1000))}"
    rec = log("ticket", "TK", "escalated", "medium", "logistics",
              f"Expedite {oid} ({o['awb']}): {reason}. Courier ticket {courier_ticket}",
              dedupe=f"exp:{oid}", courier_ticket=courier_ticket)
    if not rec.get("repeat"):
        db.add("alert", "AL", "", {"channel": "email", "to": rules.COURIER["name"] + f" <{rules.COURIER['email']}>",
                                   "team": "logistics", "subject": f"Expedite request {o['awb']} ({courier_ticket})",
                                   "ref": rec["id"], "status": "sent (simulated)"})
    return {"result": "courier_ticket_raised", "reference": rec.get("courier_ticket", courier_ticket),
            "message": f"Your order is already with {o['courier']}, so we can't speed it up from our side, but I've "
                       f"raised ticket {rec.get('courier_ticket', courier_ticket)} with them to prioritise it and told "
                       "our logistics lead. You'll get an update by SMS if the date changes."}


# ---------------------------------------------------------------- claims (the triage showcase)

ISSUES = {
    "damaged": "transit", "broken": "transit", "missing": "transit", "crushed": "transit",
    "defective": "product", "stone fell": "product", "stone came": "product", "tarnish": "product",
    "wrong": "product", "incorrect": "product", "different": "product",
    "allergy": "health", "rash": "health", "itch": "health", "skin": "health", "swelling": "health",
    "change of mind": "mind", "don't like": "mind", "dont like": "mind", "not needed": "mind", "changed my mind": "mind",
}


def _issue_kind(text: str) -> str:
    t = (text or "").lower()
    for k, v in ISSUES.items():
        if k in t:
            return v
    return "unknown"


@app.api_route("/v1/claims", methods=["GET", "POST"])
async def claim(request: Request):
    p = await params(request)
    oid, o = _verified(p)
    if oid == "MB0000":
        return JSONResponse({"result": "error", "message": "Claims system unavailable."}, status_code=503)
    if not o:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits."}
    issue = p.get("issue", "")
    kind = _issue_kind(issue)
    video = str(p.get("has_unboxing_video", "")).lower() in ("yes", "y", "true", "1")

    if kind == "health":
        rec = log("claim", "CL", "escalated", "urgent", "support", f"Skin reaction reported on {oid}: {issue}",
                  dedupe=f"{oid}:health")
        return {"result": "escalate", "reference": rec["id"],
                "message": "I'm sorry you're dealing with that. Please take the jewellery off, and see a doctor if it's "
                           "painful or spreading. I can't give medical advice, so I've marked this urgent for "
                           f"{rules.TEAM['support']['name']} in our support team (reference {rec['id']}). She'll call you today."}
    if o["status"] != "delivered":
        return {"result": "not_delivered", "message": f"Order {oid} hasn't been delivered yet. I can check where it is."}
    if kind == "mind":
        log("claim", "CL", "filtered", "low", None, f"Change-of-mind return refused {oid}")
        return {"result": "not_eligible",
                "message": "Our policy covers damaged, defective or wrong items, so change-of-mind returns aren't possible. "
                           "I'd be happy to help you find a design you'll love instead."}
    if kind == "unknown":
        return {"result": "need_issue", "message": "Is the item damaged, missing, defective, or the wrong item?"}

    age = _now() - o["delivered"]
    window = timedelta(hours=rules.TRANSIT_ISSUE_HOURS) if kind == "transit" else timedelta(days=rules.PRODUCT_ISSUE_DAYS)
    if age > window:
        limit = f"{rules.TRANSIT_ISSUE_HOURS} hours" if kind == "transit" else f"{rules.PRODUCT_ISSUE_DAYS} days"
        log("claim", "CL", "filtered", "low", None, f"Late claim refused {oid}: delivered {age.days} days ago")
        return {"result": "outside_window",
                "message": f"Order {oid} was delivered {age.days} days ago, and this kind of issue must be reported within "
                           f"{limit}, so I can't open a claim. Our care guide may help keep your other pieces looking new."}
    if not video:
        log("claim", "CL", "filtered", "low", None, f"Damage claim without unboxing video {oid}: {issue}")
        return {"result": "need_video",
                "message": "I'm sorry it arrived like that. Our policy needs an unboxing video to approve damage claims, "
                           "because it protects you and us from transit disputes. If you have one, reply 'yes' and I'll "
                           "process it right away. Without it, I'm not able to approve a replacement."}
    if o.get("prior_claims", 0) >= rules.REPEAT_CLAIM_LIMIT:
        rec = log("claim", "CL", "escalated", "medium", "orders", f"Repeat claimant {oid}: {issue}", dedupe=f"{oid}:review")
        return {"result": "human_review", "reference": rec["id"],
                "message": f"I've logged your claim as {rec['id']}. A team member will review it personally and reply "
                           "within one working day."}
    if o["value"] > rules.AUTO_REPLACE_MAX_VALUE:
        rec = log("claim", "CL", "escalated", "medium", "orders", f"High-value claim {oid} ({rupees(o['value'])}): {issue}",
                  dedupe=f"{oid}:{kind}")
        return {"result": "human_review", "reference": rec["id"],
                "message": f"Claim {rec['id']} is registered. Because this is a {rupees(o['value'])} order, "
                           f"{rules.TEAM['orders']['name']} from our orders team checks your video first and confirms a "
                           "replacement or refund within one working day."}
    rec = log("claim", "CL", "auto_resolved", "low", None, f"Replacement approved {oid}: {issue}", dedupe=f"{oid}:{kind}")
    return {"result": "replacement_approved", "reference": rec["id"],
            "message": f"Approved. Claim {rec['id']}: a replacement {o['item']} ships within 1-3 business days at no cost. "
                       f"Please email your unboxing video to {rules.CONTACT['email']} quoting {rec['id']}."}


# ---------------------------------------------------------------- callbacks

TOPIC_TEAM = {"wholesale": "sales", "bulk": "sales", "delivery": "logistics", "shipping": "logistics",
              "return": "orders", "refund": "orders", "order": "orders"}


@app.api_route("/v1/callbacks", methods=["GET", "POST"])
async def callback(request: Request):
    p = await params(request)
    phone = "".join(ch for ch in p.get("phone", "") if ch.isdigit())[-10:]
    if len(phone) != 10:
        return {"result": "need_phone", "message": "Please share a 10-digit mobile number for the callback."}
    topic = (p.get("topic") or "general").lower()
    team = next((t for k, t in TOPIC_TEAM.items() if k in topic), "support")
    rec = log("ticket", "CB", "escalated", "medium", team, f"Callback ···{phone[-4:]}: {topic}. {p.get('summary', '')}",
              dedupe=f"{phone}:{topic}")
    who = rules.TEAM[team]
    return {"result": "booked", "reference": rec["id"],
            "message": f"Callback booked (reference {rec['id']}). {who['name']} from {who['role']} will call you during "
                       f"{rules.CONTACT['hours']}, with your conversation summary already in hand."}


# ---------------------------------------------------------------- store import ("plug in your store")

def _public_https(url: str) -> str:
    if not re.match(r"^https://[A-Za-z0-9.-]+(/.*)?$", url or ""):
        raise ValueError("Enter a full https:// store address.")
    host = url.split("/")[2]
    for info in socket.getaddrinfo(host, 443):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("That address is not a public store.")
    return "https://" + host


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "DeskZero-Importer/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read(3_000_000).decode("utf-8", "ignore"))


@app.get("/v1/import")
def import_store(url: str = ""):
    """Reads a Shopify store's public catalogue and policies and drafts the agent's knowledge."""
    try:
        base = _public_https(url)
    except ValueError as e:
        return {"result": "invalid", "message": str(e)}
    out = {"store": base, "products": 0, "collections": [], "price_range": None, "policies": [], "draft_pages": []}
    try:
        products = _fetch_json(base + "/products.json?limit=250").get("products", [])
    except Exception:
        return {"result": "not_shopify", "message": "Couldn't read a Shopify catalogue at that address."}
    prices = [float(v["price"]) for x in products for v in x.get("variants", [])[:1] if v.get("price")]
    out["products"] = len(products)
    out["price_range"] = [min(prices), max(prices)] if prices else None
    out["collections"] = sorted({x.get("product_type") or "" for x in products} - {""})[:12]
    for slug in ("refund-policy", "shipping-policy", "terms-of-service", "privacy-policy"):
        try:
            pol = _fetch_json(f"{base}/policies/{slug}.json").get("policy", {})
            if pol.get("body"):
                out["policies"].append(pol.get("title") or slug)
        except Exception:
            pass
    out["draft_pages"] = ["Shipping and Delivery", "Returns and Claims", "Wholesale and Bulk Orders",
                          "Collections and Price Guide", "Materials and Care", "Orders, Payments and Contact"]
    out["result"] = "imported"
    out["message"] = (f"Imported {out['products']} products"
                      + (f" ({rupees(out['price_range'][0])}-{rupees(out['price_range'][1])})" if prices else "")
                      + f" and {len(out['policies'])} policy pages. Drafted {len(out['draft_pages'])} knowledge pages "
                        "and 6 actions ready to review.")
    return out


# ---------------------------------------------------------------- ops console

@app.get("/ops/api/feed")
def ops_feed():
    recs = db.list(500)
    requests_ = [r for r in recs if r["id"][:2] in ("WQ", "CL", "TK", "CB")]
    alerts = [r for r in recs if r["id"].startswith("AL")]
    count = lambda *o: sum(1 for r in requests_ if r.get("status") in o)
    return {"brand": rules.BRAND, "team": rules.TEAM, "requests": requests_, "alerts": alerts,
            "stats": {"total": len(requests_), "auto": count("auto_resolved"), "filtered": count("filtered"),
                      "escalated": count("escalated", "awaiting_team", "human_takeover", "approved", "declined")}}


@app.post("/ops/api/decide/{rid}/{decision}")
def ops_decide(rid: str, decision: str):
    if decision not in ("approve", "decline"):
        return JSONResponse({"result": "bad_decision"}, status_code=400)
    rec = db.get(rid.upper())
    if not rec or rec.get("status") != "awaiting_team":
        return {"result": "not_pending"}
    return {"result": "ok", "record": db.update(rid.upper(), status="approved" if decision == "approve" else "declined")}


@app.get("/ops", response_class=HTMLResponse, include_in_schema=False)
def ops_page():
    return (WEB / "ops.html").read_text(encoding="utf-8")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ops")


@app.get("/health")
def health():
    return {"ok": True, "time": _now().isoformat(timespec="seconds")}
