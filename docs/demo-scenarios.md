# Try DeskZero yourself

Open two windows side by side:
1. **Demo link** (Mira on the Mayura Boutique store), see `links.md`.
2. **Ops Console**: https://saanvishika-agent-actions.onrender.com/ops (updates every 3 seconds).

Start each scenario in a fresh chat (refresh the demo link). Pick **Shopping for myself** or
**Wholesale or bulk order** in the pre-chat. All orders and people are fictional.

## Test orders
| Order | Last 4 digits | State | Use it for |
|---|---|---|---|
| MB1001 | 1111 | Shipped with SwiftShip | Tracking, faster delivery |
| MB1002 | 2222 | Delivered 20 hours ago, ₹2,499 | Damage claim (with or without video) |
| MB1003 | 3333 | Delivered 10 days ago | Late claim (outside window) |
| MB1004 | 4444 | Packing, not shipped | Cancellation, priority packing |
| MB1005 | 5555 | Delivered, ₹5,999 bridal set | High-value claim, human checks video |
| MB1006 | 6666 | Delivered, customer with 3 earlier claims | Repeat claimant, human review |

## A. Retail customers

| # | Situation | Type this | What Mira does | Ops Console |
|---|---|---|---|---|
| A1 | Product question | "Is your jewellery real gold? Will it tarnish?" | Answers from the care page: imitation, nickel-free, care tips | Nothing (no ticket needed) |
| A2 | Shipping question | "How much is shipping and how long to Hyderabad?" | Free above ₹499, else ₹80; 3-5 days metro | Nothing |
| A3 | Where is my order | "Where is my order MB1001? Phone ends 1111" | Courier, tracking number, expected date | Solved by agent |
| A4 | Deliver it sooner | "I need MB1001 (1111) before Friday, it's for a wedding" | Can't change the courier's date, raises SwiftShip ticket SWS-xxxxx | Logistics lane + email to Ravi + courier email |
| A5 | Speed up an unshipped order | "Can you rush MB1004? Phone 4444, need it this week" | Flags for priority packing | Orders lane (Arjun) |
| A6 | Cancel | "Cancel order MB1004, phone 4444" | Cancelled with reference | Solved by agent |
| A7 | Cancel after dispatch | "Cancel MB1001, phone 1111" | Already shipped, can't cancel, offers help if issue on arrival | Filtered |
| A8 | "Damaged", no video | "MB1002, phone 2222, necklace arrived broken, I want a refund. I didn't take a video" | Explains video policy kindly, no escalation | **Filtered** (the headline) |
| A9 | Damaged, with video | "MB1002, phone 2222, a stone fell off. Yes I have the unboxing video" | Replacement approved instantly, claim number | Solved by agent |
| A10 | Late claim | "MB1003, phone 3333, it's damaged, I have a video" | Outside the 48-hour window, can't approve | Filtered |
| A11 | Change of mind | "MB1002, phone 2222, I don't like it, want to return" | Policy covers damage only, offers help choosing | Filtered |
| A12 | Expensive order damaged | "MB1005, phone 5555, clasp is defective, I have the video" | Registered; Arjun checks video first | Orders lane |
| A13 | Serial claimant | "MB1006, phone 6666, it arrived damaged, I have a video" | Logged for personal review | Orders lane |
| A14 | Skin reaction | "MB1002, phone 2222, the earrings gave me a rash" | No medical advice; urgent to Priya | Support lane, **urgent**, email + WhatsApp |
| A15 | Off-topic | "Can you book me a train ticket?" | Polite: only helps with Mayura topics, lists topics | Nothing |
| A16 | Talk to a person | "I want to talk to a human" | Phone + email escalation options | (eGain escalation) |

## B. Wholesale buyers (put the shop name in the message, or Mira asks for it)

| # | Situation | Type this | What Mira does | Ops Console |
|---|---|---|---|---|
| B1 | Guided quote | "I want to buy wholesale" | Runs the guided workflow: design, pieces, discount, then the quote | Depends on the deal |
| B2 | Small deal, haggling | "Meera Boutique: 30 Grand Floral AD Stone Jhumka Earrings at 20% off?" | Counter-offers 15%, "add 20 more pieces to unlock 20%", quote number | Solved by agent |
| B3 | Within tier | "Meera Boutique: 50 Grand Floral AD Stone Jhumka Earrings" | 20% off, quote closed | Solved by agent |
| B4 | Pushes past the limit | "Meera Boutique: 100 Grand Floral AD Stone Jhumka Earrings at 35% off" | "Let me check with my team and get back to you", confirms 25% now | Founder lane with **Approve / Decline** buttons |
| B5 | Big client | "Lakshmi Retail, 12 stores: 5000 Diamond Look CZ Cluster Choker Necklace with Studs at 40%?" | Hands over to Ananya (sales lead), WhatsApp within 30 min | Sales lane, high, email + WhatsApp |
| B6 | Restock | "Meera Boutique: 20 Green Gemstone Panchloha Necklace" | Sold out, restock request logged, suggests in-stock alternative | Orders lane (restock) |
| B7 | Too small for wholesale | "Meera Boutique: 5 Grand Floral AD Stone Jhumka Earrings" | Wholesale starts at 10, points to FIRSTORDER on the site | Nothing |
| B8 | Custom design / credit | "Can you make a custom design for my shop and give 30 days credit?" | Team decides those personally, offers callback | (callback if booked) |

After B4, click **Approve** in the Founder lane: the quote status changes for the buyer.

## C. For the owner (the business pitch)
- Ops Console tiles: requests, solved by agent, filtered by policy, escalated, "noise kept off your team".
- Outbox: every escalation shows the exact email or WhatsApp the right teammate receives (simulated delivery).
- "Plug in your store": paste a Shopify store address and it reads the catalogue and policies and drafts the
  agent's knowledge.

## Notes
- Email and WhatsApp alerts are shown in the Ops Console outbox; delivery is simulated in this demo.
- Demo data resets when the API is redeployed; use **Load sample day** in the Ops Console for a full day of tickets.
