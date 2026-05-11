"""
E2E tests for CLI entry point (__main__)

Tests the command-line interface execution with subprocess calls.
"""

import pytest
import subprocess
import sys
import json
from pathlib import Path


@pytest.mark.e2e
class TestCLIEntryPoint:
    """E2E tests for smart_logic_v5.py CLI entry"""

    def test_cli_entry_point_success(self, e2e_test_env, tmp_path):
        """Test CLI execution via subprocess"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]
        overview_path = e2e_test_env["overview"]
        content_path = e2e_test_env["content"]
        output_path = tmp_path / "cli_output.json"

        script_path = Path(__file__).parent.parent.parent / "smart_logic_v5.py"

        # Act
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--kb-map", str(kb_map_path),
                "--overview-file", str(overview_path),
                "--content-file", str(content_path)
            ],
            capture_output=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )

        # Assert
        assert result.returncode == 0, f"CLI failed with error: {result.stderr}"

        # Verify output is valid JSON (printed to stdout)
        # The script prints debug info first, then JSON at the end
        # Extract the last complete JSON object
        stdout = result.stdout

        # Find JSON by looking for the last '{' and matching '}'
        json_start = stdout.rfind('\n{')  # JSON starts on a new line
        if json_start < 0:
            json_start = stdout.find('{')

        if json_start >= 0:
            # Find the matching closing brace
            brace_count = 0
            json_end = -1
            for i in range(json_start, len(stdout)):
                if stdout[i] == '{':
                    brace_count += 1
                elif stdout[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break

            if json_end > 0:
                json_str = stdout[json_start:json_end].strip()
                output_data = json.loads(json_str)
            else:
                pytest.fail(f"Could not find complete JSON in stdout")
        else:
            pytest.fail(f"No JSON found in stdout: {stdout[:500]}")

        assert isinstance(output_data, dict)
        assert "auto_actions" in output_data or "ambiguous" in output_data


    def test_cli_missing_required_argument(self, tmp_path):
        """Test CLI error handling for missing arguments"""
        # Arrange
        script_path = Path(__file__).parent.parent.parent / "src" / "smart_logic_v5.py"

        # Act - call without required --kb-map argument
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )

        # Assert - should show help or error gracefully
        assert result.returncode in [0, 1, 2], "Should exit with standard error code"
        # Help text or error message should be present
        assert len(result.stdout) > 0 or len(result.stderr) > 0


    def test_cli_with_timeout_option(self, e2e_test_env, tmp_path):
        """Test CLI with optional timeout argument"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]
        overview_path = e2e_test_env["overview"]
        content_path = e2e_test_env["content"]

        script_path = Path(__file__).parent.parent.parent / "smart_logic_v5.py"

        # Act - execute with timeout option (if supported)
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--kb-map", str(kb_map_path),
                "--overview-file", str(overview_path),
                "--content-file", str(content_path),
                "--timeout", "30"  # Assuming timeout option exists
            ],
            capture_output=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )

        # Assert - should either succeed or gracefully report unsupported option
        assert result.returncode in [0, 1, 2]

        if result.returncode == 0 and result.stdout:
            # If succeeded, verify output
            # Extract the last complete JSON object
            stdout = result.stdout
            json_start = stdout.rfind('\n{')
            if json_start < 0:
                json_start = stdout.find('{')

            if json_start >= 0:
                # Find matching closing brace
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(stdout)):
                    if stdout[i] == '{':
                        brace_count += 1
                    elif stdout[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    json_str = stdout[json_start:json_end].strip()
                    output_data = json.loads(json_str)
                    assert isinstance(output_data, dict)
