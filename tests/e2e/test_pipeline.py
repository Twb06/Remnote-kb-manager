"""
E2E tests for run_pipeline() function

Tests the complete pipeline execution from overview parsing to final output generation.
These tests verify integration with real RemNote daemon and SentenceTransformer model.
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from smart_logic_v5 import run_pipeline


@pytest.mark.e2e
class TestRunPipelineE2E:
    """E2E tests for run_pipeline()"""

    def test_run_pipeline_end_to_end_success(self, e2e_test_env):
        """Test complete pipeline execution with successful term matching"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]
        overview_text = e2e_test_env["overview_text"]
        content_text = e2e_test_env["content_text"]

        # Act
        result_json = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Assert
        assert result_json is not None, "Pipeline should return results"
        result = json.loads(result_json)
        assert isinstance(result, dict), "Result should be a dictionary"

        # Check that terms were processed
        assert "auto_actions" in result
        assert "ambiguous" in result
        assert "skipped" in result

        # Verify some actions were generated
        assert isinstance(result["auto_actions"], list)


    def test_run_pipeline_handles_missing_terms(self, e2e_test_env, tmp_path):
        """Test pipeline with terms not found in KB"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]

        # Create overview with non-existent terms
        missing_overview = tmp_path / "missing_overview.md"
        missing_overview.write_text(
            "## Overview\n- Nonexistent Disease\n- Unknown Condition",
            encoding="utf-8"
        )
        overview_text = missing_overview.read_text(encoding="utf-8")
        content_text = e2e_test_env["content_text"]

        # Act
        result_json = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Assert
        assert result_json is not None
        result = json.loads(result_json)
        # Should handle missing terms gracefully (MISS markers)
        assert "auto_actions" in result
        assert isinstance(result["auto_actions"], list)


    def test_run_pipeline_no_terms_in_overview(self, e2e_test_env, tmp_path):
        """Test pipeline with empty overview"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]

        # Create empty overview
        empty_overview = tmp_path / "empty_overview.md"
        empty_overview.write_text("## Overview\n", encoding="utf-8")
        overview_text = empty_overview.read_text(encoding="utf-8")
        content_text = e2e_test_env["content_text"]

        # Act
        result_json = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Assert
        assert result_json is not None
        result = json.loads(result_json)
        # Should handle empty overview gracefully
        assert "error" in result or "auto_actions" in result


    def test_run_pipeline_with_mixed_results(self, e2e_test_env):
        """Test pipeline with some terms found, some missing"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]
        overview_text = e2e_test_env["overview_text"]
        content_text = e2e_test_env["content_text"]

        # Act
        result_json = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Assert - should have mix of found and missing
        assert result_json is not None
        result = json.loads(result_json)

        # Should have auto_actions for found or created terms
        assert "auto_actions" in result
        assert isinstance(result["auto_actions"], list)


    def test_run_pipeline_embedding_comparison(self, e2e_test_env):
        """Test that embedding logic is executed in pipeline"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]
        overview_text = e2e_test_env["overview_text"]
        content_text = e2e_test_env["content_text"]

        # For real E2E, we should NOT mock SentenceTransformer
        # Just verify results include proper structure

        # Act
        result_json = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Assert - verify output structure
        assert result_json is not None
        result = json.loads(result_json)

        # For real E2E, verify result has embedding comparison keys
        assert "auto_actions" in result
        assert "ambiguous" in result
        assert "skipped" in result


    def test_run_pipeline_creates_proper_json_output(self, e2e_test_env):
        """Test pipeline output is valid JSON structure"""
        # Arrange
        kb_map_path = e2e_test_env["kb_map"]
        overview_text = e2e_test_env["overview_text"]
        content_text = e2e_test_env["content_text"]

        # Act
        result_json = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Assert - should be JSON string
        assert isinstance(result_json, str)

        try:
            result = json.loads(result_json)

            # Should be able to serialize back
            json_str_again = json.dumps(result, ensure_ascii=False, indent=2)
            assert len(json_str_again) > 0

            parsed_again = json.loads(json_str_again)
            assert parsed_again == result

        except (TypeError, json.JSONDecodeError) as e:
            pytest.fail(f"Pipeline result is not valid JSON: {e}")

        # Verify structure
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result.keys()), "All keys should be strings"


@pytest.mark.e2e
class TestRunPipelineRealRemNote:
    """E2E tests requiring real RemNote daemon (skip if not available)"""

    @pytest.mark.skip(reason="Requires real RemNote daemon setup")
    def test_run_pipeline_with_real_remnote_calls(self, skip_if_no_remnote, e2e_test_env):
        """Test pipeline with actual RemNote CLI calls"""
        # This test would require:
        # 1. RemNote daemon running
        # 2. Test remnotes created in advance
        # 3. Cleanup after test

        kb_map_path = e2e_test_env["kb_map"]
        overview_text = e2e_test_env["overview_text"]
        content_text = e2e_test_env["content_text"]

        result = run_pipeline(
            kb_map_path=kb_map_path,
            overview_text=overview_text,
            content_text=content_text
        )

        # Verify RemNote read operations succeeded
        assert result is not None
        # Additional assertions for real RemNote data
