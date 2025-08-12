# test_summarization.py

import asyncio
from langchain_community.llms import Ollama
from chatbot_services.rag_handler import get_rag

async def test_summarization():
    # Step 1: Manually retrieve the content (this step is working correctly)
    raw_content = get_rag("summarize the ibrahim resume")["content"]

    if not raw_content:
        print("❌ RAG retrieval failed. Cannot proceed with summarization.")
        return

    # Step 2: Manually create a summarization prompt for the LLM
    llm = Ollama(model="qwen2.5:0.5b")
    
    summarization_prompt = f"""
    Please summarize the following resume.
    
    Resume Text:
    {raw_content}
    
    Summary:
    """

    print("--- Sending raw content to LLM for summarization ---")
    
    # Step 3: Call the LLM directly with the raw content and the summarization prompt
    summary = await llm.ainvoke(summarization_prompt)
    print("✅ LLM Summary:")
    print(summary)

if __name__ == "__main__":
    asyncio.run(test_summarization())