"""
E2E tests for main.py CLI entry point.

Tests command-line invocation of main.py via subprocess with real fixture files.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
MAIN_PY = Path(__file__).parent.parent.parent / "main.py"
KB_MAP = FIXTURES / "e2e_kb_map.json"
ANSWER = FIXTURES / "e2e_content.md"


def _run_main(*extra_args, timeout=120):
    """Run main.py as subprocess and return CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(MAIN_PY)] + list(extra_args),
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )


@pytest.mark.e2e
class TestCLIEntryPoint:
    """E2E tests for the main.py CLI."""

    def test_help_exits_zero(self):
        result = _run_main("--help", timeout=10)
        assert result.returncode == 0
        assert "--answer-file" in result.stdout
        assert "--kb-map" in result.stdout

    def test_missing_answer_file_exits_nonzero(self, tmp_path):
        result = _run_main(
            "--answer-file", str(tmp_path / "nonexistent.md"),
            "--kb-map", str(KB_MAP),
            timeout=10,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_missing_kb_map_exits_nonzero(self, tmp_path):
        result = _run_main(
            "--answer-file", str(ANSWER),
            "--kb-map", str(tmp_path / "nonexistent.json"),
            timeout=10,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_dry_run_does_not_write_output(self, tmp_path):
        out_file = tmp_path / "out.json"
        result = _run_main(
            "--answer-file", str(ANSWER),
            "--kb-map", str(KB_MAP),
            "--output", str(out_file),
            "--dry-run",
            timeout=300,
        )
        assert result.returncode == 0, result.stderr
        assert not out_file.exists()

    def test_successful_run_writes_json_output(self, tmp_path):
        out_file = tmp_path / "out.json"
        result = _run_main(
            "--answer-file", str(ANSWER),
            "--kb-map", str(KB_MAP),
            "--output", str(out_file),
            timeout=300,
        )
        assert result.returncode == 0, f"STDERR: {result.stderr[:500]}"
        assert out_file.exists(), "Output JSON file was not written"
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "pipeline_version" in data
        assert "nli_statistics" in data
        assert "detailed_output" in data

    def test_output_contains_final_actions_list(self, tmp_path):
        out_file = tmp_path / "out.json"
        result = _run_main(
            "--answer-file", str(ANSWER),
            "--kb-map", str(KB_MAP),
            "--output", str(out_file),
            timeout=300,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert isinstance(data["detailed_output"]["final_actions"], list)
