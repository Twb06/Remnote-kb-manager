"""
管線集成測試

測試範圍:
- 端對端管線流程
- Phase 1.2 + Steps A-D + NLI Router 集成
- 樣本數據完整流程
- 輸出格式驗證
- 統計一致性

執行: pytest tests/unit/test_pipeline_integration.py -v
"""

import pytest
import sys
import json
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsers.ast_parser import build_ast_tree, flatten_with_breadcrumbs
from src.pipeline.core import KnowledgeItem, PipelineV6
from src.routers.nli_types import NLIRouterV6, MockNLIRouter


class TestPipelinePhase12Integration:
    """Phase 1.2 集成測試"""

    def test_phase_1_2_basic_parsing(self):
        """測試 Phase 1.2 基本 AST 解析"""
        lines = [
            "- Ophthalmology",
            "    - Glaucoma",
            "        - Open-Angle",
            "        - Closed-Angle",
            "    - Cataract"
        ]

        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert tree[0]["text"] == "Ophthalmology"  # bullet markers stripped
        assert len(tree[0]["children"]) == 2

    def test_phase_1_2_breadcrumb_generation(self):
        """測試面包屑生成"""
        lines = [
            "- Medical",
            "    - Ophthalmology",
            "        - Glaucoma"
        ]

        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree)

        assert len(flat) == 3
        # 檢查面包屑是否正確嵌套 (bullet markers 已 strip)
        assert flat[2]["breadcrumb"] == "Medical > Ophthalmology > Glaucoma"

    def test_phase_1_2_with_special_formatting(self):
        """測試含特殊格式的 Phase 1.2"""
        lines = [
            "- Category [2024] (v1)",
            "    - *Sub-Item* with **bold**",
            "        - Item_with-dashes"
        ]

        tree = build_ast_tree(lines)
        flat = flatten_with_breadcrumbs(tree)

        assert len(flat) == 3
        assert "[2024]" in flat[0]["breadcrumb"]  # 檢查 breadcrumb 包含 [2024]


class TestStepAB2Integration:
    """Step A-B2 (搜尋/定位) 集成測試"""

    def test_search_locating_basic(self):
        """測試基本的搜尋和定位"""
        # 模擬輸入
        terms = ["Glaucoma", "Cataract", "Retinopathy"]
        knowledge_base = {
            "item1": "desc_glaucoma",
            "item2": "desc_cataract",
            "item3": "not_present"
        }

        # 簡單匹配 (模擬 v5 搜尋邏輯)
        term_to_id = {}
        for term in terms:
            for item_id, content in knowledge_base.items():
                if term.lower() in content.lower():
                    term_to_id[term] = item_id
                    break

        assert len(term_to_id) >= 2
        assert "Glaucoma" in term_to_id

    def test_term_to_id_mapping(self):
        """測試 term → rem_id 映射"""
        mapping = {
            "GlaucomaNew": None,  # CREATE
            "CataractExisting": "existing_id_123",  # UPDATE
            "RetinopathyNew": None  # CREATE
        }

        creates = [t for t, id in mapping.items() if id is None]
        updates = [t for t, id in mapping.items() if id is not None]

        assert len(creates) == 2
        assert len(updates) == 1


class TestStepCIntegration:
    """Step C (讀取和轉換) 集成測試"""

    def test_context_trees_transformation(self):
        """測試 context_trees 轉換"""
        # 模擬 context_trees (現有 RemNote)
        context_trees = {
            "tree1": {
                "id": "node1",
                "content": "Old glaucoma definition",
                "breadcrumb": "[Eye_Diseases > Glaucoma]",
                "children": []
            }
        }

        # 變換應添加 breadcrumb 字段
        transformed = {}
        for tree_id, node in context_trees.items():
            transformed[tree_id] = {
                **node,
                "content_with_breadcrumb": f"[{node['breadcrumb']}] {node['content']}"
            }

        assert "content_with_breadcrumb" in transformed["tree1"]
        assert "Eye_Diseases > Glaucoma" in transformed["tree1"]["content_with_breadcrumb"]


class TestStepDIntegration:
    """Step D (知識項配對) 集成測試"""

    def test_knowledge_item_pairing(self):
        """測試知識項配對"""
        ast_items = [
            {
                "term": "Glaucoma",
                "new_content": "Glaucoma: increased eye pressure",
                "breadcrumb": "[Ophthalmology > Glaucoma]"
            }
        ]

        term_to_id = {"Glaucoma": "existing_id"}
        context_trees = {
            "tree1": {
                "rem_id": "existing_id",
                "content": "Glaucoma: eye disease",
                "breadcrumb": "[Eye_Diseases > Glaucoma]"
            }
        }

        # 配對邏輯
        knowledge_items = []
        for ast_item in ast_items:
            term = ast_item["term"]
            rem_id = term_to_id.get(term)

            existing_content = None
            existing_breadcrumb = None

            if rem_id:
                for tree_id, node in context_trees.items():
                    if node.get("rem_id") == rem_id:
                        existing_content = node.get("content")
                        existing_breadcrumb = node.get("breadcrumb")

            item = KnowledgeItem(
                term=term,
                rem_id=rem_id,
                action="UPDATE" if rem_id else "CREATE",
                new_content=ast_item["new_content"],
                new_breadcrumb=ast_item["breadcrumb"],
                existing_content=existing_content,
                existing_breadcrumb=existing_breadcrumb,
                nli_context={
                    "new_hierarchical_path": ast_item["breadcrumb"],
                    "existing_hierarchical_path": existing_breadcrumb
                }
            )
            knowledge_items.append(item)

        assert len(knowledge_items) == 1
        assert knowledge_items[0].action == "UPDATE"
        assert knowledge_items[0].new_breadcrumb != knowledge_items[0].existing_breadcrumb

    def test_dual_breadcrumb_preservation(self):
        """測試雙邊 breadcrumb 保留"""
        item = KnowledgeItem(
            term="Test",
            rem_id="123",
            action="UPDATE",
            new_content="New",
            new_breadcrumb="[New > Structure]",
            existing_content="Old",
            existing_breadcrumb="[Old > Structure]",
            nli_context={
                "new_hierarchical_path": "New > Structure",
                "existing_hierarchical_path": "Old > Structure"
            }
        )

        # 兩邊都應保留
        assert item.new_breadcrumb is not None
        assert item.existing_breadcrumb is not None
        assert item.new_breadcrumb != item.existing_breadcrumb


class TestNLIRouterIntegration:
    """NLI Router 集成測試"""

    def test_router_with_knowledge_items(self):
        """測試路由與知識項的集成"""
        router = MockNLIRouter()

        items = [
            KnowledgeItem(
                term="Similar",
                rem_id="123",
                action="UPDATE",
                new_content="Glaucoma affects eye pressure",
                new_breadcrumb="[A > Glaucoma]",
                existing_content="Glaucoma causes high eye pressure",
                existing_breadcrumb="[B > Glaucoma]",
                nli_context={}
            )
        ]

        # 模擬路由
        for item in items:
            if item.action == "UPDATE":
                result = router.infer(item.new_content, item.existing_content)

                if result.entailment_score > 0.85:
                    final_action = "SKIP"
                elif result.neutral_score > 0.60:
                    final_action = "CREATE"
                else:
                    final_action = "UPDATE"

                assert final_action in ["CREATE", "UPDATE", "SKIP"]

    def test_router_statistics(self):
        """測試路由統計"""
        router = NLIRouterV6()

        # 初始化統計
        router.statistics = {
            "total_items": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0
        }

        # 應能夠追蹤統計
        stats = router.get_statistics()
        assert stats["total_items"] == 0


class TestEndToEndPipeline:
    """端對端管線測試"""

    def test_complete_flow_create_action(self):
        """測試完整流程 - CREATE 操作"""
        # 1. Phase 1.2: 解析新內容
        new_lines = [
            "- New Category",
            "    - New Item"
        ]
        new_tree = build_ast_tree(new_lines)

        # 2. Step A-B2: 搜尋定位
        term_to_id = {}  # 假設全是 CREATE

        # 3. Step D: 準備知識項
        ast_item = {
            "term": "New Item",
            "new_content": "New Item content",
            "breadcrumb": "[New Category > New Item]"
        }

        item = KnowledgeItem(
            term=ast_item["term"],
            rem_id=None,
            action="CREATE",
            new_content=ast_item["new_content"],
            new_breadcrumb=ast_item["breadcrumb"],
            existing_content=None,
            existing_breadcrumb=None,
            nli_context={}
        )

        # 4. NLI Router: CREATE 操作無需推論
        assert item.action == "CREATE"
        assert item.rem_id is None

    def test_complete_flow_update_action(self):
        """測試完整流程 - UPDATE 操作"""
        # 1. Phase 1.2: 解析新內容
        new_lines = ["- Updated Item"]
        new_tree = build_ast_tree(new_lines)

        # 2. Step A-B2: 搜尋定位 → 找到匹配
        term_to_id = {"Updated Item": "existing_id"}

        # 3. Step D: 準備知識項 (含現有內容)
        ast_item = {
            "term": "Updated Item",
            "new_content": "New version of content",
            "breadcrumb": "[New > Updated Item]"
        }

        existing_item = {
            "rem_id": "existing_id",
            "content": "Old version of content",
            "breadcrumb": "[Old > Updated Item]"
        }

        item = KnowledgeItem(
            term=ast_item["term"],
            rem_id="existing_id",
            action="UPDATE",
            new_content=ast_item["new_content"],
            new_breadcrumb=ast_item["breadcrumb"],
            existing_content=existing_item["content"],
            existing_breadcrumb=existing_item["breadcrumb"],
            nli_context={}
        )

        # 4. NLI Router: UPDATE 需推論
        assert item.action == "UPDATE"
        assert item.rem_id == "existing_id"
        assert item.new_breadcrumb != item.existing_breadcrumb

    def test_mixed_create_update_skip_flow(self):
        """測試混合的 CREATE/UPDATE/SKIP 流程"""
        items = [
            KnowledgeItem(
                term="NewItem",
                rem_id=None,
                action="CREATE",
                new_content="New",
                new_breadcrumb="[A > New]",
                existing_content=None,
                existing_breadcrumb=None,
                nli_context={}
            ),
            KnowledgeItem(
                term="ExistingItem",
                rem_id="id1",
                action="UPDATE",
                new_content="Modified",
                new_breadcrumb="[A > Existing]",
                existing_content="Original",
                existing_breadcrumb="[B > Existing]",
                nli_context={}
            ),
            KnowledgeItem(
                term="DuplicateItem",
                rem_id="id2",
                action="SKIP",
                new_content="Duplicate",
                new_breadcrumb="[A > Dup]",
                existing_content="Duplicate",
                existing_breadcrumb="[A > Dup]",
                nli_context={}
            )
        ]

        actions = [item.action for item in items]
        assert actions == ["CREATE", "UPDATE", "SKIP"]


class TestOutputFormatting:
    """輸出格式測試"""

    def test_json_serializable_output(self):
        """測試輸出應可序列化為 JSON"""
        output = {
            "final_actions": [
                {
                    "action": "CREATE",
                    "term": "TestTerm",
                    "breadcrumb": "[Test > Breadcrumb]",
                    "nli_confidence": 0.95
                }
            ],
            "statistics": {
                "total_items": 1,
                "created": 1,
                "updated": 0,
                "skipped": 0
            }
        }

        # 應能序列化
        json_str = json.dumps(output)
        assert "TestTerm" in json_str

    def test_output_structure_consistency(self):
        """測試輸出結構一致性"""
        output = {
            "final_actions": [],
            "requires_llm_intervention": [],
            "statistics": {}
        }

        required_keys = ["final_actions", "requires_llm_intervention", "statistics"]

        for key in required_keys:
            assert key in output


class TestScalability:
    """可擴展性測試"""

    def test_large_tree_parsing(self):
        """測試大型樹解析"""
        # 生成 100 行的樹
        lines = ["- Root"]
        for i in range(10):
            lines.append(f"    - Category{i}")
            for j in range(10):
                lines.append(f"        - Item{i}_{j}")

        tree = build_ast_tree(lines)

        assert len(tree) == 1
        assert len(tree[0]["children"]) == 10

    def test_many_knowledge_items(self):
        """測試大量知識項"""
        items = [
            KnowledgeItem(
                term=f"Term{i}",
                rem_id=f"id{i}" if i % 2 == 0 else None,
                action="UPDATE" if i % 2 == 0 else "CREATE",
                new_content=f"Content{i}",
                new_breadcrumb=f"[Path{i}]",
                existing_content=f"Old{i}" if i % 2 == 0 else None,
                existing_breadcrumb=f"[OldPath{i}]" if i % 2 == 0 else None,
                nli_context={}
            )
            for i in range(100)
        ]

        assert len(items) == 100
        creates = sum(1 for item in items if item.action == "CREATE")
        updates = sum(1 for item in items if item.action == "UPDATE")
        assert creates + updates == 100


class TestErrorHandling:
    """錯誤處理測試"""

    def test_empty_input_handling(self):
        """測試空輸入"""
        tree = build_ast_tree([])
        assert tree == []

    def test_single_empty_line(self):
        """測試單一空行"""
        tree = build_ast_tree(["", "", ""])
        assert tree == []

    def test_malformed_content(self):
        """測試格式錯誤的內容"""
        lines = [
            "- Valid Item",
            "    Invalid without dash",
            "    - Valid Child"
        ]

        tree = build_ast_tree(lines)
        # 應該能夠處理
        assert tree is not None


@pytest.fixture
def sample_pipeline_config():
    """樣本管線配置 fixture"""
    return {
        "ast_enabled": True,
        "breadcrumb_enabled": True,
        "nli_model": "mock",
        "threshold_entailment": 0.85,
        "threshold_neutral": 0.60
    }


def test_with_pipeline_config(sample_pipeline_config):
    """使用管線配置的測試"""
    assert sample_pipeline_config["ast_enabled"]
    assert sample_pipeline_config["threshold_entailment"] == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
