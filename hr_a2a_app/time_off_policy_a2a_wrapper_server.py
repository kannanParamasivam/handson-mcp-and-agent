import sys
import os

from typing_extensions import override
import json

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication
from a2a.utils import new_agent_text_message
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

# comment below line when you run this code as module with `uv python3 -m hr-a2a-app.hr-policy-a2a-wrapper-server`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../time_off_app')))
from time_off_agent import TimeOffAgent
# comment below line when you run this code as module with `uv python3 -m hr-a2a-app.hr-policy-a2a-wrapper-server`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../'))) 
from utils.log_utils import log_message


#---------------------------------------------------------------------
# Timeoff Agent Executor
#---------------------------------------------------------------------
class TimeoffAgentExecutor(AgentExecutor):
  "Executes Timeoff agent."

  def __init__(self):
    self.actor = "Timeoff Agent Executor"
    log_message(self.actor, "Timeoff Agent Executor initialized")
    self.timeoff_agent = TimeOffAgent()
    

  @override
  async def execute(
    self,
    context: RequestContext,
    event_queue: EventQueue) -> None:
    
    user_input = json.loads(context.get_user_input())
    log_message(self.actor, f"User prompt received: {user_input.get('prompt')}")
    
    async with self.timeoff_agent:
        result = await self.timeoff_agent.submit_request(user_input.get('user'), user_input.get('prompt'))

    log_message(self.actor, f"Result received: {result}")
    await event_queue.enqueue_event(new_agent_text_message(result))
    
    
  async def cancel(
    self,
    context: RequestContext, 
    event_queue: EventQueue) -> None:
    
    raise Exception("Not implemented")


if __name__ == "__main__":

  timeoff_agent_skill = AgentSkill(
    id="TimeoffSkill",
    name="Timeoff Agent Skills",
    description="Handles timeoff requests.",
    tags=["HR", "timeoff"],
  examples=[
            "What is my timeoff balance?",
            "Create a timeoff request for 5 days from 30-June-2025",
        ]
  )

  timeoff_agent_card = AgentCard(
    name="Timeoff Agent",
    description="Performs timeoff operations.",
    url="http://localhost:9002",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[timeoff_agent_skill]
  )

  timeoff_agent_request_handler = DefaultRequestHandler(
    agent_executor=TimeoffAgentExecutor(),
    task_store=InMemoryTaskStore(),
  )

  # Create ASGI Application
  timeoff_server = A2AStarletteApplication(
    agent_card=timeoff_agent_card,
    http_handler=timeoff_agent_request_handler
  )

  # Start ASGI server that hosts the Starlette application
  import uvicorn
  uvicorn.run(
    timeoff_server.build(),
    host="0.0.0.0", 
    port=9002, 
    log_level="info")


# ASGI - Asynchronous Server Gateway Interface
# * Asynchronous version of WSGI
# e.g: FastAPI, Starlette

# WSGI - Web Server Gateway Interface
# * Synchronous version of WSGI
# e.g: Flask, Django

# Get Agent Card: 
# curl http://localhost:9002/.well-known/agent.json

# Send Message: 
# curl -X POST http://localhost:9002/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "jsonrpc": "2.0",
#     "method": "message/send",
#     "params": {
#       "message": {
#         "role": "user",
#         "messageId": "test-id-1",
#         "parts": [{
#           "text": "{\"user\": \"Alice\", \"prompt\": \"What is my time off balance?\"}"
#         }]
#       }
#     },
#     "id": 1
#   }'


