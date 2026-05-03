"""
Pytest configuration and shared fixtures for smart_logic_v5 tests.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List, Any


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_kb_map(fixtures_dir: Path) -> Dict[str, Any]:
    """
    Load sample kb_map.json for testing.

    Returns a simplified kb_map structure with:
    - Root node
    - 2 branches with nested children
    """
    kb_map_file = fixtures_dir / "kb_map_sample.json"
    if kb_map_file.exists():
        with open(kb_map_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback: return minimal structure
    return {
        "root": {
            "remId": "root123",
            "title": "Test Root"
        },
        "branches": [
            {
                "remId": "branch1",
                "title": "Test Branch 1",
                "remType": "document",
                "summary": "Test branch for testing purposes",
                "children": [
                    {
                        "remId": "child1",
                        "title": "Test Child 1",
                        "remType": "text",
                        "summary": "Child node under branch 1",
                        "children": []
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_overview_md(fixtures_dir: Path) -> str:
    """
    Load sample overview markdown for testing.

    Returns markdown string with Overview section containing:
    - Main topic (bold)
    - Subtopics (regular list items)
    """
    overview_file = fixtures_dir / "overview_sample.md"
    if overview_file.exists():
        with open(overview_file, "r", encoding="utf-8") as f:
            return f.read()

    # Fallback: return minimal overview
    return """## Overview
- **Test Main Topic**
- Test Subtopic 1
- Test Subtopic 2
"""


@pytest.fixture
def sample_content_md(fixtures_dir: Path) -> str:
    """
    Load sample content markdown for testing.

    Returns markdown with multiple topic sections.
    """
    content_file = fixtures_dir / "content_sample.md"
    if content_file.exists():
        with open(content_file, "r", encoding="utf-8") as f:
            return f.read()

    # Fallback: return minimal content
    return """- **Test Topic A**
  - Content line 1 for topic A
  - Content line 2 for topic A

- **Test Topic B**
  - Content line 1 for topic B
"""


@pytest.fixture
def mock_cli_search_response() -> Dict[str, List[Dict[str, Any]]]:
    """
    Mock CLI search response structure.

    Simulates remnote-cli search output with:
    - remId, title, aliases, tags
    - parentTitle, parentRemId
    """
    return {
        "results": [
            {
                "remId": "test_id_1",
                "title": "Test Node 1",
                "aliases": ["TN1", "TestNode1"],
                "tags": ["tag1", "tag2"],
                "parentTitle": "Parent Node",
                "parentRemId": "parent_id_1"
            },
            {
                "remId": "test_id_2",
                "title": "Test Node 2",
                "aliases": [],
                "tags": ["tag3"],
                "parentTitle": "Parent Node",
                "parentRemId": "parent_id_1"
            }
        ]
    }


@pytest.fixture
def mock_cli_read_response() -> Dict[str, Any]:
    """
    Mock CLI read response structure.

    Simulates remnote-cli read output with tree structure.
    """
    return {
        "remId": "root_id",
        "title": "Root Node",
        "remType": "document",
        "children": [
            {
                "remId": "child_id_1",
                "title": "Child Node 1",
                "remType": "text",
                "children": [
                    {
                        "remId": "grandchild_id_1",
                        "title": "Grandchild Node 1",
                        "remType": "text",
                        "children": []
                    }
                ]
            },
            {
                "remId": "child_id_2",
                "title": "Child Node 2",
                "remType": "text",
                "children": []
            }
        ]
    }


@pytest.fixture
def sample_tree_node() -> Dict[str, Any]:
    """
    Sample tree node structure for tree operation tests.

    3-level tree with multiple branches.
    """
    return {
        "remId": "root",
        "title": "Root",
        "children": [
            {
                "remId": "branch_a",
                "title": "Branch A",
                "children": [
                    {
                        "remId": "leaf_a1",
                        "title": "Leaf A1",
                        "children": []
                    },
                    {
                        "remId": "leaf_a2",
                        "title": "Leaf A2",
                        "children": []
                    }
                ]
            },
            {
                "remId": "branch_b",
                "title": "Branch B",
                "children": [
                    {
                        "remId": "leaf_b1",
                        "title": "Leaf B1",
                        "children": []
                    }
                ]
            }
        ]
    }


@pytest.fixture
def configuration_constants() -> Dict[str, Any]:
    """
    Configuration constants from smart_logic_v5.py for validation tests.

    Returns dict with all configurable constants.
    """
    return {
        # Search & Matching Thresholds
        "SCORE_PERFECT_MATCH": 10.0,
        "SCORE_EXACT_MATCH_BONUS": 10.0,
        "SCORE_TITLE_CASE_BONUS": 5.0,
        "THRESHOLD_MAP_LOOKUP": 0.5,
        "THRESHOLD_SEARCH_ACCEPT": 0.6,
        "THRESHOLD_HIERARCHICAL": 0.5,

        # Scoring Weights
        "WEIGHT_ALIASES_EXIST": 2.0,
        "WEIGHT_TAGS_EXIST": 1.0,
        "WEIGHT_SUBSTRING_OVERLAP": 0.5,
        "PENALTY_GENERIC_TERMS": 0.3,

        # CLI Parameters
        "CLI_SEARCH_LIMIT": 50,
        "CLI_BRANCH_DEPTH": 2,
        "CLI_BRANCH_CHILD_LIMIT": 200,
        "CLI_TREE_DEPTH": 6,
        "CLI_CROSS_VALIDATE_DEPTH": 2,

        # Embedding Thresholds
        "EMBED_MATCH_THRESHOLD": 0.80,
        "EMBED_NEW_THRESHOLD": 0.30,

        # Timeouts
        "DEFAULT_TIMEOUT_SECONDS": 60
    }


# Mark configuration for all tests
def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "unit: Mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: Mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: Mark test as slow running (>1s)"
    )
    config.addinivalue_line(
        "markers", "pipeline: Mark test as full pipeline test"
    )
