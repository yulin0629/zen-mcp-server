#!/usr/bin/env python3
"""
O3 Model Selection Test

Tests that O3 models are properly selected and used when explicitly specified,
regardless of the default model configuration (even when set to auto).
Validates model selection via Docker logs.
"""

import datetime
import subprocess

from .base_test import BaseSimulatorTest


class O3ModelSelectionTest(BaseSimulatorTest):
    """Test O3 model selection and usage"""

    @property
    def test_name(self) -> str:
        return "o3_model_selection"

    @property
    def test_description(self) -> str:
        return "O3 model selection and usage validation"

    def get_recent_server_logs(self) -> str:
        """Get recent server logs from the log file directly"""
        try:
            # Read logs directly from the log file - use more lines to ensure we get all test-related logs
            cmd = ["docker", "exec", self.container_name, "tail", "-n", "500", "/tmp/mcp_server.log"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return result.stdout
            else:
                self.logger.warning(f"Failed to read server logs: {result.stderr}")
                return ""
        except Exception as e:
            self.logger.error(f"Failed to get server logs: {e}")
            return ""

    def run_test(self) -> bool:
        """Test O3 model selection and usage"""
        try:
            self.logger.info(" Test: O3 model selection and usage validation")

            # Check which API keys are configured
            check_cmd = [
                "docker",
                "exec",
                self.container_name,
                "python",
                "-c",
                'import os; print(f\'OPENAI_KEY:{bool(os.environ.get("OPENAI_API_KEY"))}|OPENROUTER_KEY:{bool(os.environ.get("OPENROUTER_API_KEY"))}\')',
            ]
            result = subprocess.run(check_cmd, capture_output=True, text=True)

            has_openai = False
            has_openrouter = False

            if result.returncode == 0:
                output = result.stdout.strip()
                if "OPENAI_KEY:True" in output:
                    has_openai = True
                if "OPENROUTER_KEY:True" in output:
                    has_openrouter = True

            # If only OpenRouter is configured, adjust test expectations
            if has_openrouter and not has_openai:
                self.logger.info("  ℹ️  Only OpenRouter configured - O3 models will be routed through OpenRouter")
                return self._run_openrouter_o3_test()

            # If neither OpenAI nor OpenRouter is configured, skip the test
            if not has_openai and not has_openrouter:
                self.logger.info("  ⚠️  Neither OpenAI nor OpenRouter API keys configured - skipping test")
                self.logger.info(
                    "  ℹ️  This test requires either OPENAI_API_KEY or OPENROUTER_API_KEY to be set in .env"
                )
                self.logger.info("  ✅ Test skipped (no API keys configured)")
                return True  # Return True to indicate test passed/skipped

            # Original test for when OpenAI is configured
            self.logger.info("  ℹ️  OpenAI API configured - expecting direct OpenAI API calls")

            # Setup test files for later use
            self.setup_test_files()

            # Get timestamp for log filtering
            datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Test 1: Explicit O3 model selection
            self.logger.info("  1: Testing explicit O3 model selection")

            response1, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Simple test: What is 2 + 2? Just give a brief answer.",
                    "model": "o3",
                    "temperature": 1.0,  # O3 only supports default temperature of 1.0
                },
            )

            if not response1:
                self.logger.error("  ❌ O3 model test failed")
                return False

            self.logger.info("  ✅ O3 model call completed")

            # Test 2: Explicit O3-mini model selection
            self.logger.info("  2: Testing explicit O3-mini model selection")

            response2, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Simple test: What is 3 + 3? Just give a brief answer.",
                    "model": "o3-mini",
                    "temperature": 1.0,  # O3-mini only supports default temperature of 1.0
                },
            )

            if not response2:
                self.logger.error("  ❌ O3-mini model test failed")
                return False

            self.logger.info("  ✅ O3-mini model call completed")

            # Test 3: Another tool with O3 to ensure it works across tools
            self.logger.info("  3: Testing O3 with different tool (codereview)")

            # Create a simple test file
            test_code = """def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
"""
            test_file = self.create_additional_test_file("simple_math.py", test_code)

            response3, _ = self.call_mcp_tool(
                "codereview",
                {
                    "files": [test_file],
                    "prompt": "Quick review of this simple code",
                    "model": "o3",
                    "temperature": 1.0,  # O3 only supports default temperature of 1.0
                },
            )

            if not response3:
                self.logger.error("  ❌ O3 with codereview tool failed")
                return False

            self.logger.info("  ✅ O3 with codereview tool completed")

            # Validate model usage from server logs
            self.logger.info("  4: Validating model usage in logs")
            logs = self.get_recent_server_logs()

            # Check for OpenAI API calls (this proves O3 models are being used)
            openai_api_logs = [line for line in logs.split("\n") if "Sending request to openai API for" in line]

            # Check for OpenAI model usage logs
            openai_model_logs = [
                line for line in logs.split("\n") if "Using model:" in line and "openai provider" in line
            ]

            # Check for successful OpenAI responses
            openai_response_logs = [
                line for line in logs.split("\n") if "openai provider" in line and "Using model:" in line
            ]

            # Check that we have both chat and codereview tool calls to OpenAI
            chat_openai_logs = [line for line in logs.split("\n") if "Sending request to openai API for chat" in line]

            codereview_openai_logs = [
                line for line in logs.split("\n") if "Sending request to openai API for codereview" in line
            ]

            # Validation criteria - we expect 3 OpenAI calls (2 chat + 1 codereview)
            openai_api_called = len(openai_api_logs) >= 3  # Should see 3 OpenAI API calls
            openai_model_usage = len(openai_model_logs) >= 3  # Should see 3 model usage logs
            openai_responses_received = len(openai_response_logs) >= 3  # Should see 3 responses
            chat_calls_to_openai = len(chat_openai_logs) >= 2  # Should see 2 chat calls (o3 + o3-mini)
            codereview_calls_to_openai = len(codereview_openai_logs) >= 1  # Should see 1 codereview call (o3)

            self.logger.info(f"   OpenAI API call logs: {len(openai_api_logs)}")
            self.logger.info(f"   OpenAI model usage logs: {len(openai_model_logs)}")
            self.logger.info(f"   OpenAI response logs: {len(openai_response_logs)}")
            self.logger.info(f"   Chat calls to OpenAI: {len(chat_openai_logs)}")
            self.logger.info(f"   Codereview calls to OpenAI: {len(codereview_openai_logs)}")

            # Log sample evidence for debugging
            if self.verbose and openai_api_logs:
                self.logger.debug("  📋 Sample OpenAI API logs:")
                for log in openai_api_logs[:5]:
                    self.logger.debug(f"    {log}")

            if self.verbose and chat_openai_logs:
                self.logger.debug("  📋 Sample chat OpenAI logs:")
                for log in chat_openai_logs[:3]:
                    self.logger.debug(f"    {log}")

            # Success criteria
            success_criteria = [
                ("OpenAI API calls made", openai_api_called),
                ("OpenAI model usage logged", openai_model_usage),
                ("OpenAI responses received", openai_responses_received),
                ("Chat tool used OpenAI", chat_calls_to_openai),
                ("Codereview tool used OpenAI", codereview_calls_to_openai),
            ]

            passed_criteria = sum(1 for _, passed in success_criteria if passed)
            self.logger.info(f"   Success criteria met: {passed_criteria}/{len(success_criteria)}")

            for criterion, passed in success_criteria:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {criterion}")

            if passed_criteria >= 3:  # At least 3 out of 4 criteria
                self.logger.info("  ✅ O3 model selection validation passed")
                return True
            else:
                self.logger.error("  ❌ O3 model selection validation failed")
                return False

        except Exception as e:
            self.logger.error(f"O3 model selection test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()

    def _run_openrouter_o3_test(self) -> bool:
        """Test O3 model selection when using OpenRouter"""
        try:
            # Setup test files
            self.setup_test_files()

            # Test 1: O3 model via OpenRouter
            self.logger.info("  1: Testing O3 model via OpenRouter")

            response1, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Simple test: What is 2 + 2? Just give a brief answer.",
                    "model": "o3",
                    "temperature": 1.0,
                },
            )

            if not response1:
                self.logger.error("  ❌ O3 model test via OpenRouter failed")
                return False

            self.logger.info("  ✅ O3 model call via OpenRouter completed")

            # Test 2: O3-mini model via OpenRouter
            self.logger.info("  2: Testing O3-mini model via OpenRouter")

            response2, _ = self.call_mcp_tool(
                "chat",
                {
                    "prompt": "Simple test: What is 3 + 3? Just give a brief answer.",
                    "model": "o3-mini",
                    "temperature": 1.0,
                },
            )

            if not response2:
                self.logger.error("  ❌ O3-mini model test via OpenRouter failed")
                return False

            self.logger.info("  ✅ O3-mini model call via OpenRouter completed")

            # Test 3: Codereview with O3 via OpenRouter
            self.logger.info("  3: Testing O3 with codereview tool via OpenRouter")

            test_code = """def add(a, b):
    return a + b

def multiply(x, y):
    return x * y
"""
            test_file = self.create_additional_test_file("simple_math.py", test_code)

            response3, _ = self.call_mcp_tool(
                "codereview",
                {
                    "files": [test_file],
                    "prompt": "Quick review of this simple code",
                    "model": "o3",
                    "temperature": 1.0,
                },
            )

            if not response3:
                self.logger.error("  ❌ O3 with codereview tool via OpenRouter failed")
                return False

            self.logger.info("  ✅ O3 with codereview tool via OpenRouter completed")

            # Validate OpenRouter usage in logs
            self.logger.info("  4: Validating OpenRouter usage in logs")
            logs = self.get_recent_server_logs()

            # Check for OpenRouter API calls
            openrouter_api_logs = [
                line
                for line in logs.split("\n")
                if "openrouter" in line.lower() and ("API" in line or "request" in line)
            ]

            # Check for model resolution through OpenRouter
            openrouter_model_logs = [
                line for line in logs.split("\n") if "openrouter" in line.lower() and ("o3" in line or "model" in line)
            ]

            # Check for successful responses
            openrouter_response_logs = [
                line for line in logs.split("\n") if "openrouter" in line.lower() and "response" in line
            ]

            self.logger.info(f"   OpenRouter API logs: {len(openrouter_api_logs)}")
            self.logger.info(f"   OpenRouter model logs: {len(openrouter_model_logs)}")
            self.logger.info(f"   OpenRouter response logs: {len(openrouter_response_logs)}")

            # Success criteria for OpenRouter
            openrouter_used = len(openrouter_api_logs) >= 3 or len(openrouter_model_logs) >= 3
            all_calls_succeeded = response1 and response2 and response3

            success_criteria = [
                ("All O3 model calls succeeded", all_calls_succeeded),
                ("OpenRouter provider was used", openrouter_used),
            ]

            passed_criteria = sum(1 for _, passed in success_criteria if passed)
            self.logger.info(f"   Success criteria met: {passed_criteria}/{len(success_criteria)}")

            for criterion, passed in success_criteria:
                status = "✅" if passed else "❌"
                self.logger.info(f"    {status} {criterion}")

            if passed_criteria == len(success_criteria):
                self.logger.info("  ✅ O3 model selection via OpenRouter passed")
                return True
            else:
                self.logger.error("  ❌ O3 model selection via OpenRouter failed")
                return False

        except Exception as e:
            self.logger.error(f"OpenRouter O3 test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()


def main():
    """Run the O3 model selection tests"""
    import sys

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    test = O3ModelSelectionTest(verbose=verbose)

    success = test.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
