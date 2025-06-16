"""
Test suite for conversation memory file management features.

This module tests the enhanced conversation memory system including:
- File inclusion in conversation history
- Token-aware file inclusion planning
- Smart file size limiting for conversation history
- Cross-tool file context preservation
- MCP boundary vs conversation building separation
"""

import os
from unittest.mock import patch

from utils.conversation_memory import (
    ConversationTurn,
    ThreadContext,
    _plan_file_inclusion_by_size,
    build_conversation_history,
    get_conversation_file_list,
)


class TestConversationFileList:
    """Test file list extraction from conversation turns"""

    def test_get_conversation_file_list_basic(self):
        """Test that files are returned from conversation turns, newest first"""
        turns = [
            ConversationTurn(
                role="user",
                content="First turn (older)",
                timestamp="2023-01-01T00:00:00Z",
                files=["/project/file1.py", "/project/file2.py"],
            ),
            ConversationTurn(
                role="assistant",
                content="Second turn (newer)",
                timestamp="2023-01-01T00:01:00Z",
                files=["/project/file3.py"],
            ),
        ]

        context = ThreadContext(
            thread_id="test",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:01:00Z",
            tool_name="test",
            turns=turns,
            initial_context={},
        )

        files = get_conversation_file_list(context)

        # Should contain all unique files, with newest turn files first
        assert len(files) == 3
        assert files[0] == "/project/file3.py"  # From newest turn (turn 2)
        assert "/project/file1.py" in files[1:]  # From older turn (turn 1)
        assert "/project/file2.py" in files[1:]  # From older turn (turn 1)

    def test_get_conversation_file_list_deduplication(self):
        """Test that duplicate files are removed, prioritizing newer turns"""
        turns = [
            ConversationTurn(
                role="user",
                content="First mention (older)",
                timestamp="2023-01-01T00:00:00Z",
                files=["/project/file1.py", "/project/shared.py"],
            ),
            ConversationTurn(
                role="assistant",
                content="Duplicate mention (newer)",
                timestamp="2023-01-01T00:01:00Z",
                files=["/project/shared.py", "/project/file2.py"],  # shared.py is duplicate
            ),
        ]

        context = ThreadContext(
            thread_id="test",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:01:00Z",
            tool_name="test",
            turns=turns,
            initial_context={},
        )

        files = get_conversation_file_list(context)

        # Should have unique files only, with newer turn files first
        assert len(files) == 3
        # Files from turn 2 (newer) should come first
        assert files[0] == "/project/shared.py"  # From newer turn (turn 2)
        assert files[1] == "/project/file2.py"  # From newer turn (turn 2)
        # Files from turn 1 (older) that aren't duplicates
        assert files[2] == "/project/file1.py"  # From older turn (turn 1)


class TestFileInclusionPlanning:
    """Test token-aware file inclusion planning for conversation history"""

    def test_plan_file_inclusion_within_budget(self, project_path):
        """Test file inclusion when all files fit within token budget"""
        # Create small test files
        small_file1 = os.path.join(project_path, "small1.py")
        small_file2 = os.path.join(project_path, "small2.py")

        with open(small_file1, "w") as f:
            f.write("# Small file 1\nprint('hello')\n")  # ~30 chars
        with open(small_file2, "w") as f:
            f.write("# Small file 2\nprint('world')\n")  # ~30 chars

        all_files = [small_file1, small_file2]
        max_tokens = 1000  # Generous budget

        included, skipped, total_tokens = _plan_file_inclusion_by_size(all_files, max_tokens)

        assert included == all_files
        assert skipped == []
        assert total_tokens > 0  # Should have estimated some tokens

    def test_plan_file_inclusion_exceeds_budget(self, project_path):
        """Test file inclusion when files exceed token budget"""
        # Create files with different sizes
        small_file = os.path.join(project_path, "small.py")
        large_file = os.path.join(project_path, "large.py")

        with open(small_file, "w") as f:
            f.write("# Small file\nprint('hello')\n")  # ~25 chars
        with open(large_file, "w") as f:
            f.write("# Large file\n" + "x = 1\n" * 1000)  # Much larger

        all_files = [small_file, large_file]
        max_tokens = 50  # Very tight budget

        included, skipped, total_tokens = _plan_file_inclusion_by_size(all_files, max_tokens)

        # Should include some files, skip others when budget is tight
        assert len(included) + len(skipped) == 2
        assert total_tokens <= max_tokens

    def test_plan_file_inclusion_empty_list(self):
        """Test file inclusion planning with empty file list"""
        included, skipped, total_tokens = _plan_file_inclusion_by_size([], 1000)

        assert included == []
        assert skipped == []
        assert total_tokens == 0

    def test_plan_file_inclusion_nonexistent_files(self):
        """Test file inclusion planning with non-existent files"""
        nonexistent_files = ["/does/not/exist1.py", "/does/not/exist2.py"]

        included, skipped, total_tokens = _plan_file_inclusion_by_size(nonexistent_files, 1000)

        assert included == []
        assert skipped == nonexistent_files
        assert total_tokens == 0


class TestConversationHistoryBuilding:
    """Test conversation history building with file content embedding"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": ""}, clear=False)
    def test_build_conversation_history_with_file_content(self, project_path):
        """Test that conversation history includes embedded file content"""
        from providers.registry import ModelProviderRegistry

        ModelProviderRegistry.clear_cache()

        # Create test file with known content
        test_file = os.path.join(project_path, "test.py")
        test_content = "# Test file\ndef hello():\n    print('Hello, world!')\n"
        with open(test_file, "w") as f:
            f.write(test_content)

        # Create conversation with file reference
        turns = [
            ConversationTurn(
                role="user",
                content="Please analyze this file",
                timestamp="2023-01-01T00:00:00Z",
                files=[test_file],
            )
        ]

        context = ThreadContext(
            thread_id="test-thread",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:00:00Z",
            tool_name="analyze",
            turns=turns,
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        # Verify structure
        assert "=== CONVERSATION HISTORY (CONTINUATION) ===" in history
        assert "=== FILES REFERENCED IN THIS CONVERSATION ===" in history
        assert "--- Turn 1 (Claude) ---" in history

        # Verify file content is embedded
        assert "--- BEGIN FILE:" in history
        assert test_file in history
        assert test_content in history
        assert "--- END FILE:" in history

        # Verify turn content
        assert "Please analyze this file" in history
        assert f"Files used in this turn: {test_file}" in history

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": ""}, clear=False)
    def test_build_conversation_history_file_deduplication(self, project_path):
        """Test that files are embedded only once even if referenced multiple times"""
        from providers.registry import ModelProviderRegistry

        ModelProviderRegistry.clear_cache()

        test_file = os.path.join(project_path, "shared.py")
        with open(test_file, "w") as f:
            f.write("# Shared file\nshared_var = 42\n")

        # Multiple turns referencing the same file
        turns = [
            ConversationTurn(
                role="user",
                content="First look at this file",
                timestamp="2023-01-01T00:00:00Z",
                files=[test_file],
            ),
            ConversationTurn(
                role="assistant",
                content="Analysis complete",
                timestamp="2023-01-01T00:01:00Z",
                files=[test_file],  # Same file referenced again
            ),
        ]

        context = ThreadContext(
            thread_id="test-thread",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:01:00Z",
            tool_name="analyze",
            turns=turns,
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        # File should appear in embedded section only once
        file_begin_count = history.count("--- BEGIN FILE:")
        file_end_count = history.count("--- END FILE:")
        assert file_begin_count == 1, "File should be embedded exactly once"
        assert file_end_count == 1, "File should be embedded exactly once"

        # But should show in both turn references
        turn_file_refs = history.count(f"Files used in this turn: {test_file}")
        assert turn_file_refs == 2, "Both turns should show file usage"

    def test_build_conversation_history_empty_turns(self):
        """Test conversation history building with no turns"""
        context = ThreadContext(
            thread_id="empty-thread",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:00:00Z",
            tool_name="test",
            turns=[],
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        assert history == ""
        assert tokens == 0


class TestCrossToolFileContext:
    """Test cross-tool file context preservation in conversations"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": ""}, clear=False)
    def test_cross_tool_file_context_preservation(self, project_path):
        """Test that file context is preserved across different tools"""
        from providers.registry import ModelProviderRegistry

        ModelProviderRegistry.clear_cache()

        src_file = os.path.join(project_path, "src.py")
        test_file = os.path.join(project_path, "test.py")

        with open(src_file, "w") as f:
            f.write("def main():\n    return 'hello'\n")
        with open(test_file, "w") as f:
            f.write("import src\nassert src.main() == 'hello'\n")

        # Simulate cross-tool conversation with chronological timestamps
        turns = [
            ConversationTurn(
                role="assistant",
                content="I've analyzed the source code structure",
                timestamp="2023-01-01T00:00:00Z",  # First turn
                files=[src_file],
                tool_name="analyze",
            ),
            ConversationTurn(
                role="user",
                content="Now generate tests for it",
                timestamp="2023-01-01T00:01:00Z",  # Second turn (1 minute later)
                files=[test_file],
            ),
            ConversationTurn(
                role="assistant",
                content="I've generated comprehensive tests",
                timestamp="2023-01-01T00:02:00Z",  # Third turn (2 minutes later)
                files=[src_file, test_file],  # References both files
                tool_name="testgen",
            ),
        ]

        context = ThreadContext(
            thread_id="cross-tool-thread",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:02:00Z",
            tool_name="testgen",
            turns=turns,
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        # Verify cross-tool context
        assert "--- Turn 1 (Gemini using analyze) ---" in history
        assert "--- Turn 2 (Claude) ---" in history
        assert "--- Turn 3 (Gemini using testgen) ---" in history

        # Verify file context preservation
        assert "Files used in this turn: " + src_file in history
        assert "Files used in this turn: " + test_file in history
        assert f"Files used in this turn: {src_file}, {test_file}" in history

        # Verify both files are embedded
        files_section_start = history.find("=== FILES REFERENCED IN THIS CONVERSATION ===")
        first_file_pos = history.find(src_file, files_section_start)
        second_file_pos = history.find(test_file, files_section_start)

        assert first_file_pos > 0 and second_file_pos > 0


class TestLargeConversations:
    """Test behavior with large conversations, many files, and many turns"""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": ""}, clear=False)
    def test_large_conversation_with_many_files(self, project_path):
        """Test conversation with many files across multiple turns"""
        from providers.registry import ModelProviderRegistry

        ModelProviderRegistry.clear_cache()

        # Create 20 test files
        test_files = []
        for i in range(20):
            test_file = os.path.join(project_path, f"file{i:02d}.py")
            with open(test_file, "w") as f:
                f.write(f"# File {i}\nclass Module{i}:\n    def method(self):\n        return {i}\n")
            test_files.append(test_file)

        # Create 15 conversation turns with files spread across them
        turns = []
        for turn_num in range(15):
            # Distribute files across turns (some turns have multiple files)
            if turn_num < 10:
                turn_files = test_files[turn_num * 2 : (turn_num + 1) * 2]  # 2 files per turn
            else:
                turn_files = []  # Some turns without files

            turns.append(
                ConversationTurn(
                    role="user" if turn_num % 2 == 0 else "assistant",
                    content=f"Turn {turn_num} content - working on modules",
                    timestamp=f"2023-01-01T{turn_num:02d}:00:00Z",
                    files=turn_files,
                    tool_name="analyze" if turn_num % 3 == 0 else None,
                )
            )

        context = ThreadContext(
            thread_id="large-conversation",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T14:00:00Z",
            tool_name="analyze",
            turns=turns,
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        # Verify structure
        assert "=== CONVERSATION HISTORY (CONTINUATION) ===" in history
        assert "=== FILES REFERENCED IN THIS CONVERSATION ===" in history

        # Should handle large conversation gracefully
        assert len(history) > 1000  # Should have substantial content
        assert tokens > 0

        # Files from newer turns should be prioritized
        file_list = get_conversation_file_list(context)
        assert len(file_list) == 20  # All unique files

        # Files from turn 9 (newest with files) should come first
        newest_files = test_files[18:20]  # Files from turn 9
        assert file_list[0] in newest_files
        assert file_list[1] in newest_files


class TestSmallAndNewConversations:
    """Test behavior with small/new conversations and edge cases"""

    def test_empty_conversation(self):
        """Test completely empty conversation"""
        context = ThreadContext(
            thread_id="empty",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:00:00Z",
            tool_name="test",
            turns=[],
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        assert history == ""
        assert tokens == 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": ""}, clear=False)
    def test_single_turn_conversation(self, project_path):
        """Test conversation with just one turn"""
        from providers.registry import ModelProviderRegistry

        ModelProviderRegistry.clear_cache()

        test_file = os.path.join(project_path, "single.py")
        with open(test_file, "w") as f:
            f.write("# Single file\ndef hello():\n    return 'world'\n")

        turns = [
            ConversationTurn(
                role="user",
                content="Quick question about this file",
                timestamp="2023-01-01T00:00:00Z",
                files=[test_file],
            )
        ]

        context = ThreadContext(
            thread_id="single-turn",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:00:00Z",
            tool_name="chat",
            turns=turns,
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        # Should work correctly for single turn
        assert "=== CONVERSATION HISTORY (CONTINUATION) ===" in history
        assert "=== FILES REFERENCED IN THIS CONVERSATION ===" in history
        assert "--- Turn 1 (Claude) ---" in history
        assert "Quick question about this file" in history
        assert test_file in history
        assert tokens > 0


class TestFailureScenarios:
    """Test failure scenarios and error handling"""

    def test_file_list_with_missing_files(self):
        """Test conversation with references to missing files"""
        turns = [
            ConversationTurn(
                role="user",
                content="Analyze these files",
                timestamp="2023-01-01T00:00:00Z",
                files=["/does/not/exist.py", "/also/missing.py"],
            )
        ]

        context = ThreadContext(
            thread_id="missing-files",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:00:00Z",
            tool_name="analyze",
            turns=turns,
            initial_context={},
        )

        # Should handle missing files gracefully
        files = get_conversation_file_list(context)
        assert len(files) == 2  # Still returns file paths
        assert "/does/not/exist.py" in files
        assert "/also/missing.py" in files

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": ""}, clear=False)
    def test_conversation_with_unreadable_files(self, project_path):
        """Test conversation history building with unreadable files"""
        from providers.registry import ModelProviderRegistry

        ModelProviderRegistry.clear_cache()

        # Create a file that will be treated as missing
        missing_file = os.path.join(project_path, "nonexistent.py")

        # Create a readable file for comparison
        test_file = os.path.join(project_path, "readable.py")
        with open(test_file, "w") as f:
            f.write("# Test file\ndef test(): pass\n")

        turns = [
            ConversationTurn(
                role="user",
                content="Analyze these files",
                timestamp="2023-01-01T00:00:00Z",
                files=[test_file, missing_file],
            )
        ]

        context = ThreadContext(
            thread_id="mixed-files",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:00:00Z",
            tool_name="analyze",
            turns=turns,
            initial_context={},
        )

        history, tokens = build_conversation_history(context)

        # Should handle gracefully - build history with accessible files
        assert "=== CONVERSATION HISTORY (CONTINUATION) ===" in history
        assert "--- Turn 1 (Claude) ---" in history
        assert "Analyze these files" in history
        assert tokens > 0
