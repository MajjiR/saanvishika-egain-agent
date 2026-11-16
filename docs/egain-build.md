# eGain configuration

Agentic Studio → AI Agent for Customer. Agent: **Mira - Mayura Boutique DeskZero Demo**, English (US).

## Knowledge
Six pages from `kb/` uploaded under Point to Content → Files and trained. Generated intents include
Logistics and Shipping Policy; Returns, Refunds, and Replacements; Wholesale and Bulk Procurement; Order Management
and Customer Support; Promotions and Shopping Assistance; Jewellery Product Information and Care.

## Personalize and publish
- Disclaimer: AI assistant, never share card numbers, OTPs or passwords; demo data is fictional.
- Greeting listing what Mira can do.
- Topic Identification on, with a brand-specific out-of-scope reply and topic list.
- Additional instructions: triage first (solve, filter by policy, escalate only when needed); answer only from
  published pages; the service decides prices and eligibility; relay action messages exactly; no medical advice;
  identify orders only by order number and last 4 phone digits.
- Escalation: phone and email (demo contacts) plus a "cannot answer" fallback that offers a callback.
- Pre-chat workflow attached; demo link over the storefront (see `links.md`).

## Workflows
- **Pre-chat (front door):** Select question "shopping for yourself or buying for your business?" →
  `customer_type`; Text question → `userQuery`; Send to AI Agent with both. Invalid answers fall through to the
  text question.
- **Process `Wholesale_Quote_Guide`:** design → `wq_product`; pieces → `wq_quantity`; requested discount →
  `wq_discount`; API GET `/v1/wholesale/quote`, response `message` → `wq_message`; success → Statement; On Error
  and On Timeout → fallback Statement with the wholesale team's contacts.
- **Intent "Guided wholesale quote"** → `Wholesale_Quote_Guide`.

## Custom actions
| Action | Endpoint | Parameters |
|---|---|---|
| Get wholesale quote | `/v1/wholesale/quote` | product, quantity, requested_discount, buyer_name |
| Register damage claim | `/v1/claims` | order_id, phone_last4, issue, has_unboxing_video |
| Check order status | `/v1/orders/status` | order_id, phone_last4 |
| Request faster delivery | `/v1/logistics/expedite` | order_id, phone_last4, reason |

Base URL `https://saanvishika-agent-actions.onrender.com`. The demo endpoints touch only fictional data.

## Validation
All paths were tested in Test AI Agent and through the published demo link: knowledge answers, pre-chat,
guided workflow, counter-offer, team approval, human takeover, restock, courier ticket, claim with and without
video, and escalation.
