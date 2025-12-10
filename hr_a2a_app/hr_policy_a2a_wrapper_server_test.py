import sys
import os
import json
import asyncio


# Add project root to sys.path to find utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.log_utils import log_message
from hr_policy_a2a_wrapper_server import HRPolicyAgentExecutor


class HRPolicyAgentExecutorTest:
  """Test class for HRPolicyAgentExecutor"""
  
  # Mock classes for testing
  class MockRequestContext:
    def get_user_input(self):
      # Return a JSON string with a dummy prompt
      return json.dumps({"prompt": "What is the vacation policy?"})
  
  
  class MockEventQueue:
    def __init__(self):
      self.events = []
    
    async def enqueue_event(self, event):
      log_message("MockEventQueue", f"Event enqueued: {event}")
      self.events.append(event)
  
  
  async def test_execute(self):
    """Test the execute method with dummy values"""
    # Initialize the executor
    hr_policy_agent_executor = HRPolicyAgentExecutor()
    
    # Create mock instances
    mock_context = self.MockRequestContext()
    mock_event_queue = self.MockEventQueue()
    
    # Run the execute method
    log_message("Test", "Starting test execution...")
    await hr_policy_agent_executor.execute(mock_context, mock_event_queue)
    log_message("Test", "Test execution completed!")
    
    # Assert expected behavior
    assert len(mock_event_queue.events) == 1, "Expected 1 event to be enqueued"
    log_message("Test", "✓ All assertions passed!")


if __name__ == "__main__":
  # Run the test
  test_suite = HRPolicyAgentExecutorTest()
  asyncio.run(test_suite.test_execute())
