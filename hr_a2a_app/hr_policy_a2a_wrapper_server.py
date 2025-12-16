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
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../hr_policy_app')))
import hr_policy_agent
# comment below line when you run this code as module with `uv python3 -m hr-a2a-app.hr-policy-a2a-wrapper-server`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../'))) 
from utils.log_utils import log_message


#---------------------------------------------------------------------
# HR Policy Agent Executor
#---------------------------------------------------------------------
class HRPolicyAgentExecutor(AgentExecutor):
  "Executes HR policy agent."

  def __init__(self):
    self.actor = "HR Policy Agent Executor"
    log_message(self.actor, "HR Policy Agent Executor initialized")
    

  @override
  async def execute(
    self,
    context: RequestContext,
    event_queue: EventQueue) -> None:
    
    user_input = json.loads(context.get_user_input())
    log_message(self.actor, f"User prompt received: {user_input.get('prompt')}")
    result = await hr_policy_agent.run_hr_policy_agent(user_input.get('prompt'))

    log_message(self.actor, f"Result received: {result}")
    await event_queue.enqueue_event(new_agent_text_message(result))
    
    
  async def cancel(
    self,
    context: RequestContext, 
    event_queue: EventQueue) -> None:
    
    raise Exception("Not implemented")


if __name__ == "__main__":

  hr_policy_agent_skill = AgentSkill(
    id="HRPolicySkill",
    name="HR Policy Agent Skills",
    description="Answers question about HR Policies of the organization.",
    tags=["HR", "policies", "organization policies", "code of conduct", "leave policies", "vacation policies", "remote work policies", "benefits policies", "benefits"],
    examples=[
      "What is the policy on remote work?",
      "What is the policy on sick leave?",
      "What is the policy on vacation days?",
      "Waht is the dress code?"
    ]
  )

  hr_policy_agent_card = AgentCard(
    name="HR Policy Agent",
    description="Answers question about HR Policies of the organization.",
    url="http://localhost:9001",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[hr_policy_agent_skill]
  )

  hr_policy_request_handler = DefaultRequestHandler(
    agent_executor=HRPolicyAgentExecutor(),
    task_store=InMemoryTaskStore(),
  )

  # Create ASGI Application
  hr_policy_server = A2AStarletteApplication(
    agent_card=hr_policy_agent_card,
    http_handler=hr_policy_request_handler
  )

  # Start ASGI server that hosts the Starlette application
  import uvicorn
  uvicorn.run(
    hr_policy_server.build(),
    host="0.0.0.0", 
    port=9001, 
    log_level="info")


# ASGI - Asynchronous Server Gateway Interface
# * Asynchronous version of WSGI
# e.g: FastAPI, Starlette

# WSGI - Web Server Gateway Interface
# * Synchronous version of WSGI
# e.g: Flask, Django

# Get Agent Card: 
# curl http://localhost:9001/.well-known/agent.json

# Send Message: 
# curl -X POST http://localhost:9001/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "jsonrpc": "2.0",
#     "method": "message/send",
#     "params": {
#       "message": {
#         "role": "user",
#         "messageId": "test-id-1",
#         "parts": [{
#           "text": "{\"prompt\": \"What is the policy on remote work?\"}"
#         }]
#       }
#     },
#     "id": 1
#   }'


