from typing import List

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.tool import ToolCollection
from app.tool.bash import Bash
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate


class SWEAgent(ToolCallAgent):
    """An agent that implements the SWEAgent paradigm for executing code and natural conversations."""

    name: str = "SWEAgent"
    description: str = "an autonomous AI programmer that interacts directly with the computer to solve tasks."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            [Bash(), StrReplaceEditor(), Terminate()]
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])
    max_steps: int = 30


@model_validator(mode="after")
def check_tools(self) -> "SWEAgent":
    """Ensure required tools are present."""
    if not {"bash", "str_replace_editor", "terminate"}.issubset(
        self.available_tools.tool_map.keys()
    ):
        raise ValueError(
            "SWEAgent requires 'bash', 'str_replace_editor', and 'terminate' tools."
        )
    return self
    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."

    async def think(self) -> bool:
        """Process current state and decide next action"""
        # Update working directory
        self.working_dir = await self.bash.execute("pwd")
        self.next_step_prompt = self.next_step_prompt.format(
            current_dir=self.working_dir
        )

        return await super().think()
