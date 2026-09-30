"""SQLite storage layer for the AI-Agent website operator platform.

Tables:
  tenants        — one row per business using the widget
  custom_tools   — owner-defined webhook tools per tenant
  tool_calls     — actions log: every tool call the agent made
  products       — structured product catalog extracted per tenant
  pages          — crawled pages + structured extracts (products/faqs/policies)
  conversations  — chat sessions (page-aware)
  messages       — chat history
  unanswered     — learning-loop inbox: questions the agent couldn't answer
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "app.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            website TEXT DEFAULT '',
            brand_color TEXT DEFAULT '#4f46e5',
            welcome_message TEXT DEFAULT '',
            trigger_config TEXT DEFAULT '{}',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS custom_tools (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            params_schema TEXT DEFAULT '{}',
            webhook_url TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at REAL NOT NULL,
            UNIQUE(tenant_id, name)
        );
        CREATE TABLE IF NOT EXISTS tool_calls (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            conversation_id TEXT DEFAULT '',
            tool_name TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            result TEXT DEFAULT '',
            duration_ms INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL,
            currency TEXT DEFAULT 'USD',
            specs TEXT DEFAULT '[]',
            stock INTEGER DEFAULT -1,
            url TEXT DEFAULT '',
            source_page TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS pages (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT DEFAULT '',
            text_content TEXT DEFAULT '',
            extracted TEXT DEFAULT '{}',
            crawled_at REAL NOT NULL,
            UNIQUE(tenant_id, url)
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            page_url TEXT DEFAULT '',
            page_title TEXT DEFAULT '',
            resolved INTEGER DEFAULT 1,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS unanswered (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            question TEXT NOT NULL,
            page_url TEXT DEFAULT '',
            count INTEGER DEFAULT 1,
            answered INTEGER DEFAULT 0,
            answer_text TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        """)
    return True


def _row_to_dict(r):
    return dict(r) if r else None


# ---------------------------------------------------------------- tenants ---
def create_tenant(name, website="", brand_color="#4f46e5", welcome_message="",
                  trigger_config=None):
    tid = "tnt_" + uuid.uuid4().hex[:10]
    with _conn() as c:
        c.execute(
            "INSERT INTO tenants (id, name, website, brand_color, welcome_message,"
            " trigger_config, created_at) VALUES (?,?,?,?,?,?,?)",
            (tid, name, website, brand_color, welcome_message,
             json.dumps(trigger_config or {}), time.time()))
    return get_tenant(tid)


def get_tenant(tid):
    with _conn() as c:
        r = c.execute("SELECT * FROM tenants WHERE id=?", (tid,)).fetchone()
    d = _row_to_dict(r)
    if d:
        d["trigger_config"] = json.loads(d["trigger_config"] or "{}")
    return d


def list_tenants():
    with _conn() as c:
        rows = c.execute("SELECT * FROM tenants ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["trigger_config"] = json.loads(d["trigger_config"] or "{}")
        out.append(d)
    return out


def update_tenant(tid, **fields):
    allowed = {"name", "website", "brand_color", "welcome_message", "trigger_config"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(json.dumps(v) if k == "trigger_config" else v)
    if not sets:
        return get_tenant(tid)
    vals.append(tid)
    with _conn() as c:
        c.execute(f"UPDATE tenants SET {', '.join(sets)} WHERE id=?", vals)
    return get_tenant(tid)


def delete_tenant(tid):
    with _conn() as c:
        for t in ("custom_tools", "tool_calls", "products", "pages",
                  "conversations", "messages", "unanswered"):
            c.execute(f"DELETE FROM {t} WHERE tenant_id=?", (tid,))
        c.execute("DELETE FROM tenants WHERE id=?", (tid,))
    return True


# ------------------------------------------------------------ custom tools --
def create_tool(tenant_id, name, description="", params_schema=None,
                webhook_url="", enabled=True):
    tool_id = "tool_" + uuid.uuid4().hex[:10]
    with _conn() as c:
        c.execute(
            "INSERT INTO custom_tools (id, tenant_id, name, description,"
            " params_schema, webhook_url, enabled, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (tool_id, tenant_id, name, description,
             json.dumps(params_schema or {}), webhook_url,
             1 if enabled else 0, time.time()))
    return get_tool(tool_id)


def get_tool(tool_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM custom_tools WHERE id=?", (tool_id,)).fetchone()
    d = _row_to_dict(r)
    if d:
        d["params_schema"] = json.loads(d["params_schema"] or "{}")
        d["enabled"] = bool(d["enabled"])
    return d


def list_tools(tenant_id, enabled_only=False):
    q = "SELECT * FROM custom_tools WHERE tenant_id=?"
    if enabled_only:
        q += " AND enabled=1"
    q += " ORDER BY created_at"
    with _conn() as c:
        rows = c.execute(q, (tenant_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["params_schema"] = json.loads(d["params_schema"] or "{}")
        d["enabled"] = bool(d["enabled"])
        out.append(d)
    return out


def update_tool(tool_id, **fields):
    allowed = {"name", "description", "params_schema", "webhook_url", "enabled"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            if k == "params_schema":
                v = json.dumps(v)
            if k == "enabled":
                v = 1 if v else 0
            vals.append(v)
    if sets:
        vals.append(tool_id)
        with _conn() as c:
            c.execute(f"UPDATE custom_tools SET {', '.join(sets)} WHERE id=?", vals)
    return get_tool(tool_id)


def delete_tool(tool_id):
    with _conn() as c:
        c.execute("DELETE FROM custom_tools WHERE id=?", (tool_id,))
    return True


# -------------------------------------------------------------- actions log -
def log_tool_call(tenant_id, tool_name, params, result, conversation_id="",
                  duration_ms=0):
    cid = "tc_" + uuid.uuid4().hex[:10]
    with _conn() as c:
        c.execute(
            "INSERT INTO tool_calls (id, tenant_id, conversation_id, tool_name,"
            " params, result, duration_ms, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (cid, tenant_id, conversation_id, tool_name, json.dumps(params),
             str(result)[:4000], duration_ms, time.time()))
    return cid


def list_tool_calls(tenant_id, limit=50):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM tool_calls WHERE tenant_id=? ORDER BY created_at DESC"
            " LIMIT ?", (tenant_id, limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["params"] = json.loads(d["params"] or "{}")
        out.append(d)
    return out


def tool_call_counts(tenant_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT tool_name, COUNT(*) AS n FROM tool_calls WHERE tenant_id=?"
            " GROUP BY tool_name ORDER BY n DESC", (tenant_id,)).fetchall()
    return [{"tool_name": r["tool_name"], "count": r["n"]} for r in rows]


# ---------------------------------------------------------------- products --
def upsert_products(tenant_id, products):
    """products: list of dicts {name, price, currency, specs, stock, url, source_page}"""
    with _conn() as c:
        for p in products:
            existing = c.execute(
                "SELECT id FROM products WHERE tenant_id=? AND name=?",
                (tenant_id, p.get("name", ""))).fetchone()
            specs = json.dumps(p.get("specs", []))
            if existing:
                c.execute(
                    "UPDATE products SET price=?, currency=?, specs=?, stock=?,"
                    " url=?, source_page=? WHERE id=?",
                    (p.get("price"), p.get("currency", "USD"), specs,
                     p.get("stock", -1), p.get("url", ""),
                     p.get("source_page", ""), existing["id"]))
            else:
                c.execute(
                    "INSERT INTO products (id, tenant_id, name, price, currency,"
                    " specs, stock, url, source_page) VALUES (?,?,?,?,?,?,?,?,?)",
                    ("prd_" + uuid.uuid4().hex[:10], tenant_id, p.get("name", ""),
                     p.get("price"), p.get("currency", "USD"), specs,
                     p.get("stock", -1), p.get("url", ""),
                     p.get("source_page", "")))


def list_products(tenant_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM products WHERE tenant_id=? ORDER BY name",
            (tenant_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["specs"] = json.loads(d["specs"] or "[]")
        out.append(d)
    return out


def search_products(tenant_id, query="", max_price=None, in_stock_only=False):
    q = "SELECT * FROM products WHERE tenant_id=?"
    vals = [tenant_id]
    if query:
        q += " AND (name LIKE ? OR specs LIKE ?)"
        vals += [f"%{query}%", f"%{query}%"]
    if max_price is not None:
        q += " AND price IS NOT NULL AND price <= ?"
        vals.append(max_price)
    if in_stock_only:
        q += " AND stock != 0"
    q += " ORDER BY price"
    with _conn() as c:
        rows = c.execute(q, vals).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["specs"] = json.loads(d["specs"] or "[]")
        out.append(d)
    return out


# ------------------------------------------------------------------- pages --
def save_page(tenant_id, url, title, text_content, extracted):
    pid = "pg_" + uuid.uuid4().hex[:10]
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO pages (id, tenant_id, url, title,"
            " text_content, extracted, crawled_at) VALUES (?,?,?,?,?,?,?)",
            (pid, tenant_id, url, title, text_content,
             json.dumps(extracted), time.time()))


def list_pages(tenant_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT url, title, extracted, crawled_at FROM pages WHERE tenant_id=?"
            " ORDER BY crawled_at DESC", (tenant_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["extracted"] = json.loads(d["extracted"] or "{}")
        out.append(d)
    return out


def page_texts(tenant_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT title, text_content FROM pages WHERE tenant_id=?",
            (tenant_id,)).fetchall()
    return [(r["title"], r["text_content"]) for r in rows]


# ----------------------------------------------------------- conversations --
def get_or_create_conversation(tenant_id, session_id, page_url="", page_title=""):
    with _conn() as c:
        r = c.execute(
            "SELECT * FROM conversations WHERE tenant_id=? AND session_id=?"
            " ORDER BY created_at DESC LIMIT 1",
            (tenant_id, session_id)).fetchone()
        if r:
            return dict(r)
        cid = "cnv_" + uuid.uuid4().hex[:10]
        c.execute(
            "INSERT INTO conversations (id, tenant_id, session_id, page_url,"
            " page_title, resolved, created_at) VALUES (?,?,?,?,?,?,?)",
            (cid, tenant_id, session_id, page_url, page_title, 1, time.time()))
        return {"id": cid, "tenant_id": tenant_id, "session_id": session_id,
                "page_url": page_url, "page_title": page_title, "resolved": 1}


def add_message(conversation_id, role, content):
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at)"
            " VALUES (?,?,?,?,?)",
            ("msg_" + uuid.uuid4().hex[:10], conversation_id, role, content,
             time.time()))


def conversation_history(conversation_id, limit=20):
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE conversation_id=?"
            " ORDER BY created_at DESC LIMIT ?", (conversation_id, limit)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def mark_unresolved(conversation_id):
    with _conn() as c:
        c.execute("UPDATE conversations SET resolved=0 WHERE id=?",
                  (conversation_id,))


def conversation_stats(tenant_id):
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE tenant_id=?",
            (tenant_id,)).fetchone()["n"]
        unresolved = c.execute(
            "SELECT COUNT(*) AS n FROM conversations WHERE tenant_id=?"
            " AND resolved=0", (tenant_id,)).fetchone()["n"]
    return {"total_conversations": total, "unresolved_conversations": unresolved}


def top_questions(tenant_id, limit=10):
    with _conn() as c:
        rows = c.execute(
            "SELECT content, COUNT(*) AS n FROM messages"
            " WHERE role='user' AND conversation_id IN"
            " (SELECT id FROM conversations WHERE tenant_id=?)"
            " GROUP BY content ORDER BY n DESC LIMIT ?",
            (tenant_id, limit)).fetchall()
    return [{"question": r["content"][:140], "count": r["n"]} for r in rows]


# --------------------------------------------------------------- unanswered -
def log_unanswered(tenant_id, question, page_url=""):
    norm = " ".join(question.lower().split())
    with _conn() as c:
        r = c.execute(
            "SELECT id, count FROM unanswered WHERE tenant_id=? AND"
            " LOWER(question)=? AND answered=0",
            (tenant_id, norm)).fetchone()
        if r:
            c.execute("UPDATE unanswered SET count=count+1 WHERE id=?",
                      (r["id"],))
            return r["id"]
        uid = "unq_" + uuid.uuid4().hex[:10]
        c.execute(
            "INSERT INTO unanswered (id, tenant_id, question, page_url, count,"
            " answered, created_at) VALUES (?,?,?,?,?,?,?)",
            (uid, tenant_id, question, page_url, 1, 0, time.time()))
        return uid


def list_unanswered(tenant_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM unanswered WHERE tenant_id=? ORDER BY answered,"
            " count DESC", (tenant_id,)).fetchall()
    return [dict(r) for r in rows]


def answer_unanswered(uid, answer_text):
    with _conn() as c:
        c.execute(
            "UPDATE unanswered SET answered=1, answer_text=? WHERE id=?",
            (answer_text, uid))
        r = c.execute("SELECT * FROM unanswered WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None


def unanswered_count(tenant_id):
    with _conn() as c:
        return c.execute(
            "SELECT COUNT(*) AS n FROM unanswered WHERE tenant_id=?"
            " AND answered=0", (tenant_id,)).fetchone()["n"]
