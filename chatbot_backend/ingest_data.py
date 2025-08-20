import os
import time
import camelot
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

DATA_PATH = "./data"
PERSIST_DIR = "./chroma_db"

def ingest_data():
    start_time = time.time()
    
    # Check if vector store already exists
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        print(f"Vector store exists in {PERSIST_DIR}. Skipping ingestion.")
        return

    os.makedirs(PERSIST_DIR, exist_ok=True)

    documents = []
    load_time = time.time()
    for file in os.listdir(DATA_PATH):
        filepath = os.path.join(DATA_PATH, file)
        if file.endswith(".pdf"):
            # Use PyMuPDFLoader for faster PDF parsing
            loader = PyMuPDFLoader(filepath)
            pdf_docs = loader.load()
            # Extract tables using camelot for employee records
            try:
                tables = camelot.read_pdf(filepath, flavor='stream')
                table_text = "\n".join([table.df.to_string() for table in tables])
                pdf_docs.append(Document(page_content=table_text, metadata={"source": filepath, "type": "table"}))
            except Exception as e:
                print(f"No tables found in {file}: {e}")
            documents.extend(pdf_docs)
        elif file.endswith(".docx"):
            loader = UnstructuredWordDocumentLoader(filepath)
            documents.extend(loader.load())
        elif file.endswith(".txt"):
            loader = TextLoader(filepath)
            documents.extend(loader.load())
        else:
            print(f"Skipping unsupported file: {file}")

    if not documents:
        print("⚠ No documents found in the data directory.")
        return

    print(f"Document loading: {time.time() - load_time:.2f}s")

    split_time = time.time()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,  # Reduced chunk size for faster embedding and retrieval
        chunk_overlap=50
    )
    docs_chunks = text_splitter.split_documents(documents)
    print(f"Document splitting: {time.time() - split_time:.2f}s")

    embed_time = time.time()
    ollama_embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma.from_documents(
        documents=docs_chunks,
        embedding=ollama_embeddings,
        persist_directory=PERSIST_DIR,
        collection_metadata={"hnsw:space": "l2", "hnsw:M": 16}  # Optimized HNSW index
    )
    vectorstore.persist()
    print(f"Embedding and storage: {time.time() - embed_time:.2f}s")
    print(f"Total ingestion: {time.time() - start_time:.2f}s")
    print(f"✅ Ingested {len(docs_chunks)} document chunks into {PERSIST_DIR}.")

if __name__ == "__main__":
    ingest_data()