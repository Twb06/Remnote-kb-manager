"""
E2E tests for main.run_pipeline().

Tests the complete pipeline using the real e2e fixture files.
NLI router is mocked to avoid model loading overhead in CI.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import _build_context_trees, _flatten_kb_map, _parse_answer_lines, run_pipeline

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixtures():
    """Load e2e fixture data once."""
    kb_data = json.loads((FIXTURES / "e2e_kb_map.json").read_text(encoding="utf-8-sig"))
    kb_map = _flatten_kb_map(kb_data)
    context_trees = _build_context_trees(kb_data)
    answer_lines = _parse_answer_lines(FIXTURES / "e2e_content.md")
    return answer_lines, kb_map, context_trees


def _make_mock_router(created=2, updated=1, skipped=1):
    """Build a MockNLIRouter that returns a minimal valid result dict."""
    from src.routers.nli_types import FinalAction

    actions = [
        FinalAction(
            action="CREATE",
            term=f"Term{i}",
            new_breadcrumb=f"[Root] Term{i}",
            existing_breadcrumb=None,
            nli_confidence=0.95,
            delta_confidence=0.0,
        )
        for i in range(created)
    ]
    mock = MagicMock()
    mock.apply_nli_routing.return_value = {
        "final_actions": actions,
        "requires_llm_intervention": [],
        "statistics": {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "requires_llm": 0,
            "avg_nli_confidence": 0.92,
        },
    }
    return mock


@pytest.mark.e2e
class TestRunPipelineE2E:
    """E2E tests for main.run_pipeline() using fixture files."""

    def test_result_has_required_top_level_keys(self):
        answer_lines, kb_map, context_trees = _load_fixtures()
        with patch("main.RealNLIRouter", return_value=_make_mock_router()):
            result = run_pipeline(answer_lines, kb_map, context_trees)
        assert "pipeline_version" in result
        assert "nli_statistics" in result
        assert "detailed_output" in result
        assert "execution_summary" in result

    def test_final_actions_is_list(self):
        answer_lines, kb_map, context_trees = _load_fixtures()
        with patch("main.RealNLIRouter", return_value=_make_mock_router()):
            result = run_pipeline(answer_lines, kb_map, context_trees)
        assert isinstance(result["detailed_output"]["final_actions"], list)

    def test_statistics_contains_counts(self):
        answer_lines, kb_map, context_trees = _load_fixtures()
        with patch("main.RealNLIRouter", return_value=_make_mock_router(created=3, updated=2, skipped=1)):
            result = run_pipeline(answer_lines, kb_map, context_trees)
        stats = result["nli_statistics"]
        for key in ("created", "updated", "skipped", "requires_llm", "avg_nli_confidence"):
            assert key in stats

    def test_auto_processing_rate_between_0_and_1(self):
        answer_lines, kb_map, context_trees = _load_fixtures()
        with patch("main.RealNLIRouter", return_value=_make_mock_router()):
            result = run_pipeline(answer_lines, kb_map, context_trees)
        assert 0.0 <= result["auto_processing_rate"] <= 1.0

    def test_empty_answer_lines_returns_result(self):
        _unused, kb_map, context_trees = _load_fixtures()
        with patch("main.RealNLIRouter", return_value=_make_mock_router(created=0, updated=0, skipped=0)):
            result = run_pipeline([], kb_map, context_trees)
        assert result["execution_summary"]["total_knowledge_items"] == 0

    def test_pipeline_version_is_v03(self):
        answer_lines, kb_map, context_trees = _load_fixtures()
        with patch("main.RealNLIRouter", return_value=_make_mock_router()):
            result = run_pipeline(answer_lines, kb_map, context_trees)
        assert result["pipeline_version"] == "v0.3"
