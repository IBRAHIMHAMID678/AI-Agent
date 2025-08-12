import os
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

DATA_PATH = "./data"
PERSIST_DIR = "./chroma_db"

def ingest_documents():
    
    os.makedirs(PERSIST_DIR, exist_ok=True)

    documents = []
    for file in os.listdir(DATA_PATH):
        filepath = os.path.join(DATA_PATH, file)
        if file.endswith(".pdf"):
            loader = PyPDFLoader(filepath)
            documents.extend(loader.load())
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


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    docs_chunks = text_splitter.split_documents(documents)

    # Create embeddings using Ollama model
    ollama_embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Store chunks in Chroma vector DB
    vectorstore = Chroma.from_documents(
        documents=docs_chunks,
        embedding=ollama_embeddings,
        persist_directory=PERSIST_DIR
    )

    print(f"✅ Ingested {len(docs_chunks)} document chunks into {PERSIST_DIR}.")

if __name__ == "__main__":
    ingest_documents()
