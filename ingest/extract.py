"""Structured extraction: turn raw page text into products, FAQs, policies.

Heuristic (no LLM needed): price patterns -> products, Q/A shapes -> FAQs,
policy keywords -> policies. The admin dashboard shows these per page so the
owner can see exactly what the agent learned.
"""
import re

PRICE_RE = re.compile(
    r"(?P<cur>\$|Rs\.?|PKR|€|£)\s?(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d{2})?)")
SPEC_SPLIT = re.compile(r"\s*[•|\-–]\s*|\s{2,}")

POLICY_KEYWORDS = {
    "shipping": ["shipping", "delivery", "dispatch", "ships in"],
    "returns": ["return", "refund", "exchange", "money-back"],
    "warranty": ["warranty", "guarantee"],
    "privacy": ["privacy policy", "we collect", "cookies"],
}


def _find_prices(text):
    return [(m.group("cur"), m.group("num")) for m in PRICE_RE.finditer(text)]


def extract_products(title, text, url):
    """Find product-like blocks: a name line near a price."""
    products = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        m = PRICE_RE.search(line)
        if not m:
            continue
        # product name: this line without the price, or the previous heading-ish line
        name = PRICE_RE.sub("", line).strip(" -–:|")
        if len(name) < 3 or len(name) > 90:
            if i > 0 and 3 <= len(lines[i - 1]) <= 90:
                name = lines[i - 1]
            else:
                continue
        cur = {"$": "USD", "Rs": "PKR", "Rs.": "PKR", "PKR": "PKR",
               "€": "EUR", "£": "GBP"}.get(m.group("cur"), "USD")
        try:
            price = float(m.group("num").replace(",", ""))
        except ValueError:
            continue
        # specs: following short lines until a blank/long break
        specs = []
        for j in range(i + 1, min(i + 6, len(lines))):
            nxt = lines[j]
            if PRICE_RE.search(nxt) or len(nxt) > 120:
                break
            if 3 < len(nxt) < 120:
                specs.append(nxt)
        stock = -1
        blob = " ".join(lines[i:i + 6]).lower()
        if "out of stock" in blob or "sold out" in blob:
            stock = 0
        elif m2 := re.search(r"(\d+)\s+in stock", blob):
            stock = int(m2.group(1))
        products.append({"name": name, "price": price, "currency": cur,
                         "specs": specs[:6], "stock": stock, "url": url,
                         "source_page": title})
    # dedupe by name
    seen, out = set(), []
    for p in products:
        if p["name"].lower() not in seen:
            seen.add(p["name"].lower())
            out.append(p)
    return out


def extract_faqs(title, text):
    faqs = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        is_q = (line.endswith("?") and 10 < len(line) < 200) or \
               re.match(r"^(Q:|FAQ:?)\s*.+", line, re.I)
        if is_q:
            q = re.sub(r"^(Q:|FAQ:?)\s*", "", line, flags=re.I)
            a_parts = []
            for j in range(i + 1, min(i + 5, len(lines))):
                nxt = lines[j]
                if nxt.endswith("?") or re.match(r"^(Q:|FAQ:?)\s*", nxt, re.I):
                    break
                a_parts.append(re.sub(r"^(A:)\s*", "", nxt, flags=re.I))
            a = " ".join(a_parts).strip()
            if a:
                faqs.append({"q": q, "a": a[:800]})
        i += 1
    return faqs


def extract_policies(title, text):
    policies = []
    low_title = title.lower()
    for ptype, keywords in POLICY_KEYWORDS.items():
        if ptype in low_title or "policy" in low_title:
            hit = any(k in text.lower() for k in keywords)
            if hit:
                # grab the most relevant paragraph block
                paras = [p for p in text.split("\n\n") if len(p) > 60]
                best = max(paras, key=lambda p: sum(k in p.lower() for k in keywords),
                           default="")
                if best:
                    policies.append({"type": ptype, "text": best[:1200]})
                break
    return policies


def extract_page(title, text, url):
    return {
        "products": extract_products(title, text, url),
        "faqs": extract_faqs(title, text),
        "policies": extract_policies(title, text),
    }
