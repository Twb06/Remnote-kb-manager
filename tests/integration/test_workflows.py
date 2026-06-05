"""
Integration tests for v0.3 pipeline workflow.

Tests main.py helper functions and PipelineV6 stages with mocked NLI router.
No external services required.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import _build_context_trees, _flatten_kb_map, _parse_answer_lines
from src.pipeline.core import KnowledgeItem, PipelineV6

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# _flatten_kb_map
# ---------------------------------------------------------------------------


MINIMAL_KB_MAP = {
    "root": {"remId": "root1", "title": "Root"},
    "branches": [
        {
            "remId": "b1",
            "title": "Vision Loss",
            "children": [
                {"remId": "c1", "title": "GCA", "children": []},
                {"remId": "c2", "title": "CRAO", "children": []},
            ],
        }
    ],
}


@pytest.mark.integration
class TestFlattenKbMap:
    """Tests for the main._flatten_kb_map helper."""

    def test_root_is_included(self):
        flat = _flatten_kb_map(MINIMAL_KB_MAP)
        assert "Root" in flat
        assert flat["Root"] == "root1"

    def test_branch_included(self):
        flat = _flatten_kb_map(MINIMAL_KB_MAP)
        assert "Vision Loss" in flat
        assert flat["Vision Loss"] == "b1"

    def test_nested_children_included(self):
        flat = _flatten_kb_map(MINIMAL_KB_MAP)
        assert "GCA" in flat
        assert flat["GCA"] == "c1"
        assert "CRAO" in flat

    def test_empty_kb_map_returns_empty(self):
        flat = _flatten_kb_map({})
        assert flat == {}

    def test_none_remid_mapped_to_none(self):
        data = {
            "branches": [
                {"title": "NoId", "children": []}
            ]
        }
        flat = _flatten_kb_map(data)
        assert flat["NoId"] is None


# ---------------------------------------------------------------------------
# _build_context_trees
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBuildContextTrees:
    """Tests for the main._build_context_trees helper."""

    def test_returns_dict_keyed_by_remid(self):
        trees = _build_context_trees(MINIMAL_KB_MAP)
        assert "b1" in trees

    def test_tree_has_expected_structure(self):
        trees = _build_context_trees(MINIMAL_KB_MAP)
        tree = trees["b1"]
        assert tree["title"] == "Vision Loss"
        assert isinstance(tree["children"], list)
        assert len(tree["children"]) == 2

    def test_empty_branches_returns_empty(self):
        trees = _build_context_trees({"branches": []})
        assert trees == {}


# ---------------------------------------------------------------------------
# _parse_answer_lines
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestParseAnswerLines:
    """Tests for the main._parse_answer_lines helper."""

    def test_strips_header(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("## answer\n- Topic A\n  - Sub B\n", encoding="utf-8")
        lines = _parse_answer_lines(f)
        assert all(not l.strip().startswith("## ") for l in lines)
        assert any("Topic A" in l for l in lines)

    def test_preserves_indentation(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("Root\n  Child\n    Grandchild\n", encoding="utf-8")
        lines = _parse_answer_lines(f)
        assert lines[1].startswith("  ")
        assert lines[2].startswith("    ")

    def test_trailing_blank_lines_stripped(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("Line 1\n\n\n", encoding="utf-8")
        lines = _parse_answer_lines(f)
        assert lines[-1].strip() != ""


# ---------------------------------------------------------------------------
# PipelineV6 integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPipelineV6Workflow:
    """Integration tests for PipelineV6 steps with in-memory data."""

    LINES = [
        "Vision Loss",
        "  GCA",
        "    Jaw claudication",
        "  CRAO",
    ]
    KB_MAP = {"Vision Loss": "b1", "GCA": "c1", "CRAO": "c2", "Jaw claudication": None}
    CONTEXT_TREES = {
        "b1": {
            "id": "b1",
            "title": "Vision Loss",
            "content": "Broad category of visual impairment",
            "children": [
                {"id": "c1", "title": "GCA", "content": "Giant cell arteritis", "children": []}
            ],
        }
    }

    def test_execute_pipeline_returns_knowledge_items(self):
        pipeline = PipelineV6()
        items = pipeline.execute_pipeline(
            self.LINES,
            list(self.KB_MAP.keys()),
            self.KB_MAP,
            self.CONTEXT_TREES,
        )
        assert len(items) == 4
        assert all(isinstance(i, KnowledgeItem) for i in items)

    def test_existing_term_gets_update_action(self):
        pipeline = PipelineV6()
        items = pipeline.execute_pipeline(
            self.LINES,
            list(self.KB_MAP.keys()),
            self.KB_MAP,
            self.CONTEXT_TREES,
        )
        gca_item = next(i for i in items if i.term == "GCA")
        assert gca_item.action == "UPDATE"
        assert gca_item.rem_id == "c1"

    def test_new_term_gets_create_action(self):
        pipeline = PipelineV6()
        items = pipeline.execute_pipeline(
            self.LINES,
            list(self.KB_MAP.keys()),
            self.KB_MAP,
            self.CONTEXT_TREES,
        )
        jaw_item = next(i for i in items if i.term == "Jaw claudication")
        assert jaw_item.action == "CREATE"
        assert jaw_item.rem_id is None

    def test_breadcrumb_path_preserved(self):
        pipeline = PipelineV6()
        items = pipeline.execute_pipeline(
            self.LINES,
            list(self.KB_MAP.keys()),
            self.KB_MAP,
            self.CONTEXT_TREES,
        )
        jaw_item = next(i for i in items if i.term == "Jaw claudication")
        assert "Vision Loss" in jaw_item.new_breadcrumb or "Vision Loss" in " > ".join(
            jaw_item.new_breadcrumb_parts
        )

    def test_statistics_populated_after_pipeline(self):
        pipeline = PipelineV6()
        pipeline.execute_pipeline(
            self.LINES,
            list(self.KB_MAP.keys()),
            self.KB_MAP,
            self.CONTEXT_TREES,
        )
        stats = pipeline.get_statistics()
        assert stats["total_items"] == 4
        assert stats["create_count"] + stats["update_count"] == 4




@pytest.mark.integration
class TestSearchUnmapped:
    """Legacy placeholder - kept as skip to preserve suite history."""

    def test_search_finds_results(self):
        pytest.skip("smart_logic_v5 removed; covered by TestPipelineV6Workflow")

    def test_search_empty_results(self):
        pytest.skip("smart_logic_v5 removed; covered by TestPipelineV6Workflow")

    def test_search_top_5_candidates(self):
        pytest.skip("smart_logic_v5 removed; covered by TestPipelineV6Workflow")
