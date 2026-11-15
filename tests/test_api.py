import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.sqlite3")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

c = TestClient(app)


def q(**kw):
    return c.post("/v1/wholesale/quote", json=kw).json()


def test_search_budget():
    r = c.get("/v1/products/search", params={"query": "jhumka", "max_price": 1500}).json()
    assert r["result"] == "found" and r["p1_price"] <= 1500


def test_quote_tiers_and_upsell():
    r = q(product="Emerald Screwback Jhumka", quantity=30)
    assert r["result"] == "quote_issued" and r["discount_percent"] == 15
    assert r["unit_price"] == round(1299 * 0.85) and "Add 20 more" in r["message"]


def test_quote_below_minimum():
    assert q(product="Emerald Screwback Jhumka", quantity=5)["result"] == "below_minimum"


def test_counter_offer_when_asking_more_than_tier():
    r = q(product="Emerald Screwback Jhumka", quantity=30, requested_discount=20)
    assert r["result"] == "counter_offer" and r["discount_percent"] == 15


def test_owner_approval_above_ceiling():
    r = q(product="Emerald Screwback Jhumka", quantity=100, requested_discount=35)
    assert r["result"] == "owner_approval"
    status = c.get(f"/v1/quotes/{r['quote_id']}").json()
    assert status["result"] == "pending_owner"
    c.post(f"/owner/api/quotes/{r['quote_id']}/approve", params={"key": "owner-demo"})
    assert c.get(f"/v1/quotes/{r['quote_id']}").json()["result"] == "approved_by_owner"


def test_quote_query_params_also_work():
    r = c.post("/v1/wholesale/quote?product=Emerald%20Screwback%20Jhumka&quantity=50").json()
    assert r["discount_percent"] == 20


def test_ambiguous_product():
    assert q(product="earrings", quantity=20)["result"] in ("ambiguous", "not_found")


def test_order_status_and_verification():
    assert c.get("/v1/orders/status", params={"order_id": "SV1001", "phone_last4": "1111"}).json()["result"] == "shipped"
    assert c.get("/v1/orders/status", params={"order_id": "SV1001", "phone_last4": "9999"}).json()["result"] == "not_found"
    assert c.get("/v1/orders/status", params={"order_id": "1001", "phone_last4": "1111"}).json()["result"] == "shipped"


def test_rehearsed_failure():
    assert c.get("/v1/orders/status", params={"order_id": "SV0000"}).status_code == 503


def test_cancel_rules():
    assert c.post("/v1/orders/cancel", json={"order_id": "SV1001", "phone_last4": "1111"}).json()["result"] == "not_cancellable"
    r1 = c.post("/v1/orders/cancel", json={"order_id": "SV1004", "phone_last4": "4444"}).json()
    r2 = c.post("/v1/orders/cancel", json={"order_id": "SV1004", "phone_last4": "4444"}).json()
    assert r1["result"] == "cancelled" and r1["reference"] == r2["reference"]


def claim(**kw):
    return c.post("/v1/claims", json=kw).json()


def test_claim_paths():
    assert claim(order_id="SV1002", phone_last4="2222", issue="stone broken", has_unboxing_video="no")["result"] == "need_video"
    ok = claim(order_id="SV1002", phone_last4="2222", issue="stone broken", has_unboxing_video="yes")
    assert ok["result"] == "replacement_approved"
    assert claim(order_id="SV1003", phone_last4="3333", issue="damaged", has_unboxing_video="yes")["result"] == "outside_window"
    assert claim(order_id="SV1005", phone_last4="5555", issue="defective clasp", has_unboxing_video="yes")["result"] == "human_review"
    assert claim(order_id="SV1006", phone_last4="6666", issue="damaged", has_unboxing_video="yes")["result"] == "human_review"
    assert claim(order_id="SV1002", phone_last4="2222", issue="I don't like it")["result"] == "not_eligible"
    assert claim(order_id="SV1002", phone_last4="2222", issue="skin rash")["result"] == "escalate"


def test_callback():
    assert c.post("/v1/callbacks", json={"phone": "12345"}).json()["result"] == "need_phone"
    assert c.post("/v1/callbacks", json={"phone": "+91 90000 00001", "topic": "bulk"}).json()["result"] == "booked"


def test_owner_key_required():
    assert c.get("/owner/api/records").status_code == 401
