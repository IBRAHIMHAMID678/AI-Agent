"""Tenant-aware ReAct operator agent.

Uses LangChain chat models (Ollama by default, Groq optional) with a manual
ReAct loop — the model emits TOOL: {...} lines or a final ANSWER:. Every tool
call is executed, logged to the actions log, and fed back as an observation.

Env:
  LLM_PROVIDER=ollama|groq   (default ollama)
  LLM_MODEL                  (default qwen2.5:7b for ollama, llama-3.3-70b-versatile for groq)
  GROQ_API_KEY               (required when LLM_PROVIDER=groq)
  OLLAMA_BASE_URL            (default http://localhost:11434)
  AGENT_MAX_STEPS            (default 6)
"""
import json
import os
import re

import storage
from agent.prompts import SYSTEM_PROMPT
from agent.tools import run_tool, tool_spec_block

MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
        )
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=os.getenv("LLM_MODEL", "qwen2.5:7b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.2,
    )


TOOL_RE = re.compile(r"^TOOL:\s*(\{.*\})\s*$", re.DOTALL)


def _parse_tool_call(text):
    for line in text.strip().splitlines():
        m = TOOL_RE.match(line.strip())
        if m:
            try:
                call = json.loads(m.group(1))
                if "name" in call:
                    return call["name"], call.get("args", {})
            except json.JSONDecodeError:
                continue
    return None


def _strip_answer(text):
    text = text.strip()
    if text.upper().startswith("ANSWER:"):
        text = text[len("ANSWER:"):].strip()
    # drop any leaked TOOL: lines
    lines = [l for l in text.splitlines() if not l.strip().startswith("TOOL:")]
    return "\n".join(lines).strip()


def chat(tenant_id, session_id, message, page_url="", page_title=""):
    """Run one operator turn. Returns dict(reply, sources, tools_used)."""
    tenant = storage.get_tenant(tenant_id)
    if not tenant:
        return {"reply": "This chat isn't configured yet.",
                "sources": [], "tools_used": []}

    conv = storage.get_or_create_conversation(tenant_id, session_id,
                                              page_url, page_title)
    storage.add_message(conv["id"], "user", message)

    spec_block, _ = tool_spec_block(tenant_id)
    system = SYSTEM_PROMPT.format(
        business_name=tenant["name"],
        page_title=page_title or "(unknown page)",
        page_url=page_url or "(unknown url)",
        custom_tools_summary="(none configured)" if "custom" not in spec_block
        else "see tool list below",
        max_steps=MAX_STEPS,
    )
    tool_prompt = ("TOOLS:\n" + spec_block +
                   "\n\nTo use a tool, output EXACTLY one line like:\n"
                   'TOOL: {"name": "search_products", "args": {"query": "laptop"}}\n'
                   "Then wait for the result. When finished, output:\n"
                   "ANSWER: <reply>")

    history = storage.conversation_history(conv["id"], limit=12)
    transcript = "\n".join(
        f"{'Visitor' if h['role'] == 'user' else 'Agent'}: {h['content']}"
        for h in history[:-1])  # current message appended below

    llm = get_llm()
    messages = [
        {"role": "system", "content": system + "\n\n" + tool_prompt},
    ]
    if transcript:
        messages.append({"role": "user",
                         "content": f"[earlier in this chat]\n{transcript}"})
    user_turn = f"[visitor is on: {page_title} ({page_url})]\n{message}"
    messages.append({"role": "user", "content": user_turn})

    tools_used = []
    sources = []
    reply = ""
    unanswered_logged = False

    for _ in range(MAX_STEPS + 1):
        resp = llm.invoke(messages)
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
        call = _parse_tool_call(text)
        if not call:
            reply = _strip_answer(text)
            break
        name, args = call
        if not isinstance(args, dict):
            args = {}
        messages.append({"role": "assistant", "content": text})
        observation = run_tool(tenant_id, name, args, conversation_id=conv["id"])
        tools_used.append({"name": name, "params": args,
                           "result_summary": observation[:300]})
        if "search_knowledge_base" in name or "search_products" in name:
            pass  # sources extracted below from collection hits if needed
        messages.append({"role": "user",
                         "content": f"[tool result]\n{observation}\n"
                                    "Continue: call another tool if needed, else ANSWER."})
    else:
        reply = _strip_answer(text)

    if not reply:
        reply = "I couldn't work that out — could you rephrase it?"

    # Learning loop: honest "don't know" -> unanswered inbox
    low = reply.lower()
    if any(p in low for p in ("don't know", "do not know", "no information",
                              "couldn't find", "not sure")):
        storage.log_unanswered(tenant_id, message, page_url)
        storage.mark_unresolved(conv["id"])
        unanswered_logged = True

    storage.add_message(conv["id"], "assistant", reply)
    return {"reply": reply, "sources": sources, "tools_used": tools_used,
            "unanswered_logged": unanswered_logged}
