# app/prompt/tool_use.py

# Define constants for system prompts
TOOL_DESCRIPTION = """
You have access to the following tools:
{tool_description}
"""

FORMAT_INSTRUCTIONS = """
Your response MUST be valid JSON, and the outermost encapsulating object MUST be a single JSON object.
The ONLY top-level keys you should use are one of the following: {tool_names}

You MUST include the full JSON blob in your response.

"""

# JSON formatting
JSON_START = "```json"
JSON_END = "```"