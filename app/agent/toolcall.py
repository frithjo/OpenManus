# app/agent/toolcall.py
import json
from typing import List, Optional, Tuple
from pydantic import Field

from app.agent.base import Agent
from app.llm import LLM
from app.logger import logger
from app.prompt.prompt_formatter import format_prompt
from app.schema import Message, ToolCall, ToolChoice
from app.tool import ToolCollection, ToolResult, Terminate
from app.tool.base import ToolFailure  # add this import
from app.config import Config
from app.prompt.tool_use import FORMAT_INSTRUCTIONS, JSON_END, JSON_START


class ToolCallAgent(Agent):
    """
    An agent that uses tools to interact with the environment.
    This agent selects tools to use and calls them based on the tool's description and parameters.
    """

    name: str = "tool_call"
    description: str = "An agent that uses tools to interact with the environment."
    system_prompt: str
    next_step_prompt: str
    available_tools: ToolCollection
    tool_choices: ToolChoice = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    config: Config

    def __init__(
        self,
        llm: LLM,
        system_prompt: str,
        next_step_prompt: str,
        available_tools: ToolCollection,
        config: Config,
        tool_choices: ToolChoice = ToolChoice.AUTO,  # type: ignore
    ) -> None:
        super().__init__(llm=llm, config=config)
        self.system_prompt = system_prompt
        self.next_step_prompt = next_step_prompt
        self.available_tools = available_tools
        self.tool_choices = tool_choices
        self.special_tool_names = [Terminate().name]

    async def think(self) -> bool:
        """
        Decide what to do next and store tool calls in memory.

        Returns:
            bool: True if tool calls were made, False otherwise.
        """
        # --- Construct the system message ---
        system_message = Message.system_message(
            format_prompt(
                "tool_call",
                tool_description=self.available_tools.get_tool_descriptions(),
                tool_names=[tool.name for tool in self.available_tools.tools],
            )
        )

        # Format next_step_prompt and add to memory
        prompt = format_prompt(
            "message",
            user_input=self.next_step_prompt,
            history=self.memory.to_dict_list(),
        )
        self.memory.add_message(Message.user_message(prompt))

        # Call the LLM
        response, tool_calls = await self.llm.ask_tool(
            messages=self.memory.get_messages(),
            system_msgs=[system_message],
            tools=self.available_tools.to_params(),
        )
        logger.info(f"✨ Agent's thoughts: \n{response.content}")

        if tool_calls:
            self.tool_calls = tool_calls
            logger.info(f"🛠️  Agent selected {len(tool_calls)} tools to use")
            tool_names = [tool_call.function.name for tool_call in tool_calls]
            logger.info(f"🧰 Tools being prepared: {tool_names}")
            # Store tool call response in memory
            self.memory.add_message(
                Message.assistant_message(content=response.content, tool_calls=tool_calls)
            )
            return True  # Continue to act()
        else:
            # If no tool calls, we're done. Update memory with the response.
            if response.content is not None:  # Check for None content
                self.memory.add_message(
                    Message.assistant_message(content=response.content)
                )  # Add response to memory
            return False

    async def act(self) -> str:
        """
        Execute tools and return the result.

        Returns:
            str: The result of the tool execution.
        """
        logger.info("Agent is calling the act method")
        messages = self.memory.get_messages()
        last_message = messages[-1]

        if last_message.role == "assistant" and last_message.tool_calls:
            tool_calls = last_message.tool_calls
            results = await self.execute_tool_calls(tool_calls)

            # After executing tool calls, update memory with tool results
            for tool_call, result in zip(tool_calls, results):
                if isinstance(result, ToolResult) and result.output:
                    self.update_memory(
                        "tool",
                        str(result.output),
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )  # Add result to memory
                elif isinstance(result, ToolResult) and result.error:
                    # If there was an error, store the error message in memory
                    self.update_memory(
                        "tool",
                        f"Error: {result.error}",
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )
            return ""  # Return empty string.
        else:
            # If no tool calls, nothing more to do
            return ""  # Or some other appropriate value

    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """
        Executes a list of tool calls and returns the results.

        Args:
            tool_calls: A list of ToolCall objects representing the tools to be called.

        Returns:
            A list of ToolResult objects, each containing the result of a tool call.
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool = self.available_tools.get_tool(tool_name)

            if tool is None:
                results.append(
                    ToolFailure(
                        error=f"Error: Tool '{tool_name}' not found.",
                    )
                )
                continue

            try:
                arguments = json.loads(tool_call.function.arguments)
                result = await tool.execute(**arguments)
                results.append(result)

            except Exception as e:
                results.append(
                    ToolFailure(error=f"Error: {str(e)}")
                )
        return results

    async def _handle_special_tool(self, tool_call: ToolCall) -> str:
        """Handles special tools like 'terminate'."""
        tool_name = tool_call.function.name
        tool_input_str = tool_call.function.arguments

        logger.info(f"🏁 Special tool '{tool_name}' has completed the task!")
        result = await self.available_tools.execute(
            name=tool_name, tool_input=tool_input_str
        )  # Await the result
        return f"Observed output of cmd `{tool_name}` executed:\n{result.output}"
