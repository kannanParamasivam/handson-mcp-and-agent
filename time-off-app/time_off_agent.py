from dotenv import load_dotenv
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_ollama import ChatOllama
import asyncio
#-----------------------------------------------------------------------
# load environment variables
#-----------------------------------------------------------------------

load_dotenv()

#-----------------------------------------------------------------------
# Initialize the LLM
#-----------------------------------------------------------------------
model = ChatOllama(model="llama3.1")

#-----------------------------------------------------------------------
# Define the HR timeoff agent that will use the MCP server
# to manage timeoff requests.
#-----------------------------------------------------------------------
async def run_timeoff_agent(user: str, prompt: str) -> str:
  mcp_server_url = "http://localhost:8000"

  async with streamablehttp_client(mcp_server_url) as streamable_http_client:
    read, write, other = streamable_http_client
    
    async with ClientSession(read, write) as session:
      # initialize session
      await session.initialize()

      mcp_tools = await load_mcp_tools(session)
      print("\nTools loaded:")
      for tool in mcp_tools:
        print(f"Tool: {tool.name} - {tool.description}")

      llm_prompt = await load_mcp_prompt(session,
                                    "get_llm_prompt",
                                    arguments={"user" : user, "prompt" : prompt})
      print("\nPrompt loaded :", llm_prompt)

      # Create ReAct agent with model and tools
      react_agent = create_react_agent(model, mcp_tools)

      # Invoke agent with prompt
      agent_response = await react_agent.ainvoke(
        {"messages": llm_prompt})

      return agent_response["messages"][-1].content


async def main():
    """Run multiple timeoff agent queries in sequence"""
    response = await run_timeoff_agent("Alice", "What is my time off balance?")
    print(f"\nResponse: {response}")

    response = await run_timeoff_agent(
        "Alice", 
        "File a time off request for 5 days starting from 2025-05-05")
    print(f"\nResponse: {response}")

    response = await run_timeoff_agent(
        "Alice", 
        "What is my time off balance now?")
    print("\nResponse:", response)


if __name__ == "__main__":
    asyncio.run(main())