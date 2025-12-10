import asyncio
import os
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama


# - ----------------------------------------------------------------------
# Setup LLM for the agent
# -----------------------------------------------------------------------
load_dotenv()

# chat wrapper is suitable for interct with model by assigning it a role and make it tool call aware
model = ChatOllama(
    model="llama3.1",  # or any other model you have installed
    temperature=0.7)

# - ----------------------------------------------------------------------
# Setup mcp server parameters
# -----------------------------------------------------------------------
mcp_server_file_name = "hr_policy_mcp_server.py"
mcp_server_full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), mcp_server_file_name)) 

mcp_server_params = StdioServerParameters(
    command="uv",
    args=["run", mcp_server_full_path]
)


# - ----------------------------------------------------------------------
# Run the agent
# -----------------------------------------------------------------------
async def run_hr_policy_agent(prompt: str) -> str:
    
    # create stdio mcp client
    async with stdio_client(mcp_server_params) as client:
        read, write = client
        
        # create mcp session
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # load mcp tools and prompt
            mcp_tools = await load_mcp_tools(session)
            mcp_prompt = await load_mcp_prompt(session, 
                                    "get_llm_prompt", 
                                    arguments={"query": prompt})

            print("\nTools loaded :", [tool.name for tool in mcp_tools])
            print("\nPrompt loaded :", mcp_prompt)
            
            # create agent
            agent = create_react_agent(model=model, tools=mcp_tools)

            # invoke agent with prompt        
            agent_response = await agent.ainvoke(
                {"messages": mcp_prompt})

            return agent_response["messages"][-1].content

        return "Error"  # should never reach here

if __name__ == "__main__":
    # Run the agent with a sample query
    print("\nRunning HR Policy Agent...")
    response = asyncio.run(
        run_hr_policy_agent("What is the policy on remote work?"))

    print("\nResponse: ", response)








