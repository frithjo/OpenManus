# test_sync_reference_guide.py
import os
import unittest
from unittest.mock import patch

from sync_reference_guide import (
    compare_components,
    extract_component_details,
    extract_markdown_sections,
    reflect_on_code,
)


class TestSyncReferenceGuide(unittest.TestCase):
    def setUp(self):
        # Create dummy files and directories for testing
        os.makedirs("test_dir", exist_ok=True)
        with open("test_dir/test_file.py", "w") as f:
            f.write(
                """
class TestClass:
    def test_method(self):
        pass
def test_function(arg1, arg2):
    pass
"""
            )
        with open("test_dir/test_file2.py", "w") as f:
            f.write(
                """
class TestClass2:
    def test_method2(self):
        pass
"""
            )
        with open("test_reference.md", "w") as f:
            f.write(
                """
## Project Structure
- `test_dir/test_file.py` [PIN: TestClass]
    - **Purpose:** Test class.
    - **Relationships:** None.
    - **Dependencies:** None.
    - `TestClass` (class): Test class.
        - `test_method` (method): Test method.
- `test_dir/test_file2.py` [PIN: TestClass2]
    - **Purpose:** Test class 2.
    - **Relationships:** None.
    - **Dependencies:** None.
    - `TestClass2` (class): Test class 2.
        - `test_method2` (method): Test method 2.
"""
            )

    def tearDown(self):
        # Clean up dummy files and directories
        os.remove("test_dir/test_file.py")
        os.remove("test_dir/test_file2.py")
        os.remove("test_reference.md")
        os.rmdir("test_dir")

    def test_extract_markdown_sections(self):
        sections = extract_markdown_sections("test_reference.md")
        self.assertIn("Project Structure", sections)

    def test_extract_component_details(self):
        with open("test_reference.md", "r") as f:
            content = f.read()
        sections = extract_markdown_sections("test_reference.md")
        details = extract_component_details(sections["Project Structure"])
        self.assertEqual(len(details), 2)
        self.assertEqual(details[0]["file"], "test_dir/test_file.py")
        self.assertEqual(details[0]["tag_name"], "TestClass")

    def test_reflect_on_code(self):
        code_details = reflect_on_code("test_dir/test_file.py")
        self.assertIn("TestClass", code_details["classes"])
        self.assertIn("test_method", code_details["classes"]["TestClass"]["methods"])
        self.assertIn("test_function", code_details["functions"])
        self.assertIn("arg1", code_details["functions"]["test_function"]["args"])

    def test_compare_components_new(self):
        reference_components = extract_component_details(
            extract_markdown_sections("test_reference.md")["Project Structure"]
        )
        code_details = {
            "test_dir/test_file.py": reflect_on_code("test_dir/test_file.py"),
            "test_dir/test_file2.py": reflect_on_code("test_dir/test_file2.py"),
            "test_dir/test_file3.py": {"classes": {"TestClass3": {"methods": []}}},
        }
        comparison_results = compare_components(reference_components, code_details)
        self.assertEqual(len(comparison_results["new"]), 1)
        self.assertEqual(len(comparison_results["removed"]), 0)
        self.assertEqual(len(comparison_results["modified"]), 0)

    def test_compare_components_removed(self):
        reference_components = extract_component_details(
            extract_markdown_sections("test_reference.md")["Project Structure"]
        )
        code_details = {
            "test_dir/test_file.py": reflect_on_code("test_dir/test_file.py")
        }
        comparison_results = compare_components(reference_components, code_details)
        self.assertEqual(len(comparison_results["new"]), 0)
        self.assertEqual(len(comparison_results["removed"]), 1)
        self.assertEqual(len(comparison_results["modified"]), 0)

    def test_compare_components_modified(self):
        reference_components = extract_component_details(
            extract_markdown_sections("test_reference.md")["Project Structure"]
        )
        code_details = {
            "test_dir/test_file.py": reflect_on_code("test_dir/test_file.py"),
            "test_dir/test_file2.py": {"classes": {"TestClass2": {"methods": ["test_method3"]}}},
        }
        comparison_results = compare_components(reference_components, code_details)
        self.assertEqual(len(comparison_results["new"]), 0)
        self.assertEqual(len(comparison_results["removed"]), 0)
        self.assertEqual(len(comparison_results["modified"]), 1)

    def test_reflect_on_code_file_not_found(self):
        code_details = reflect_on_code("nonexistent_file.py")
        self.assertEqual(code_details, {})

    def test_reflect_on_code_invalid_syntax(self):
        with open("test_dir/invalid_file.py", "w") as f:
            f.write("invalid python code")
        code_details = reflect_on_code("test_dir/invalid_file.py")
        self.assertEqual(code_details, {})
        os.remove("test_dir/invalid_file.py")

    @patch("builtins.print")
    def test_main_new_components(self, mock_print):
        # Create a new file to simulate a new component
        with open("app/new_component.py", "w") as f:
            f.write("class NewComponent:\n    pass")

        # Run the main function
        from sync_reference_guide import main

        main()

        # Assert that the new component is detected
        mock_print.assert_called_with(
            "- app/new_component.py: NewComponent"
        )

        # Clean up the new file
        
