# Submission kit: DeskZero

**Agent name:** DeskZero (demo agent "Mira" for Mayura Boutique)
**Industry:** Retail / D2C e-commerce (jewellery), retail and wholesale
**Use case:** An AI ops desk for D2C brands: triages every customer message, solves or filters most of them,
and routes only what truly needs a person to the right team member, with deal negotiation built in.

**Tagline:** *Only what truly needs a human reaches your team.*

## Description (150 words max; this is 146)

I run a D2C jewellery brand doing 1,000-1,500 orders a month. Most messages are the same: where is my order,
"it's damaged" with no unboxing video, "deliver it sooner", "what's your bulk price". Each one lands on a person.
DeskZero is an eGain AI Agent that triages every message against the brand's own rules. It solves what it can
(order status, cancellations, approved replacements, wholesale quotes), filters what policy doesn't allow
(no-video claims, late claims, change-of-mind returns), and escalates only the rest to the one teammate who owns
it: support, orders, logistics or sales, by email and WhatsApp. Faster-delivery requests raise a courier ticket.
Deals negotiate in three tiers: auto-quote within limits, "let me check with my team" above them, and a sales
lead takeover for 1,000+ pieces. A store-import tool drafts the agent's knowledge from any Shopify store.

**Disclosure:** custom action API (FastAPI on Render), Ops Console and demo storefront (Vercel) written for this
entry with AI assistance. Mayura Boutique is fictional; product photos are used with the brand owner's permission.
All orders, people and contacts are demo data.

## Links
- Demo link: see `links.md`
- Demo store: https://mayura-boutique-demo.vercel.app
- Ops Console: https://saanvishika-agent-actions.onrender.com/ops

## One-minute video script (record with the Ops Console open in a second window)

| Time | Screen | Say |
|---|---|---|
| 0:00-0:07 | You on camera or the store | "I run a D2C jewellery brand, about 1,500 orders a month. My team drowns in the same messages." |
| 0:07-0:12 | Demo link, pre-chat, "Shopping for myself" | "This is DeskZero, built on eGain." |
| 0:12-0:22 | "Order MB1002, phone 2222, necklace arrived broken, I want a refund, no unboxing video" | "No video? Mira explains the policy kindly. Nobody on my team is bothered." Cut to Ops Console: *filtered*. |
| 0:22-0:32 | "Order MB1001, phone 1111, I need it before Friday for a wedding" | "Delivery requests raise a courier ticket automatically and ping logistics." Ops: Logistics lane, SwiftShip email. |
| 0:32-0:48 | "I'm Lakshmi Retail. 30 Grand Floral AD Stone Jhumka Earrings at 20%?" then "5000 Diamond Look CZ Cluster Choker Necklaces at 40% for Lakshmi Retail" | "Small deals: it counter-offers within my limits. Big deals: my sales lead takes over, with email and WhatsApp." Ops: Sales lane + outbox. |
| 0:48-0:55 | Ops Console tiles, then "Plug in your store" import | "Every message triaged. Any Shopify store can plug in." |
| 0:55-1:00 | Tagline | "DeskZero: only what truly needs a human reaches your team." |

Tip: include the shop name in wholesale messages; the agent otherwise asks for it first.
