import sys
import os
from annotated_types import UpperCase
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Any
import operator
import asyncio
import uuid
import json
import httpx

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, AnyMessage
from a2a.client import ClientFactory
from a2a.types import SendMessageRequest, MessageSendParams, AgentCard, Message

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'../'))) 
from utils.log_utils import log_message

load_dotenv()

actor = "Router Agent"
# - ----------------------------------------------------------------------
# Setup LLM for the agent
# -----------------------------------------------------------------------


# chat wrapper is suitable for interacting with model by assigning it a role and make it tool call aware
model = ChatOllama(
    model="llama3.1",  # or any other model you have installed
    temperature=0.7)

# ---------------------------------------------------------------
# Setup System Prompt to assign persona to LLM and select user
# ---------------------------------------------------------------
system_prompt = """ 
    You are a Router, that analyzes the input query and chooses 3 options:
    POLICY: If the query is about HR policies, like leave, remote work, etc.
    TIMEOFF: If the query is about time off requests, both creating requests and checking balances
    UNSUPPORTED: Any other query that is not related to HR policies or time off requests.

    The output should only be just one word out of the possible 3 : POLICY, TIMEOFF, UNSUPPORTED.
    """

user = "Alice"

# ---------------------------------------------------------------
# Router Graph configuration
# ---------------------------------------------------------------
router_graph_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# ---------------------------------------------------------------
# Helper method to invoke remote agent through agent wrapper
# ---------------------------------------------------------------
async def execute_a2a_agent(agent_card_url: str, user: str, prompt: str) -> str:
    
    # create http client  
    async with httpx.AsyncClient(timeout=30) as httpx_client:
        
      # create agent card from URL
      agent_card_response = await httpx_client.get(f"{agent_card_url}/.well-known/agent-card.json")
      agent_card_response.raise_for_status()
      agent_card = AgentCard(**agent_card_response.json()) 
      
      # create agent client with agent card
      from a2a.client import ClientConfig
      # instead of connecting to agent, the efficient way would be creating client object and using it to send message.
      agent_client = await ClientFactory.connect(
          agent=agent_card,
          client_config=ClientConfig(httpx_client=httpx_client)
      )

      input_dict = {"user": user, "prompt": prompt} 

      agent_payload: dict[str, Any] = {
              "message": {
                  "role": "user",
                  "parts": [
                      {"kind": "text", "text": json.dumps(input_dict)},
                  ],
                  "messageId": uuid.uuid4().hex,
              },
          }

      agent_response_iterator = agent_client.send_message(request=Message(**agent_payload["message"]))
      
      text = ""
      async for response_item in agent_response_iterator:
          if isinstance(response_item, Message):
              agent_response_json = response_item.model_dump(mode='json', exclude_none=True)
              # Structure might vary, safeguard access
              parts = agent_response_json.get("parts", [])
              if parts and isinstance(parts, list):
                  text = parts[0].get("text", "")
      
      return text




# ---------------------------------------------------------------
# Shared State for the router agent
# ---------------------------------------------------------------
class RouterAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add] # list with reduction operator to add messages


class RouterHRAgent:

    def __init__(self, model, system_prompt, user, debug=False):
        
        self.model = model
        self.system_prompt = system_prompt
        self.user = user
        self.debug = debug

        router_graph = StateGraph(RouterAgentState)
        router_graph.add_node("Router", self.call_llm)
        router_graph.add_node("Policy_Agent", self.call_policy_agent)
        router_graph.add_node("Timeoff_Agent", self.call_timeoff_agent)
        router_graph.add_node("Unsupported_functions", self.unsupported_node)

        router_graph.add_conditional_edges(
            "Router",
            self.find_route,
            {"POLICY": "Policy_Agent",
             "TIMEOFF": "Timeoff_Agent",
             "UNSUPPORTED": "Unsupported_functions"}
        )

        # Terminate the route so that the graph engine doesn't keep running and error out
        router_graph.add_edge("Policy_Agent", END)
        router_graph.add_edge("Timeoff_Agent", END)
        router_graph.add_edge("Unsupported_functions", END)

        # Set the entry point of the graph
        router_graph.set_entry_point("Router")

        # Compile and create the runnable graph
        self.router_graph = router_graph.compile()
    

    def call_llm(self, state: RouterAgentState):
      
      messages = state["messages"]

      # Crate system message to set persona to LLM. 
      # This system prompt asks LLM to act as agent router
      if self.system_prompt:
        messages = [SystemMessage(content=self.system_prompt)] + messages

      llm_response = self.model.invoke(messages)

      if self.debug:
        log_message(actor, f"LLM response : {llm_response}")

      return {"messages": [llm_response]} # the graph engine adds this AIMessage to the shared state


    def find_route(self, state: RouterAgentState):
      last_message = state["messages"][-1]
      
      if last_message.content.upper() not in ["POLICY", "TIMEOFF", "UNSUPPORTED"]:
        return "UNSUPPORTED"
      
      if self.debug:
        log_message(actor, f"Router: Last result from LLM : {last_message}")

      # Set the last message as the destination
      destination = last_message.content

      log_message(actor, f"Destination chosen : {destination}")
      return destination

    
    def call_policy_agent(self, state: RouterAgentState):
      
      messages = state["messages"]

      # read original prompt from the user
      original_prompt = messages[0].content
      
      if self.debug:
        log_message(actor, f"Policy Agent node received : {original_prompt}")     

      # Invoke the HR Policy agent with original prompt 
      policy_agent_response = asyncio.run(execute_a2a_agent("http://localhost:9001", self.user, original_prompt))

      if self.debug:
        log_message(actor, f"Policy Agent response : {policy_agent_response}")

      return {"messages": [AIMessage(content=policy_agent_response)]} # the graph engine adds this AIMessage to the shared state


    def call_timeoff_agent(self, state: RouterAgentState):
      messages = state["messages"]

      # read original prompt from the user
      original_prompt = messages[0].content

      if self.debug:
        log_message(actor, f"Timeoff Agent node received : {original_prompt}")

      # Invoke the TimeOff agent with original prompt
      timeoff_agent_response = asyncio.run(execute_a2a_agent("http://localhost:9002", self.user, original_prompt))

      if self.debug:
        log_message(actor, f"Timeoff Agent response : {timeoff_agent_response}")

      return {"messages": [AIMessage(content=timeoff_agent_response)]} # the graph engine adds this AIMessage to the shared state

    
    def unsupported_node(self, state: RouterAgentState):
        messages = state["messages"]

        print("Unsupported node invoked")

        response = """Sorry, I cannot help you with this request.
        I only support HR policy queries and timeoff requests.
        Please contact your HR representative for assistance."""

        if self.debug:
            print(f"Unsupported node response : {response}")

        return {"messages": [AIMessage(content=response)]}

    



if __name__ == "__main__":

  try:
    # Mimic chatbot

    router_hr_agent = RouterHRAgent(model, system_prompt, user, debug=False)

    user_inputs = [
            # "Tell me about payroll processing",
            # "What is the policy for remote work?",
            # "What is my vacation balance?",
            # "File a time off request for 5 days starting from 2025-05-05",
            # "What is vacation balance now?",
            "how to handle conflicts?"
        ]

    for input in user_inputs:
            print(f"----------------------------------------\nUSER : {input}")
            # Format the user message
            user_message = {"messages": [HumanMessage(input)]}
            # Get response from the agent
            ai_response = router_hr_agent.router_graph.invoke(
                user_message, config=router_graph_config)
            # Print the response
            print(f"\nAGENT : {ai_response['messages'][-1].content}")

  except Exception as e:
    log_message(actor, f"An error occurred: {e}")
  