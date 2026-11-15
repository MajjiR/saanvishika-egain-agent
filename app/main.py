"""Action API for the Saanvishika eGain AI Agent.

Every response is flat JSON: `result` (a fixed word the eGain workflow branches on)
and `message` (a sentence the agent can show as-is). Parameters are read from the
query string or a JSON body, whichever the eGain action sends.
"""

import os
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from . import rules
from .store import IST, _now, find_product, open_db, search_products, test_orders

app = FastAPI(title="Saanvishika Agent Actions", version="1.0.0",
              description="Actions for The Saanvishika Co eGain AI Agent. All orders and buyers are fictional.")
db = open_db()
API_KEY = os.environ.get("API_KEY", "")
OWNER_KEY = os.environ.get("OWNER_KEY", "owner-demo")
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


# ---------------------------------------------------------------- products

@app.api_route("/v1/products/search", methods=["GET", "POST"])
async def product_search(request: Request):
    p = await params(request)
    max_price = to_int(p.get("max_price"))
    results, _, _ = search_products(p.get("query", ""), max_price=max_price, limit=3)
    if not results:
        return {"result": "none", "message": "I couldn't find an in-stock piece matching that. Try another style or budget.",
                "count": 0}
    lines = [f"{i+1}. {r['title']} - {rupees(r['price'])} - {r['url']}" for i, r in enumerate(results)]
    out = {"result": "found", "count": len(results), "message": "Here are the closest matches:\n" + "\n".join(lines)}
    for i, r in enumerate(results, 1):
        out[f"p{i}_title"], out[f"p{i}_price"], out[f"p{i}_url"] = r["title"], r["price"], r["url"]
    return out


# ---------------------------------------------------------------- wholesale quotes

@app.api_route("/v1/wholesale/quote", methods=["GET", "POST"])
async def wholesale_quote(request: Request):
    p = await params(request)
    qty = to_int(p.get("quantity"))
    asked = to_int(p.get("requested_discount"), 0) or 0
    buyer = p.get("buyer_name") or "Wholesale buyer"
    city = p.get("city") or ""

    if not qty or qty <= 0:
        return {"result": "need_quantity", "message": "How many pieces would you like? Please send a number."}
    if qty < rules.WHOLESALE_MIN_PIECES:
        return {"result": "below_minimum",
                "message": f"Wholesale pricing starts at {rules.WHOLESALE_MIN_PIECES} pieces per design. For {qty} pieces, "
                           f"please order on the website, where first orders get 10% off with code FIRSTORDER."}

    product, candidates = find_product(p.get("product", ""))
    if not product:
        if candidates:
            opts = "; ".join(f"{c['title']} ({rupees(c['price'])})" for c in candidates)
            return {"result": "ambiguous", "message": f"Which design do you mean? Closest matches: {opts}. "
                                                      "Please send the exact name."}
        return {"result": "not_found", "message": "I couldn't find that design in our catalogue. Please send the product "
                                                  "name as shown on saanvishika.co, or ask for our team."}
    if not product["available"]:
        return {"result": "out_of_stock",
                "message": f"{product['title']} is out of stock right now. Our team can check restock dates: {contact_line()}."}

    tier = rules.tier_for(qty)
    unit = round(product["price"] * (100 - tier) / 100)
    total = unit * qty
    nxt = rules.next_tier(qty)
    upsell = (f" Add {nxt[0] - qty} more pieces to reach {nxt[0]} and unlock {nxt[1]}% off." if nxt else "")

    needs_owner = asked > rules.OWNER_APPROVAL_DISCOUNT_ABOVE or qty > rules.OWNER_APPROVAL_PIECES_ABOVE
    status = "pending_owner" if needs_owner else "issued"
    valid_until = (_now() + timedelta(days=rules.QUOTE_VALID_DAYS)).strftime("%d %b %Y")
    rec = db.add("quote", "WQ", "", {
        "status": status, "buyer": buyer, "city": city, "product": product["title"], "product_url": product["url"],
        "quantity": qty, "retail_price": product["price"], "tier_discount": tier, "unit_price": unit, "total": total,
        "requested_discount": asked, "valid_until": valid_until,
    })
    base = {"quote_id": rec["id"], "product": product["title"], "quantity": qty, "discount_percent": tier,
            "unit_price": unit, "total": total, "valid_until": valid_until}

    if needs_owner:
        why = (f"{asked}% is above what I can approve" if asked > rules.OWNER_APPROVAL_DISCOUNT_ABOVE
               else f"orders above {rules.OWNER_APPROVAL_PIECES_ABOVE} pieces are priced personally")
        return {**base, "result": "owner_approval",
                "message": f"{why}, so I've sent quote {rec['id']} to the owner for approval. Today's best confirmed price is "
                           f"{tier}% off: {rupees(unit)} per piece, {rupees(total)} for {qty} pieces. "
                           f"You'll hear back within one working day, or reach us on {contact_line()}."}
    if asked > tier:
        return {**base, "result": "counter_offer",
                "message": f"I can't do {asked}% at {qty} pieces, but I can do {tier}%: {rupees(unit)} per piece, "
                           f"{rupees(total)} total for {product['title']}.{upsell} Quote {rec['id']} is valid until {valid_until}."}
    return {**base, "result": "quote_issued",
            "message": f"Quote {rec['id']}: {qty} x {product['title']} at {tier}% off = {rupees(unit)} per piece, "
                       f"{rupees(total)} total (prices include GST).{upsell} Valid until {valid_until}. "
                       f"To confirm, reply with your quote number on WhatsApp {rules.CONTACT['whatsapp']}."}


# ---------------------------------------------------------------- orders

def _order(p):
    oid = (p.get("order_id") or "").upper().replace("#", "").replace(" ", "")
    if oid and oid.isdigit():
        oid = "SV" + oid
    return oid, test_orders().get(oid)


@app.api_route("/v1/orders/status", methods=["GET", "POST"])
async def order_status(request: Request):
    p = await params(request)
    oid, o = _order(p)
    if oid == "SV0000":
        return JSONResponse({"result": "error", "message": "Order system unavailable."}, status_code=503)
    if not o or p.get("phone_last4", "") != o["phone_last4"]:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits. "
                                                  "Please check both, or contact us: " + contact_line() + "."}
    if o["status"] == "processing":
        msg = f"Order {oid} ({o['item']}) is being packed and will ship within 1-3 business days."
    elif o["status"] == "shipped":
        eta = (o["placed"] + timedelta(days=o["eta_days"] + 2)).strftime("%d %b")
        msg = f"Order {oid} ({o['item']}) has shipped with {o['courier']}, tracking number {o['awb']}. Expected by {eta}."
    else:
        msg = f"Order {oid} ({o['item']}) was delivered on {o['delivered'].strftime('%d %b, %I:%M %p')}."
    return {"result": o["status"], "order_id": oid, "message": msg}


@app.api_route("/v1/orders/cancel", methods=["GET", "POST"])
async def order_cancel(request: Request):
    p = await params(request)
    oid, o = _order(p)
    if not o or p.get("phone_last4", "") != o["phone_last4"]:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits."}
    if o["status"] != "processing":
        return {"result": "not_cancellable",
                "message": f"Order {oid} has already been dispatched, so it can't be cancelled. If something is wrong "
                           "when it arrives, I can help you report it."}
    rec = db.add("cancellation", "CN", oid, {"order_id": oid, "status": "cancelled"})
    return {"result": "cancelled", "reference": rec["id"],
            "message": f"Done. Order {oid} is cancelled (reference {rec['id']}). Your refund goes to the original payment "
                       "method within 7-10 business days."}


# ---------------------------------------------------------------- claims

ISSUES = {
    "damaged": "transit", "broken": "transit", "missing": "transit",
    "defective": "product", "stone fell": "product", "wrong": "product", "incorrect": "product",
    "allergy": "health", "rash": "health", "itch": "health", "skin": "health",
    "change of mind": "mind", "don't like": "mind", "dont like": "mind", "not needed": "mind",
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
    oid, o = _order(p)
    if oid == "SV0000":
        return JSONResponse({"result": "error", "message": "Claims system unavailable."}, status_code=503)
    if not o or p.get("phone_last4", "") != o["phone_last4"]:
        return {"result": "not_found", "message": "I couldn't match that order number with those phone digits."}
    kind = _issue_kind(p.get("issue", ""))
    has_video = str(p.get("has_unboxing_video", "")).lower() in ("yes", "y", "true", "1")

    if kind == "health":
        rec = db.add("claim", "CL", f"{oid}:health", {"order_id": oid, "status": "escalated", "issue": p.get("issue")})
        return {"result": "escalate", "reference": rec["id"],
                "message": "I'm sorry you're having a skin reaction. Please take the jewellery off and, if it's painful or "
                           "spreading, see a doctor. I can't give medical advice, so I've passed this to our team "
                           f"(reference {rec['id']}). They'll contact you today: {contact_line()}."}
    if o["status"] != "delivered":
        return {"result": "not_delivered", "message": f"Order {oid} hasn't been delivered yet, so there's nothing to claim. "
                                                      "I can check its status for you."}
    if kind == "mind":
        return {"result": "not_eligible",
                "message": "Our policy covers damaged, defective or incorrect items, so change-of-mind returns aren't "
                           "possible. If you'd like a different design, our team can help on " + contact_line() + "."}
    if kind == "unknown":
        return {"result": "need_issue", "message": "Is the item damaged, missing, defective, or the wrong item?"}
    if o.get("prior_claims", 0) >= rules.REPEAT_CLAIM_LIMIT:
        rec = db.add("claim", "CL", f"{oid}:review", {"order_id": oid, "status": "human_review", "issue": p.get("issue")})
        return {"result": "human_review", "reference": rec["id"],
                "message": f"I've logged your claim as {rec['id']}. A team member will review it personally and reply "
                           "within one working day."}

    age = _now() - o["delivered"]
    window = timedelta(hours=rules.TRANSIT_ISSUE_HOURS) if kind == "transit" else timedelta(days=rules.PRODUCT_ISSUE_DAYS)
    if age > window:
        limit = f"{rules.TRANSIT_ISSUE_HOURS} hours" if kind == "transit" else f"{rules.PRODUCT_ISSUE_DAYS} days"
        return {"result": "outside_window",
                "message": f"Order {oid} was delivered {age.days} days ago, and {('damage or missing items' if kind == 'transit' else 'defects or wrong items')} "
                           f"must be reported within {limit}. I can't approve this, but our team can take a look: {contact_line()}."}
    if not has_video:
        return {"result": "need_video",
                "message": "To process this, we need your unboxing video. Do you have one? If not, photos of the item and "
                           f"packaging can be reviewed by our team on {contact_line()}."}
    if o["value"] > rules.AUTO_REPLACE_MAX_VALUE:
        rec = db.add("claim", "CL", f"{oid}:{kind}", {"order_id": oid, "status": "human_review", "issue": p.get("issue")})
        return {"result": "human_review", "reference": rec["id"],
                "message": f"Claim {rec['id']} is registered. For orders above {rupees(rules.AUTO_REPLACE_MAX_VALUE)} a team "
                           "member checks your video first, then confirms a replacement or refund within one working day."}
    rec = db.add("claim", "CL", f"{oid}:{kind}", {"order_id": oid, "status": "replacement_approved", "issue": p.get("issue")})
    return {"result": "replacement_approved", "reference": rec["id"],
            "message": f"Approved. Claim {rec['id']}: a replacement {o['item']} ships within 1-3 business days, at no cost. "
                       f"Please email your unboxing video to {rules.CONTACT['email']} quoting {rec['id']}. "
                       "Prefer a refund instead? Just tell me."}


# ---------------------------------------------------------------- callbacks

@app.api_route("/v1/callbacks", methods=["GET", "POST"])
async def callback(request: Request):
    p = await params(request)
    phone = "".join(ch for ch in p.get("phone", "") if ch.isdigit())[-10:]
    if len(phone) != 10:
        return {"result": "need_phone", "message": "Please share a 10-digit mobile number for the callback."}
    rec = db.add("callback", "CB", f"{phone}:{p.get('topic', '')}", {
        "name": p.get("name", ""), "phone_last4": phone[-4:], "topic": p.get("topic", "general"),
        "summary": p.get("summary", ""), "status": "booked"})
    return {"result": "booked", "reference": rec["id"],
            "message": f"Callback booked (reference {rec['id']}). Our team will call you during {rules.CONTACT['hours']}, "
                       "and they'll already have your conversation summary."}


# ---------------------------------------------------------------- owner console

@app.get("/owner/api/records")
def owner_records(key: str = ""):
    if key != OWNER_KEY:
        return JSONResponse({"result": "unauthorized"}, status_code=401)
    return {"records": db.list()}


@app.post("/owner/api/quotes/{qid}/{decision}")
def owner_decide(qid: str, decision: str, key: str = ""):
    if key != OWNER_KEY:
        return JSONResponse({"result": "unauthorized"}, status_code=401)
    if decision not in ("approve", "decline"):
        return JSONResponse({"result": "bad_decision"}, status_code=400)
    rec = db.update(qid, status="approved_by_owner" if decision == "approve" else "declined_by_owner")
    return {"result": "ok" if rec else "not_found", "record": rec}


@app.get("/v1/quotes/{qid}")
def quote_lookup(qid: str):
    rec = db.get(qid.upper())
    if not rec or not rec["id"].startswith("WQ"):
        return {"result": "not_found", "message": "I couldn't find that quote number."}
    labels = {"issued": "issued", "pending_owner": "waiting for the owner's approval",
              "approved_by_owner": f"approved by the owner at your requested {rec['requested_discount']}%",
              "declined_by_owner": f"declined at {rec['requested_discount']}%; the standard {rec['tier_discount']}% still stands"}
    return {"result": rec["status"], "message": f"Quote {rec['id']} is {labels.get(rec['status'], rec['status'])}."}


@app.get("/owner", response_class=HTMLResponse, include_in_schema=False)
def owner_page():
    return (WEB / "owner.html").read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"ok": True, "time": _now().astimezone(IST).isoformat(timespec="seconds")}
