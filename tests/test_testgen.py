"""
Tests for TestGen tool implementation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.mock_helpers import create_mock_provider
from tools.testgen import TestGenerationRequest, TestGenerationTool


class TestTestGenTool:
    """Test the TestGen tool"""

    @pytest.fixture
    def tool(self):
        return TestGenerationTool()

    @pytest.fixture
    def temp_files(self):
        """Create temporary test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create sample code files
            code_file = temp_path / "calculator.py"
            code_file.write_text(
                """
def add(a, b):
    '''Add two numbers'''
    return a + b

def divide(a, b):
    '''Divide two numbers'''
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
            )

            # Create sample test files (different sizes)
            small_test = temp_path / "test_small.py"
            small_test.write_text(
                """
import unittest

class TestBasic(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1 + 1, 2)
"""
            )

            large_test = temp_path / "test_large.py"
            large_test.write_text(
                """
import unittest
from unittest.mock import Mock, patch

class TestComprehensive(unittest.TestCase):
    def setUp(self):
        self.mock_data = Mock()

    def test_feature_one(self):
        # Comprehensive test with lots of setup
        result = self.process_data()
        self.assertIsNotNone(result)

    def test_feature_two(self):
        # Another comprehensive test
        with patch('some.module') as mock_module:
            mock_module.return_value = 'test'
            result = self.process_data()
            self.assertEqual(result, 'expected')

    def process_data(self):
        return "test_result"
"""
            )

            yield {
                "temp_dir": temp_dir,
                "code_file": str(code_file),
                "small_test": str(small_test),
                "large_test": str(large_test),
            }

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "testgen"
        assert "COMPREHENSIVE TEST GENERATION" in tool.get_description()
        assert "BE SPECIFIC about scope" in tool.get_description()
        assert tool.get_default_temperature() == 0.2  # Analytical temperature

        # Check model category
        from tools.models import ToolModelCategory

        assert tool.get_model_category() == ToolModelCategory.EXTENDED_REASONING

    def test_input_schema_structure(self, tool):
        """Test input schema structure"""
        schema = tool.get_input_schema()

        # Required fields
        assert "files" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "files" in schema["required"]
        assert "prompt" in schema["required"]

        # Optional fields
        assert "test_examples" in schema["properties"]
        assert "thinking_mode" in schema["properties"]
        assert "continuation_id" in schema["properties"]

        # Should not have temperature or use_websearch
        assert "temperature" not in schema["properties"]
        assert "use_websearch" not in schema["properties"]

        # Check test_examples description
        test_examples_desc = schema["properties"]["test_examples"]["description"]
        assert "absolute paths" in test_examples_desc
        assert "smallest representative tests" in test_examples_desc

    def test_request_model_validation(self):
        """Test request model validation"""
        # Valid request
        valid_request = TestGenerationRequest(files=["/tmp/test.py"], prompt="Generate tests for calculator functions")
        assert valid_request.files == ["/tmp/test.py"]
        assert valid_request.prompt == "Generate tests for calculator functions"
        assert valid_request.test_examples is None

        # With test examples
        request_with_examples = TestGenerationRequest(
            files=["/tmp/test.py"], prompt="Generate tests", test_examples=["/tmp/test_example.py"]
        )
        assert request_with_examples.test_examples == ["/tmp/test_example.py"]

        # Invalid request (missing required fields)
        with pytest.raises(ValueError):
            TestGenerationRequest(files=["/tmp/test.py"])  # Missing prompt

    @pytest.mark.asyncio
    async def test_execute_success(self, tool, temp_files):
        """Test successful execution using real integration testing"""
        import importlib
        import os

        # Save original environment
        original_env = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL"),
        }

        try:
            # Set up environment for real provider resolution
            os.environ["OPENAI_API_KEY"] = "sk-test-key-testgen-success-test-not-real"
            os.environ["DEFAULT_MODEL"] = "o3-mini"

            # Clear other provider keys to isolate to OpenAI
            for key in ["GEMINI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)

            # Reload config and clear registry
            import config

            importlib.reload(config)
            from providers.registry import ModelProviderRegistry

            ModelProviderRegistry._instance = None

            # Test with real provider resolution
            try:
                result = await tool.execute(
                    {
                        "files": [temp_files["code_file"]],
                        "prompt": "Generate comprehensive tests for the calculator functions",
                        "model": "o3-mini",
                    }
                )

                # If we get here, check the response format
                assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert "status" in response_data

            except Exception as e:
                # Expected: API call will fail with fake key
                error_msg = str(e)
                # Should NOT be a mock-related error
                assert "MagicMock" not in error_msg
                assert "'<' not supported between instances" not in error_msg

                # Should be a real provider error
                assert any(
                    phrase in error_msg
                    for phrase in ["API", "key", "authentication", "provider", "network", "connection"]
                )

        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

            # Reload config and clear registry
            importlib.reload(config)
            ModelProviderRegistry._instance = None

    @pytest.mark.asyncio
    async def test_execute_with_test_examples(self, tool, temp_files):
        """Test execution with test examples using real integration testing"""
        import importlib
        import os

        # Save original environment
        original_env = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL"),
        }

        try:
            # Set up environment for real provider resolution
            os.environ["OPENAI_API_KEY"] = "sk-test-key-testgen-examples-test-not-real"
            os.environ["DEFAULT_MODEL"] = "o3-mini"

            # Clear other provider keys to isolate to OpenAI
            for key in ["GEMINI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)

            # Reload config and clear registry
            import config

            importlib.reload(config)
            from providers.registry import ModelProviderRegistry

            ModelProviderRegistry._instance = None

            # Test with real provider resolution
            try:
                result = await tool.execute(
                    {
                        "files": [temp_files["code_file"]],
                        "prompt": "Generate tests following existing patterns",
                        "test_examples": [temp_files["small_test"]],
                        "model": "o3-mini",
                    }
                )

                # If we get here, check the response format
                assert len(result) == 1
                response_data = json.loads(result[0].text)
                assert "status" in response_data

            except Exception as e:
                # Expected: API call will fail with fake key
                error_msg = str(e)
                # Should NOT be a mock-related error
                assert "MagicMock" not in error_msg
                assert "'<' not supported between instances" not in error_msg

                # Should be a real provider error
                assert any(
                    phrase in error_msg
                    for phrase in ["API", "key", "authentication", "provider", "network", "connection"]
                )

        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

            # Reload config and clear registry
            importlib.reload(config)
            ModelProviderRegistry._instance = None

    def test_process_test_examples_empty(self, tool):
        """Test processing empty test examples"""
        content, note = tool._process_test_examples([], None)
        assert content == ""
        assert note == ""

    def test_process_test_examples_budget_allocation(self, tool, temp_files):
        """Test token budget allocation for test examples"""
        with patch.object(tool, "filter_new_files") as mock_filter:
            mock_filter.return_value = [temp_files["small_test"], temp_files["large_test"]]

            with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
                mock_prepare.return_value = (
                    "Mocked test content",
                    [temp_files["small_test"], temp_files["large_test"]],
                )

                # Test with available tokens
                content, note = tool._process_test_examples(
                    [temp_files["small_test"], temp_files["large_test"]], None, available_tokens=100000
                )

                # Should allocate 25% of 100k = 25k tokens for test examples
                mock_prepare.assert_called_once()
                call_args = mock_prepare.call_args
                assert call_args[1]["max_tokens"] == 25000  # 25% of 100k

    def test_process_test_examples_size_sorting(self, tool, temp_files):
        """Test that test examples are sorted by size (smallest first)"""
        with patch.object(tool, "filter_new_files") as mock_filter:
            # Return files in random order
            mock_filter.return_value = [temp_files["large_test"], temp_files["small_test"]]

            with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
                mock_prepare.return_value = ("test content", [temp_files["small_test"], temp_files["large_test"]])

                tool._process_test_examples(
                    [temp_files["large_test"], temp_files["small_test"]], None, available_tokens=50000
                )

                # Check that files were passed in size order (smallest first)
                call_args = mock_prepare.call_args[0]
                files_passed = call_args[0]

                # Verify smallest file comes first
                assert files_passed[0] == temp_files["small_test"]
                assert files_passed[1] == temp_files["large_test"]

    @pytest.mark.asyncio
    async def test_prepare_prompt_structure(self, tool, temp_files):
        """Test prompt preparation structure"""
        request = TestGenerationRequest(files=[temp_files["code_file"]], prompt="Test the calculator functions")

        with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.return_value = ("mocked file content", [temp_files["code_file"]])

            prompt = await tool.prepare_prompt(request)

            # Check prompt structure
            assert "=== USER CONTEXT ===" in prompt
            assert "Test the calculator functions" in prompt
            assert "=== CODE TO TEST ===" in prompt
            assert "mocked file content" in prompt
            assert tool.get_system_prompt() in prompt

    @pytest.mark.asyncio
    async def test_prepare_prompt_with_examples(self, tool, temp_files):
        """Test prompt preparation with test examples"""
        request = TestGenerationRequest(
            files=[temp_files["code_file"]], prompt="Generate tests", test_examples=[temp_files["small_test"]]
        )

        with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.return_value = ("mocked content", [temp_files["code_file"]])

            with patch.object(tool, "_process_test_examples") as mock_process:
                mock_process.return_value = ("test examples content", "Note: examples included")

                prompt = await tool.prepare_prompt(request)

                # Check test examples section
                assert "=== TEST EXAMPLES FOR STYLE REFERENCE ===" in prompt
                assert "test examples content" in prompt
                assert "Note: examples included" in prompt

    def test_format_response(self, tool):
        """Test response formatting"""
        request = TestGenerationRequest(files=["/tmp/test.py"], prompt="Generate tests")

        raw_response = "Generated test cases with edge cases"
        formatted = tool.format_response(raw_response, request)

        # Check formatting includes new action-oriented next steps
        assert raw_response in formatted
        assert "EXECUTION MODE" in formatted
        assert "ULTRATHINK" in formatted
        assert "CREATE" in formatted
        assert "VALIDATE BY EXECUTION" in formatted
        assert "MANDATORY" in formatted

    @pytest.mark.asyncio
    async def test_error_handling_invalid_files(self, tool):
        """Test error handling for invalid file paths"""
        result = await tool.execute(
            {"files": ["relative/path.py"], "prompt": "Generate tests"}  # Invalid: not absolute
        )

        # Should return error for relative path
        response_data = json.loads(result[0].text)
        assert response_data["status"] == "error"
        assert "absolute" in response_data["content"]

    @pytest.mark.asyncio
    async def test_large_prompt_handling(self, tool):
        """Test handling of large prompts"""
        large_prompt = "x" * 60000  # Exceeds MCP_PROMPT_SIZE_LIMIT

        result = await tool.execute({"files": ["/tmp/test.py"], "prompt": large_prompt})

        # Should return resend_prompt status
        response_data = json.loads(result[0].text)
        assert response_data["status"] == "resend_prompt"
        assert "too large" in response_data["content"]

    def test_token_budget_calculation(self, tool):
        """Test token budget calculation logic"""
        # Mock model capabilities
        with patch.object(tool, "get_model_provider") as mock_get_provider:
            mock_provider = create_mock_provider(context_window=200000)
            mock_get_provider.return_value = mock_provider

            # Simulate model name being set
            tool._current_model_name = "test-model"

            with patch.object(tool, "_process_test_examples") as mock_process:
                mock_process.return_value = ("test content", "")

                with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
                    mock_prepare.return_value = ("code content", ["/tmp/test.py"])

                    request = TestGenerationRequest(
                        files=["/tmp/test.py"], prompt="Test prompt", test_examples=["/tmp/example.py"]
                    )

                    # This should trigger token budget calculation
                    import asyncio

                    asyncio.run(tool.prepare_prompt(request))

                    # Verify test examples got 25% of 150k tokens (75% of 200k context)
                    mock_process.assert_called_once()
                    call_args = mock_process.call_args[0]
                    assert call_args[2] == 150000  # 75% of 200k context window

    @pytest.mark.asyncio
    async def test_continuation_support(self, tool, temp_files):
        """Test continuation ID support"""
        with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.return_value = ("code content", [temp_files["code_file"]])

            request = TestGenerationRequest(
                files=[temp_files["code_file"]], prompt="Continue testing", continuation_id="test-thread-123"
            )

            await tool.prepare_prompt(request)

            # Verify continuation_id was passed to _prepare_file_content_for_prompt
            # The method should be called twice (once for code, once for test examples logic)
            assert mock_prepare.call_count >= 1

            # Check that continuation_id was passed in at least one call
            calls = mock_prepare.call_args_list
            continuation_passed = any(
                call[0][1] == "test-thread-123" for call in calls  # continuation_id is second argument
            )
            assert continuation_passed, f"continuation_id not passed. Calls: {calls}"

    def test_no_websearch_in_prompt(self, tool, temp_files):
        """Test that web search instructions are not included"""
        request = TestGenerationRequest(files=[temp_files["code_file"]], prompt="Generate tests")

        with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.return_value = ("code content", [temp_files["code_file"]])

            import asyncio

            prompt = asyncio.run(tool.prepare_prompt(request))

            # Should not contain web search instructions
            assert "WEB SEARCH CAPABILITY" not in prompt
            assert "web search" not in prompt.lower()

    @pytest.mark.asyncio
    async def test_duplicate_file_deduplication(self, tool, temp_files):
        """Test that duplicate files are removed from code files when they appear in test_examples"""
        # Create a scenario where the same file appears in both files and test_examples
        duplicate_file = temp_files["code_file"]

        request = TestGenerationRequest(
            files=[duplicate_file, temp_files["large_test"]],  # code_file appears in both
            prompt="Generate tests",
            test_examples=[temp_files["small_test"], duplicate_file],  # code_file also here
        )

        # Track the actual files passed to _prepare_file_content_for_prompt
        captured_calls = []

        def capture_prepare_calls(files, *args, **kwargs):
            captured_calls.append(("prepare", files))
            return ("mocked content", files)

        with patch.object(tool, "_prepare_file_content_for_prompt", side_effect=capture_prepare_calls):
            await tool.prepare_prompt(request)

            # Should have been called twice: once for test examples, once for code files
            assert len(captured_calls) == 2

            # First call should be for test examples processing (via _process_test_examples)
            captured_calls[0][1]
            # Second call should be for deduplicated code files
            code_files = captured_calls[1][1]

            # duplicate_file should NOT be in code files (removed due to duplication)
            assert duplicate_file not in code_files
            # temp_files["large_test"] should still be there (not duplicated)
            assert temp_files["large_test"] in code_files

    @pytest.mark.asyncio
    async def test_no_deduplication_when_no_test_examples(self, tool, temp_files):
        """Test that no deduplication occurs when test_examples is None/empty"""
        request = TestGenerationRequest(
            files=[temp_files["code_file"], temp_files["large_test"]],
            prompt="Generate tests",
            # No test_examples
        )

        with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare:
            mock_prepare.return_value = ("mocked content", [temp_files["code_file"], temp_files["large_test"]])

            await tool.prepare_prompt(request)

            # Should only be called once (for code files, no test examples)
            assert mock_prepare.call_count == 1

            # All original files should be passed through
            code_files_call = mock_prepare.call_args_list[0]
            code_files = code_files_call[0][0]
            assert temp_files["code_file"] in code_files
            assert temp_files["large_test"] in code_files

    @pytest.mark.asyncio
    async def test_path_normalization_in_deduplication(self, tool, temp_files):
        """Test that path normalization works correctly for deduplication"""
        import os

        # Create variants of the same path (with and without normalization)
        base_file = temp_files["code_file"]
        # Add some path variations that should normalize to the same file
        variant_path = os.path.join(os.path.dirname(base_file), ".", os.path.basename(base_file))

        request = TestGenerationRequest(
            files=[variant_path, temp_files["large_test"]],  # variant path in files
            prompt="Generate tests",
            test_examples=[base_file],  # base path in test_examples
        )

        # Track the actual files passed to _prepare_file_content_for_prompt
        captured_calls = []

        def capture_prepare_calls(files, *args, **kwargs):
            captured_calls.append(("prepare", files))
            return ("mocked content", files)

        with patch.object(tool, "_prepare_file_content_for_prompt", side_effect=capture_prepare_calls):
            await tool.prepare_prompt(request)

            # Should have been called twice: once for test examples, once for code files
            assert len(captured_calls) == 2

            # Second call should be for code files
            code_files = captured_calls[1][1]

            # variant_path should be removed due to normalization matching base_file
            assert variant_path not in code_files
            # large_test should still be there
            assert temp_files["large_test"] in code_files
