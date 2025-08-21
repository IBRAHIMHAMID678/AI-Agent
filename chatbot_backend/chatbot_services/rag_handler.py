# chatbot_services/rag_handler.py

import os
import logging
import time
from typing import Dict, Any
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PERSIST_DIRECTORY = "./chroma_db"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2:0.5b-instruct-q4_0"  # you can replace with llama3:8b for better results


class RAGHandler:
    def __init__(self):
        self.vectorstore = None
        self.qa_chain = None
        self._initialize()

    def _initialize(self):
        try:
            embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
            if os.path.exists(PERSIST_DIRECTORY):
                self.vectorstore = Chroma(
                    persist_directory=PERSIST_DIRECTORY,
                    embedding_function=embeddings,
                    collection_metadata={"hnsw:space": "l2", "hnsw:M": 8},
                )
                llm = Ollama(model=LLM_MODEL)

                prompt_template = """You are an assistant that answers questions about employee records.
Each record has fields: ID, Name, Role, Department.
Use the context to answer the question as accurately as possible.

Context: {context}

Question: {question}

Answer:"""

                prompt = PromptTemplate(
                    template=prompt_template, input_variables=["context", "question"]
                )

                # ✅ RetrievalQA expects "query" not "question"
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                    chain_type_kwargs={"prompt": prompt},
                    return_source_documents=True,
                )
                logging.info("RAGHandler initialized successfully.")
            else:
                logging.error(f"Vector store directory {PERSIST_DIRECTORY} does not exist.")
                raise FileNotFoundError(f"Vector store directory {PERSIST_DIRECTORY} not found.")
        except Exception as e:
            logging.error(f"Error initializing RAGHandler: {e}")
            raise

    async def search_documents_with_rag(self, query: str) -> Dict[str, Any]:
        """Async version for FastAPI"""
        if self.qa_chain is None:
            return {"content": "RAGHandler not initialized. Please run data ingestion.", "score": 0.0}
        try:
            start_time = time.time()
            # ✅ Use "query" instead of "question"
            result = await self.qa_chain.ainvoke({"query": query})
            elapsed_time = time.time() - start_time
            logging.info(f"Query processed in {elapsed_time:.2f}s: {query}")

            # Handle different return formats
            answer = result.get("result") or result.get("output_text") or "No answer found."
            return {"content": answer, "score": 1.0, "sources": result.get("source_documents", [])}
        except Exception as e:
            logging.error(f"Error processing query '{query}': {e}")
            return {"content": f"Error processing query: {str(e)}", "score": 0.0}

    def search_sync(self, query: str) -> Dict[str, Any]:
        """Synchronous version for agents"""
        if self.qa_chain is None:
            return {"content": "RAGHandler not initialized.", "score": 0.0}
        try:
            # ✅ Use "query" instead of "question"
            result = self.qa_chain.invoke({"query": query})
            answer = result.get("result") or result.get("output_text") or "No answer found."
            return {"content": answer, "score": 1.0, "sources": result.get("source_documents", [])}
        except Exception as e:
            return {"content": f"Error: {str(e)}", "score": 0.0}


if __name__ == "__main__":
    import asyncio

    async def run_query():
        rag_handler = RAGHandler()
        query = "What is John Doe's department?"
        response = await rag_handler.search_documents_with_rag(query)
        print(f"Response: {response['content']}")

    asyncio.run(run_query())
