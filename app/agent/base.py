# app/agent/base.py
from abc import ABC, abstractmethod
from typing import  Optional

from app.llm import LLM  # Corrected import: Use the existing LLM class
from app.logger import logger
from app.schema import AgentState, Memory, Message  # Corrected import
from app.prompt.message import MessagePrompt # Corrected import
from app.config import Config


class Agent(ABC):
    """
    Abstract base class for all agents.

    An agent interacts with a user and/or tools to process requests.
    """

    name: str
    description: str

    llm: LLM
    memory: Memory = Memory()
    state: AgentState = AgentState.IDLE
    

    def __init__(self, llm: LLM, config:Config):
        """Initialize the agent with an LLM."""
        self.llm = llm
        self.config = config
        self.message_prompt : MessagePrompt = MessagePrompt(
        """
        {{- history -}}
        {% if history -%}
        {{user_input}}
        {%- else -%}
        {{user_input}}
        {%- endif -%}
        """)

    @abstractmethod
    async def think(self) -> bool:
        """Decide what to do next."""
        raise NotImplementedError

    @abstractmethod
    async def act(self) -> str:
        """Do the action."""
        raise NotImplementedError

    async def run(self, request: Optional[str] = None) -> str:
        """
        Run the agent.

        Args:
            request: An optional initial user request or prompt.

        Returns:
            str: The final result or output of the agent's execution.
        """
        if request:
            self.update_memory("user", request)
        step = 0
        max_steps = 20  # Prevent infinite loops, set your own limit.
        self.state = AgentState.RUNNING
        result = ""
        while self.state == AgentState.RUNNING and step < max_steps:
            step += 1
            logger.info(f"Executing step {step}/{max_steps}")

            should_continue = await self.think()  # Check if we should continue
            if not should_continue:
                self.state = AgentState.FINISHED
                break

            result = await self.act()
            if not result:
                self.state = AgentState.IDLE
                break

            if result:
                self.memory.add_message(self.message_prompt.assistant_message(content=result))

        return result

    def update_memory(
        self,
        role: str,
        content: str,
        **kwargs,
    ) -> None:
        """
        Add a message to the agent's memory.

        Args:
            role: The role of the message (e.g., "user", "system", "assistant", "tool").
            content: The content of the message.
            **kwargs: Additional keyword arguments to be passed to the Message class.
        """

        if role == "user":
            msg = Message.user_message(content)
        elif role == "system":
            msg = Message.system_message(content)
        elif role == "assistant":
            msg = Message.assistant_message(content, **kwargs) #type: ignore
        elif role == "tool":
            msg = Message.tool_message(content=content, **kwargs)
        else:
            raise ValueError(f"Unsupported message role: {role}")

        self.memory.add_message(msg)
