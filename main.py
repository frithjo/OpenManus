# main.py
import asyncio

from app.agent.manus import Manus
from app.config import Config
from app.llm import LLM
from app.logger import logger
from app.tool import ToolCollection, WebSearch, BrowserUseTool, PythonExecute, Terminate, FileSaver, PlanningTool

async def main():
    """Main function to run the agent."""
    logger.info("Starting agent...")

    config = Config()
    llm = LLM(config=config)

    # Correctly instantiate the tools *before* adding them to the ToolCollection
    tools = [
        WebSearch(),  # Create instances!
        BrowserUseTool(), # Create instances!
        PythonExecute(), # Create instances!
        Terminate(),     # Create instances!
        FileSaver(),     # Create instances!
        PlanningTool(), # Create instance!, dummy ToolCollection.
    ]
    tool_collection = ToolCollection(tools=tools)
    # Replace the dummy ToolCollection
    for tool in tools:
        if isinstance(tool,PlanningTool):
            tool.tool_collection = tool_collection

    agent = Manus(llm=llm, config=config) #use tool_collection

    while True:
        try:
            user_prompt = input("Enter your prompt (or type 'exit' to quit): ")
            if user_prompt.lower() == "exit":
                break

            logger.info("Processing your request...")
            await agent.run(user_prompt)  # Pass the user's prompt to the run method

        except KeyboardInterrupt:
            logger.warning("Operation interrupted by user.")
            break
        except Exception:
            logger.exception("An unexpected error occurred.")
            break

if __name__ == "__main__":
    asyncio.run(main())  # Use asyncio.run() to run the async main function
