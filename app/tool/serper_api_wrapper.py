# app/tool/serper_api_wrapper.py
import os
from typing import Any, Dict, Optional

import aiohttp
from dotenv import load_dotenv

from app.logger import logger  # Import the logger


# Load environment variables
load_dotenv()


class SerperAPIWrapper:
    """
    Wrapper around the Serper.dev Google Search API.

    This class provides methods to interact with the Serper API asynchronously.
    It handles API key management, request construction, and response parsing.
    """

    def __init__(self, serper_api_key: Optional[str] = None) -> None:
        """
        Initializes the SerperAPIWrapper.

        Args:
            serper_api_key: The Serper.dev API key.  If not provided, it's
                loaded from the SERPER_API_KEY environment variable.
        """
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")
        if not self.serper_api_key:
            raise ValueError(
                "Serper API key not found.  Set the SERPER_API_KEY environment variable or pass it to the constructor."
            )
        self.search_url = "https://google.serper.dev/search"
        self.headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json",
        }

    async def results(self, query: str) -> str:
        """
        Performs a search and returns the raw JSON response as a string.

        Args:
            query: The search query string.

        Returns:
            The JSON response from the Serper API as a string.

        Raises:
            aiohttp.ClientError: If there's an error during the HTTP request.
            Exception: For other errors, including Serper API errors.
        """
        payload: Dict[str, Any] = {"q": query}  # Use Any for flexibility

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.search_url, headers=self.headers, json=payload
                ) as response:
                    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                    return await response.text()  # Return raw JSON string

            except aiohttp.ClientError as e:
                logger.error(f"aiohttp client error: {e}")  # Log the aiohttp error
                raise  # Re-raise the exception to be handled by the caller

            except Exception as e:
                logger.exception(f"An unexpected error occurred: {e}")
                raise

    async def search(self, query: str) -> str:
        """Alias for the results method (for backwards compatibility)"""
        return await self.results(query)
