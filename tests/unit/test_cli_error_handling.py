"""
Tests for CLI error handling in smart_logic_v5.py

These tests cover error paths in run_cli() that were previously
uncovered, including JSON parsing errors and subprocess exceptions.
"""

import pytest
from unittest.mock import patch, MagicMock
from smart_logic_v5 import run_cli


class TestRunCliErrorHandling:
    """Test error handling in run_cli function"""

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_handles_json_decode_error(self, mock_run):
        """Test run_cli handles invalid JSON from CLI"""
        # Mock subprocess to return invalid JSON
        mock_result = MagicMock()
        mock_result.stdout = "Invalid JSON {{"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = run_cli(["search", "test"])

        assert "error" in result
        assert "No JSON found" in result["error"]
        assert "raw" in result
        assert result["raw"] == "Invalid JSON {{"

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_handles_empty_output(self, mock_run):
        """Test run_cli handles empty CLI output"""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = run_cli(["search", "test"])

        assert "error" in result
        assert "No JSON found" in result["error"]

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_handles_subprocess_exception(self, mock_run):
        """Test run_cli handles subprocess exceptions"""
        # Mock subprocess to raise OSError
        mock_run.side_effect = OSError("Command not found: npx")

        result = run_cli(["search", "test"])

        assert "error" in result
        assert "Command not found" in result["error"]

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_handles_timeout_exception(self, mock_run):
        """Test run_cli handles subprocess timeout"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["npx", "remnote-cli"],
            timeout=60
        )

        result = run_cli(["search", "test"])

        assert "error" in result
        # TimeoutExpired error message contains the command and timeout
        assert "remnote-cli" in result["error"] or "timeout" in result["error"].lower()

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_handles_json_with_trailing_text(self, mock_run):
        """Test run_cli extracts JSON when surrounded by other text"""
        mock_result = MagicMock()
        mock_result.stdout = 'Some debug output\n{"success": true}\nMore output'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = run_cli(["search", "test"])

        # Should successfully extract the JSON object
        assert "error" not in result
        assert result["success"] is True

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_handles_unexpected_exception_type(self, mock_run):
        """Test run_cli handles unexpected exception types"""
        # Simulate an unexpected error type
        mock_run.side_effect = RuntimeError("Unexpected system error")

        result = run_cli(["search", "test"])

        assert "error" in result
        assert "Unexpected system error" in result["error"]
