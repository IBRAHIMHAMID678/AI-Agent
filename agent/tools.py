"""Tool definitions for the website operator agent.

Built-in tools operate on the tenant's crawled data (products, knowledge base).
Custom tools are owner-defined webhooks: the agent POSTs {"tool", "params"} as JSON
to the owner's URL and reports the returned {"result"} back in chat.
"""
import json
import time

import httpx

import storage
from ingest.pipeline import search_collection


def _fmt_price(p):
    if p.get("price") is None:
        return "price on request"
    cur = {"USD": "$", "PKR": "Rs ", "EUR": "€"}.get(p.get("currency", "USD"),
                                                    p.get("currency", "USD") + " ")
    v = p["price"]
    v = int(v) if float(v).is_integer() else v
    return f"{cur}{v}"


def _fmt_product(p):
    line = f"- **{p['name']}** — {_fmt_price(p)}"
    stock = p.get("stock", -1)
    if stock == 0:
        line += " (out of stock)"
    elif stock > 0:
        line += f" ({stock} in stock)"
    specs = p.get("specs") or []
    if specs:
        line += "\n  " + ", ".join(specs[:6])
    return line


# ------------------------------------------------------------- built-ins ---
def search_products(tenant_id, query="", max_price=None, in_stock_only=False):
    """Search the business's product catalog."""
    results = storage.search_products(tenant_id, query=query,
                                      max_price=max_price,
                                      in_stock_only=in_stock_only)
    if not results:
        return "No products matched."
    return "\n".join(_fmt_product(p) for p in results[:10])


def compare_products(tenant_id, names):
    """Compare 2-4 products side by side. names: list of product names."""
    catalog = storage.list_products(tenant_id)
    picked = []
    for n in names[:4]:
        n_low = n.lower()
        match = next((p for p in catalog if n_low in p["name"].lower()), None)
        if match:
            picked.append(match)
    if len(picked) < 2:
        return ("Could not find at least two of those products. "
                "Available: " + ", ".join(p["name"] for p in catalog[:12]))
    lines = []
    for p in picked:
        specs = "; ".join((p.get("specs") or [])[:6])
        stock = p.get("stock", -1)
        stock_s = "out of stock" if stock == 0 else (f"{stock} in stock" if stock > 0 else "stock unknown")
        lines.append(f"- **{p['name']}**: {_fmt_price(p)}, {stock_s}"
                     + (f" — {specs}" if specs else ""))
    return "Comparison:\n" + "\n".join(lines)


def check_stock(tenant_id, product_name):
    """Check stock for one product."""
    results = storage.search_products(tenant_id, query=product_name)
    if not results:
        return f"No product found matching '{product_name}'."
    p = results[0]
    stock = p.get("stock", -1)
    if stock == 0:
        return f"{p['name']} is currently out of stock."
    if stock > 0:
        return f"{p['name']} — {stock} units in stock at {_fmt_price(p)}."
    return f"{p['name']} — stock level unknown, priced at {_fmt_price(p)}."


def search_knowledge_base(tenant_id, query):
    """Search site docs, FAQs, policies (shipping, returns, warranty...)."""
    hits = search_collection(tenant_id, query, k=4)
    if not hits:
        return "NO_RESULTS"
    return "\n\n".join(f"[{h['title']}]({h['url']}): {h['text'][:600]}"
                       for h in hits)


BUILTIN_TOOLS = {
    "search_products": {
        "fn": search_products,
        "description": "Search the product catalog by keyword, with optional max_price and in_stock_only filters.",
        "params": {"query": "keyword (string)", "max_price": "number, optional",
                   "in_stock_only": "boolean, optional"},
    },
    "compare_products": {
        "fn": compare_products,
        "description": "Compare 2-4 products side by side by name (price, specs, stock).",
        "params": {"names": "array of product name strings"},
    },
    "check_stock": {
        "fn": check_stock,
        "description": "Check stock level for a single product by name.",
        "params": {"product_name": "string"},
    },
    "search_knowledge_base": {
        "fn": search_knowledge_base,
        "description": "Search website docs/FAQs/policies (shipping, returns, warranty, how-tos).",
        "params": {"query": "string"},
    },
}


# ----------------------------------------------------------- custom webhook -
def call_custom_tool(tool, params, timeout=20):
    """POST {"tool", "params"} to the owner's webhook URL. Returns result text."""
    payload = {"tool": tool["name"], "params": params}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(tool["webhook_url"], json=payload)
        r.raise_for_status()
        try:
            data = r.json()
        except Exception:
            return r.text[:2000]
    if isinstance(data, dict) and "result" in data:
        return str(data["result"])[:2000]
    return json.dumps(data)[:2000]


def tool_spec_block(tenant_id):
    """Render the tool catalog for the system prompt + return dispatch table."""
    specs = []
    dispatch = {}
    for name, t in BUILTIN_TOOLS.items():
        specs.append(f"- {name}{json.dumps(t['params'])}: {t['description']}")
        dispatch[name] = ("builtin", t["fn"])
    for tool in storage.list_tools(tenant_id, enabled_only=True):
        schema = tool.get("params_schema") or {}
        specs.append(f"- {tool['name']}{json.dumps(schema)}: {tool['description']}")
        dispatch[tool["name"]] = ("custom", tool)
    return "\n".join(specs), dispatch


def run_tool(tenant_id, name, args, conversation_id=""):
    """Execute a tool by name, log it to the actions log, return observation."""
    _, dispatch = tool_spec_block(tenant_id)
    if name not in dispatch:
        return f"ERROR: unknown tool '{name}'."
    kind, target = dispatch[name]
    start = time.time()
    try:
        if kind == "builtin":
            result = target(tenant_id, **args)
        else:
            result = call_custom_tool(target, args)
        ok = True
    except Exception as e:
        result = f"ERROR calling {name}: {e}"
        ok = False
    duration_ms = int((time.time() - start) * 1000)
    storage.log_tool_call(tenant_id, name, args, result,
                          conversation_id=conversation_id,
                          duration_ms=duration_ms)
    status = "ok" if ok else "failed"
    return f"[{name} {status}, {duration_ms}ms] {result}"
