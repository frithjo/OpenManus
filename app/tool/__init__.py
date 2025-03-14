# app/tool/__init__.py
from app.tool.base import BaseTool, ToolResult  # Import BaseTool and ToolResult
from app.tool.planning import PlanningTool  # Import PlanningTool
from app.tool.python_execute import PythonExecute  # Import PythonExecute
from app.tool.serper_api_wrapper import SerperAPIWrapper  # Import SerperAPIWrapper
from app.tool.web_search import WebSearch  # Import WebSearch
from app.tool.file_saver import FileSaver  # Import FileSaver
from app.tool.browser_use_tool import BrowserUseTool  # Import BrowserUseTool
from app.tool.tool_collection import ToolCollection #Import ToolCollection


class Terminate(BaseTool):
    """
    A tool that can be used to terminate the conversation.
    """

    name: str = "terminate"
    description: str = "Terminates the conversation."
    parameters: dict = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Whether the conversation was successfully completed or not.",
                "enum": ["success", "failure"],
            },
            "reason": {
                "type": "string",
                "description": "Reason for completing/failing the conversation.",
            },
        },
    }

    async def execute(self, status: str, reason: str) -> ToolResult:
        """Terminate the conversation."""
        return ToolResult(
            output=f"The interaction has been completed with status: {status}\n{reason}"
        )



# Make tools directly available when importing the package
__all__ = [
    "BaseTool",
    "Terminate",
    "ToolCollection",
    "PlanningTool",
    "PythonExecute",
    "SerperAPIWrapper",
    "WebSearch",
    "FileSaver",
    "BrowserUseTool",
]
