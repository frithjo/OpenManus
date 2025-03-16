# main.py
import asyncio
import signal

from app.agent.manus import Manus
from app.config import Config
from app.llm import LLM
from app.logger import logger

async def shutdown_agent(agent):
    """Perform cleanup for all available tools."""
    if hasattr(agent, 'available_tools') and agent.available_tools:
        for tool in agent.available_tools.tools:
            if hasattr(tool, 'cleanup') and callable(getattr(tool, 'cleanup')):
                try:
                    await tool.cleanup()  # Ensure cleanup is awaited
                except Exception as e:
                    logger.error(f"Error during cleanup of {tool.name}: {e}")
    logger.info("OpenManus execution complete.")

async def main():
    """Main function to run the agent."""
    logger.info("Starting agent...")
    agent = None

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():  # Combined signal handler
        logger.warning("Shutdown signal received, initiating graceful shutdown...")
        stop_event.set()

    # Register signal handlers for graceful shutdown (works on Unix)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)  # Register for both signals
    # Note: Signal handling in this way is not reliable on Windows.
    #       For Windows, consider using SetConsoleCtrlHandler (pywin32)
    #       or a different approach.

    try:
        config = Config()
        llm = LLM(config=config)
        agent = Manus(llm=llm, config=config)  # Agent handles its own configuration & tool initialization
        user_prompt = input("Enter your prompt (or type 'exit' to quit): ")
        if user_prompt.lower().strip() == "exit":
            logger.info("Exiting...")
            return
        await agent.run(user_prompt)  # Process initial prompt

        # Optional: limit the maximum number of iterations to avoid infinite loops
        max_steps = 20
        step = 1
        while agent.state != "FINISHED" and step < max_steps and not stop_event.is_set():
            await agent.run()  # Continue conversation without new user input
            step += 1
        if step >= max_steps:
            logger.warning("Maximum number of steps reached, terminating agent.")
        elif agent.state == "FINISHED":
            logger.info("Agent finished successfully") #log if it was successful
    except KeyboardInterrupt:
        logger.warning("Operation interrupted by user (KeyboardInterrupt).")
    except Exception:
        logger.exception("An unexpected error occurred.")
    finally:
        if agent is not None:
            await shutdown_agent(agent)
        else:
            logger.info("Agent was not initialized.")

if __name__ == "__main__":
    asyncio.run(main())
