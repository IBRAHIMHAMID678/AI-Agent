"""Indexing pipeline: chunk text -> embed -> per-tenant Chroma collection.

Re-crawling a tenant replaces its collection. Structured extracts (products)
go to SQLite via storage.upsert_products; raw text goes to Chroma.
"""
import os
import re

import storage

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def _collection_name(tenant_id):
    return "tenant_" + re.sub(r"[^a-zA-Z0-9_]", "_", tenant_id)


def _embeddings():
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )


def get_collection(tenant_id):
    from langchain_chroma import Chroma
    return Chroma(
        collection_name=_collection_name(tenant_id),
        embedding_function=_embeddings(),
        persist_directory=CHROMA_DIR,
    )


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        if end < len(text):
            # break on a paragraph/sentence boundary when possible
            cut = text.rfind("\n\n", start, end)
            if cut == -1:
                cut = text.rfind(". ", start, end)
            if cut > start + size // 3:
                end = cut + 1
        chunks.append(text[start:end].strip())
        start = max(end - overlap, start + 1)
    return [c for c in chunks if len(c) > 40]


def reset_collection(tenant_id):
    from langchain_chroma import Chroma
    Chroma(
        collection_name=_collection_name(tenant_id),
        embedding_function=_embeddings(),
        persist_directory=CHROMA_DIR,
    ).delete_collection()


def index_texts(tenant_id, docs):
    """docs: list of {title, url, text}. Appends to the tenant collection."""
    from langchain_chroma import Chroma
    texts, metas = [], []
    for d in docs:
        for i, chunk in enumerate(chunk_text(d["text"])):
            texts.append(chunk)
            metas.append({"title": d.get("title", ""), "url": d.get("url", ""),
                          "chunk": i})
    if not texts:
        return 0
    Chroma.from_texts(
        texts=texts,
        embedding=_embeddings(),
        metadatas=metas,
        collection_name=_collection_name(tenant_id),
        persist_directory=CHROMA_DIR,
    )
    return len(texts)


def search_collection(tenant_id, query, k=4):
    try:
        coll = get_collection(tenant_id)
        docs = coll.similarity_search(query, k=k)
    except Exception:
        return []
    return [{"title": d.metadata.get("title", ""),
             "url": d.metadata.get("url", ""),
             "text": d.page_content} for d in docs]


def ingest_pages(tenant_id, pages, replace=True):
    """Full pipeline for crawled pages: extract structured data, index text.

    pages: [{url, title, text}]. Returns {pages, chunks, products_found}.
    """
    from ingest.extract import extract_page
    if replace:
        try:
            reset_collection(tenant_id)
        except Exception:
            pass
    chunks = index_texts(tenant_id, pages)
    n_products = 0
    for p in pages:
        extracted = extract_page(p["title"], p["text"], p["url"])
        storage.save_page(tenant_id, p["url"], p["title"], p["text"][:20000],
                          extracted)
        if extracted["products"]:
            storage.upsert_products(tenant_id, extracted["products"])
            n_products += len(extracted["products"])
    return {"pages": len(pages), "chunks": chunks, "products_found": n_products}


def ingest_answer(tenant_id, question, answer):
    """Learning loop: owner-answered question -> knowledge base."""
    doc = {"title": f"Owner answer: {question[:80]}",
           "url": "",
           "text": f"Question: {question}\nAnswer: {answer}"}
    return index_texts(tenant_id, [doc])
