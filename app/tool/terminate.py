# app/tool/terminate.py
from app.tool.base import BaseTool, ToolResult


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
        "required": ["status", "reason"],
    }

    async def execute(self, status: str, reason: str) -> ToolResult:
        """Terminate the conversation."""
        return ToolResult(
            output=f"The interaction has been completed with status: {status}\n{reason}"
        )
