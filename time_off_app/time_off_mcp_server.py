from dotenv import load_dotenv
import sys
import os

# Add the current directory to sys.path to allow imports when running as a module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from time_off_datastore import TimeOffDatastore
from fastmcp import FastMCP

#-----------------------------------------------------------------------
#Setup the MCP Server
#-----------------------------------------------------------------------
load_dotenv()
mcp = FastMCP("time-off-mcp-server")

#-----------------------------------------------------------------------
# Initialize datastore
#-----------------------------------------------------------------------
timeoff_db = TimeOffDatastore()

#-----------------------------------------------------------------------
# Define MCP Tools
#-----------------------------------------------------------------------
# Tool to get timeoff balance for an employee
@mcp.tool()
def get_timeoff_balance(employee_name: str):
    """Get the timeoff balance for the employee, given their name."""
    print(f"Getting timeoff balance for employee: {employee_name}")
    timeoff_balance = timeoff_db.get_timeoff_balance(employee_name)
    print(f"Timeoff balance for {employee_name}: {timeoff_balance}")
    return timeoff_balance


# Tool to request timeoff for an employee
@mcp.tool()
def request_timeoff(employee_name: str, start_date: str, total_days: int):
    """Request timeoff for an employee by employee name with start date and total days including start date."""
    print(f"Requesting timeoff for {employee_name} from {start_date} for {total_days} days")
    message = timeoff_db.add_timeoff_request(employee_name, start_date, total_days)
    print(f"Timeoff request result for employee {employee_name}: {message}")
    return message


#Get prompt for the LLM to use to answer the query
@mcp.prompt()
def get_llm_prompt(user: str, prompt: str) -> str:
    """Generates a a prompt for the LLM to use to answer the query
    give a user and a query"""
    print("Generating prompt for user: ", user)
    return f"""
    You are a helpful timeoff assistant. 
    Execute the action requested in the query using the tools provided to you.
    Action: {prompt}
    The tasks need to be executed in terms of the user {user}
    """

#-----------------------------------------------------------------------
# Test the TimeOff Server
#-----------------------------------------------------------------------

# Test code
# print("TEST: Time off balance for Alice: ", get_timeoff_balance("Alice"))
# print("TEST: Add time off request for Alice: ", request_timeoff("Alice", "2025-05-05", 5))
# print("TEST: New Time off balance for Alice: ", get_timeoff_balance("Alice"))


if __name__ == "__main__":
    print("Starting TimeOff MCP Server...")
    mcp.run(transport="streamable-http",
                    host="localhost",
                    port=8000,
                    path="/",
                    log_level="debug")
    print("TimeOff MCP Server started successfully!")
