import asyncio
from langchain_community.llms import Ollama
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_core.prompts import PromptTemplate
from chatbot_services.tools import tools 


llm = Ollama(model="qwen3:0.6b")


prompt = hub.pull("hwchase17/react")

system_message = (
    "You are a helpful assistant with access to the following tools: {tool_names}. "
    "Your primary goal is to answer questions by using these tools. "
    "If a question is about specific documents, people, or data you have been given, "
    "you MUST use the 'get_rag_search' tool to find the answer first. "
    "Only use your general knowledge if the user's question does not require a tool, "
    "such as for a general greeting or an opinion-based question."
)

prompt = prompt.partial(agent_scratchpad="", intermediate_steps="", tool_names=[tool.name for tool in tools])
prompt = PromptTemplate.from_template(f"{system_message}\n\n{prompt.template}")


agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)


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

if __name__ == "__main__":
    print("🤖 Chatbot is running. Type 'quit' to exit.")
    print("\nHere are some examples of what I can do:")
    print(" - 'What is the weather in London?'")
    print(" - 'Who is the CEO of OpenAI?'")
    print(" - 'What is Ibrahim's email?' (if the data is in your RAG system)")

    while True:
        q = input("\nYou: ")
        if q.lower() in ["quit", "exit"]:
            break
        ans = asyncio.run(handle_user_query(q))
        print(f"Bot: {ans['response']}")