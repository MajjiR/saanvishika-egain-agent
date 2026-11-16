# DeskZero: the AI ops desk for D2C brands

**Only what truly needs a human reaches your team.**

DeskZero is an eGain AI Agent for direct-to-consumer brands that sell both retail and wholesale. Every customer
message is triaged against the brand's own rules: the agent **solves** what it can, **filters** what policy does
not allow, and **routes** the rest to exactly one owner on the team, with the alert that person needs.

Demo brand: **Mayura Boutique**, a fictional D2C jewellery store (all orders, people and contacts are demo data).

| | Link |
|---|---|
| Live agent (eGain demo link) | see [`docs/links.md`](docs/links.md) |
| Demo storefront | https://mayura-boutique-demo.vercel.app |
| Ops Console (team view) | https://saanvishika-agent-actions.onrender.com/ops |
| Try-it scenarios | [`docs/demo-scenarios.md`](docs/demo-scenarios.md) |

## What it handles

| Customer says | DeskZero does |
|---|---|
| "Where is my order?" | Looks up courier, tracking and ETA (verified by order number + last 4 phone digits) |
| "It arrived damaged" without an unboxing video | Explains the policy kindly; **filtered**, nobody is pinged |
| "It arrived damaged", video, low value | Approves a replacement instantly |
| Expensive order, repeat claimant | Registers the claim and routes it for human review |
| "I got a rash" | No medical advice; urgent to Support, copied to Manager and Manufacturing |
| "Deliver before Friday" | Raises a courier ticket with the vendor and alerts Logistics |
| "Cancel my order" | Cancels before dispatch; politely refuses after |
| "30 pieces at 20% off?" | Counter-offers the allowed tier and shows how many more pieces unlock the next |
| "100 pieces at 35%?" | "Let me check with my team"; quote waits in the Manager's approval queue |
| "5,000 pieces for my 12 stores" | Hands over to the wholesale sales lead (email + WhatsApp), copies Manager and Manufacturing |
| "20 of a sold-out design" | Logs a restock request for Manufacturing and suggests an in-stock alternative |
| Product, shipping, care questions | Answers from the brand's published policies |

## How it is built

```
Customer ─▶ eGain AI Agent "Mira"
             · knowledge: 6 policy pages, generated intents
             · pre-chat: retail or wholesale, then the question
             · process workflow: guided wholesale quote (linked to an intent)
             · escalation: phone, email, cannot-answer fallback
             · 4 custom actions ─────────────┐
                                             ▼
                      DeskZero Actions API (FastAPI)
                      rules.py decides prices, eligibility, routing
                                             │
                                             ▼
                      Ops Console: categories, routing board, approvals, alerts outbox
```

Prices, discount limits, claim windows and routing live in [`app/rules.py`](app/rules.py), not in the prompt, so
the agent cannot be talked past them.

### Team routing (demo roster)
Customer Support · Orders & Returns · Logistics · Wholesale Sales · Operations Manager (approvals, repeat
claimants) · Vendors & Courier · Manufacturing & QC (restock, product defects, material complaints).

### Actions API
| Endpoint | Purpose |
|---|---|
| `GET /v1/wholesale/quote` | Three-tier negotiation: auto quote, team approval, human takeover; restock on sold-out items |
| `GET /v1/claims` | Damage, defect, wrong item or skin reaction triage (window, video, value, history) |
| `GET /v1/orders/status` | Courier, tracking and ETA |
| `GET /v1/logistics/expedite` | Courier ticket or priority packing |
| `GET /v1/orders/cancel` | Cancel before dispatch |
| `GET /v1/callbacks` | Book a callback with the right team |
| `GET /v1/import?url=` | Read a Shopify store's catalogue and policies to draft the agent's knowledge |

Every response returns `result` (for the workflow to branch on) and `message` (for the agent to relay).
API docs: https://saanvishika-agent-actions.onrender.com/docs

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest httpx
.venv/bin/uvicorn app.main:app --reload        # Ops Console at http://127.0.0.1:8000/ops
.venv/bin/python -m pytest -q
```

## Repository
- `app/` actions API, rules, demo catalogue and test orders
- `web/ops.html` Ops Console
- `kb/` knowledge pages uploaded to the eGain agent
- `storefront/` demo store (Vercel) and its generator
- `docs/` live links, eGain configuration, try-it scenarios
- `tests/` API tests

Built for the eGain AI Agent Hackathon, November 2026. Code written with AI assistance. Product photography is
used with the permission of the D2C jewellery brand that inspired the demo.
