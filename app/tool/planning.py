# app/tool/planning.py
import json
import os
from typing import Dict, List, Literal, Optional, ClassVar  # Import ClassVar

from app.exceptions import ToolError
from app.schema import Step  # Import the Step model
from app.tool.base import BaseTool, ToolResult

_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans for solving complex tasks.
The tool provides functionality for creating plans, updating plan steps, and tracking progress.
"""


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    The tool provides functionality for creating plans, updating plan steps, and tracking progress.
    """

    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute.  Available commands: create, update, list, get, set_active, mark_step, delete.",
                "enum": [
                    "create",
                    "update",
                    "list",
                    "get",
                    "set_active",
                    "mark_step",
                    "delete",
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands. Optional for get and mark_step (uses active plan if not specified).",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command, optional for update command.",
                "type": "string",
            },
            "steps": {
                "description": "List of plan steps. Required for create command, optional for update command.",
                "type": "array",
                "items": {"type": "string"},
            },
            "step_index": {
                "description": "Index of the step to update (0-based). Required for mark_step command.",
                "type": "integer",
            },
            "step_status": {
                "description": "Status to set for a step. Used with mark_step command.",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "type": "string",
            },
            "step_notes": {
                "description": "Additional notes for a step. Optional for mark_step command.",
                "type": "string",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    plans: Dict[str, Dict] = {}  # Dictionary to store plans by plan_id
    _current_plan_id: Optional[str] = None  # Track the current active plan
    PLANS_DIR: ClassVar[str] = "plans"  # Directory to store plan files.  Now with ClassVar

    def __init__(self):
        super().__init__()
        self._load_plans()

    def _load_plans(self):
        """Loads plans from JSON files in the plans directory."""
        if not os.path.exists(self.PLANS_DIR):
            try:
                os.makedirs(self.PLANS_DIR)
            except OSError as e:
                raise ToolError(f"Failed to create plans directory: {e}")
            return  # No plans to load yet

        for filename in os.listdir(self.PLANS_DIR):
            if filename.endswith(".json"):
                plan_id = filename[:-5]  # Remove .json extension
                filepath = os.path.join(self.PLANS_DIR, filename)
                try:
                    with open(filepath, "r") as f:
                        plan_data = json.load(f)

                        # Deserialize steps into Step objects
                        plan_data["steps"] = [
                            Step(**step_data) for step_data in plan_data["steps"]
                        ]

                    self.plans[plan_id] = plan_data
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Error loading plan {plan_id} from {filename}: {e}")
                    # Consider more robust error handling, like moving the corrupted file
                except Exception as e:
                    print(f"Unexpected Error: loading plan {plan_id} from {filename}: {e}")


    def _save_plan(self, plan: Dict):
        """Saves a plan to a JSON file."""
        plan_id = plan["plan_id"]
        filepath = os.path.join(self.PLANS_DIR, f"{plan_id}.json")

        # Serialize steps to dictionaries
        plan_data_to_save = plan.copy()  # Create copy so original object is not changed
        plan_data_to_save["steps"] = [step.model_dump() for step in plan["steps"]]

        try:
            with open(filepath, "w") as f:
                json.dump(plan_data_to_save, f, indent=4)
        except OSError as e:
            raise ToolError(f"Failed to save plan {plan_id}: {e}")
        except Exception as e:
            print(f"Unexpected Error: saving plan {plan_id}: {e}")


    async def execute(
        self,
        *,
        command: Literal[
            "create", "update", "list", "get", "set_active", "mark_step", "delete"
        ],
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[
            Literal["not_started", "in_progress", "completed", "blocked"]
        ] = None,
        step_notes: Optional[str] = None,
        **kwargs,
    ):
        """
        Execute the planning tool with the given command and parameters.

        Parameters:
        - command: The operation to perform
        - plan_id: Unique identifier for the plan
        - title: Title for the plan (used with create command)
        - steps: List of steps for the plan (used with create command)
        - step_index: Index of the step to update (used with mark_step command)
        - step_status: Status to set for a step (used with mark_step command)
        - step_notes: Additional notes for a step (used with mark_step command)
        """

        if command == "create":
            return self._create_plan(plan_id, title, steps)
        elif command == "update":
            return self._update_plan(plan_id, title, steps)
        elif command == "list":
            return self._list_plans()
        elif command == "get":
            return self._get_plan(plan_id)
        elif command == "set_active":
            return self._set_active_plan(plan_id)
        elif command == "mark_step":
            return self._mark_step(plan_id, step_index, step_status, step_notes)
        elif command == "delete":
            return self._delete_plan(plan_id)
        else:
            raise ToolError(
                f"Unrecognized command: {command}. Allowed commands are: create, update, list, get, set_active, mark_step, delete"
            )

    def _create_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """Create a new plan with the given ID, title, and steps."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: create")

        if plan_id in self.plans:
            raise ToolError(
                f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans."
            )

        if not title:
            raise ToolError("Parameter `title` is required for command: create")

        if (
            not steps
            or not isinstance(steps, list)
            or not all(isinstance(step, str) for step in steps)
        ):
            raise ToolError(
                "Parameter `steps` must be a non-empty list of strings for command: create"
            )

        # Create a new plan with initialized step statuses, using Step objects
        new_plan = {
            "plan_id": plan_id,
            "title": title,
            "steps": [
                Step(description=step_description) for step_description in steps
            ],  # Create Step instances
        }

        self.plans[plan_id] = new_plan
        self._current_plan_id = plan_id  # Set as active plan
        self._save_plan(new_plan) # save the plan

        return ToolResult(
            output=f"Plan created successfully with ID: {plan_id}\n\n{self._format_plan(new_plan)}"
        )

    def _update_plan(
        self, plan_id: Optional[str], title: Optional[str], steps: Optional[List[str]]
    ) -> ToolResult:
        """Update an existing plan with new title or steps."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: update")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]

        if title:
            plan["title"] = title

        if steps:
            if not isinstance(steps, list) or not all(
                isinstance(step, str) for step in steps
            ):
                raise ToolError(
                    "Parameter `steps` must be a list of strings for command: update"
                )

            # Create new Step objects, preserving status/notes if possible
            new_steps = []
            for i, new_step_description in enumerate(steps):
                if i < len(plan["steps"]) and plan["steps"][i].description == new_step_description:
                    # Reuse the existing Step object
                    new_steps.append(plan["steps"][i])
                else:
                    # Create a new Step object
                    new_steps.append(Step(description=new_step_description))

            plan["steps"] = new_steps
        self._save_plan(plan) # save the plan
        return ToolResult(
            output=f"Plan updated successfully: {plan_id}\n\n{self._format_plan(plan)}"
        )

    def _list_plans(self) -> ToolResult:
        """List all available plans."""
        if not self.plans:
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self._current_plan_id else ""
            completed = sum(1 for step in plan["steps"] if step.status == "completed")
            total = len(plan["steps"])
            progress = f"{completed}/{total} steps completed"
            output += f"• {plan_id}{current_marker}: {plan['title']} - {progress}\n"

        return ToolResult(output=output)

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Get details of a specific plan."""
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Set a plan as the active plan."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: set_active")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        self._current_plan_id = plan_id
        return ToolResult(
            output=f"Plan '{plan_id}' is now the active plan.\n\n{self._format_plan(self.plans[plan_id])}"
        )

    def _mark_step(
        self,
        plan_id: Optional[str],
        step_index: Optional[int],
        step_status: Optional[str],
        step_notes: Optional[str],
    ) -> ToolResult:
        """Mark a step with a specific status and optional notes."""
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self._current_plan_id:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self._current_plan_id

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        if step_index is None:
            raise ToolError("Parameter `step_index` is required for command: mark_step")

        plan = self.plans[plan_id]

        if step_index < 0 or step_index >= len(plan["steps"]):
            raise ToolError(
                f"Invalid step_index: {step_index}. Valid indices range from 0 to {len(plan['steps'])-1}."
            )

        if step_status and step_status not in [
            "not_started",
            "in_progress",
            "completed",
            "blocked",
        ]:
            raise ToolError(
                f"Invalid step_status: {step_status}. Valid statuses are: not_started, in_progress, completed, blocked"
            )

        if step_status:
            plan["steps"][step_index].status = step_status  # Update status on Step object

        if step_notes is not None:  # Allow clearing notes by passing an empty string
            plan["steps"][step_index].notes = step_notes  # Update notes on Step object
        self._save_plan(plan) # save
        return ToolResult(
            output=f"Step {step_index} updated in plan '{plan_id}'.\n\n{self._format_plan(plan)}"
        )

    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Delete a plan."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: delete")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        # Delete the plan file
        filepath = os.path.join(self.PLANS_DIR, f"{plan_id}.json")
        try:
            os.remove(filepath)
        except OSError as e:
            raise ToolError(f"Failed to delete plan file for {plan_id}: {e}")

        del self.plans[plan_id]

        # If the deleted plan was the active plan, clear the active plan
        if self._current_plan_id == plan_id:
            self._current_plan_id = None

        return ToolResult(output=f"Plan '{plan_id}' has been deleted.")

    def _format_plan(self, plan: Dict) -> str:
        """Format a plan for display."""
        output = f"Plan: {plan['title']} (ID: {plan['plan_id']})\n"
        output += "=" * len(output) + "\n\n"

        # Calculate progress statistics
        total_steps = len(plan["steps"])
        completed = sum(1 for step in plan["steps"] if step.status == "completed")
        in_progress = sum(1 for step in plan["steps"] if step.status == "in_progress")
        blocked = sum(1 for step in plan["steps"] if step.status == "blocked")
        not_started = sum(1 for step in plan["steps"] if step.status == "not_started")

        output += f"Progress: {completed}/{total_steps} steps completed "
        if total_steps > 0:
            percentage = (completed / total_steps) * 100
            output += f"({percentage:.1f}%)\n"
        else:
            output += "(0%)\n"

        output += f"Status: {completed} completed, {in_progress} in progress, {blocked} blocked, {not_started} not started\n\n"
        output += "Steps:\n"

        # Add each step with its status and notes
        for i, step in enumerate(plan["steps"]):
            status_symbol = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(step.status, "[ ]")  # Access status from Step object
            output += f"{i}. {status_symbol} {step.description}\n"  # Access description from Step object
            if step.notes:
                output += f"    Notes: {step.notes}\n"  # Access notes from Step object

        return output