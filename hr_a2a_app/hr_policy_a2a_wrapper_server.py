import sys
import os
from typing_extensions import override
import json

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

# comment below line when you run this code as module with `uv python3 -m hr-a2a-app.hr-policy-a2a-wrapper-server`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../hr-policy-app')))
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
  





