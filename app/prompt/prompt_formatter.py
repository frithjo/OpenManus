# app/prompt/prompt_formatter.py

from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound


def format_prompt(template_name: str, **kwargs: Any) -> str:
    """
    Formats a prompt template using Jinja2.

    Args:
        template_name: The name of the template file (without extension).
        **kwargs: Keyword arguments to pass to the template.

    Returns:
        The formatted prompt string.

    Raises:
        ValueError: If the template file is not found or if there's a Jinja2 rendering error.
    """
    # Provide a default for format_instructions if not present
    kwargs.setdefault("format_instructions", "")
    kwargs.setdefault("json_start", "")
    kwargs.setdefault("json_end", "")
    env = Environment(
        loader=FileSystemLoader("app/prompt/templates"), undefined=StrictUndefined
    )
    try:
        # Load the template
        template = env.get_template(f"{template_name}.jinja")
        # Render the template with provided keyword arguments
        return template.render(**kwargs)
    except TemplateNotFound as e:
        raise ValueError(f"Template '{template_name}' not found: {e}") from e
    except Exception as e:
        raise ValueError(f"Error rendering template '{template_name}': {e}") from e
