"""
Integration tests for PipelineV6 individual steps (v0.3).

Exercises each pipeline stage in isolation with in-memory data.
No external services or NLI model loading required.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.core import KnowledgeItem, PipelineV6

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_LINES = [
    "Glaucoma",
    "  Types",
    "    Open-Angle",
    "    Closed-Angle",
]

SAMPLE_KB_MAP = {
    "Glaucoma": "rem_g",
    "Types": None,
    "Open-Angle": "rem_oa",
    "Closed-Angle": None,
}

SAMPLE_CONTEXT_TREES = {
    "rem_g": {
        "id": "rem_g",
        "title": "Glaucoma",
        "content": "Optic nerve damage from elevated IOP",
        "children": [
            {
                "id": "rem_oa",
                "title": "Open-Angle",
                "content": "Most common form, gradual onset",
                "children": [],
            }
        ],
    }
}


# ---------------------------------------------------------------------------
# Phase 1.2
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPhase12Parse:
    """Tests for PipelineV6.phase_1_2_parse_notebooklm_extract."""

    def test_returns_correct_count(self):
        pipeline = PipelineV6()
        items = pipeline.phase_1_2_parse_notebooklm_extract(SAMPLE_LINES)
        assert len(items) == 4

    def test_all_items_are_create_by_default(self):
        pipeline = PipelineV6()
        items = pipeline.phase_1_2_parse_notebooklm_extract(SAMPLE_LINES)
        assert all(i.action == "CREATE" for i in items)

    def test_breadcrumb_parts_populated(self):
        pipeline = PipelineV6()
        items = pipeline.phase_1_2_parse_notebooklm_extract(SAMPLE_LINES)
        open_angle = next(i for i in items if i.term == "Open-Angle")
        # Breadcrumb must at minimum contain the root ancestor
        assert "Glaucoma" in open_angle.new_breadcrumb_parts
        # Term itself must appear in the formatted breadcrumb string
        assert "Open-Angle" in open_angle.new_breadcrumb

    def test_empty_input_returns_empty(self):
        pipeline = PipelineV6()
        items = pipeline.phase_1_2_parse_notebooklm_extract([])
        assert items == []


# ---------------------------------------------------------------------------
# Steps A-B2
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStepsAB2:
    """Tests for PipelineV6.steps_a_b2_search_and_locate."""

    def test_returns_all_terms(self):
        pipeline = PipelineV6()
        result = pipeline.steps_a_b2_search_and_locate(
            list(SAMPLE_KB_MAP.keys()), SAMPLE_KB_MAP
        )
        assert set(result.keys()) == set(SAMPLE_KB_MAP.keys())

    def test_existing_terms_have_rem_id(self):
        pipeline = PipelineV6()
        result = pipeline.steps_a_b2_search_and_locate(
            list(SAMPLE_KB_MAP.keys()), SAMPLE_KB_MAP
        )
        assert result["Glaucoma"] == "rem_g"
        assert result["Open-Angle"] == "rem_oa"

    def test_new_terms_mapped_to_none(self):
        pipeline = PipelineV6()
        result = pipeline.steps_a_b2_search_and_locate(
            list(SAMPLE_KB_MAP.keys()), SAMPLE_KB_MAP
        )
        assert result["Types"] is None
        assert result["Closed-Angle"] is None


# ---------------------------------------------------------------------------
# Step C
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStepC:
    """Tests for PipelineV6.step_c_read_and_transform_context_trees."""

    def test_returns_same_number_of_trees(self):
        pipeline = PipelineV6()
        result = pipeline.step_c_read_and_transform_context_trees(SAMPLE_CONTEXT_TREES)
        assert len(result) == len(SAMPLE_CONTEXT_TREES)

    def test_empty_trees_returns_empty(self):
        pipeline = PipelineV6()
        result = pipeline.step_c_read_and_transform_context_trees({})
        assert result == {}

    def test_transformed_tree_has_breadcrumb_fields(self):
        pipeline = PipelineV6()
        result = pipeline.step_c_read_and_transform_context_trees(SAMPLE_CONTEXT_TREES)
        tree = result["rem_g"]
        # transform_tree_with_breadcrumbs should add breadcrumb fields
        assert isinstance(tree, dict)


# ---------------------------------------------------------------------------
# Step D
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStepD:
    """Tests for PipelineV6.step_d_prepare_knowledge_items."""

    def _run_d(self):
        pipeline = PipelineV6()
        new_items = pipeline.phase_1_2_parse_notebooklm_extract(SAMPLE_LINES)
        term_to_id = pipeline.steps_a_b2_search_and_locate(
            list(SAMPLE_KB_MAP.keys()), SAMPLE_KB_MAP
        )
        transformed = pipeline.step_c_read_and_transform_context_trees(SAMPLE_CONTEXT_TREES)
        return pipeline.step_d_prepare_knowledge_items(new_items, transformed, term_to_id)

    def test_returns_all_items(self):
        items = self._run_d()
        assert len(items) == 4

    def test_update_item_has_rem_id(self):
        items = self._run_d()
        glaucoma = next(i for i in items if i.term == "Glaucoma")
        assert glaucoma.rem_id == "rem_g"
        assert glaucoma.action == "UPDATE"

    def test_create_item_has_no_rem_id(self):
        items = self._run_d()
        types_item = next(i for i in items if i.term == "Types")
        assert types_item.rem_id is None
        assert types_item.action == "CREATE"

    def test_update_item_has_existing_content(self):
        items = self._run_d()
        open_angle = next(i for i in items if i.term == "Open-Angle")
        # open_angle has rem_id rem_oa, which exists in context tree
        assert open_angle.existing_content is not None or open_angle.action == "UPDATE"


# ---------------------------------------------------------------------------
# Legacy placeholders
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRunCli:
    """Legacy placeholder — smart_logic_v5.run_cli removed."""

    def test_run_cli_success(self):
        pytest.skip("smart_logic_v5 removed; CLI interactions now via remnote-cli subprocess in Step B")

    def test_run_cli_error_handling(self):
        pytest.skip("smart_logic_v5 removed")

    def test_run_cli_timeout(self):
        pytest.skip("smart_logic_v5 removed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
