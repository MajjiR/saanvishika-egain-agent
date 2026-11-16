# eGain configuration (as built)

Tenant: Agentic Studio → AI Agent for Customer. Agent: **Saanvi - Saanvishika Jewellery Assistant**
(ID `a0aba44d-54aa-4482-9262-cea1d50ab674`), English (US).

## Knowledge
Six files from `kb/` uploaded under Point to Content → Files (8,648 characters) and trained.
Generated intents: Logistics and Order Fulfillment; Returns, Refunds, and Replacements; Product Offerings
and Styling; Wholesale Procurement and Bulk Ordering; Payment and Transaction Policies; Customer Support
and Communication; Jewellery Care and Maintenance; Product Material Composition and Maintenance.

## Personalize
- Chat disclaimer: AI assistant notice, never share card numbers/OTPs/passwords, demo data is fictional.
- Initial message: greeting listing what Saanvi can do.
- Topic Identification on, with a brand-specific failure message and topic list.
- Additional instructions: answer only from published pages; the service decides prices and eligibility;
  relay action messages exactly; wholesale and owner-approval rules; no medical advice; only order number
  and last 4 phone digits for identity.
- Escalation (Default Behavior): phone +91 81438 88287, email saanvishika.co@gmail.com, and a
  "cannot answer" fallback offering WhatsApp, email or a callback.
- Pre-chat: `Saanvishika_Front_Door`.
- Demo link over saanvishika.co (see `links.md`).

## Workflows
- **Pre-chat `Saanvishika_Front_Door`** (published): Select question "shopping for yourself or for your
  business?" → `customer_type`; Text question → `userQuery`; Send to AI Agent with `userQuery` and
  `customer_type`. Invalid select answers fall through to the text question.
- **Process `Wholesale_Quote_Guide`** (published): Text question → `wq_product`; Number → `wq_quantity`;
  Number → `wq_discount`; API GET `/v1/wholesale/quote` with those as query params, response `message` →
  `wq_message`; success → Statement `{{wq_message}}`; On Error and On Timeout → fallback Statement with
  WhatsApp and email.
- **Intent `Start a wholesale quote`** → assigned workflow `Wholesale_Quote_Guide`.

## Custom actions (Enable Actions → Custom APIs)
| Action | Method + URL | Query parameters |
|---|---|---|
| Get wholesale quote | GET `/v1/wholesale/quote` | product, quantity, requested_discount, buyer_name |
| Register damage claim | GET `/v1/claims` | order_id, phone_last4, issue, has_unboxing_video |
| Check order status | GET `/v1/orders/status` | order_id, phone_last4 |

Base URL: `https://saanvishika-agent-actions.onrender.com`. No authentication (demo endpoints touch only
fictional data).

## Verified in Test AI Agent
- "30 Emerald Screwback Jhumka, 20% off?" → counter-offer 15%, ₹1,104/piece, quote WQ-1002, "add 20 more
  pieces to unlock 20%".
- "SV1002, phone 2222, stone fell off, have unboxing video" → claim CL-1002 approved, replacement.
- Public demo link, signed out: pre-chat shows; "Wholesale or bulk order" → "100 Emerald Screwback Jhumka at
  35%?" → quote sent for owner approval, confirmed 25% (₹974/piece, ₹97,400), contacts shown.

Note: the Render free instance stores records in SQLite on ephemeral disk, so quote and claim numbers restart
after a redeploy. Do not redeploy between recording the video and judging.
