import asyncio
from contextlib import AsyncExitStack
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.prompts import load_mcp_prompt
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

class TimeOffAgent:
    def __init__(self, mcp_server_url: str = "http://localhost:8000", model_name: str = "llama3.1"):
        self.mcp_server_url = mcp_server_url
        self.model = ChatOllama(model=model_name)
        self.model = ChatOllama(model=model_name)
        # self.exit_stack is initialized in __aenter__
        self.session = None
        self.agent = None

    async def __aenter__(self):
        self.exit_stack = AsyncExitStack()
        # Connect to the MCP server
        client = streamablehttp_client(self.mcp_server_url)
        read, write, _ = await self.exit_stack.enter_async_context(client)

        # Initialize the session
        self.session = ClientSession(read, write)
        await self.exit_stack.enter_async_context(self.session)
        print("Initializing session...")
        await self.session.initialize()

        # Load tools and create the agent
        tools = await load_mcp_tools(self.session)
        print(f"\nTools loaded: {[t.name for t in tools]}")
        
        print("\nCreating ReAct agent...")
        self.agent = create_react_agent(self.model, tools)
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.exit_stack.aclose()

    async def submit_request(self, user: str, prompt: str) -> str:
        """Process a query for a user using the agent."""
        if not self.agent or not self.session:
            raise RuntimeError("Agent not initialized. Use 'async with' context manager.")

        # Load the prompt context from the MCP server
        llm_prompt = await load_mcp_prompt(
            self.session,
            "get_llm_prompt",
            arguments={"user": user, "prompt": prompt}
        )
        print(f"\nPrompt loaded: {llm_prompt}")
        
        # Invoke the agent
        response = await self.agent.ainvoke({"messages": llm_prompt})
        return response["messages"][-1].content

async def main():
    """Run multiple timeoff agent queries in sequence."""
    mcp_url = "http://localhost:8000"
    
    try:
        async with TimeOffAgent(mcp_url) as agent:
            queries = [
                ("Alice", "What is my time off balance?"),
                ("Alice", "File a time off request for 5 days starting from 2025-05-05"),
                ("Alice", "What is my time off balance now?")
            ]

            for i, (user, query_text) in enumerate(queries, 1):
                print(f"\n" + "="*50)
                print(f"Query {i}: {query_text}")
                print("="*50)
                response = await agent.submit_request(user, query_text)
                print(f"\nResponse: {response}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())