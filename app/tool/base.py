from abc import ABC, abstractmethod
from typing import Any, Optional


class ToolResult:
    """
    Represents the result of a tool execution.

    Attributes:
        output (Optional[str]): The output of the tool, if successful.
        error (Optional[str]): The error message, if the tool failed.
        system (Optional[str]): System or debug information.
    """

    def __init__(
        self,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        system: Optional[str] = None,
    ):
        self.output = (
            str(output) if output is not None else None
        )  # Convert output to string
        self.error = error
        self.system = system


class BaseTool(ABC):
    """Abstract base class for tools."""

    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def execute(self, *args, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters. Must be implemented by subclasses."""
        raise NotImplementedError


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class AgentAwareTool:
    agent: Optional = None
