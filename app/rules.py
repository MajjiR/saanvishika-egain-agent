"""Business rules for The Saanvishika Co agent.

Every number the agent is allowed to promise lives here, not in the chat prompt,
so a buyer cannot talk the AI into a better deal than the owner set.

PLACEHOLDER VALUES: the wholesale tiers below are placeholders until the owner
confirms the real ones. Edit this file and redeploy; nothing else changes.
"""

# Wholesale: minimum pieces per quote, and discount (percent) by quantity.
WHOLESALE_MIN_PIECES = 10
WHOLESALE_TIERS = [  # (min_pieces, discount_percent) - highest matching tier wins
    (10, 10),
    (25, 15),
    (50, 20),
    (100, 25),
]
# Above this discount, or above this order size, the owner decides, not the agent.
OWNER_APPROVAL_DISCOUNT_ABOVE = 25
OWNER_APPROVAL_PIECES_ABOVE = 500
QUOTE_VALID_DAYS = 7

# Retail shipping (from saanvishika.co/pages/shipping-policy)
FREE_SHIPPING_ABOVE = 499
FLAT_SHIPPING = 80

# Claims (from shipping-policy and refund-and-cancellation pages)
TRANSIT_ISSUE_HOURS = 48       # damaged or missing items: report within 48 hours
PRODUCT_ISSUE_DAYS = 7         # defective or incorrect items: report within 7 days
AUTO_REPLACE_MAX_VALUE = 3000  # above this order value a person reviews the claim
REPEAT_CLAIM_LIMIT = 2         # this many earlier claims on a phone -> human review

CONTACT = {
    "whatsapp": "+91 81438 88287",
    "email": "saanvishika.co@gmail.com",
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
