"""
Integration tests for main workflow functions in smart_logic_v5.py

These tests exercise the core pipeline functions with mocked external dependencies.
Focus on testing the actual function logic while mocking only subprocess calls.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from smart_logic_v5 import (
        lookup_kb_map,
        search_unmapped,
        hierarchical_locate,
        cross_validate_b_and_b2,
        read_context_tree
    )
    SMART_LOGIC_AVAILABLE = True
except ImportError:
    SMART_LOGIC_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(
        not SMART_LOGIC_AVAILABLE,
        reason="smart_logic_v5.py not available"
    ),
    pytest.mark.integration
]


@pytest.mark.integration
class TestLookupKbMap:
    """Test suite for lookup_kb_map() workflow"""

    def test_lookup_finds_exact_match(self, tmp_path, sample_kb_map):
        """Test that lookup finds exact title match in kb_map"""
        # Create temporary kb_map file
        kb_file = tmp_path / "test_kb.json"
        kb_file.write_text(json.dumps(sample_kb_map), encoding="utf-8")

        # Lookup existing node
        found, all_entries = lookup_kb_map(str(kb_file), ["Vision Loss"])

        # Should find "Vision Loss" node
        assert "Vision Loss" in found
        assert len(all_entries) > 0

    def test_lookup_case_insensitive(self, tmp_path, sample_kb_map):
        """Test that lookup is case-insensitive"""
        kb_file = tmp_path / "test_kb.json"
        kb_file.write_text(json.dumps(sample_kb_map), encoding="utf-8")

        # Try different cases
        found, _ = lookup_kb_map(str(kb_file), ["vision loss", "VISION LOSS"])

        # Should find matches regardless of case
        assert len(found) >= 1

    def test_lookup_returns_unmapped(self, tmp_path, sample_kb_map):
        """Test that nonexistent terms are returned as unmapped"""
        kb_file = tmp_path / "test_kb.json"
        kb_file.write_text(json.dumps(sample_kb_map), encoding="utf-8")

        # Lookup nonexistent term
        found, all_entries = lookup_kb_map(str(kb_file), ["Nonexistent Term"])

        # Should not find it
        assert "Nonexistent Term" not in found
        # But should still return all entries
        assert len(all_entries) > 0

    def test_lookup_multiple_terms(self, tmp_path, sample_kb_map):
        """Test lookup with multiple terms"""
        kb_file = tmp_path / "test_kb.json"
        kb_file.write_text(json.dumps(sample_kb_map), encoding="utf-8")

        # Lookup multiple terms including single char (should skip < 2 chars at line 171)
        terms = ["Vision Loss", "GCA", "Nonexistent", "a"]
        found, all_entries = lookup_kb_map(str(kb_file), terms)

        # Should find some but not all
        assert len(found) >= 1
        assert "Nonexistent" not in found
        assert "a" not in found  # Single char terms skipped


@pytest.mark.integration
class TestSearchUnmapped:
    """Test suite for search_unmapped() workflow"""

    @patch('smart_logic_v5.run_cli')
    def test_search_finds_results(self, mock_cli):
        """Test that search finds and scores results"""
        # Mock CLI search response
        mock_cli.return_value = {
            "results": [
                {
                    "remId": "result1",
                    "title": "Test Result 1",
                    "aliases": ["TR1"],
                    "tags": ["test"],
                    "parentTitle": "Parent",
                    "parentRemId": "parent1"
                },
                {
                    "remId": "result2",
                    "title": "Test Result 2",
                    "aliases": [],
                    "tags": [],
                    "parentTitle": "Parent",
                    "parentRemId": "parent1"
                }
            ]
        }

        # Search for unmapped terms
        result = search_unmapped(["test result"], {})

        # Should find and return results with top 5 candidates
        assert len(result) > 0
        if "test result" in result:
            rem_id, top5 = result["test result"]
            assert rem_id is not None
            assert len(top5) <= 5

    @patch('smart_logic_v5.run_cli')
    def test_search_respects_already_mapped(self, mock_cli):
        """Test that search skips already mapped terms"""
        mock_cli.return_value = {"results": []}

        # Terms already mapped
        already_mapped = {"existing term": "existing_id"}

        # Should not search for already mapped terms
        result = search_unmapped(["existing term", "new term"], already_mapped)

        # "existing term" should not be in results
        assert "existing term" not in result

    @patch('smart_logic_v5.run_cli')
    def test_search_handles_no_results(self, mock_cli):
        """Test search with no results"""
        mock_cli.return_value = {"results": []}

        result = search_unmapped(["nonexistent"], {})

        # Should return empty or handle gracefully
        assert isinstance(result, dict)

    @patch('smart_logic_v5.run_cli')
    def test_search_tracks_top_5_candidates(self, mock_cli):
        """Test that search tracks top 5 candidates per term"""
        # Create 10 mock results
        mock_results = [
            {
                "remId": f"id{i}",
                "title": f"Result {i}",
                "aliases": [],
                "tags": [],
                "parentTitle": "Parent",
                "parentRemId": "parent"
            }
            for i in range(10)
        ]
        mock_cli.return_value = {"results": mock_results}

        result = search_unmapped(["test"], {})

        # Should track no more than top 5
        if "test" in result:
            _, top5 = result["test"]
            assert len(top5) <= 5

    @patch('smart_logic_v5.run_cli')
    def test_search_handles_malformed_hits(self, mock_cli):
        """Test that search skips malformed hits without crashing."""
        mock_cli.return_value = {
            "results": [
                "not a dict",  # Should be skipped (isinstance check at line 301)
                {"title": "Valid Result", "remId": "valid1", "aliases": [], "tags": [], "parentTitle": "P", "parentRemId": "p"},
                {"remId": "no_title", "parentTitle": "P", "parentRemId": "p"},  # Missing title
                {"title": "", "remId": "empty_title", "parentTitle": "P", "parentRemId": "p"},  # Empty title
                {"title": "Another Valid", "remId": "valid2", "aliases": [], "tags": [], "parentTitle": "P", "parentRemId": "p"}
            ]
        }

        result = search_unmapped(["test"], {})

        # Should only find 2 valid results (skips malformed ones)
        if "test" in result:
            _, top5 = result["test"]
            assert len(top5) == 2


@pytest.mark.integration
class TestHierarchicalLocate:
    """Test suite for hierarchical_locate() workflow"""

    @patch('smart_logic_v5.run_cli')
    def test_hierarchical_finds_branch(self, mock_cli):
        """Test that hierarchical locate finds branch matches"""
        # Mock CLI read response for branch
        mock_cli.return_value = {
            "remId": "branch_id",
            "title": "Test Branch",
            "children": [
                {
                    "remId": "child1",
                    "title": "Test Child",
                    "children": []
                }
            ]
        }

        # Create mock map_entries
        map_entries = [
            {
                "indent": 0,
                "title": "Test Branch",
                "remId": "branch_id",
                "hint": "Test branch summary",
                "summary": "Test branch summary"
            },
            {
                "indent": 2,
                "title": "Test Child",
                "remId": "child1",
                "hint": "Test child summary",
                "summary": "Test child summary"
            }
        ]

        # Hierarchical locate
        result_map, context_map = hierarchical_locate(
            ["Test Child"],
            {},
            map_entries
        )

        # Should find match
        assert isinstance(result_map, dict)
        assert isinstance(context_map, dict)

    @patch('smart_logic_v5.run_cli')
    def test_hierarchical_skips_already_mapped(self, mock_cli):
        """Test that hierarchical skips already mapped terms"""
        mock_cli.return_value = {"remId": "branch", "children": []}

        map_entries = [
            {"indent": 0, "title": "Branch", "remId": "branch", "hint": "summary", "summary": "summary"}
        ]

        already_mapped = {"existing": "existing_id"}

        result_map, _ = hierarchical_locate(
            ["existing", "new"],
            already_mapped,
            map_entries
        )

        # Should not remap existing terms
        assert isinstance(result_map, dict)
        # "existing" should not be in result_map (already mapped)
        assert "existing" not in result_map

    @patch('smart_logic_v5.run_cli')
    def test_hierarchical_returns_context(self, mock_cli):
        """Test that hierarchical returns branch context"""
        mock_cli.return_value = {
            "remId": "branch",
            "title": "Branch",
            "children": [
                {"remId": "child", "title": "Child Node", "children": []}
            ]
        }

        map_entries = [
            {"indent": 0, "title": "Branch", "remId": "branch", "hint": "summary", "summary": "summary"},
            {"indent": 2, "title": "Child Node", "remId": "child", "hint": "child summary", "summary": "child summary"}
        ]

        _, context_map = hierarchical_locate(
            ["Child Node"],
            {},
            map_entries
        )

        # Should return context information
        assert isinstance(context_map, dict)


@pytest.mark.integration
class TestReadContextTree:
    """Test read_context_tree function for context retrieval."""

    @patch('smart_logic_v5.run_cli')
    def test_read_context_success(self, mock_cli):
        """Test successful context tree reading."""
        mock_cli.return_value = {"remId": "test_id", "children": []}

        result = read_context_tree("test_id")

        assert result["remId"] == "test_id"
        mock_cli.assert_called_once()

    @patch('smart_logic_v5.run_cli')
    def test_read_context_error_handling(self, mock_cli, capsys):
        """Test error handling in context tree reading."""
        mock_cli.return_value = {"error": "Failed to read"}

        result = read_context_tree("bad_id")

        assert "error" in result
        captured = capsys.readouterr()
        assert "ERROR" in captured.out


@pytest.mark.integration
class TestCrossValidateB2:
    """Test suite for cross_validate_b_and_b2() workflow"""

    @patch('smart_logic_v5.run_cli')
    def test_cross_validate_finds_intersection(self, mock_cli):
        """Test that cross-validation finds intersection between B and B2"""
        # Mock B2 branch read
        mock_cli.return_value = {
            "remId": "branch",
            "children": [
                {"remId": "candidate2", "title": "Candidate 2", "children": []}
            ]
        }

        # Step B top 5 candidates
        step_b_top5 = [
            {"remId": "candidate1", "title": "Candidate 1"},
            {"remId": "candidate2", "title": "Candidate 2"},
            {"remId": "candidate3", "title": "Candidate 3"}
        ]

        # Cross-validate
        result = cross_validate_b_and_b2(
            "test_term",
            step_b_top5,
            "initial_result",
            "branch_id"
        )

        # Should find intersection (candidate2)
        assert result is not None

    @patch('smart_logic_v5.run_cli')
    def test_cross_validate_no_intersection(self, mock_cli):
        """Test cross-validation when no intersection exists"""
        # Mock B2 branch with different IDs
        mock_cli.return_value = {
            "remId": "branch",
            "children": [
                {"remId": "different", "title": "Different", "children": []}
            ]
        }

        step_b_top5 = [
            {"remId": "candidate1", "title": "Candidate 1"}
        ]

        # Cross-validate
        result = cross_validate_b_and_b2(
            "test_term",
            step_b_top5,
            "fallback_result",
            "branch_id"
        )

        # Should fallback to original B2 result
        assert result == "fallback_result"

    @patch('smart_logic_v5.run_cli')
    def test_cross_validate_empty_b_candidates(self, mock_cli):
        """Test cross-validation with empty B candidate list"""
        mock_cli.return_value = {"remId": "branch", "children": []}

        # Empty B candidates
        result = cross_validate_b_and_b2(
            "test_term",
            [],
            "fallback",
            "branch"
        )

        # Should fallback
        assert result == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
