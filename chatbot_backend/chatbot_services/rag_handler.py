# chatbot_services/rag_handler.py

import os
from typing import Dict, Any
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

# --- Performance Fix: Initialize these globally once ---
PERSIST_DIRECTORY = "./chroma_db"
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = None

def _initialize_vectorstore():
    """Initializes the vectorstore if it hasn't been already."""
    global vectorstore
    if vectorstore is None and os.path.exists(PERSIST_DIRECTORY):
        vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings
        )

def get_rag(query: str, k: int = 3) -> Dict[str, Any]:
    """
    Retrieve the most relevant chunks from the vector DB for the given query.
    
    Args:
        query (str): The user's question.
        k (int): Number of top matching chunks to return.

    Returns:
        Dict: {"content": str, "score": float} or empty dict if no matches.
    """
    _initialize_vectorstore()

    if vectorstore is None:
        return {"content": "No knowledge base found. Please run data ingestion.", "score": 0.0}

    docs_with_scores = vectorstore.similarity_search_with_score(query, k=k)

    if not docs_with_scores:
        return {"content": "No relevant context found.", "score": 0.0}
    
    highest_score = 1 - docs_with_scores[0][1]

    context_content = "\n\n".join([doc.page_content for doc, _ in docs_with_scores])

    return {
        "content": context_content,
        "score": highest_score
    }