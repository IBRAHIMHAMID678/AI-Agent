"""AI-Agent — website operator agent API.

One script tag embeds the widget on any site. The agent knows the site's data
(crawled into a per-tenant vector index + structured product catalog) and ACTS
on it via built-in tools and owner-defined webhook tools.

Run:  uvicorn app:app --reload        (Ollama running locally for LLM+embeddings)
Docs: README.md
"""
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import storage
from agent.agent import chat as agent_chat

BASE_DIR = Path(__file__).parent
storage.init_db()

app = FastAPI(title="AI-Agent — Website Operator", version="2.0.0")


# ------------------------------------------------------------------ models --
class TenantIn(BaseModel):
    name: str
    website: str = ""
    brand_color: str = "#4f46e5"
    welcome_message: str = ""
    trigger_config: dict = Field(default_factory=dict)


class IngestIn(BaseModel):
    website_url: str


class ChatIn(BaseModel):
    tenant_id: str
    session_id: str
    message: str
    page_url: str = ""
    page_title: str = ""


class ToolIn(BaseModel):
    name: str
    description: str = ""
    params_schema: dict = Field(default_factory=dict)
    webhook_url: str = ""
    enabled: bool = True


class AnswerIn(BaseModel):
    answer: str


# ------------------------------------------------------------------- health -
@app.get("/")
def health():
    return {"status": "ok", "service": "ai-agent website operator",
            "tenants": len(storage.list_tenants())}


# ------------------------------------------------------------------ tenants -
@app.get("/api/tenants")
def api_list_tenants():
    return storage.list_tenants()


@app.post("/api/tenants")
def api_create_tenant(t: TenantIn):
    return storage.create_tenant(t.name, t.website, t.brand_color,
                                 t.welcome_message, t.trigger_config)


@app.get("/api/tenants/{tid}")
def api_get_tenant(tid: str):
    t = storage.get_tenant(tid)
    if not t:
        raise HTTPException(404, "tenant not found")
    return t


@app.put("/api/tenants/{tid}")
def api_update_tenant(tid: str, t: TenantIn):
    if not storage.get_tenant(tid):
        raise HTTPException(404, "tenant not found")
    return storage.update_tenant(tid, name=t.name, website=t.website,
                                 brand_color=t.brand_color,
                                 welcome_message=t.welcome_message,
                                 trigger_config=t.trigger_config)


@app.delete("/api/tenants/{tid}")
def api_delete_tenant(tid: str):
    storage.delete_tenant(tid)
    return {"ok": True}


@app.get("/api/tenants/{tid}/widget-config")
def api_widget_config(tid: str):
    """Public config for the embed widget (no secrets)."""
    t = storage.get_tenant(tid)
    if not t:
        raise HTTPException(404, "tenant not found")
    trig = t.get("trigger_config") or {}
    return {
        "business_name": t["name"],
        "brand_color": t["brand_color"],
        "welcome_message": t["welcome_message"]
        or f"Hi! I'm {t['name']}'s assistant — ask me anything.",
        "trigger": {
            "enabled": bool(trig.get("enabled")),
            "pages": trig.get("pages", []),
            "delay_sec": trig.get("delay_sec", 25),
            "message": trig.get("message", "Need a hand? I can help."),
        },
    }


# ------------------------------------------------------------------ ingest -
@app.post("/api/tenants/{tid}/ingest")
def api_ingest(tid: str, body: IngestIn):
    if not storage.get_tenant(tid):
        raise HTTPException(404, "tenant not found")
    from ingest.crawler import crawl_site
    from ingest.pipeline import ingest_pages
    pages = crawl_site(body.website_url)
    stats = ingest_pages(tid, pages, replace=True)
    return stats


@app.post("/api/tenants/{tid}/upload")
async def api_upload(tid: str, files: list[UploadFile] = File(...)):
    if not storage.get_tenant(tid):
        raise HTTPException(404, "tenant not found")
    from ingest.loaders import load_upload
    from ingest.pipeline import index_texts
    docs, n = [], 0
    for f in files:
        try:
            docs.append(load_upload(f, BASE_DIR / "data" / "uploads" / tid))
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
    n = index_texts(tid, [{"title": d["title"], "url": "", "text": d["text"]}
                          for d in docs])
    return {"files_indexed": len(docs), "chunks": n}


@app.get("/api/tenants/{tid}/pages")
def api_pages(tid: str):
    if not storage.get_tenant(tid):
        raise HTTPException(404, "tenant not found")
    return storage.list_pages(tid)


# ------------------------------------------------------------ custom tools --
@app.get("/api/tenants/{tid}/tools")
def api_list_tools(tid: str):
    return storage.list_tools(tid)


@app.post("/api/tenants/{tid}/tools")
def api_create_tool(tid: str, t: ToolIn):
    if not storage.get_tenant(tid):
        raise HTTPException(404, "tenant not found")
    return storage.create_tool(tid, t.name, t.description, t.params_schema,
                               t.webhook_url, t.enabled)


@app.put("/api/tenants/{tid}/tools/{tool_id}")
def api_update_tool(tid: str, tool_id: str, t: ToolIn):
    tool = storage.update_tool(tool_id, name=t.name, description=t.description,
                               params_schema=t.params_schema,
                               webhook_url=t.webhook_url, enabled=t.enabled)
    if not tool:
        raise HTTPException(404, "tool not found")
    return tool


@app.delete("/api/tenants/{tid}/tools/{tool_id}")
def api_delete_tool(tid: str, tool_id: str):
    storage.delete_tool(tool_id)
    return {"ok": True}


# -------------------------------------------------------------- actions log -
@app.get("/api/tenants/{tid}/actions")
def api_actions(tid: str, limit: int = 50):
    return storage.list_tool_calls(tid, limit=limit)


# -------------------------------------------------------------------- chat --
def _suggested_replies(tid):
    products = storage.list_products(tid)
    if products:
        return ["Show me your catalog", "Track my order", "Shipping & returns info"]
    return ["What do you offer?", "Shipping info", "Talk to support"]


@app.post("/api/chat")
def api_chat(body: ChatIn):
    if not storage.get_tenant(body.tenant_id):
        raise HTTPException(404, "tenant not found")
    result = agent_chat(body.tenant_id, body.session_id, body.message,
                        body.page_url, body.page_title)
    result["suggested_replies"] = _suggested_replies(body.tenant_id)
    return result


# -------------------------------------------------------------- unanswered --
@app.get("/api/tenants/{tid}/unanswered")
def api_unanswered(tid: str):
    return storage.list_unanswered(tid)


@app.post("/api/tenants/{tid}/unanswered/{qid}/answer")
def api_answer_unanswered(tid: str, qid: str, body: AnswerIn):
    rec = storage.answer_unanswered(qid, body.answer)
    if not rec:
        raise HTTPException(404, "question not found")
    from ingest.pipeline import ingest_answer
    ingest_answer(tid, rec["question"], body.answer)
    return {"ok": True}


# --------------------------------------------------------------- analytics --
@app.get("/api/tenants/{tid}/analytics")
def api_analytics(tid: str):
    stats = storage.conversation_stats(tid)
    return {
        "top_questions": storage.top_questions(tid),
        "tool_calls": storage.tool_call_counts(tid),
        "unanswered_count": storage.unanswered_count(tid),
        **stats,
    }


# ------------------------------------------------------- demo order webhook -
# Demo target for the seeded `check_order_status` webhook tool. In production
# the owner points their tools at their OWN order system / helpdesk / CRM.
DEMO_ORDERS = {
    "TZ-1042": "Shipped via TCS on Sep 28 — arriving Thursday. Tracking: TCS88210042.",
    "TZ-1043": "Packed, ships tomorrow morning.",
    "TZ-1044": "Delivered Sep 25. Signed by recipient.",
}


@app.post("/api/demo/order-status")
async def api_demo_order_status(request: Request):
    body = await request.json()
    params = body.get("params", {})
    order_id = str(params.get("order_id", "")).upper().strip()
    if order_id in DEMO_ORDERS:
        return {"result": f"Order {order_id}: {DEMO_ORDERS[order_id]}"}
    return {"result": f"No order found for '{order_id}'. Orders look like TZ-1042."}


@app.post("/api/tenants/{tid}/seed-demo")
def api_seed_demo(tid: str, request: Request):
    """Seed the TechZone demo catalog + order-status webhook tool."""
    from seed_data import TECHZONE_PRODUCTS
    if not storage.get_tenant(tid):
        raise HTTPException(404, "tenant not found")
    storage.upsert_products(tid, TECHZONE_PRODUCTS)
    base = str(request.base_url).rstrip("/")
    for tool in storage.list_tools(tid):
        if tool["name"] == "check_order_status":
            storage.delete_tool(tool["id"])
    storage.create_tool(
        tid, "check_order_status",
        "Look up a TechZone order by ID (e.g. TZ-1042): status + tracking.",
        {"order_id": "order ID string, e.g. TZ-1042"},
        f"{base}/api/demo/order-status", True)
    return {"ok": True, "products": len(TECHZONE_PRODUCTS)}


# ------------------------------------------------------------- static bits -
@app.get("/widget.js")
def widget_js():
    return FileResponse(BASE_DIR / "widget" / "widget.js",
                        media_type="application/javascript")


@app.get("/widget.css")
def widget_css():
    return FileResponse(BASE_DIR / "widget" / "widget.css",
                        media_type="text/css")


@app.get("/admin")
def admin_page():
    return FileResponse(BASE_DIR / "admin" / "index.html", media_type="text/html")


@app.get("/demo")
def demo_page():
    return FileResponse(BASE_DIR / "demo" / "index.html", media_type="text/html")


@app.get("/demo/{path:path}")
def demo_static(path: str):
    f = BASE_DIR / "demo" / path
    if f.is_file():
        return FileResponse(f)
    raise HTTPException(404, "not found")
