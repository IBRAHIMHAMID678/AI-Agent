import asyncio
from langchain_community.llms import Ollama
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from chatbot_services.tools import tools

llm = Ollama(model="qwen2:0.5b-instruct-q4_0")

# Pull the ReAct prompt from Hub
base_prompt = hub.pull("hwchase17/react")

# Add your custom system rule as prefix
system_instructions = """
You are a helpful assistant with access to tools.

🚨 RULES:
- If the user asks about PEOPLE, NAMES, EMPLOYEES, DOCUMENTS, or RECORDS,
  you MUST use the `search_documents_with_rag` tool.
- Do NOT guess or answer directly from memory.
"""

# Merge system rules with the base prompt
prompt = base_prompt.partial(
    tool_names=[tool.name for tool in tools],
    input="{input}",
    agent_scratchpad="{agent_scratchpad}",
    # prepend system rules
    prefix=system_instructions
)

# Create the ReAct agent
agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

# Create executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

async def handle_user_query(user_input: str) -> dict:
    try:
        response = await agent_executor.ainvoke({"input": user_input})
        return {"response": response['output']}
    except Exception as e:
        return {"response": f"❌ Error: {str(e)}"}

async def main():
    print("🤖 Chatbot is running. Type 'quit' to exit.")
    while True:
        q = input("\nYou: ")
        if q.lower() in ["quit", "exit"]:
            break
        ans = await handle_user_query(q)
        print(f"Bot: {ans['response']}")

if __name__ == "__main__":
    asyncio.run(main())
