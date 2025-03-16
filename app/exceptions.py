# app/exceptions.py
class ToolError(Exception):
    """Custom exception for tool-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AgentError(Exception):
    """Custom exception for agent-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class LLMError(Exception):
    """Custom exception for LLM-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class MemoryError(Exception):
    """Custom exception for memory-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class SchemaError(Exception):
    """Custom exception for schema-related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
