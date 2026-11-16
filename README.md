# Saanvi: the Saanvishika jewellery assistant (eGain AI Agent)

An eGain AI Agent for **The Saanvishika Co**, a real imitation-jewellery brand that sells retail on
[saanvishika.co](https://saanvishika.co) and wholesale over WhatsApp. One agent serves two customers:

- **Retail shoppers:** policy-grounded answers, order status, cancellations, damage claims.
- **Wholesale buyers:** instant tiered quotes with a quote number, counter-offers, and owner approval
  for anything above the agent's limit.

All orders, buyers and claims in this demo are **fictional**. Product names and prices come from the
public catalogue; policies come from the brand's published pages.

## How it fits together

```
Customer → eGain AI Agent (knowledge, intents, pre-chat, process + escalation workflows)
              │  Custom API actions (HTTPS + X-API-Key)
              ▼
         This service (FastAPI): rules.py decides prices and eligibility
              │
              ▼
         Owner Desk (/owner): approve or decline quotes above the limit
```

Rules live in [`app/rules.py`](app/rules.py), not in the prompt, so the agent cannot be talked past them.

## Actions

| Endpoint | What it does | `result` values |
|---|---|---|
| `POST /v1/wholesale/quote` | product + quantity (+ requested discount) → tier price and quote ID | `quote_issued`, `counter_offer`, `owner_approval`, `below_minimum`, `ambiguous`, `not_found`, `out_of_stock`, `need_quantity` |
| `GET /v1/quotes/{id}` | quote status after the owner decides | `issued`, `pending_owner`, `approved_by_owner`, `declined_by_owner` |
| `GET /v1/products/search` | query + max price → top 3 in-stock pieces | `found`, `none` |
| `POST /v1/orders/status` | order ID + last 4 phone digits | `processing`, `shipped`, `delivered`, `not_found` |
| `POST /v1/orders/cancel` | cancels only before dispatch | `cancelled`, `not_cancellable`, `not_found` |
| `POST /v1/claims` | damage, defect or wrong item → checks window and video | `replacement_approved`, `need_video`, `outside_window`, `human_review`, `escalate`, `not_eligible`, `need_issue` |
| `POST /v1/callbacks` | books a callback with a conversation summary | `booked`, `need_phone` |

Parameters may be sent as query string or JSON body. Every response carries `result` (to branch on)
and `message` (to show the customer). `order_id=SV0000` returns a 503 so the error path can be tested.

### Test orders (fictional)

| Order | Last 4 digits | State |
|---|---|---|
| SV1001 | 1111 | shipped |
| SV1002 | 2222 | delivered 20 hours ago (claim approves) |
| SV1003 | 3333 | delivered 10 days ago (outside window) |
| SV1004 | 4444 | processing (can cancel) |
| SV1005 | 5555 | ₹4,999 order (claim goes to a person) |
| SV1006 | 6666 | repeat claimant (claim goes to a person) |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest httpx
.venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m pytest -q
```

Environment: `API_KEY` (required header `X-API-Key` on `/v1/*` when set), `OWNER_KEY` (Owner Desk), `DB_PATH`.

## Disclosure

Built for the eGain AI Agent Hackathon (November 2026). Code and knowledge pages were written for this
entry with AI assistance. No templates or third-party code beyond FastAPI and Uvicorn.
