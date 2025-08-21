# chatbot_services/tools.py

from langchain.tools import tool
from .api_handlers import show_weather_api_async
from .rag_handler import RAGHandler

# Initialize once (so vectorstore + QA chain are ready)
rag_handler = RAGHandler()

@tool
async def get_weather(city: str) -> str:
    """ONLY use this tool when the user explicitly asks about the WEATHER in a CITY. 
    The input MUST be a valid city name (e.g., 'Paris', 'London'). 
    DO NOT use this tool for people, documents, or general questions."""
    response = await show_weather_api_async(city)
    return response.get("message", "An error occurred while fetching weather.")

@tool
async def search_documents_with_rag(query: str) -> str:
    """ALWAYS use this tool when the user is asking about a PERSON, NAME, DOCUMENT, or RECORD. 
    Do not attempt to answer from memory. 
    This tool retrieves authoritative information from the knowledge base."""
    
    rag_result = await rag_handler.search_documents_with_rag(query)

    # Extract fields safely
    answer = rag_result.get("content", "No answer found.")
    sources = rag_result.get("sources", [])
    sources_str = ", ".join(sources) if sources else "N/A"

    if "No relevant context found." in answer or "No knowledge base found." in answer:
        return (
            f"I could not find any information on this topic in my documents. "
            f"I can try to answer using my general knowledge. Question: {query}"
        )
    
    return f"Answer: {answer}\n\nSources: {sources_str}"

tools = [
    get_weather,
    search_documents_with_rag
]
