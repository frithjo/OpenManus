# app/agent/manus.py
from app.agent.toolcall import ToolCallAgent
from app.config import Config
from app.llm import LLM
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT  # Import prompts
from app.schema import ToolCall
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.python_execute import PythonExecute
from app.tool.web_search import WebSearch


class Manus(ToolCallAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT  # Use the imported prompts
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 2000
    max_steps: int = 20

    def __init__(self, llm: LLM, config: Config):
        """
        Initialize the Manus agent.

        Args:
            llm: The language model instance to be used.
            config: The configuration instance for the agent.
        """
        # Initialize the ToolCollection with the desired tools
        tools = [
            PythonExecute(),
            WebSearch(),
            BrowserUseTool(),
            FileSaver(),
            Terminate(),
        ]
        # Call the superclass constructor with the ToolCollection instance
        super().__init__(
            llm=llm,
            available_tools=ToolCollection(tools),
            system_prompt=self.system_prompt,
            next_step_prompt=self.next_step_prompt,
            config=config,
        )

    async def _handle_special_tool(self, tool_call: ToolCall):
        """Handles special tools."""
        if tool_call.function.name == Terminate().name:
            # Now use the correct tool
            browser_tool = self.available_tools.get_tool(BrowserUseTool().name)
            if browser_tool:
                await browser_tool.cleanup()

        return await super()._handle_special_tool(tool_call)
