import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.sqlite3")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)


def q(**kw):
    return c.post("/v1/wholesale/quote", json=kw).json()


def feed():
    return c.get("/ops/api/feed").json()


def test_search_budget():
    r = c.get("/v1/products/search", params={"query": "jhumka", "max_price": 1500}).json()
    assert r["result"] == "found"


def test_tier1_auto_quote_and_counter():
    r = q(product="Floral AD Stone Jhumka", quantity=30)
    assert r["result"] == "quote_issued" and r["discount_percent"] == 15 and "Add 20 more" in r["message"]
    assert q(product="Floral AD Stone Jhumka", quantity=30, requested_discount=20)["result"] == "counter_offer"


def test_tier2_team_check_and_approval():
    r = q(product="Floral AD Stone Jhumka", quantity=100, requested_discount=35)
    assert r["result"] == "team_check" and "check with my team" in r["message"]
    c.post(f"/ops/api/decide/{r['quote_id']}/approve")
    assert c.get(f"/v1/quotes/{r['quote_id']}").json()["result"] == "approved"


def test_tier3_human_takeover_routes_to_sales_with_whatsapp():
    r = q(product="Floral AD Stone Jhumka", quantity=5000)
    assert r["result"] == "human_takeover"
    alerts = [a for a in feed()["alerts"] if a["ref"] == r["quote_id"]]
    assert {a["channel"] for a in alerts} == {"email", "whatsapp"} and all(a["team"] == "sales" for a in alerts)


def test_below_minimum_and_ambiguous():
    assert q(product="Floral AD Stone Jhumka", quantity=5)["result"] == "below_minimum"
    assert q(product="earrings", quantity=20)["result"] in ("ambiguous", "not_found")


def test_order_status_verification_and_failure():
    assert c.get("/v1/orders/status", params={"order_id": "MB1001", "phone_last4": "1111"}).json()["result"] == "shipped"
    assert c.get("/v1/orders/status", params={"order_id": "MB1001", "phone_last4": "9"}).json()["result"] == "not_found"
    assert c.get("/v1/orders/status", params={"order_id": "MB0000"}).status_code == 503


def test_cancel_rules():
    assert c.post("/v1/orders/cancel", json={"order_id": "MB1001", "phone_last4": "1111"}).json()["result"] == "not_cancellable"
    r1 = c.post("/v1/orders/cancel", json={"order_id": "MB1004", "phone_last4": "4444"}).json()
    r2 = c.post("/v1/orders/cancel", json={"order_id": "MB1004", "phone_last4": "4444"}).json()
    assert r1["result"] == "cancelled" and r1["reference"] == r2["reference"]


def test_expedite_raises_courier_ticket_and_alerts_logistics():
    r = c.get("/v1/logistics/expedite", params={"order_id": "MB1001", "phone_last4": "1111", "reason": "wedding"}).json()
    assert r["result"] == "courier_ticket_raised" and r["reference"].startswith("SWS-")
    assert any(a["team"] == "logistics" and "SwiftShip" in a["to"] for a in feed()["alerts"])


def claim(**kw):
    return c.post("/v1/claims", json=kw).json()


def test_triage_filters_noise_and_escalates_only_what_matters():
    before = feed()["stats"]
    assert claim(order_id="MB1002", phone_last4="2222", issue="stone broken", has_unboxing_video="no")["result"] == "need_video"
    assert claim(order_id="MB1003", phone_last4="3333", issue="damaged", has_unboxing_video="yes")["result"] == "outside_window"
    assert claim(order_id="MB1002", phone_last4="2222", issue="I changed my mind")["result"] == "not_eligible"
    after = feed()["stats"]
    assert after["filtered"] - before["filtered"] == 3 and after["escalated"] == before["escalated"]
    assert claim(order_id="MB1002", phone_last4="2222", issue="stone broken", has_unboxing_video="yes")["result"] == "replacement_approved"
    assert claim(order_id="MB1005", phone_last4="5555", issue="defective clasp", has_unboxing_video="yes")["result"] == "human_review"
    assert claim(order_id="MB1006", phone_last4="6666", issue="damaged", has_unboxing_video="yes")["result"] == "human_review"
    assert claim(order_id="MB1002", phone_last4="2222", issue="skin rash")["result"] == "escalate"


def test_callback_routes_by_topic():
    assert c.post("/v1/callbacks", json={"phone": "12345"}).json()["result"] == "need_phone"
    r = c.post("/v1/callbacks", json={"phone": "+91 90000 00011", "topic": "late delivery"}).json()
    assert r["result"] == "booked" and "Logistics" in r["message"]


def test_import_rejects_non_public_urls():
    assert c.get("/v1/import", params={"url": "http://localhost"}).json()["result"] == "invalid"
    assert c.get("/v1/import", params={"url": "https://127.0.0.1"}).json()["result"] == "invalid"


def test_ops_console_serves():
    assert "DeskZero" in c.get("/ops").text


def test_sold_out_logs_restock_request_and_suggests_alternative():
    r = q(product="Solitaire Drop Stud Earrings Yellow", quantity=20)
    assert r["result"] == "out_of_stock" and r["reference"].startswith("TK")
    assert any(x["team"] == "orders" and "Restock" in x["summary"] for x in feed()["requests"])
