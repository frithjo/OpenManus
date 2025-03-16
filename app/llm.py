import os
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import AsyncOpenAI
from openai import AzureOpenAI as AsyncAzureOpenAI
from openai.types.chat import ChatCompletionMessageToolCall
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import Config  # Import Config (not config instance)
from app.logger import logger
from app.schema import Message, ToolCall  # Import Message and ToolCall


def get_tool_calls(
    calls: Union[
        ChatCompletionMessageToolCall, List[ChatCompletionMessageToolCall], None
    ]
) -> List[ToolCall]:
    """
    Convert tool call data from the OpenAI API response to a list of ToolCall objects.
    Supports both a single call (as a dict-like object from the new API) or a list of calls.

    Args:
        calls: A ChatCompletionMessageToolCall object, a list of them, or None.

    Returns:
        A list of ToolCall objects.
    """
    if not calls:
        return []
    # Ensure we have a list (if a single call is provided, wrap it in a list)
    calls_list = calls if isinstance(calls, list) else [calls]
    converted_calls = []
    for call in calls_list:
        if call.type != "function":
            logger.warning(f"Unsupported tool call type: {call.type}. Skipping.")
            continue
        converted_calls.append(
            ToolCall(
                id=getattr(call, "id", "function_call"),
                type=call.type,
                function={
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            )
        )
    return converted_calls


class LLM:
    """
    Large Language Model (LLM) class to interact with the OpenAI API.
    """

    def __init__(self, config: Config, client: Optional[AsyncOpenAI] = None):
        """
        Initializes the LLM.

        Args:
            config: The configuration instance for the LLM.
            client: An optional pre-configured OpenAI client.
        """
        # Determine if using Azure or standard OpenAI endpoint
        if config.llm.get("api_type") == "azure":
            config.llm["default"].api_type
            api_version = config.llm["default"].api_version
            base_url = config.llm["default"].base_url
            api_key = config.llm["default"].api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable, "
                    "or add it to your config.toml file"
                )
            self.client = client or AsyncAzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=base_url,
            )
        else:
            api_key = config.llm["default"].api_key or os.getenv("OPENAI_API_KEY")
            base_url = config.llm["default"].base_url
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable, "
                    "or add it to your config.toml file"
                )
            self.client = client or AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.model = config.llm["default"].model  # Get model from config
        self.max_tokens = config.llm["default"].max_tokens
        self.temperature = config.llm["default"].temperature

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def ask(
        self,
        messages: List[Message],
        system_msgs: Optional[List[Message]] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Ask the LLM a question and get a response.

        Args:
            messages: List of Message objects representing the conversation history.
            system_msgs: Optional list of system messages.
            stream: Whether to use streaming mode.
            temperature: Temperature for the model (overrides default if provided).

        Returns:
            A string representing the LLM's response.
        """
        # Prepend any system messages
        if system_msgs:
            messages = system_msgs + messages

        # Format messages to the API-expected format
        messages = self.format_messages(messages)

        if not stream:
            # Non-streaming request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=temperature or self.temperature,
                stream=False,
            )
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty or invalid response from LLM")
            return response.choices[0].message.content

        # Streaming request; note: in production you may wish to yield these chunks instead of logging/printing.
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=temperature or self.temperature,
            stream=True,
        )

        collected_messages = []
        async for chunk in response:
            # In the updated API, the delta may include parts of the message content.
            chunk_message = chunk.choices[0].delta.content or ""
            collected_messages.append(chunk_message)
            logger.info(chunk_message)  # Log each chunk (or use a callback as needed)

        full_response = "".join(collected_messages).strip()
        if not full_response:
            raise ValueError("Empty response from streaming LLM")
        return full_response

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def ask_tool(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        system_msgs: Optional[List[Message]] = None,
    ) -> Tuple[Message, List[ToolCall]]:
        """
        Ask the LLM a question with functions (tools) enabled and return both the response and any tool calls.

        Args:
            messages: List of Message objects for conversation history.
            tools: List of function descriptors (tools) for the LLM to potentially call.
            system_msgs: Optional system messages.

        Returns:
            A tuple of:
              - Message object (assistant response)
              - List of ToolCall objects representing any function calls.
        """
        if system_msgs:
            messages = system_msgs + messages

        messages = self.format_messages(messages)

        # Use updated parameter name "functions" (instead of "tools")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=tools,
            stream=False,
            tool_choice="auto",  # Let the model decide; adjust per your needs.
        )

        content = response.choices[0].message.content or ""
        # In the latest API, function calls are returned in the "function_call" field
        tool_call_data = getattr(response.choices[0].message, "function_call", None)
        converted_tool_calls = get_tool_calls(tool_call_data)

        return (
            Message(role="assistant", content=content, tool_calls=converted_tool_calls),
            converted_tool_calls,
        )

    @staticmethod
    def format_messages(messages: List[Message]) -> List[dict]:
        """
        Format messages to the format expected by the OpenAI API.
        """
        formatted_messages = []
        for message in messages:
            if isinstance(message, Message):
                formatted_messages.append(message.to_chat_completion_message())
            else:
                raise TypeError(f"Unsupported message type: {type(message)}")
        return formatted_messages
