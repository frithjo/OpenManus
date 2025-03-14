# app/tool/python_execute.py
import sys
from io import StringIO
import multiprocessing
from app.tool.base import BaseTool, ToolResult


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions."""

    name: str = "python_execute"
    description: str = "Executes Python code string. Returns both the stdout and the return value of the code. Use print statements for debugging, as those are captured in stdout."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    def _run_code(self, code: str, result_queue: multiprocessing.Queue, safe_globals: dict) -> None:
        """Executes Python code in a sandboxed environment and captures stdout and return value."""
        original_stdout = sys.stdout
        try:
            output_buffer = StringIO()
            sys.stdout = output_buffer  # Redirect stdout

            # Execute the code and capture the return value
            locales = {}
            exec(code, safe_globals, locales)
            return_value = locales.get("result", None)  # Capture return value from 'result' variable

            result_queue.put((return_value, output_buffer.getvalue(), True))  # Send both

        except Exception as e:
            result_queue.put((None, str(e), False))  # Send error information
        finally:
            sys.stdout = original_stdout  # Restore stdout

    async def execute(
        self,
        code: str,
        timeout: int = 5, # Added type hint
    ) -> ToolResult:
        """
        Executes the provided Python code with a timeout.

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            ToolResult: Contains 'output' with the return value, 'stdout' with the standard output, and 'success' status.
        """
        with multiprocessing.Manager() as manager:
            result_queue = manager.Queue()  # Use a Queue for communication

            if isinstance(__builtins__, dict):
                safe_globals = {"__builtins__": __builtins__}
            else:
                safe_globals = {"__builtins__": __builtins__.__dict__.copy()}

            proc = multiprocessing.Process(
                target=self._run_code,
                args=(code, result_queue, safe_globals)
            )
            proc.start()
            proc.join(timeout)

            if proc.is_alive():
                proc.terminate()
                proc.join(1)  # Ensure termination
                return ToolResult(
                    output=None,
                    error=f"Execution timed out after {timeout} seconds",
                    system=f"Execution timed out after {timeout} seconds" #Added system message
                )

            try:
                return_value, stdout, success = result_queue.get(block=False)  # Non-blocking get
                if success:
                    return ToolResult(output=return_value, system=stdout) #stdout saved in system
                else:
                    return ToolResult(output=None, error=stdout, system=stdout) #stdout saved in system

            except Exception:
                return ToolResult(output=None, error="Failed to retrieve results from subprocess.")