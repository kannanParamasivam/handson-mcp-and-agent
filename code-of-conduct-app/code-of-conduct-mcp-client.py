from dotenv import load_dotenv
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_ollama import ChatOllama
import os
import asyncio
from utils.model_utils import test_model_connection


# ------------------------------------------------------------------------
# Load environment variables from .env file
# ------------------------------------------------------------------------
load_dotenv()

# ------------------------------------------------------------------------
# Configure MCP server connection
# ------------------------------------------------------------------------
# get current files absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
server_path = os.path.join(current_dir, "code-of-conduct-mcp-server.py")

server_params = StdioServerParameters(
    command="uv",
    args=["run", server_path]
)

# ------------------------------------------------------------------------
# Configure Ollama model
# ------------------------------------------------------------------------
model = ChatOllama(
    model="llama3.1",  # or any other model you have installed
    temperature=0.7
)


# ------------------------------------------------------------------------
# Fetch content from MCP resource
# ------------------------------------------------------------------------
async def fetch_resource_content():
    # Start MCP Server
    async with stdio_client(server_params) as client:
        read, write = client
        
        # Initialize a session with MCP server
        async with ClientSession(read, write) as session:
            await session.initialize()
            # load mcp resources available
            resources = await load_mcp_resources(session)
            
            for resource in resources:
                print(f"Resource: {resource.metadata}")

            # Return body of the first resource
            return resources[0].data


# ------------------------------------------------------------------------
# Run mcp client app, fetches and prints the first resource content
# ------------------------------------------------------------------------
if __name__ == "__main__":
    # Test model connectivity
    if not asyncio.run(test_model_connection(model)):
        exit(1)
    
    # Fetch code of conduct from MCP server
    received_content = asyncio.run(fetch_resource_content())

    user_query = "What are the data privacy policies of the company?"

    # Create prompt with user query and retrieved content as context
    prompt = f"""Answer the query based on the following context provided.
                Context: {received_content} 
                Query: {user_query}
                """
    
    # Invoke the model with the prompt
    model_response = model.invoke(prompt)
    print(f"User Query: {user_query}")
    print("\nModel response:")
    print(model_response.content)
            

        




        
        