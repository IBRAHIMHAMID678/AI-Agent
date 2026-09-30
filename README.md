# AI-Agent — conversational AI backend with tools

A FastAPI backend that exposes a **LangChain ReAct agent** as a chat API.
Send it a message; the agent reasons step-by-step, calls tools when needed,
and replies.

## What it does

- `POST /chat` with `{"user_input": "..."}` → the agent
  (`handle_user_query` in `chatbot_services/main_service.py`) responds with
  `{"response": "..."}`.
- The agent uses the ReAct prompt (`hwchase17/react`) on
  **Ollama `qwen2:0.5b-instruct-q4_0`**, with a system rule: questions about
  people, names, employees, documents, or records **must** go through the
  RAG tool — never answered from memory.
- **Two tools** (`chatbot_services/tools.py`):
  - `get_weather` — current weather for any city via the free Open-Meteo
    API (geocoding + forecast, no API key). Results are cached in memory
    for 5 minutes.
  - `search_documents_with_rag` — answers questions about the employee
    records in `data/Employees.json` using a Chroma vector store
    (`nomic-embed-text` embeddings) with a `RetrievalQA` chain, returning
    the answer plus source documents.
- `GET /` — health check (`{"status": "ok", ...}`).
- Also runs as a **terminal chatbot**: `python chatbot_services/main_service.py`
  (type `quit` to exit).

> **Note:** this repo is backend-only — there is no frontend/UI code here.
> An earlier version of this README mentioned a Next.js frontend; that was
> inaccurate and has been removed.

## Setup

**Prerequisites:** [Ollama](https://ollama.com) running locally with the
models pulled:

```bash
ollama pull qwen2:0.5b-instruct-q4_0
ollama pull nomic-embed-text
```

```bash
cd chatbot_backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
# requirements.txt is missing two packages the code imports:
.venv/bin/pip install langchain-ollama langchain-chroma

# 1. Build the knowledge base (reads data/*.json -> ./chroma_db)
.venv/bin/python ingest_data.py

# 2. Start the API
.venv/bin/uvicorn app:app --reload   # http://localhost:8000
```

(The `if __name__ == "__main__"` block in `app.py` references module
`main:app`; run with `uvicorn app:app` as above.)

**Try it:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_input": "What is the weather in Lahore?"}'
# -> {"response": "..."}
```

## Project layout

```
chatbot_backend/
├── app.py                  # FastAPI app: GET / health, POST /chat
├── ingest_data.py          # builds ./chroma_db from data/*.json
├── requirements.txt
├── data/
│   └── Employees.json      # employee records (id, name, role, department)
└── chatbot_services/
    ├── main_service.py     # ReAct agent + handle_user_query (+ CLI mode)
    ├── tools.py            # get_weather, search_documents_with_rag
    ├── rag_handler.py      # Chroma vectorstore + RetrievalQA chain
    └── api_handlers.py     # Open-Meteo weather calls (5-min cache)
```

## Notes

- `requirements.txt` does not pin versions and omits `langchain-ollama`
  / `langchain-chroma` (both imported) — install them as shown above.
- `venv/`-style directories and `chroma_db/` are currently committed to
  this repo, which makes it very large. A `.gitignore` is now included;
  removing the committed environments from git history is recommended.
