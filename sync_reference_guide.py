# sync_reference_guide.py
import ast
import inspect
import os
import re
from typing import Any, Dict, List, Tuple

from app.config import Config
from app.llm import LLM
from app.logger import logger
from app.schema import Message
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.python_execute import PythonExecute
from app.tool.web_search import WebSearch


def extract_markdown_sections(filepath: str) -> Dict[str, str]:
    """Extract sections from a Markdown file."""
    sections = {}
    with open(filepath, "r") as f:
        content = f.read()
    pattern = r"## (.*?)\n(.*?)(?=(?:\n## )|$)"
    matches = re.findall(pattern, content, re.DOTALL)
    for title, body in matches:
        sections[title.strip()] = body.strip()
    return sections


def extract_component_details(section_body: str) -> List[Dict[str, Any]]:
    """Extract component details from a section body."""
    components = []
    pattern = r"- `(.*?)` \[(.*?): (.*?)\]\n(.*?)(?=(?:- `)|$)"
    matches = re.findall(pattern, section_body, re.DOTALL)
    for file, tag_type, tag_name, details in matches:
        components.append(
            {
                "file": file.strip(),
                "tag_type": tag_type.strip(),
                "tag_name": tag_name.strip(),
                "details": details.strip(),
            }
        )
    return components


def reflect_on_code(filepath: str) -> Dict[str, Any]:
    """Reflect on the code to extract details."""
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read())
    except FileNotFoundError:
        print(f"Warning: File not found: {filepath}")
        return {}
    except Exception as e:
        print(f"Error parsing file {filepath}: {e}")
        return {}
    details = {"classes": {}, "functions": {}}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            details["classes"][class_name] = {
                "methods": [
                    m.name
                    for m in node.body
                    if isinstance(m, ast.FunctionDef)
                ],
                "attributes": [
                    a.target.id
                    for a in node.body
                    if isinstance(a, ast.AnnAssign)
                ],
            }
        elif isinstance(node, ast.FunctionDef):
            details["functions"][node.name] = {
                "args": [arg.arg for arg in node.args.args]
            }
    return details


def compare_components(
    reference_components: List[Dict[str, Any]], code_details: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare components from the reference guide with code details."""
    comparison_results = {"new": [], "removed": [], "modified": []}
    for ref_comp in reference_components:
        file = ref_comp["file"]
        tag_name = ref_comp["tag_name"]
        if file not in code_details:
            comparison_results["removed"].append(ref_comp)
        else:
            code_comp = code_details[file]
            if tag_name not in code_comp:
                comparison_results["removed"].append(ref_comp)
            else:
                if ref_comp["details"] != str(code_comp[tag_name]):
                    comparison_results["modified"].append(
                        {
                            "reference": ref_comp,
                            "code": code_comp[tag_name],
                        }
                    )
    for file, code_comp in code_details.items():
        for tag_name in code_comp:
            found = False
            for ref_comp in reference_components:
                if ref_comp["file"] == file and ref_comp["tag_name"] == tag_name:
                    found = True
                    break
            if not found:
                comparison_results["new"].append(
                    {"file": file, "tag_name": tag_name, "details": code_comp[tag_name]}
                )
    return comparison_results


def main():
    """Main function to compare the reference guide with the code."""
    reference_filepath = "REFERENCE_GUIDE.md"
    sections = extract_markdown_sections(reference_filepath)
    reference_components = []
    for section_name, section_body in sections.items():
        if section_name == "Project Structure":
            reference_components.extend(extract_component_details(section_body))

    code_details = {}
    # Add all the files to check
    files_to_check = [
        "app/agent/base.py",
        "app/agent/manus.py",
        "app/agent/toolcall.py",
        "app/agent/planning.py",
        "app/tool/base.py",
        "app/tool/browser_use_tool.py",
        "app/tool/python_execute.py",
        "app/tool/web_search.py",
        "app/tool/planning.py",
        "app/tool/file_saver.py",
        "app/tool/terminate.py",
        "app/tool/terminal.py",
        "app/tool/serper_api_wrapper.py",
        "app/tool/tool_collection.py",
        "app/llm.py",
        "app/schema.py",
        "app/prompt/prompt_formatter.py",
        "app/prompt/message.py",
        "app/prompt/tool_use.py",
        "app/prompt/base.py",
        "app/prompt/planning.py",
        "app/config.py",
        "main.py",
        "app/exceptions.py",
        "app/logger.py",
        "app/agent/__init__.py",
        "app/tool/__init__.py",
        "app/memory/__init__.py",
        "app/memory/base.py",
    ]

    for file in files_to_check:
        code_details[file] = reflect_on_code(file)

    comparison_results = compare_components(reference_components, code_details)

    print("Comparison Results:")
    if comparison_results["new"]:
        print("\nNew Components:")
        for comp in comparison_results["new"]:
            print(f"- {comp['file']}: {comp['tag_name']}")
    if comparison_results["removed"]:
        print("\nRemoved Components:")
        for comp in comparison_results["removed"]:
            print(f"- {comp['file']}: {comp['tag_name']}")
    if comparison_results["modified"]:
        print("\nModified Components:")
        for comp in comparison_results["modified"]:
            print(f"- {comp['reference']['file']}: {comp['reference']['tag_name']}")
            print(f"  - Reference: {comp['reference']['details']}")
            print(f"  - Code: {comp['code']}")


if __name__ == "__main__":
    main()
