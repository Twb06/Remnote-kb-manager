"""
修復後的 Phase 1.2 AST + Breadcrumb 測試套件

根據實際實現修復：
1. detect_indent_level() 保留 "-" 前綴 (lstrip only)
2. build_ast_tree() 的 text 節點已 strip bullet markers (- * +)
3. flatten_with_breadcrumbs() 返回字典列表 (非字符串)

執行: pytest tests/unit/test_phase_1_2_fixed.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsers.ast_parser import (
    detect_indent_level,
    build_ast_tree,
    flatten_with_breadcrumbs,
    transform_tree_with_breadcrumbs,
    BreadcrumbIndex,
    enrich_nli_input_with_breadcrumb
)


class TestDetectIndentLevel:
    """detect_indent_level() 功能测试"""

    def test_no_indent(self):
        """无缩排"""
        depth, content = detect_indent_level("Glaucoma")
        assert depth == 0
        assert content == "Glaucoma"

    def test_four_space_indent(self):
        """4 spaces = 1 level"""
        depth, content = detect_indent_level("    - Glaucoma")
        assert depth == 1
        assert content == "- Glaucoma"  # 保留前綴

    def test_eight_space_indent(self):
        """8 spaces = 2 levels"""
        depth, content = detect_indent_level("        - Open-Angle")
        assert depth == 2
        assert content == "- Open-Angle"

    def test_two_space_pattern(self):
        """2 spaces per level"""
        depth, content = detect_indent_level("  - Child")
        assert depth == 1
        assert content == "- Child"

    def test_tab_indent(self):
        """Tab = 1 level"""
        depth, content = detect_indent_level("\t- Item")
        assert depth == 1
        assert content == "- Item"

    def test_multiple_tabs(self):
        """多个 Tabs"""
        depth, content = detect_indent_level("\t\t- Item")
        assert depth == 2
        assert content == "- Item"

    def test_no_dash_prefix(self):
        """无 dash 前缀"""
        depth, content = detect_indent_level("    Glaucoma")
        assert depth == 1
        assert content == "Glaucoma"

    def test_empty_line(self):
        """空行"""
        depth, content = detect_indent_level("")
        assert depth == 0
        assert content == ""

    def test_only_whitespace(self):
        """仅空格"""
        depth, content = detect_indent_level("    ")
        assert depth == 0
        assert content == ""


class TestBuildAstTree:
    """build_ast_tree() 功能测试"""

    def test_single_item(self):
        """单项"""
        lines = ["- Root"]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert tree[0]["text"] == "Root"
        assert tree[0]["breadcrumb"] == "Root"
        assert tree[0]["depth"] == 0

    def test_two_level_hierarchy(self):
        """两层结构"""
        lines = [
            "- Ophthalmology",
            "    - Glaucoma"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 1
        root = tree[0]
        assert root["text"] == "Ophthalmology"
        assert root["breadcrumb"] == "Ophthalmology"

        assert len(root["children"]) == 1
        child = root["children"][0]
        assert child["text"] == "Glaucoma"
        assert child["breadcrumb"] == "Ophthalmology > Glaucoma"

    def test_three_level_deep_nesting(self):
        """三层深层嵌套"""
        lines = [
            "- Level0",
            "    - Level1",
            "        - Level2"
        ]
        tree = build_ast_tree(lines)

        root = tree[0]
        assert root["depth"] == 0

        level1 = root["children"][0]
        assert level1["depth"] == 1

        level2 = level1["children"][0]
        assert level2["depth"] == 2
        assert level2["breadcrumb"] == "Level0 > Level1 > Level2"

    def test_multiple_siblings(self):
        """多个兄弟节点"""
        lines = [
            "- Parent",
            "    - Child 1",
            "    - Child 2",
            "    - Child 3"
        ]
        tree = build_ast_tree(lines)

        parent = tree[0]
        assert len(parent["children"]) == 3

        for i, child in enumerate(parent["children"], 1):
            assert f"Child {i}" in child["text"]
            assert "Parent" in child["breadcrumb"]

    def test_mixed_siblings_and_children(self):
        """混合兄弟和子节点"""
        lines = [
            "- Parent 1",
            "    - Child 1.1",
            "- Parent 2",
            "    - Child 2.1",
            "        - Grandchild 2.1.1"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 2
        assert "Parent 1" in tree[0]["text"]
        assert "Parent 2" in tree[1]["text"]
        assert len(tree[1]["children"][0]["children"]) == 1

    def test_skip_empty_lines(self):
        """跳过空行"""
        lines = [
            "- Item 1",
            "",
            "- Item 2"
        ]
        tree = build_ast_tree(lines)

        assert len(tree) == 2

    def test_breadcrumb_construction(self):
        """面包屑路径构建"""
        lines = [
            "Ophthalmology",
            "    Glaucoma",
            "        Open-Angle",
            "            NTG"
        ]
        tree = build_ast_tree(lines)

        root = tree[0]
        assert len(root["children"]) > 0

        glaucoma = root["children"][0]
        assert len(glaucoma["children"]) > 0

        open_angle = glaucoma["children"][0]
        assert len(open_angle["children"]) > 0

        ntg = open_angle["children"][0]

        assert ntg["breadcrumb"] == "Ophthalmology > Glaucoma > Open-Angle > NTG"


class TestFlattenWithBreadcrumbs:
    """flatten_with_breadcrumbs() 功能测试"""

    def test_single_item_flat(self):
        """单项展平"""
        lines = ["- Root"]
        tree = build_ast_tree(lines)
        flattened = flatten_with_breadcrumbs(tree)

        assert len(flattened) == 1
        item = flattened[0]
        assert "text" in item
        assert "breadcrumb" in item
        assert item["text"] == "Root"

    def test_hierarchical_flat_plain_format(self):
        """多层展平 - plain 格式"""
        lines = [
            "- Root",
            "    - Child"
        ]
        tree = build_ast_tree(lines)
        flattened = flatten_with_breadcrumbs(tree, prefix_format="plain")

        assert len(flattened) == 2

        # 根项
        assert flattened[0]["breadcrumb"] == "Root"
        assert "[Root]" in flattened[0]["content_with_breadcrumb"]

        # 子項
        assert "Child" in flattened[1]["breadcrumb"]
        assert "[Root > Child]" in flattened[1]["content_with_breadcrumb"]

    def test_markdown_format(self):
        """Markdown 格式"""
        lines = ["- Item"]
        tree = build_ast_tree(lines)
        flattened = flatten_with_breadcrumbs(tree, prefix_format="markdown")

        assert len(flattened) == 1
        assert "**[" in flattened[0]["content_with_breadcrumb"]
        assert "]**" in flattened[0]["content_with_breadcrumb"]

    def test_html_format(self):
        """HTML 格式"""
        lines = ["- Item"]
        tree = build_ast_tree(lines)
        flattened = flatten_with_breadcrumbs(tree, prefix_format="html")

        assert len(flattened) == 1
        content = flattened[0]["content_with_breadcrumb"]
        assert "<breadcrumb>" in content
        assert "<content>" in content
        assert "</breadcrumb>" in content
        assert "</content>" in content

    def test_flattened_structure(self):
        """展平後的字典結構"""
        lines = [
            "- Root",
            "    - Child",
            "        - Grandchild"
        ]
        tree = build_ast_tree(lines)
        flattened = flatten_with_breadcrumbs(tree)

        assert len(flattened) == 3

        for item in flattened:
            assert "text" in item
            assert "breadcrumb" in item
            assert "breadcrumb_parts" in item
            assert "depth" in item
            assert "content_with_breadcrumb" in item
            assert isinstance(item["breadcrumb_parts"], list)


class TestBreadcrumbIndex:
    """BreadcrumbIndex 類測試"""

    def test_add_and_get(self):
        """新增和查詢"""
        idx = BreadcrumbIndex()
        idx.add("NTG", "Glaucoma > Open-Angle > NTG")

        result = idx.get_breadcrumb("NTG")
        assert result == "Glaucoma > Open-Angle > NTG"

    def test_get_nonexistent(self):
        """查詢不存在的項"""
        idx = BreadcrumbIndex()
        result = idx.get_breadcrumb("Nonexistent")
        assert result is None

    def test_multiple_entries(self):
        """多個條目"""
        idx = BreadcrumbIndex()
        idx.add("Item1", "Path > Item1")
        idx.add("Item2", "Path > Item2")
        idx.add("Item3", "Different > Path > Item3")

        assert idx.get_breadcrumb("Item1") == "Path > Item1"
        assert idx.get_breadcrumb("Item2") == "Path > Item2"
        assert idx.get_breadcrumb("Item3") == "Different > Path > Item3"

    def test_get_all_breadcrumbs(self):
        """取得所有面包屑"""
        idx = BreadcrumbIndex()
        idx.add("A", "Path > A")
        idx.add("B", "Path > B")

        all_bc = idx.get_all_breadcrumbs()
        assert len(all_bc) == 2
        assert all_bc["A"] == "Path > A"
        assert all_bc["B"] == "Path > B"

    def test_get_hierarchy_info(self):
        """解析面包屑層級"""
        idx = BreadcrumbIndex()
        info = idx.get_hierarchy_info("[Ophthalmology > Glaucoma > NTG]")

        assert info["depth"] == 3
        assert info["leaf"] == "NTG"
        assert "Ophthalmology" in info["ancestors"]
        assert "Glaucoma" in info["ancestors"]


class TestTransformTreeWithBreadcrumbs:
    """transform_tree_with_breadcrumbs() 功能測試"""

    def test_simple_transform(self):
        """簡單轉換"""
        tree = {
            "id": "root_1",
            "title": "Root",
            "content": "Root content",
            "children": []
        }

        transformed = transform_tree_with_breadcrumbs(tree)

        assert transformed["id"] == "root_1"
        assert transformed["title"] == "Root"
        assert transformed["breadcrumb"] == "Root"
        assert transformed["depth"] == 0

    def test_nested_transform(self):
        """嵌套轉換"""
        tree = {
            "id": "root",
            "title": "Root",
            "content": "Root content",
            "children": [
                {
                    "id": "child",
                    "title": "Child",
                    "content": "Child content",
                    "children": []
                }
            ]
        }

        transformed = transform_tree_with_breadcrumbs(tree)

        assert transformed["breadcrumb"] == "Root"
        assert transformed["children"][0]["breadcrumb"] == "Root > Child"
        assert transformed["children"][0]["depth"] == 1

    def test_deep_nesting_transform(self):
        """深層嵌套轉換"""
        tree = {
            "id": "l0",
            "title": "Level0",
            "content": "",
            "children": [
                {
                    "id": "l1",
                    "title": "Level1",
                    "content": "",
                    "children": [
                        {
                            "id": "l2",
                            "title": "Level2",
                            "content": "",
                            "children": []
                        }
                    ]
                }
            ]
        }

        transformed = transform_tree_with_breadcrumbs(tree)

        assert transformed["breadcrumb"] == "Level0"
        assert transformed["children"][0]["breadcrumb"] == "Level0 > Level1"
        assert transformed["children"][0]["children"][0]["breadcrumb"] == "Level0 > Level1 > Level2"
        assert transformed["children"][0]["children"][0]["depth"] == 2


class TestEnrichNLIInput:
    """enrich_nli_input_with_breadcrumb() 功能測試"""

    def test_with_breadcrumb_enabled(self):
        """啟用面包屑增強"""
        node = {
            "text": "Normal Tension Glaucoma",
            "breadcrumb": "Ophthalmology > Glaucoma > Open-Angle > NTG"
        }

        premise, hypothesis = enrich_nli_input_with_breadcrumb(
            node,
            "IOP < 21 mmHg",
            use_breadcrumb=True
        )

        assert "[Ophthalmology > Glaucoma > Open-Angle > NTG]" in premise
        assert "[Ophthalmology > Glaucoma > Open-Angle > NTG]" in hypothesis

    def test_with_breadcrumb_disabled(self):
        """禁用面包屑增強"""
        node = {
            "text": "NTG",
            "breadcrumb": "Ophthalmology > NTG"
        }

        premise, hypothesis = enrich_nli_input_with_breadcrumb(
            node,
            "IOP < 21",
            use_breadcrumb=False
        )

        assert premise == "NTG"
        assert hypothesis == "IOP < 21"


class TestIntegration:
    """集成測試"""

    def test_full_pipeline_notebooklm_style(self):
        """完整管線 - NotebookLM 風格"""
        extract = """- Medical Knowledge
    - Ophthalmology
        - Glaucoma
            - Open-Angle
                - Normal Tension Glaucoma
                    - IOP: <21 mmHg"""

        lines = extract.strip().split("\n")

        # 步驟 1: 構建 AST
        tree = build_ast_tree(lines)
        assert len(tree) == 1

        # 步驟 2: 展平
        flattened = flatten_with_breadcrumbs(tree)
        assert len(flattened) > 0

        # 驗證最深層項目包含完整路徑
        ntg_items = [item for item in flattened if "Normal Tension Glaucoma" in item["text"]]
        assert len(ntg_items) > 0
        assert "Medical Knowledge" in ntg_items[0]["breadcrumb"]

    def test_full_pipeline_remnote_style(self):
        """完整管線 - RemNote 風格"""
        tree = {
            "id": "med_root",
            "title": "Medicine",
            "content": "Medical notes",
            "children": [
                {
                    "id": "eye_102",
                    "title": "Ophthalmology",
                    "content": "Eye diseases",
                    "children": [
                        {
                            "id": "glau_205",
                            "title": "Glaucoma",
                            "content": "Glaucoma info",
                            "children": []
                        }
                    ]
                }
            ]
        }

        # 轉換
        transformed = transform_tree_with_breadcrumbs(tree)

        # 驗證路徑
        assert transformed["breadcrumb"] == "Medicine"
        assert transformed["children"][0]["breadcrumb"] == "Medicine > Ophthalmology"
        assert transformed["children"][0]["children"][0]["breadcrumb"] == "Medicine > Ophthalmology > Glaucoma"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
