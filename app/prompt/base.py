#app/prompt/base.py
from typing import Any, List, Optional
from jinja2 import Environment, FileSystemLoader, meta, Undefined

class PromptTemplate:
    """
    A template for prompts.

    This class provides a simple wrapper around Jinja2 templating, allowing for
    easy creation and rendering of prompts.
    """

    def __init__(
        self,
        template: str,
        input_variables: Optional[List[str]] = None,
    ) -> None:
        """Initialize a PromptTemplate.
        Args:
            template: String representation of the template
            input_variables: List of input variables for the template. If not
                provided, they will be inferred from the template.
        """

        self.env = Environment()
        self.env.globals["len"] = len
        self.template_string = template
        self.template = self.env.from_string(template)

        if input_variables is None:
            # Infer input variables from the template
            self.input_variables = self._get_input_variables(template)
        else:
            self.input_variables = input_variables

        # Check for invalid variables (variables used in template but not in input_variables)
        parsed_content = self.env.parse(template)
        undefined_variables = meta.find_undeclared_variables(parsed_content)
        invalid_variables = [v for v in undefined_variables if v not in self.input_variables]
        if invalid_variables:
            raise ValueError(f"Invalid variables used in template: {invalid_variables}")

    def _get_input_variables(self, template_str: str) -> List[str]:
        """
        Parse the template string to extract used variables.
        Args:
            template_str: String representation of the template
        """
        parsed_content = self.env.parse(template_str)
        return list(meta.find_undeclared_variables(parsed_content))

    async def render(self, **kwargs: Any) -> str:
        """Asynchronously render the template with the provided keyword arguments.

        Args:
            **kwargs: Values for the input variables of the template

        Returns:
            Rendered template string

        Raises:
            ValueError: If a required variable is missing
        """
        # Check for missing variables
        missing_vars = [var for var in self.input_variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Missing values for input variables: {missing_vars}")

        # Check for extra variables (variables provided but not in input_variables)
        extra_vars = [var for var in kwargs if var not in self.input_variables]
        if extra_vars:
            print(f"Extra variables provided that are not in input_variables: {extra_vars}")
            # Remove extra variables
            for var in extra_vars:
                kwargs.pop(var)

        async def _render_async():
            try:
                return self.template.render(**kwargs)
            except Exception as e:
                raise ValueError(f"Error rendering template: {e}, {kwargs} , {self.input_variables}")

        return await _render_async()