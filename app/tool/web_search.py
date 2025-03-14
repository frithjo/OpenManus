# app/tool/web_search.py
import json
from typing import Dict

from pydantic import Field

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
#from app.tool.serper_api_wrapper import SerperAPIWrapper  # Remove relative import
from app.tool import SerperAPIWrapper # Changed.

class WebSearch(BaseTool):
    """A tool for performing web searches."""

    name: str = "web_search"
    description: str = (
        "A tool for performing web searches. "
        "It's useful for finding information on the internet. "
        "Input should be the query."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
        },
        "required": ["query"],
    }

    api_wrapper: SerperAPIWrapper = Field(default_factory=SerperAPIWrapper)

    async def execute(self, query: str) -> ToolResult: # Changed.
        """Execute the web search tool."""

        logger.info(f"Searching the web for: {query}")
        try:
            # SerperAPIWrapper's search method returns a JSON string.
            search_results_json = await self.api_wrapper.results(query) # Changed
            search_results = json.loads(search_results_json)

             # Check for errors in the Serper API response.  This is important
            # because the Serper API can return error messages *within* a
            # successful HTTP response (status code 200).
            if "error" in search_results:
                return ToolResult(
                    output=None,
                    error=search_results["error"],
                )
            # Extract organic results, handling potential KeyError
            organic_results = search_results.get("organic", [])
            if not organic_results:
                return ToolResult(
                    output="No organic search results found.",
                    error=None
                    )
            # If we got here, we have successful results, we need to return those
            result_links = [result["link"] for result in organic_results] #extract just the links
            return ToolResult(
                    output=result_links, #return the links
                    error=None
                )
        except Exception as e:
            logger.exception(f"Error during web search: {e}")
            return ToolResult(output=None, error=str(e))