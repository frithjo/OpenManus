# app/prompt/message.py
from app.schema import Message
from app.prompt.base import PromptTemplate

class MessagePrompt:
    """
    A class to create and manage message prompts.

    This class uses a PromptTemplate to format user input and conversation history.
    """
    def __init__(self, template: str):
        """
        Initialize a MessagePrompt instance.

        Args:
            template: The template string used for formatting the prompt.
        """
        self.template = PromptTemplate(template)

    def system_message(self, content: str) -> Message:
        """
        Creates a system message.

        Args:
            content: The content of the system message.

        Returns:
            A Message object representing a system message.
        """
        return Message.system_message(content)

    def user_message(self, content: str) -> Message:
        """
        Creates a user message.

        Args:
            content: The content of the user message.

        Returns:
            A Message object representing a user message.
        """
        return Message.user_message(content)

    def assistant_message(self, content: str = "", tool_calls=None) -> Message:
        """
        Creates an assistant message.

        Args:
            content: The content of the assistant message.
            tool_calls: Optional tool calls associated with the assistant message.

        Returns:
            A Message object representing an assistant message.
        """
        return Message.assistant_message(content=content, tool_calls=tool_calls)
