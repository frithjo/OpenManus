"""Collection classes for managing multiple tools."""
from typing import Any, Dict, List, Union, Optional

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolFailure, ToolResult
import json


class ToolCollection:
    """A collection of defined tools."""

    def __init__(self, tools: Optional[List[BaseTool]] = None):
        self.tools: List[BaseTool] = tools if tools is not None else []
        self.tool_map: Dict[str, BaseTool] = {tool.name: tool for tool in self.tools}

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> List[Dict[str, Any]]:
        """
        Convert each tool in the collection to a serializable dict.
        If a tool provides a 'model_dump()' method, use that; otherwise, fallback to __dict__.
        """
        return [
            tool.model_dump() if hasattr(tool, "model_dump") else tool.__dict__
            for tool in self.tools
        ]

    def get_tool_descriptions(self) -> List[str]:
        return [tool.description for tool in self.tools]

    async def execute(
        self, *, name: str, tool_input: Union[Dict, str] = None
    ) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")

        if isinstance(tool_input, str):
            try:
                # Attempt to parse JSON if tool_input is a string
                tool_input = json.loads(tool_input)
            except json.JSONDecodeError:
                raise ValueError(
                    f"Invalid input for tool '{name}'. Expected JSON, got: {tool_input}"
                )

        try:
            if tool_input:
                result = await tool.execute(**tool_input)
            else:
                result = await tool.execute()
            return result
        except ToolError as e:
            return ToolFailure(error=e.message) # Corrected: Access e.message
        except Exception as e:
           return ToolFailure(error=str(e))

    async def execute_all(self) -> List[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result) #type: ignore
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    def get_tool(self, name: str) -> Union[BaseTool, None]:
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool):
        self.tools.append(tool)
        self.tool_map[tool.name] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        for tool in tools:
            self.add_tool(tool)
        return self
