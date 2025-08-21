import os
import time
import json
import logging
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_PATH = "./data"
PERSIST_DIR = "./chroma_db"

def ingest_data():
    start_time = time.time()
    
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        logging.info(f"Vector store exists in {PERSIST_DIR}. Skipping ingestion.")
        return

    os.makedirs(PERSIST_DIR, exist_ok=True)

    documents = []
    load_time = time.time()
    for file in os.listdir(DATA_PATH):
        filepath = os.path.join(DATA_PATH, file)
        if file.lower().endswith(".json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for record in data:
                    record_text = f"ID: {record.get('id', '')}, Name: {record.get('name', '')}, Role: {record.get('role', '')}, Department: {record.get('department', '')}"
                    documents.append(Document(page_content=record_text, metadata={"source": filepath, "type": "employee_record", "id": record.get('id')}))
                logging.info(f"Processed {file} with {len(data)} employee records.")
            except Exception as e:
                logging.error(f"Error processing {file}: {e}")
        else:
            logging.warning(f"Skipping unsupported file: {file}")

    if not documents:
        logging.error("No documents found in the data directory.")
        return

    logging.info(f"Document loading: {time.time() - load_time:.2f}s")

    split_time = time.time()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=20
    )
    docs_chunks = text_splitter.split_documents(documents)
    logging.info(f"Document splitting: {time.time() - split_time:.2f}s")

    embed_time = time.time()
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    try:
        Chroma.from_documents(
            documents=docs_chunks,
            embedding=embeddings,
            persist_directory=PERSIST_DIR,
            collection_metadata={"hnsw:space": "l2", "hnsw:M": 8}
        )
        logging.info(f"Embedding and storage: {time.time() - embed_time:.2f}s")
        logging.info(f"Total ingestion: {time.time() - start_time:.2f}s")
        logging.info(f"Ingested {len(docs_chunks)} document chunks into {PERSIST_DIR}.")
    except Exception as e:
        logging.error(f"Error creating vector store: {e}")
        raise

if __name__ == "__main__":
    ingest_data()