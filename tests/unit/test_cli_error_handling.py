"""
Tests for CLI error handling in main.py (v0.3 pipeline entry point).

Covers error paths: missing files, bad kb_map, and pipeline argument validation.
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import main as main_module


class TestRunCliErrorHandling:
    """Test error handling in main.main() CLI entry point"""

    def test_missing_answer_file_returns_nonzero(self, tmp_path):
        """main() returns 1 when the answer file does not exist"""
        kb_map = tmp_path / "kb_map.json"
        kb_map.write_text(json.dumps({"root": {"remId": "r1", "title": "t"}, "branches": []}))
        rc = main_module.main([
            "--answer-file", str(tmp_path / "nonexistent.md"),
            "--kb-map", str(kb_map),
        ])
        assert rc == 1

    def test_missing_kb_map_returns_nonzero(self, tmp_path):
        """main() returns 1 when the kb_map file does not exist"""
        answer = tmp_path / "answer.md"
        answer.write_text("*   Glaucoma\n")
        rc = main_module.main([
            "--answer-file", str(answer),
            "--kb-map", str(tmp_path / "nonexistent.json"),
        ])
        assert rc == 1

    def test_dry_run_does_not_write_output(self, tmp_path):
        """main() with --dry-run must not create the output JSON"""
        answer = tmp_path / "answer.md"
        answer.write_text("*   Glaucoma\n")
        kb_map = tmp_path / "kb_map.json"
        kb_map.write_text(json.dumps({"root": {"remId": "r1", "title": "t"}, "branches": []}))
        output = tmp_path / "out.json"

        with patch("main.RealNLIRouter") as mock_router_cls:
            mock_router = MagicMock()
            mock_router.apply_nli_routing.return_value = {
                "final_actions": [],
                "requires_llm_intervention": [],
                "statistics": {
                    "created": 0, "updated": 0, "skipped": 0,
                    "requires_llm": 0, "avg_nli_confidence": 1.0,
                    "ambiguous_rate": 0.0, "total_processed": 0,
                },
            }
            mock_router_cls.return_value = mock_router

            rc = main_module.main([
                "--answer-file", str(answer),
                "--kb-map", str(kb_map),
                "--output", str(output),
                "--dry-run",
            ])

        assert rc == 0
        assert not output.exists()

    def test_valid_run_writes_output(self, tmp_path):
        """main() writes pipeline_output.json on a successful run"""
        answer = tmp_path / "answer.md"
        answer.write_text("*   Glaucoma\n")
        kb_map = tmp_path / "kb_map.json"
        kb_map.write_text(json.dumps({"root": {"remId": "r1", "title": "t"}, "branches": []}))
        output = tmp_path / "out.json"

        with patch("main.RealNLIRouter") as mock_router_cls:
            mock_router = MagicMock()
            mock_router.apply_nli_routing.return_value = {
                "final_actions": [],
                "requires_llm_intervention": [],
                "statistics": {
                    "created": 0, "updated": 0, "skipped": 0,
                    "requires_llm": 0, "avg_nli_confidence": 1.0,
                    "ambiguous_rate": 0.0, "total_processed": 0,
                },
            }
            mock_router_cls.return_value = mock_router

            rc = main_module.main([
                "--answer-file", str(answer),
                "--kb-map", str(kb_map),
                "--output", str(output),
            ])

        assert rc == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["pipeline_version"] == "v0.3"

    def test_output_contains_statistics_key(self, tmp_path):
        """Output JSON must contain nli_statistics"""
        answer = tmp_path / "answer.md"
        answer.write_text("*   Glaucoma\n")
        kb_map = tmp_path / "kb_map.json"
        kb_map.write_text(json.dumps({"root": {"remId": "r1", "title": "t"}, "branches": []}))
        output = tmp_path / "out.json"

        with patch("main.RealNLIRouter") as mock_router_cls:
            mock_router = MagicMock()
            mock_router.apply_nli_routing.return_value = {
                "final_actions": [],
                "requires_llm_intervention": [],
                "statistics": {
                    "created": 0, "updated": 0, "skipped": 0,
                    "requires_llm": 0, "avg_nli_confidence": 1.0,
                    "ambiguous_rate": 0.0, "total_processed": 0,
                },
            }
            mock_router_cls.return_value = mock_router

            main_module.main([
                "--answer-file", str(answer),
                "--kb-map", str(kb_map),
                "--output", str(output),
            ])

        data = json.loads(output.read_text())
        assert "nli_statistics" in data

    def test_output_contains_final_actions_list(self, tmp_path):
        """detailed_output.final_actions must be a list"""
        answer = tmp_path / "answer.md"
        answer.write_text("*   Glaucoma\n")
        kb_map = tmp_path / "kb_map.json"
        kb_map.write_text(json.dumps({"root": {"remId": "r1", "title": "t"}, "branches": []}))
        output = tmp_path / "out.json"

        with patch("main.RealNLIRouter") as mock_router_cls:
            mock_router = MagicMock()
            mock_router.apply_nli_routing.return_value = {
                "final_actions": [],
                "requires_llm_intervention": [],
                "statistics": {
                    "created": 0, "updated": 0, "skipped": 0,
                    "requires_llm": 0, "avg_nli_confidence": 1.0,
                    "ambiguous_rate": 0.0, "total_processed": 0,
                },
            }
            mock_router_cls.return_value = mock_router

            main_module.main([
                "--answer-file", str(answer),
                "--kb-map", str(kb_map),
                "--output", str(output),
            ])

        data = json.loads(output.read_text())
        assert isinstance(data["detailed_output"]["final_actions"], list)

