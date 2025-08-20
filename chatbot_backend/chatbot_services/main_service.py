import asyncio
from langchain_community.llms import Ollama
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from chatbot_services.tools import tools


llm = Ollama(model="gemma3:1b")


prompt = hub.pull("hwchase17/react")


prompt = prompt.partial(
    agent_scratchpad="",
    tool_names=[tool.name for tool in tools],
    input="You are a helpful assistant with access to the following tools: {tool_names}. "
          "Your main goal is to answer the user's questions by using the available tools and your general knowledge.\n\n"
          "{input}"
)

# Create the ReAct agent
agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

# Create the AgentExecutor. handle_parsing_errors=True is a good practice.
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

async def handle_user_query(user_input: str) -> dict:
    """
    Executes the agent to handle user queries.
    """
    try:
        response = await agent_executor.ainvoke({"input": user_input})
        return {"response": response['output']}
    except Exception as e:
        return {"response": f"❌ Error: {str(e)}"}

async def main():
    """
    Main asynchronous function to run the chatbot.
    """
    print("🤖 Chatbot is running. Type 'quit' to exit.")
    print("\nHere are some examples of what I can do:")
    print(" - 'What is the weather in London?'")
    print(" - 'Who is the CEO of OpenAI?'")
    print(" - 'What is Ibrahim's email?' (if the data is in your RAG system)")

    while True:
        q = input("\nYou: ")
        if q.lower() in ["quit", "exit"]:
            break
        
        ans = await handle_user_query(q)
        print(f"Bot: {ans['response']}")

if __name__ == "__main__":
    
    asyncio.run(main())