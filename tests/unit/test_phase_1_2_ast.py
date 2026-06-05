"""
Phase 1.2 AST + Breadcrumb 邊界測試套件

測試範圍:
- detect_indent_level() - 縮排檢測及內容解析
- build_ast_tree() - 樹狀結構建構及面包屑生成
- flatten_with_breadcrumbs() - 扁平化及格式化輸出
- transform_tree_with_breadcrumbs() - RemNote 結構轉換
- BreadcrumbIndex - 內存索引追蹤

執行: pytest tests/unit/test_phase_1_2_ast.py -v
"""

import pytest
import sys
from pathlib import Path

# 新增項目路徑以導入模塊
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsers.ast_parser import (
    detect_indent_level,
    build_ast_tree,
    flatten_with_breadcrumbs,
    transform_tree_with_breadcrumbs,
    BreadcrumbIndex
)


class TestDetectIndentLevel:
    """縮排深度檢測測試"""

    def test_no_indent(self):
        """測試無縮排的行"""
        depth, content = detect_indent_level("Glaucoma Types")
        assert depth == 0
        assert content == "Glaucoma Types"

    def test_single_dash_no_indent(self):
        """測試帶 dash 但無縮排"""
        depth, content = detect_indent_level("- Glaucoma Types")
        assert depth == 0
        assert content == "- Glaucoma Types"  # detect_indent_level 不移除 dash

    def test_four_space_indent(self):
        """測試 4 空格縮排"""
        depth, content = detect_indent_level("    - Open-Angle")
        assert depth == 1
        assert content == "- Open-Angle"

    def test_eight_space_indent(self):
        """測試 8 空格縮排 (2 層深度)"""
        depth, content = detect_indent_level("        - Normal Tension Glaucoma")
        assert depth == 2
        assert content == "- Normal Tension Glaucoma"

    def test_two_space_indent(self):
        """測試 2 空格縮排"""
        depth, content = detect_indent_level("  - Item")
        assert depth == 1
        assert content == "- Item"  # detect_indent_level 不移除 dash，同 test_single_dash_no_indent

    def test_tab_indent(self):
        """測試 tab 縮排"""
        depth, content = detect_indent_level("\t- Item")
        assert depth >= 1  # Tab 作為至少 1 層
        assert content == "- Item"  # detect_indent_level 不移除 dash

    def test_asterisk_prefix(self):
        """測試 asterisk 前綴"""
        depth, content = detect_indent_level("* Item")
        assert depth == 0
        assert content == "* Item"

    def test_multiple_spaces_and_dash(self):
        """測試多個空格及 dash"""
        depth, content = detect_indent_level("        * Deep Item")
        assert depth == 2
        assert content == "* Deep Item"

    def test_content_with_special_chars(self):
        """測試含特殊字符的內容"""
        depth, content = detect_indent_level("    - Test [Content] with (special) chars")
        assert depth == 1
        assert content == "- Test [Content] with (special) chars"

    def test_content_with_brackets(self):
        """測試帶括號的內容"""
        depth, content = detect_indent_level("    - [Ophthalmology] Deep Learning")
        assert depth == 1
        assert content == "- [Ophthalmology] Deep Learning"  # dash 保留，由 build_ast_tree 負責 strip

    def test_empty_after_indent(self):
        """測試縮排後空行"""
        depth, content = detect_indent_level("    ")
        # 應該返回某些合理值
        assert isinstance(depth, int)
        assert isinstance(content, str)

    def test_mixed_leading_spaces_and_dashes(self):
        """測試混合的前導字符"""
        depth, content = detect_indent_level("        - - Nested Dashes")
        assert depth == 2
        assert "- Nested Dashes" in content


class TestBuildASTTree:
    """AST 樹狀結構建構測試"""

    def test_single_root_item(self):
        """測試單一根節點"""
        lines = ["- Glaucoma Types"]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert tree[0]["text"] == "Glaucoma Types"
        assert tree[0]["level"] == 0
        assert tree[0]["breadcrumb"] == "Glaucoma Types"
        assert tree[0]["children"] == []

    def test_two_level_hierarchy(self):
        """測試二級層級"""
        lines = [
            "- Glaucoma Types",
            "    - Open-Angle"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert tree[0]["text"] == "Glaucoma Types"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["text"] == "Open-Angle"
        assert tree[0]["children"][0]["breadcrumb"] == "Glaucoma Types > Open-Angle"

    def test_three_level_hierarchy(self):
        """測試三級層級"""
        lines = [
            "- Glaucoma Types",
            "    - Open-Angle",
            "        - Normal Tension Glaucoma"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 1
        assert len(tree[0]["children"][0]["children"]) == 1

        leaf = tree[0]["children"][0]["children"][0]
        assert leaf["text"] == "Normal Tension Glaucoma"
        assert leaf["breadcrumb"] == "Glaucoma Types > Open-Angle > Normal Tension Glaucoma"

    def test_sibling_nodes(self):
        """測試兄弟節點"""
        lines = [
            "- Glaucoma Types",
            "    - Open-Angle",
            "    - Closed-Angle"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 2
        assert tree[0]["children"][0]["text"] == "Open-Angle"
        assert tree[0]["children"][1]["text"] == "Closed-Angle"
        assert tree[0]["children"][1]["breadcrumb"] == "Glaucoma Types > Closed-Angle"

    def test_multiple_roots(self):
        """測試多個根節點"""
        lines = [
            "- Category A",
            "    - Item A1",
            "- Category B",
            "    - Item B1"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 2
        assert tree[0]["text"] == "Category A"
        assert tree[1]["text"] == "Category B"
        assert len(tree[0]["children"]) == 1
        assert len(tree[1]["children"]) == 1

    def test_empty_lines_ignored(self):
        """測試空行應被忽略"""
        lines = [
            "- Glaucoma Types",
            "",
            "    - Open-Angle",
            "",
            "        - Normal Tension Glaucoma"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 1
        assert len(tree[0]["children"][0]["children"]) == 1

    def test_path_calculation(self):
        """測試路徑計算的正確性"""
        lines = [
            "- Root",
            "    - Child1",
            "    - Child2",
            "        - GrandChild"
        ]
        tree = build_ast_tree(lines)

        root = tree[0]
        assert root["path"] == [0]
        assert root["children"][0]["path"] == [0, 0]  # Root 的第 0 個子節點
        assert root["children"][1]["path"] == [0, 1]  # Root 的第 1 個子節點
        assert root["children"][1]["children"][0]["path"] == [0, 1, 0]  # Child2 的第 0 個子節點

    def test_deep_nesting(self):
        """測試深層嵌套"""
        lines = [
            "- L0",
            "    - L1",
            "        - L2",
            "            - L3",
            "                - L4"
        ]
        tree = build_ast_tree(lines)

        node = tree[0]
        for i in range(4):
            assert len(node["children"]) == 1
            node = node["children"][0]
            assert node["level"] == i + 1

    def test_reindent_at_different_levels(self):
        """測試在不同級別重新縮排"""
        lines = [
            "- Root",
            "    - Level1A",
            "        - Level2A",
            "    - Level1B",
            "        - Level2B"
        ]
        tree = build_ast_tree(lines)

        root = tree[0]
        assert len(root["children"]) == 2
        assert root["children"][0]["text"] == "Level1A"
        assert root["children"][1]["text"] == "Level1B"
        assert len(root["children"][0]["children"]) == 1
        assert len(root["children"][1]["children"]) == 1


class TestFlattenWithBreadcrumbs:
    """扁平化與面包屑文本生成測試"""

    def test_single_item_plain_format(self):
        """測試單一項目的 plain 格式"""
        lines = ["- Glaucoma Types"]
        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree, prefix_format="plain")

        assert len(flat) == 1
        assert flat[0]["content_with_breadcrumb"] == "[Glaucoma Types] Glaucoma Types"

    def test_multiple_levels_plain_format(self):
        """測試多級層級的 plain 格式"""
        lines = [
            "- Glaucoma",
            "    - Open-Angle",
            "        - NTG"
        ]
        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree, prefix_format="plain")

        assert len(flat) == 3
        assert flat[0]["content_with_breadcrumb"] == "[Glaucoma] Glaucoma"
        assert flat[1]["content_with_breadcrumb"] == "[Glaucoma > Open-Angle] Open-Angle"
        assert flat[2]["content_with_breadcrumb"] == "[Glaucoma > Open-Angle > NTG] NTG"

    def test_markdown_format(self):
        """測試 markdown 格式"""
        lines = ["- Item"]
        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree, prefix_format="markdown")

        assert len(flat) == 1
        assert "**[" in flat[0]["content_with_breadcrumb"]
        assert "]**" in flat[0]["content_with_breadcrumb"]

    def test_html_format(self):
        """測試 HTML 格式"""
        lines = ["- Item"]
        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree, prefix_format="html")

        assert len(flat) == 1
        assert "<breadcrumb>" in flat[0]["content_with_breadcrumb"]
        assert "</breadcrumb>" in flat[0]["content_with_breadcrumb"]
        assert "<content>" in flat[0]["content_with_breadcrumb"]
        assert "</content>" in flat[0]["content_with_breadcrumb"]

    def test_sibling_breadcrumbs(self):
        """測試兄弟節點的面包屑"""
        lines = [
            "- Parent",
            "    - Child1",
            "    - Child2"
        ]
        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree, prefix_format="plain")

        assert len(flat) == 3
        # 兄弟節點應有不同的面包屑
        assert "Child1" in flat[1]["content_with_breadcrumb"]
        assert "Child2" in flat[2]["content_with_breadcrumb"]
        assert flat[1]["content_with_breadcrumb"] != flat[2]["content_with_breadcrumb"]


class TestTransformTreeWithBreadcrumbs:
    """RemNote 結構轉換測試"""

    def test_simple_transform(self):
        """測試簡單的轉換"""
        tree = {
            "id": "item1",
            "content": "Test Content",
            "children": []
        }

        result = transform_tree_with_breadcrumbs(tree)

        assert "breadcrumb" in result
        assert result["content_with_breadcrumb"] is not None

    def test_nested_transform(self):
        """測試嵌套轉換"""
        tree = {
            "id": "root",
            "content": "Root",
            "children": [
                {
                    "id": "child",
                    "content": "Child",
                    "children": []
                }
            ]
        }

        result = transform_tree_with_breadcrumbs(tree)

        assert result["children"] is not None
        if len(result["children"]) > 0:
            assert "breadcrumb" in result["children"][0]


class TestBreadcrumbIndex:
    """Breadcrumb 索引追蹤測試"""

    def test_add_and_retrieve(self):
        """測試新增和檢索"""
        index = BreadcrumbIndex()
        index.add("Test Content", "[Category > SubCategory]")

        bc = index.get_breadcrumb("Test Content")
        assert bc == "[Category > SubCategory]"

    def test_retrieve_nonexistent(self):
        """測試檢索不存在的項"""
        index = BreadcrumbIndex()
        result = index.get_breadcrumb("Nonexistent")

        assert result is None

    def test_multiple_entries(self):
        """測試多個項"""
        index = BreadcrumbIndex()
        index.add("Item1", "[Path1]")
        index.add("Item2", "[Path2]")

        entries = index.get_all_breadcrumbs()
        assert len(entries) == 2
        assert entries["Item1"] == "[Path1]"
        assert entries["Item2"] == "[Path2]"

    def test_overwrite_entry(self):
        """測試覆蓋項"""
        index = BreadcrumbIndex()
        index.add("Item", "[Old Path]")
        index.add("Item", "[New Path]")

        bc = index.get_breadcrumb("Item")
        assert bc == "[New Path]"


class TestEdgeCases:
    """邊界情況測試"""

    def test_very_deep_nesting(self):
        """測試非常深的嵌套 (10 層)"""
        lines = ["- L" + str(i) for i in range(10)]
        for i in range(1, 10):
            lines.append("    " * i + "- L" + str(i))

        tree = build_ast_tree(lines)
        # 應該不崩潰
        assert tree is not None

    def test_unicode_content(self):
        """測試包含 unicode 的內容"""
        lines = [
            "- 青光眼",
            "    - 開角型",
            "        - 正常眼壓型青光眼"
        ]
        tree = build_ast_tree(lines)

        assert tree[0]["text"] == "青光眼"
        assert tree[0]["breadcrumb"] == "青光眼"

    def test_special_characters(self):
        """測試含特殊字符的內容"""
        lines = [
            "- Test [2024] (Final) {Advanced}",
            "    - Sub-item: Value = 42.5"
        ]
        tree = build_ast_tree(lines)

        assert "[2024]" in tree[0]["text"]
        assert "=" in tree[0]["children"][0]["text"]

    def test_inconsistent_indentation(self):
        """測試不一致的縮排"""
        lines = [
            "- Item1",
            "  - Item2",      # 2 空格
            "    - Item3",    # 4 空格
            "      - Item4"   # 6 空格
        ]
        tree = build_ast_tree(lines)

        # 應該能夠處理並建構某種結構
        assert tree is not None


@pytest.fixture
def sample_tree():
    """樣本樹 fixture"""
    lines = [
        "- Ophthalmology",
        "    - Glaucoma",
        "        - Open-Angle",
        "        - Closed-Angle",
        "    - Cataract"
    ]
    return build_ast_tree(lines)


def test_with_fixture(sample_tree):
    """使用 fixture 的測試"""
    assert len(sample_tree) == 1
    assert len(sample_tree[0]["children"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
