# chatbot_services/tools.py

from langchain.tools import tool
import asyncio


from .api_handlers import show_weather_api_async
from .rag_handler import get_rag as rag_handler_function 

@tool
async def get_weather(city: str) -> str:
    """Fetches the current weather for a specific city. The input must be a city name."""
    response = await show_weather_api_async(city)
    return response.get("message", "An error occurred while fetching weather.")

@tool
async def search_documents_with_rag(query: str) -> str:
    """A powerful tool for answering questions about custom documents like resumes and reports. 
    Use this tool to retrieve information from a provided knowledge base. This is useful for tasks such as summarizing documents, finding specific details (like an email address), or answering questions based on the content of the files.
    Input should be the question to search for, e.g., "summarize the report" or "What is Ibrahim's email?"."""
    
    
    rag_result =  rag_handler_function(query) 
    
   
    if "No relevant context found." in rag_result["content"] or "No knowledge base found." in rag_result["content"]:
        return f"I could not find any information on this topic in my documents. I can try to answer using my general knowledge. Question: {query}"
    
    
    return f"Based on this document: '{rag_result['content']}', please answer the question: '{query}'."

tools = [
    get_weather,
    search_documents_with_rag
]