# app/agent/planning.py
import json
import time
from typing import Dict, List, Optional

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.config import Config
from app.llm import LLM
from app.logger import logger
from app.prompt.planning import NEXT_STEP_PROMPT, PLANNING_SYSTEM_PROMPT
from app.schema import Message, ToolCall, ToolChoice
from app.tool import PlanningTool, Terminate, ToolCollection


class PlanningAgent(ToolCallAgent):
    """
    An agent that creates and manages plans to solve tasks.

    This agent uses a planning tool to create and manage structured plans,
    and tracks progress through individual steps until task completion.
    """

    name: str = "planning"
    description: str = "An agent that creates and manages plans to solve tasks"

    system_prompt: str = PLANNING_SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection([PlanningTool(), Terminate()])
    )
    tool_choices: ToolChoice = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    active_plan_id: Optional[str] = Field(default=None)
    config: Config

    # Add a dictionary to track the step status for each tool call
    step_execution_tracker: Dict[str, Dict] = Field(default_factory=dict)
    current_step_index: Optional[int] = None

    max_steps: int = 20

    def __init__(self, llm: LLM, config: Config):
        """
        Initialize the PlanningAgent.

        Args:
            llm: The language model instance to be used.
            config: The configuration instance for the agent.
        """
        system_prompt = PLANNING_SYSTEM_PROMPT
        next_step_prompt = NEXT_STEP_PROMPT
        tools = [PlanningTool(), Terminate()]  # Define the tools
        self.config = config  # Add the config
        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            next_step_prompt=next_step_prompt,
            available_tools=ToolCollection(tools),
            config=config,
        )

    @model_validator(mode="after")
    def check_tools(self) -> "PlanningAgent":
        """Ensure required tools are present."""
        if not {"planning", "terminate"}.issubset(self.available_tools.tool_map.keys()):
            raise ValueError("PlanningAgent requires 'planning' and 'terminate' tools.")
        return self

    async def think(self) -> bool:
        """Decide the next action based on plan status."""

        # If there's no active plan, something went wrong. Don't proceed.
        if not self.active_plan_id:
            logger.error("No active plan ID.  Cannot think.")
            return False

        prompt = (
            f"CURRENT PLAN STATUS:\n{await self.get_plan()}\n\n{self.next_step_prompt}"
        )

        self.update_memory("user", prompt)  # Add to memory
        # Get the current step index before thinking
        self.current_step_index = await self._get_current_step_index()
        result = await super().think()  # Call super().think

        # After thinking, if we decided to execute a tool and it's not a planning tool or special tool,
        # associate it with the current step for tracking
        if result and self.tool_calls:
            latest_tool_call = self.tool_calls[0]  # Get the most recent tool call
            if (
                latest_tool_call.function.name != "planning"
                and latest_tool_call.function.name not in self.special_tool_names
                and self.current_step_index is not None
            ):
                self.step_execution_tracker[latest_tool_call.id] = {
                    "step_index": self.current_step_index,
                    "tool_name": latest_tool_call.function.name,
                    "status": "pending",  # Will be updated after execution
                }

        return result

    async def act(self) -> str:
        """Execute a step and track its completion status."""
        result = await super().act()

        # After executing the tool, update the plan status
        if self.tool_calls:
            latest_tool_call = self.tool_calls[0]

            # Update the execution status to completed
            if latest_tool_call.id in self.step_execution_tracker:
                self.step_execution_tracker[latest_tool_call.id]["status"] = "completed"
                self.step_execution_tracker[latest_tool_call.id]["result"] = result

                # Update the plan status if this was a non-planning, non-special tool
                if (
                    latest_tool_call.function.name != "planning"
                    and latest_tool_call.function.name not in self.special_tool_names
                ):
                    await self.update_plan_status(latest_tool_call.id)

        return result

    async def get_plan(self) -> str:
        """Retrieve the current plan status."""
        if not self.active_plan_id:
            return "No active plan. Please create a plan first."

        result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )
        return result.output if hasattr(result, "output") else str(result)

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with an optional initial request."""
        if request:
            # Create the initial plan.
            await self.create_initial_plan()
        return await super().run(request)

    async def update_plan_status(self, tool_call_id: str) -> None:
        """
        Update the current plan progress based on completed tool execution.
        Only marks a step as completed if the associated tool has been successfully executed.
        """
        if not self.active_plan_id:
            return

        if tool_call_id not in self.step_execution_tracker:
            logger.warning(f"No step tracking found for tool call {tool_call_id}")
            return

        tracker = self.step_execution_tracker[tool_call_id]
        if tracker["status"] != "completed":
            logger.warning(f"Tool call {tool_call_id} has not completed successfully")
            return

        step_index = tracker["step_index"]

        try:
            # Mark the step as completed
            await self.available_tools.execute(
                name="planning",
                tool_input={
                    "command": "mark_step",
                    "plan_id": self.active_plan_id,
                    "step_index": step_index,
                    "step_status": "completed",
                },
            )
            logger.info(
                f"Marked step {step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")

    async def _get_current_step_index(self) -> Optional[int]:
        """
        Parse the current plan to identify the first non-completed step's index.
        Returns None if no active step is found.
        """
        if not self.active_plan_id:
            return None
        try:
            planning_tool = self.available_tools.get_tool("planning")
            plan = planning_tool.plans.get(
                self.active_plan_id
            )  # Access plan using get()
            if plan is None:
                logger.warning(
                    f"Plan with id {self.active_plan_id} not found in get_current_step"
                )
                return None  # Or raise, depending on how critical this is
            for i, step in enumerate(plan["steps"]):
                if step.status in ("not_started", "in_progress"):
                    # Mark current step as in_progress
                    await self.available_tools.execute(
                        name="planning",
                        tool_input={
                            "command": "mark_step",
                            "plan_id": self.active_plan_id,
                            "step_index": i,
                            "step_status": "in_progress",
                        },
                    )
                    return i
            return None

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None

    async def create_initial_plan(self) -> None:
        """Create an initial plan based on the request."""

        # Get the initial request from memory
        user_messages = [msg for msg in self.memory.messages if msg.role == "user"]
        if not user_messages:
            logger.error("No user request found to create initial plan.")
            return

        initial_request = user_messages[0].content  # Get the *first* user message
        if initial_request is None:
            logger.error("No user request found to create initial plan.")
            return

        # Generate a plan ID using the time module
        self.active_plan_id = f"plan_{int(time.time())}"
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        prompt = f"Analyze the request and create a plan with ID {self.active_plan_id}: {initial_request}"

        messages = [Message.user_message(prompt)]  # Correct: Uses Message class

        response = await self.llm.ask_tool(
            messages=messages,  # Use the constructed messages
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.REQUIRED,  # Force tool use for plan creation
        )
        content = response.content if response.content is not None else ""

        assistant_msg = Message.assistant_message(
            content=content, tool_calls=response.tool_calls
        )
        self.memory.add_message(assistant_msg)

        plan_created = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                try:
                    # Parse arguments using json.loads
                    tool_input = json.loads(tool_call.function.arguments)
                    # Add the plan_id to the tool input.
                    tool_input["plan_id"] = self.active_plan_id  # Add the plan id
                    result = await self.available_tools.execute(
                        name=tool_call.function.name, tool_input=tool_input
                    )

                    logger.info(
                        f"Executed tool {tool_call.function.name} with result: {result}"
                    )

                    # Add tool response to memory
                    tool_msg = Message.tool_message(
                        content=str(result),  # Ensure result is a string
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )
                    self.memory.add_message(tool_msg)
                    plan_created = True

                except Exception as e:
                    logger.exception(
                        f"Error executing planning tool: {e}"
                    )  # use logger.exception to log error stacktrace
                    plan_created = False
                    break  # Exit loop on error

        if not plan_created:
            logger.warning("No plan created from initial request")
            # Add a message to memory indicating failure
            self.update_memory("assistant", "Failed to create initial plan.")
