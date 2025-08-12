from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging

# Import the chatbot service
from chatbot_services.main_service import handle_user_query


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---
app = FastAPI(
    title="LLM Chatbot API",
    description="A FastAPI backend for a conversational LLM.",
    version="1.0.0",
)

# CORS (Cross-Origin Resource Sharing) middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Model for Request Body ---
class ChatRequest(BaseModel):
    user_input: str

@app.get("/")
async def health_check():
    """Endpoint to check if the API is running."""
    return {"status": "ok", "message": "API is running and healthy."}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint for a chat message.
    It calls the LLM service and returns its response.
    """
    user_input = request.user_input
    logger.info(f"Received user input: '{user_input}'")
    
    try:
       response = await handle_user_query(user_input)
       return response
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return {"response": f"❌ An internal error occurred: {str(e)}", "action_required": False}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)