import os
from dotenv import load_dotenv
from fastmcp import FastMCP
import PyPDF2

# ------------------------------------------------------------------------
# Setup  MCP Server
# ------------------------------------------------------------------------
load_dotenv()
mcp = FastMCP("hr-code-of-conduct-mcp-server")
# ------------------------------------------------------------------------
# Setup Resources
# ------------------------------------------------------------------------
pdf_file_name = "code_of_conduct.pdf"
pdf_file_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), pdf_file_name))
pdf_uri = f"file:///{pdf_file_path.replace(os.sep, '/')}"


# ------------------------------------------------------------------------
# Define  Resources
# ------------------------------------------------------------------------
@mcp.resource(
    uri="file://code-of-conduct",
    name="Code of Conduct",
    description="Provides the code of conduct for the company.",
    mime_type="text/plain"  # Type of content returned
)
def get_code_of_conduct() -> str:
    """Returns the text content of the code of conduct PDF file."""
    # Open code_of_conduct.pdf and extract text
    with open(pdf_file_path, "rb") as code_of_conduct_buffer:
        reader = PyPDF2.PdfReader(code_of_conduct_buffer)
        text = ""
        
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text
            
        return text


if __name__ == "__main__":
    mcp.run(transport="stdio")

