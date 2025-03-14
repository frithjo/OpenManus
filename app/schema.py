import json
from enum import Enum
from typing import Any, List, Literal, Optional, Dict, Union

from pydantic import BaseModel, Field, root_validator, validator, model_validator


class Role(str, Enum):
    """Message role options."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolChoice(str, Enum):
    """Tool choice options."""

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


class AgentState(str, Enum):
    """Agent execution states."""

    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class FunctionCall(BaseModel):
    name: str
    arguments: str

    def get_arguments_as_dict(self) -> Union[Dict[str, Any], None]:
        """
        Parses the JSON string in arguments and returns a dictionary.
        Returns None if parsing fails.
        """
        try:
            return json.loads(self.arguments)
        except (json.JSONDecodeError, TypeError):
            return None


class ToolCall(BaseModel):
    """Represents a tool/function call in a message."""

    id: str
    type: str = "function"
    function: FunctionCall


class Message(BaseModel):
    """Represents a chat message in the conversation."""

    role: Role
    content: Optional[str] = None  # Content can be None for tool calls
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None

    @model_validator(mode="after")
    def check_content_or_tool_calls(self) -> "Message":
        """
        Ensures that either content is provided or tool_calls are present.
        This is useful to prevent accidental empty messages.
        """
        content, tool_calls = self.content, self.tool_calls
        if not content and not tool_calls:
            raise ValueError("Either 'content' or 'tool_calls' must be provided.")
        return self

    def to_chat_completion_message(self) -> Dict[str, Any]:
        """
        Converts the Message object to the format expected by OpenAI's API.
        You may adjust this method to support additional API formats (e.g., function_call).
        """
        message: Dict[str, Any] = {"role": self.role.value}
        if self.content:
            message["content"] = self.content
        if self.tool_calls is not None:
            # Retain 'tool_calls' for compatibility with your LLM conversion functions.
            message["tool_calls"] = [
                tool_call.model_dump() for tool_call in self.tool_calls
            ]
        if self.name is not None:
            message["name"] = self.name
        return message

    def __add__(self, other: Union["Message", List["Message"]]) -> List["Message"]:
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other: List["Message"]) -> List["Message"]:
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    @classmethod
    def user_message(cls, content: str) -> "Message":
        return cls(role=Role.USER, content=content)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(
        cls, content: Optional[str] = None, tool_calls: Optional[List[ToolCall]] = None
    ) -> "Message":
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool_message(cls, content: str, tool_call_id: str, name: str) -> "Message":
        """Creates a tool message."""
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)

    def __str__(self) -> str:
        """Provides a human-readable representation of the message."""
        return f"[{self.role.value.upper()}] {self.name or ''}: {self.content or ''}"


class Memory(BaseModel):
    """
    Manages the conversation history (a list of Message objects).
    """

    messages: List[Message] = Field(default_factory=list)
    max_messages: int = 100  # You can adjust this

    def add_message(self, message: Message):
        """Adds a message to the history."""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]  # Keep only the last max_messages

    def clear(self):
        """Clears the conversation history."""
        self.messages.clear()

    def get_messages(self) -> List[Message]:
        """Returns all messages in the history."""
        return self.messages

    def to_dict_list(self) -> List[Dict]:
        """Convert messages to list of dicts."""
        return [msg.model_dump() for msg in self.messages]


class Step(BaseModel):
    """Represents a step in a plan."""

    description: str
    status: Literal["not_started", "in_progress", "completed", "blocked"] = "not_started"
    notes: str = ""
    # Consider changing this field to a specific type (e.g., ToolCall) if your steps always reference a tool call.
    tool_call: Optional[Dict[str, Any]] = None
