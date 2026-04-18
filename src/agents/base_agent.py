"""
Base Agent class providing OpenAI-powered agentic capabilities.
Supports tool registration, structured output, and autonomous execution.
"""

import json
import logging
from typing import Any, Callable, Optional

from openai import OpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentTool:
    """Represents a tool that an agent can call."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        function: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseAgent:
    """
    Base agent class with OpenAI tool-calling capabilities.
    
    Features:
    - System prompt configuration
    - Tool registration and automatic execution
    - Multi-turn tool-calling loop
    - Structured logging of all interactions
    """

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "gpt-4o-mini",
        api_key: str = "",
        temperature: float = 0.7,
        max_tool_rounds: int = 5,
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.max_tool_rounds = max_tool_rounds
        self.tools: dict[str, AgentTool] = {}

        self.client = OpenAI(api_key=api_key)

        logger.info(f"[*] Agent initialized: {self.name} ({self.role})")

    def register_tool(self, tool: AgentTool) -> None:
        """Register a tool that this agent can call."""
        self.tools[tool.name] = tool
        logger.info(f"  [*] Tool registered: {tool.name}")

    def run(self, user_message: str) -> str:
        """
        Execute the agent with the given user message.
        Handles multi-turn tool-calling automatically.
        
        Returns the final text response from the agent.
        """
        logger.info(f"[START] Agent [{self.name}] starting execution")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Prepare tools for OpenAI
        openai_tools = (
            [tool.to_openai_schema() for tool in self.tools.values()]
            if self.tools
            else None
        )

        for round_num in range(self.max_tool_rounds):
            logger.info(f"  [*] Round {round_num + 1}: Calling {self.model}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools,
                temperature=self.temperature,
            )

            choice = response.choices[0]
            message = choice.message

            # If no tool calls, we have our final answer
            if not message.tool_calls:
                result = message.content or ""
                logger.info(f"  [OK] Agent [{self.name}] completed")
                logger.info(f"  Output length: {len(result)} chars")
                logger.info(
                    f"  Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}"
                )
                return result

            # Process tool calls
            messages.append(message.model_dump())

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                logger.info(f"  [*] Tool call: {func_name}({json.dumps(func_args, indent=2)[:200]})")

                if func_name in self.tools:
                    try:
                        tool_result = self.tools[func_name].function(**func_args)
                        result_str = (
                            json.dumps(tool_result)
                            if not isinstance(tool_result, str)
                            else tool_result
                        )
                        logger.info(f"  [DATA] Tool result: {result_str[:200]}...")
                    except Exception as e:
                        result_str = f"Error calling {func_name}: {str(e)}"
                        logger.error(f"  [ERROR] Tool error: {result_str}")
                else:
                    result_str = f"Unknown tool: {func_name}"
                    logger.warning(f"  [WARN] {result_str}")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    }
                )

        # If we exhausted all rounds, return the last message
        logger.warning(
            f"  [WARN] Agent [{self.name}] hit max tool rounds ({self.max_tool_rounds})"
        )
        return message.content or "Agent could not complete the task within the allowed rounds."
