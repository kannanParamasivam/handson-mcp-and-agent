import sys
from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_community.document_loaders import PyPDFLoader, pdf
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
import os
from pathlib import Path

# append the path to the root
sys.path.append(str(Path(__file__).parent.parent)) # uncommend just for debugging
from utils.show_splitted_documents import show_splitted_documents

# -----------------------------------------------------------------------
# Setup the MCP Server
# -----------------------------------------------------------------------
load_dotenv()
mcp = FastMCP("hr-policies-mcp-server")

# -----------------------------------------------------------------------
# Setup the Vector Store for use in retrieving policies
# This will use the hr_policy_document.pdf file as its source
# -----------------------------------------------------------------------

pdf_filename = "hr_policy_document.pdf"
pdf_full_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), pdf_filename))

# Load and split the PDF document
loader = PyPDFLoader(pdf_full_path)
policy_document_context_splitted = loader.load_and_split()
# show_splitted_documents(policy_document_context_splitted)

# Create embeddings (a wrapper around embedding model)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") # This is a sentence-transformers model: It maps sentences & paragraphs to a 384 dimensional dense vector space and can be used for tasks like clustering or semantic search.
policy_vector_store = InMemoryVectorStore.from_documents(policy_document_context_splitted, embeddings)

# -----------------------------------------------------------------------
# Setup the MCP tool to query for policies, given a user query string
# -----------------------------------------------------------------------
@mcp.tool()
def query_policies(query: str):
    # perform a semantic search in the vector store
    results = policy_vector_store.similarity_search(query, k=3)
    return results


# -----------------------------------------------------------------------
# Setup the MCP prompt to dynamically generate the prompt for the LLM
# using the input query.
# -----------------------------------------------------------------------
@mcp.prompt()
def get_llm_prompt(query: str) -> str:
    """Generates a a prompt for the LLM to use to answer the query"""

    return f"""
    You are a helpful HR assistant. Answer the following query about HR policies
    by only using the tools provided to you. Do not make up any information.

    Query: {query}
    """


if __name__ == "__main__":
    # print(query_policies("I have problem with some of my colleagues. What should I do?"))
    mcp.run(transport="stdio")





