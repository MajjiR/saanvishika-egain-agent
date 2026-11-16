"""Builds the Mayura Boutique demo storefront and the matching API catalogue.

Input: a Shopify products.json snapshot (product photos used with the brand owner's permission).
Output: storefront/index.html and app/catalog.json, so every product on the page can be quoted by the agent.
Run: python3 storefront/build.py path/to/products.json
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLD_OUT = {"Solitaire Drop Stud Earrings (Yellow)", "Green Gemstone Panchloha Necklace"}
E = html.escape


def load(path):
    items, seen = [], set()
    for x in json.load(open(path))["products"]:
        if not x.get("images") or not any(v["available"] for v in x["variants"]):
            continue
        title = x["title"].strip()
        if title in seen:
            continue
        seen.add(title)
        v = x["variants"][0]
        price = float(v["price"])
        cmp_ = float(v["compare_at_price"]) if v.get("compare_at_price") else round(price * 1.5, -1)
        items.append({"id": x["handle"], "title": title, "price": price, "compare_at": max(cmp_, price),
                      "available": title not in SOLD_OUT, "tags": [t.lower() for t in x["tags"]],
                      "image": x["images"][0]["src"].split("?")[0],
                      "url": f"https://mayura-boutique-demo.vercel.app/#{x['handle']}",
                      "description": html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", x["body_html"] or ""))).strip()[:300]})
    return items


def pick(items, words, n, used=None):
    out = []
    for p in items:
        t = (p["title"] + " " + " ".join(p["tags"])).lower()
        if any(w in t for w in words) and (used is None or p["id"] not in used):
            out.append(p)
            if used is not None:
                used.add(p["id"])
        if len(out) == n:
            break
    return out


def img(p, w=600):
    return f"{p['image']}?width={w}"


def rs(x):
    return f"Rs. {x:,.0f}"


def card(p):
    off = round(100 - 100 * p["price"] / p["compare_at"]) if p["compare_at"] > p["price"] else 0
    badge = '<span class="badge so">Sold out</span>' if not p["available"] else (f'<span class="badge">Sale</span>' if off else "")
    btn = "Notify me" if not p["available"] else "Add to cart"
    return (f'<article class="card" id="{E(p["id"])}"><a class="ph" href="#{E(p["id"])}"><img src="{E(img(p))}" alt="{E(p["title"])}" loading="lazy">{badge}</a>'
            f'<h3>{E(p["title"])}</h3><p class="price">{f"<s>{rs(p["compare_at"])}</s> " if off else ""}<b>{rs(p["price"])}</b></p>'
            f'<button class="add" type="button">{btn}</button></article>')


def grid(ps, cls="grid"):
    return f'<div class="{cls}">' + "".join(card(p) for p in ps) + "</div>"


def section(title, body, sub="", link="View all", anchor=""):
    a = f' id="{anchor}"' if anchor else ""
    return (f'<section class="wrap"{a}><div class="sh"><h2>{E(title)}</h2>{f"<p>{E(sub)}</p>" if sub else ""}</div>{body}'
            f'{f"<div class=\"more\"><a href=\"#shop\">{link}</a></div>" if link else ""}</section>')


def tile(label, p):
    return f'<a class="tile" href="#shop"><img src="{E(img(p, 500))}" alt="" loading="lazy"><span>{E(label)}</span></a>'


def build(items):
    used = set()
    circles_spec = [("Prebooking", ["prebook", "new"]), ("Necklace Set", ["necklace"]), ("Chokers", ["choker"]),
                    ("Haram", ["haram", "mala"]), ("Ear Chains", ["ear chain", "earchain"]), ("Tikka", ["tikka"]),
                    ("Ear Cuffs", ["earcuff", "ear cuff"]), ("Nose Pins", ["nose"]), ("Neck Patti", ["patti"]),
                    ("Jhumkas", ["jhumka"])]
    circles = ""
    for label, words in circles_spec:
        ps = pick(items, words, 1)
        if ps:
            circles += f'<a class="circ" href="#shop"><img src="{E(img(ps[0], 200))}" alt="" loading="lazy"><span>{E(label)}</span></a>'

    hero = pick(items, ["bridal"], 1, used) + pick(items, ["choker"], 1, used) + pick(items, ["peacock"], 1, used)
    featured_product = pick(items, ["detachable", "dangler"], 1, used)
    featured = pick(items, ["earcuff", "victorian", "beads"], 4, used)
    new_arrivals = [p for p in items if p["id"] not in used][:8]
    used.update(p["id"] for p in new_arrivals)
    sold = [p for p in items if not p["available"]]
    for p in sold:
        if p not in new_arrivals:
            new_arrivals[-1:] = [p]
    interchangeable = pick(items, ["detachable", "interchangeable"], 4, used)
    beads = pick(items, ["beads", "mala"], 4, used)
    peacock = pick(items, ["peacock"], 4, used)
    bridal = pick(items, ["bridal", "heavy"], 4, used)
    shown = {p["id"]: p for p in hero + featured_product + featured + new_arrivals + interchangeable + beads + peacock + bridal}

    neck = [(l, pick(items, w, 1)) for l, w in [("Necklace", ["necklace"]), ("Haram", ["haram"]), ("Beads Mala", ["mala", "beads"]),
                                                ("Chokers", ["choker"]), ("Kante", ["kante", "kasu"]), ("Neck Patti", ["patti"])]]
    ear = [(l, pick(items, w, 1)) for l, w in [("Jhumka Earrings", ["jhumka"]), ("Danglers", ["dangler"]), ("Ear Cuffs", ["earcuff"]),
                                               ("Ear Chains", ["ear chain", "earchain"]), ("Stud Earrings", ["stud"]), ("Chandbalis", ["chandbali"])]]
    acc = [(l, pick(items, w, 1)) for l, w in [("Tikka", ["tikka"]), ("Nose Pins", ["nose"]), ("Pendants", ["pendant"]), ("Choti", ["choti"])]]
    tiles = lambda rows: '<div class="tiles">' + "".join(tile(l, ps[0]) for l, ps in rows if ps) + "</div>"
    budget = "".join(f'<a class="bud" href="#shop"><small>Below</small><b>₹{b}</b></a>' for b in ["499", "999", "1,999", "2,999", "3,999"])
    fp = featured_product[0] if featured_product else items[0]
    faqs = [("What are your pieces made of?", "High-quality nickel-free imitation metals with gold or silver plating, CZ/AD stones, kundan and beads. Nothing is real gold or diamond."),
            ("Do you offer free shipping?", "Yes, on orders above ₹499 across India. Orders of ₹499 or less have a flat ₹80 charge."),
            ("What is your return policy?", "Replacements or refunds for damaged, defective or wrong items, reported within 48 hours (transit damage) or 7 days (defects) with an unboxing video. No change-of-mind returns."),
            ("Do you take bulk or wholesale orders?", "Yes, from 10 pieces a design with 10-25% off. Ask Mira for an instant quote; 1,000+ pieces are handled by our sales lead."),
            ("How long does delivery take?", "Orders ship in 1-3 business days; delivery takes 3-5 days to metros and 5-7 days elsewhere."),
            ("Can you deliver sooner?", "Once shipped, our courier sets the date, but Mira can raise a priority ticket with them for you.")]
    faq = "".join(f"<details><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in faqs)
    tabs = "".join(f'<button class="tab{" on" if i == 0 else ""}" data-t="t{i}">{n}</button>' for i, n in enumerate(["Beads Jewellery", "Peacock Jewellery", "Bridal Jewellery"]))
    panes = "".join(f'<div class="pane{" on" if i == 0 else ""}" id="t{i}">{grid(ps)}</div>' for i, ps in enumerate([beads, peacock, bridal]))
    off_fp = round(100 - 100 * fp["price"] / fp["compare_at"])

    page = TEMPLATE.format(
        circles=circles, h0=E(img(hero[0], 1600)), h1=E(img(hero[1], 900)), h2=E(img(hero[2], 900)), budget=budget,
        fp_img=E(img(fp, 900)), fp_title=E(fp["title"]), fp_cmp=rs(fp["compare_at"]), fp_price=rs(fp["price"]), fp_off=off_fp,
        featured=section("Featured collection", grid(featured), anchor="best"),
        new=section("New Arrivals", grid(new_arrivals), "Fresh drops for the wedding season", anchor="shop"),
        bridal_img=E(img(bridal[0] if bridal else hero[0], 1000)),
        neck=section("Necklace Collection", tiles(neck), link=""), ear=section("Earrings Collection", tiles(ear), link=""),
        acc=section("Accessories", tiles(acc), link=""),
        inter=section("Special Interchangeable Jewellery", grid(interchangeable),
                      "Switch stone colours to match any outfit: wear it as a necklace, pendant or layered piece."),
        tabs=tabs, panes=panes, faq=faq)
    return page, list(shown.values())


TEMPLATE = Path(__file__).with_name("template.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    items = load(sys.argv[1])
    page, shown = build(items)
    (ROOT / "storefront" / "index.html").write_text(page, encoding="utf-8")
    for p in shown:
        p["tags"] = p["tags"][:3]
    json.dump(shown, open(ROOT / "app" / "catalog.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(shown)} products on page and in catalogue")
