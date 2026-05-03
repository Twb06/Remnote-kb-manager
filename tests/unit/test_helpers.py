"""
單元測試：Step D/E 輔助函式

測試 map_destinations, get_node_by_id, extract_knowledge_lines, compare_knowledge 等函式
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from smart_logic_v5 import (
        map_destinations,
        get_node_by_id,
        extract_knowledge_lines,
        compare_knowledge
    )
    SMART_LOGIC_AVAILABLE = True
except ImportError:
    SMART_LOGIC_AVAILABLE = False


@pytest.mark.skipif(not SMART_LOGIC_AVAILABLE, reason="smart_logic_v5 not available")
@pytest.mark.unit
class TestMapDestinations:
    """測試 map_destinations 函式（目標映射邏輯）"""

    def test_found_terms_get_update_action(self):
        """測試已找到的術語獲得 UPDATE 動作"""
        terms = ["GCA", "CRAO"]
        term_to_id = {"GCA": "gca123", "CRAO": "crao456"}
        context_trees = {}

        result = map_destinations(terms, term_to_id, context_trees)

        assert result["GCA"]["action"] == "UPDATE"
        assert result["GCA"]["remId"] == "gca123"
        assert result["CRAO"]["action"] == "UPDATE"
        assert result["CRAO"]["remId"] == "crao456"

    def test_missing_terms_get_create_action(self):
        """測試未找到的術語獲得 CREATE 動作"""
        terms = ["GCA", "New Term"]
        term_to_id = {"GCA": "gca123"}
        context_trees = {}

        result = map_destinations(terms, term_to_id, context_trees)

        assert result["New Term"]["action"] == "CREATE"
        assert result["New Term"]["remId"] is None

    def test_infers_parent_from_topic(self):
        """測試從主題推斷父節點"""
        terms = ["Vision Loss", "GCA"]
        term_to_id = {"Vision Loss": "vl123"}
        context_trees = {}

        result = map_destinations(terms, term_to_id, context_trees, topic="Vision Loss")

        # GCA should be created under Vision Loss (topic)
        assert result["GCA"]["action"] == "CREATE"
        assert result["GCA"]["parentRemId"] == "vl123"

    def test_infers_parent_from_sibling(self):
        """測試從兄弟節點推斷父節點"""
        terms = ["GCA", "CRAO", "New Term"]
        term_to_id = {"GCA": "gca123", "CRAO": "crao456"}

        # Mock context tree with parent information
        context_trees = {
            "vl123": {
                "remId": "vl123",
                "title": "Vision Loss",
                "children": [
                    {"remId": "gca123", "title": "GCA", "parentRemId": "vl123"},
                    {"remId": "crao456", "title": "CRAO", "parentRemId": "vl123"}
                ]
            }
        }

        result = map_destinations(terms, term_to_id, context_trees)

        # New Term should use sibling's parent
        assert result["New Term"]["action"] == "CREATE"
        assert result["New Term"]["parentRemId"] == "vl123"

    def test_handles_empty_inputs(self):
        """測試處理空輸入"""
        result = map_destinations([], {}, {})

        assert result == {}

    def test_extracts_parent_from_context_tree(self):
        """測試從上下文樹提取父節點資訊"""
        terms = ["GCA"]
        term_to_id = {"GCA": "gca123"}
        context_trees = {
            "tree1": {
                "remId": "root",
                "children": [
                    {"remId": "gca123", "title": "G CA", "parentRemId": "parent123"}
                ]
            }
        }

        result = map_destinations(terms, term_to_id, context_trees)

        assert result["GCA"]["parentRemId"] == "parent123"


@pytest.mark.skipif(not SMART_LOGIC_AVAILABLE, reason="smart_logic_v5 not available")
@pytest.mark.unit
class TestGetNodeById:
    """測試 get_node_by_id 函式（遞迴節點查找）"""

    def test_finds_node_at_root(self):
        """測試在根節點找到目標"""
        tree = {"remId": "target", "title": "Target Node"}

        result = get_node_by_id(tree, "target")

        assert result is not None
        assert result["remId"] == "target"

    def test_finds_node_in_children(self):
        """測試在子節點中找到目標"""
        tree = {
            "remId": "root",
            "children": [
                {"remId": "child1", "title": "Child 1"},
                {"remId": "target", "title": "Target Node"}
            ]
        }

        result = get_node_by_id(tree, "target")

        assert result is not None
        assert result["remId"] == "target"

    def test_finds_node_nested_deeply(self):
        """測試在深層巢狀中找到目標"""
        tree = {
            "remId": "root",
            "children": [
                {
                    "remId": "level1",
                    "children": [
                        {
                            "remId": "level2",
                            "children": [
                                {"remId": "target", "title": "Deep Target"}
                            ]
                        }
                    ]
                }
            ]
        }

        result = get_node_by_id(tree, "target")

        assert result is not None
        assert result["remId"] == "target"

    def test_returns_none_when_not_found(self):
        """測試未找到時返回 None"""
        tree = {"remId": "root", "children": [{"remId": "child"}]}

        result = get_node_by_id(tree, "nonexistent")

        assert result is None

    def test_handles_non_dict_input(self):
        """測試處理非字典輸入"""
        result = get_node_by_id("not a dict", "target")

        assert result is None

    def test_handles_id_field_variations(self):
        """測試處理 _id 欄位變體"""
        tree = {"_id": "target", "title": "Node with _id"}

        result = get_node_by_id(tree, "target")

        assert result is not None
        assert result["_id"] == "target"

    def test_handles_content_structured_field(self):
        """測試處理 contentStructured 欄位（替代 children）"""
        tree = {
            "remId": "root",
            "contentStructured": [
                {"remId": "target", "title": "Target in contentStructured"}
            ]
        }

        result = get_node_by_id(tree, "target")

        assert result is not None
        assert result["remId"] == "target"


@pytest.mark.skipif(not SMART_LOGIC_AVAILABLE, reason="smart_logic_v5 not available")
@pytest.mark.unit
class TestExtractKnowledgeLines:
    """測試 extract_knowledge_lines 函式（知識行提取）"""

    def test_extracts_title_only(self):
        """測試只提取標題"""
        node = {"title": "Test Title"}

        result = extract_knowledge_lines(node)

        assert len(result) == 1
        assert result[0] == "Test Title"

    def test_extracts_content_only(self):
        """測試只提取內容"""
        node = {"content": "Test content line"}

        result = extract_knowledge_lines(node)

        assert len(result) == 1
        assert result[0] == "Test content line"

    def test_extracts_both_title_and_content(self):
        """測試提取標題和內容"""
        node = {
            "title": "Test Title",
            "content": "Test content"
        }

        result = extract_knowledge_lines(node)

        assert len(result) == 2
        assert result[0] == "Test Title"
        assert result[1] == "Test content"

    def test_splits_multiline_content(self):
        """測試分割多行內容"""
        node = {
            "title": "Title",
            "content": "Line 1\nLine 2\nLine 3"
        }

        result = extract_knowledge_lines(node)

        assert len(result) == 4
        assert result[0] == "Title"
        assert result[1] == "Line 1"
        assert result[2] == "Line 2"
        assert result[3] == "Line 3"

    def test_skips_empty_lines(self):
        """測試跳過空行"""
        node = {
            "content": "Line 1\n\n\nLine 2\n  \nLine 3"
        }

        result = extract_knowledge_lines(node)

        assert len(result) == 3
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_recursively_extracts_from_children(self):
        """測試遞迴從子節點提取"""
        node = {
            "title": "Parent",
            "children": [
                {"title": "Child 1"},
                {"title": "Child 2", "content": "Child 2 content"}
            ]
        }

        result = extract_knowledge_lines(node)

        assert len(result) == 4
        assert "Parent" in result
        assert "Child 1" in result
        assert "Child 2" in result
        assert "Child 2 content" in result

    def test_handles_deeply_nested_structure(self):
        """測試處理深層巢狀結構"""
        node = {
            "title": "Level 0",
            "children": [
                {
                    "title": "Level 1",
                    "contentStructured": [
                        {"title": "Level 2", "content": "Deep content"}
                    ]
                }
            ]
        }

        result = extract_knowledge_lines(node)

        assert len(result) == 4
        assert "Level 0" in result
        assert "Level 1" in result
        assert "Level 2" in result
        assert "Deep content" in result

    def test_handles_empty_node(self):
        """測試處理空節點"""
        node = {}

        result = extract_knowledge_lines(node)

        assert result == []

    def test_handles_non_dict_input(self):
        """測試處理非字典輸入"""
        result = extract_knowledge_lines("not a dict")

        assert result == []

    def test_strips_whitespace(self):
        """測試去除空白字元"""
        node = {
            "title": "  Padded Title  ",
            "content": "  Padded Content  \n  Another Line  "
        }

        result = extract_knowledge_lines(node)

        assert result[0] == "Padded Title"
        assert result[1] == "Padded Content"
        assert result[2] == "Another Line"


@pytest.mark.skipif(not SMART_LOGIC_AVAILABLE, reason="smart_logic_v5 not available")
@pytest.mark.unit
class TestCompareKnowledge:
    """測試 compare_knowledge 函式（嵌入式知識比較）"""

    def test_handles_empty_new_lines(self):
        """測試處理空的新行列表（早期返回分支）"""
        result = compare_knowledge(["existing"], [])

        assert result == {"match": [], "new": [], "ambiguous": []}

    def test_all_new_when_no_existing(self):
        """測試當沒有現有內容時，所有項目標記為 NEW（早期返回分支）"""
        new_lines = ["Line 1", "Line 2", "Line 3"]

        result = compare_knowledge([], new_lines)

        assert len(result["new"]) == 3
        assert len(result["match"]) == 0
        assert len(result["ambiguous"]) == 0
        assert all("line" in item for item in result["new"])
        assert all("best_similarity" in item for item in result["new"])
