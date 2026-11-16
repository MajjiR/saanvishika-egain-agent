"""Business rules for the DeskZero demo brand, Mayura Boutique (fictional).

Every number the agent may promise lives here, not in the chat prompt, so a customer
cannot talk the AI past it. A real brand edits this file; nothing else changes.
"""

BRAND = "Mayura Boutique"
PRODUCT = "DeskZero"

# ---- Wholesale negotiation: three tiers of authority -------------------------
WHOLESALE_MIN_PIECES = 10
WHOLESALE_TIERS = [  # (min_pieces, discount_percent): the agent may give these on its own
    (10, 10),
    (25, 15),
    (50, 20),
    (100, 25),
]
TEAM_CHECK_DISCOUNT_ABOVE = 25   # asks above this: "let me check with my team", owner decides
TEAM_CHECK_PIECES_FROM = 300     # orders this big: owner confirms before it is final
HUMAN_TAKEOVER_PIECES_FROM = 1000  # enterprise deals: a salesperson takes over the chat
QUOTE_VALID_DAYS = 7

# ---- Retail policy ------------------------------------------------------------
FREE_SHIPPING_ABOVE = 499
FLAT_SHIPPING = 80
TRANSIT_ISSUE_HOURS = 48       # damaged or missing in transit
PRODUCT_ISSUE_DAYS = 7         # defective or wrong item
UNBOXING_VIDEO_REQUIRED = True
AUTO_REPLACE_MAX_VALUE = 3000  # above this a person checks the video first
REPEAT_CLAIM_LIMIT = 2

# ---- The team (fictional) and where each kind of issue goes ---------------------
TEAM = {
    "support":   {"name": "Priya", "role": "Customer Support", "email": "support@mayura-demo.in", "whatsapp": "+91 90000 00001"},
    "orders":    {"name": "Arjun", "role": "Orders & Returns", "email": "orders@mayura-demo.in", "whatsapp": "+91 90000 00002"},
    "logistics": {"name": "Ravi", "role": "Logistics", "email": "logistics@mayura-demo.in", "whatsapp": "+91 90000 00003"},
    "sales":     {"name": "Ananya", "role": "Wholesale Sales Lead", "email": "sales@mayura-demo.in", "whatsapp": "+91 90000 00004"},
    "owner":     {"name": "Owner", "role": "Founder", "email": "owner@mayura-demo.in", "whatsapp": "+91 90000 00005"},
}
COURIER = {"name": "SwiftShip Logistics (demo)", "email": "ops@swiftship-demo.in"}

CONTACT = {
    "whatsapp": "+91 90000 00001",
    "email": "support@mayura-demo.in",
    "hours": "Mon-Sat, 10 AM - 7 PM IST",
}


def tier_for(pieces: int) -> int:
    pct = 0
    for min_pieces, discount in WHOLESALE_TIERS:
        if pieces >= min_pieces:
            pct = discount
    return pct


def next_tier(pieces: int):
    for min_pieces, discount in WHOLESALE_TIERS:
        if pieces < min_pieces:
            return min_pieces, discount
    return None
