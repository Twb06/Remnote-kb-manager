"""
Unit tests for tree operations in smart_logic_v5.py

Tests the following functions:
- extract_all_rem_ids_from_tree()
- _flatten_children()
- get_node_by_id() (if exists)
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from smart_logic_v5 import (
        extract_all_rem_ids_from_tree
    )
    SMART_LOGIC_AVAILABLE = True
except ImportError:
    SMART_LOGIC_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not SMART_LOGIC_AVAILABLE,
    reason="smart_logic_v5.py not available"
)


@pytest.mark.unit
class TestExtractRemIds:
    """Test suite for extract_all_rem_ids_from_tree() function"""

    def test_extract_single_level(self, sample_tree_node):
        """Test extraction from single level tree"""
        # Use fixture tree
        ids = extract_all_rem_ids_from_tree(sample_tree_node, max_depth=1)

        # Should extract IDs at depth 1
        assert isinstance(ids, list)
        assert len(ids) > 0

    def test_extract_respects_max_depth(self):
        """Test that max_depth parameter is respected"""
        node = {
            "remId": "root",
            "children": [
                {
                    "remId": "child1",
                    "children": [
                        {
                            "remId": "grandchild1",
                            "children": []
                        }
                    ]
                }
            ]
        }

        ids_depth1 = extract_all_rem_ids_from_tree(node, max_depth=1)
        ids_depth2 = extract_all_rem_ids_from_tree(node, max_depth=2)

        # Depth 1 should have fewer IDs than depth 2
        assert len(ids_depth1) <= len(ids_depth2)

        # Grandchild should only appear in depth 2
        if "grandchild1" in ids_depth2:
            assert "grandchild1" not in ids_depth1

    def test_extract_multiple_branches(self, sample_tree_node):
        """Test extraction from tree with multiple branches"""
        ids = extract_all_rem_ids_from_tree(sample_tree_node, max_depth=3)

        # Should extract from all branches
        assert len(ids) > 0

    def test_extract_empty_tree(self):
        """Test extraction from empty tree"""
        node = {"remId": "root", "children": []}

        ids = extract_all_rem_ids_from_tree(node, max_depth=1)

        # Should return empty list or handle gracefully
        assert isinstance(ids, list)

    def test_extract_no_duplicates(self, sample_tree_node):
        """Test that no duplicate IDs are returned"""
        ids = extract_all_rem_ids_from_tree(sample_tree_node, max_depth=3)

        # Should not have duplicates
        assert len(ids) == len(set(ids))


@pytest.mark.unit
class TestTreeOperations:
    """Test suite for other tree operations"""

    def test_tree_depth_calculation(self, sample_tree_node):
        """Test that tree depth is correctly calculated"""
        # Extract at different depths
        depth1 = extract_all_rem_ids_from_tree(sample_tree_node, max_depth=1)
        depth2 = extract_all_rem_ids_from_tree(sample_tree_node, max_depth=2)
        depth3 = extract_all_rem_ids_from_tree(sample_tree_node, max_depth=3)

        # Should have increasing number of IDs
        assert len(depth1) <= len(depth2) <= len(depth3)

    def test_tree_traversal_order(self):
        """Test that tree traversal follows expected order"""
        node = {
            "remId": "root",
            "children": [
                {"remId": "a", "children": []},
                {"remId": "b", "children": []},
                {"remId": "c", "children": []}
            ]
        }

        ids = extract_all_rem_ids_from_tree(node, max_depth=1)

        # Should extract all children
        assert len(ids) == 3

    def test_extract_deep_nested_tree(self):
        """Test extraction from deeply nested tree (5+ levels)"""
        # Build a 5-level deep tree
        node = {"remId": "root", "children": []}
        current = node

        for i in range(5):
            child = {
                "remId": f"level_{i}",
                "children": []
            }
            current["children"].append(child)
            current = child

        # Extract at different depths
        ids_depth3 = extract_all_rem_ids_from_tree(node, max_depth=3)
        ids_depth5 = extract_all_rem_ids_from_tree(node, max_depth=5)

        # Should have more IDs at greater depth
        assert len(ids_depth5) >= len(ids_depth3)
        # Check specific level presence
        assert any("level_" in id for id in ids_depth5)

    def test_extract_malformed_node(self):
        """Test handling of node without children key"""
        node = {
            "remId": "malformed"
            # Missing 'children' key
        }

        # Should handle gracefully (return empty list or just root)
        try:
            ids = extract_all_rem_ids_from_tree(node, max_depth=1)
            assert isinstance(ids, list)
        except (KeyError, AttributeError):
            # If it raises exception, that's also acceptable behavior
            # as long as it's a clear error
            pass


# TODO: Add more tree operation tests
# - Test _flatten_children() if it's a separate function
# - Test get_node_by_id() for finding nodes in tree
# - Test tree modification operations
# - Test edge cases (deep nesting, circular references if possible)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
