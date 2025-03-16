# app/memory/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.schema import Message  # Import the Message class


class BaseMemory(ABC):
    """
    Abstract base class for memory implementations.
    All memory implementations should inherit from this class.
    """

    @abstractmethod
    def add_message(self, message: Message) -> None:
        """Adds a message to the memory."""
        raise NotImplementedError

    @abstractmethod
    def get_messages(self) -> List[Message]:
        """Retrieves all messages from the memory."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clears all messages from the memory."""
        raise NotImplementedError

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert messages to list of dicts"""
        return [msg.model_dump() for msg in self.get_messages()]


class SimpleMemory(BaseMemory):
    """
    A simple, in-memory list-based memory implementation.
    """

    def __init__(self):
        self.messages: List[Message] = []

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def get_messages(self) -> List[Message]:
        return self.messages

    def clear(self) -> None:
        self.messages = []


def get_memory(memory_config: Dict[str, Any]) -> BaseMemory:
    """
    Factory function to create a memory instance based on the configuration.

    Args:
        memory_config: A dictionary containing memory configuration.  Should have a "type"
            key indicating the memory type (e.g., "simple").  Other keys can
            provide additional configuration options specific to the memory type.

    Returns:
        An instance of a BaseMemory subclass.

    Raises:
        ValueError: If an unsupported memory type is specified.
    """
    memory_type = memory_config.get("type", "simple")  # Default to SimpleMemory

    if memory_type == "simple":
        return SimpleMemory()  # No configuration needed for SimpleMemory
    # elif memory_type == "database":  # Example of adding another memory type
    #     return DatabaseMemory(config["database_url"])
    # elif memory_type == "vector_db": # Example for vector database
    #     return VectorDBMemory(config["vector_db_url"])
    else:
        raise ValueError(f"Unsupported memory type: {memory_type}")
