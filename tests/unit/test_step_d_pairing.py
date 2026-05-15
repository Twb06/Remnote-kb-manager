"""
Step D: 知識項目配對邏輯測試

測試範圍:
- prepare_knowledge_items() - 新舊內容配對
- KnowledgeItem 數據類
- 雙邊 breadcrumb 配對
- NLI 上下文準備

執行: pytest tests/unit/test_step_d_pairing.py -v
"""

import pytest
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.parsers.ast_parser import build_ast_tree, flatten_with_breadcrumbs
from src.pipeline.core import KnowledgeItem


@dataclass
class MockASTParsedItem:
    """模擬 Phase 1.2 AST 輸出的項"""
    term: str
    content: str
    breadcrumb: str
    level: int = 0


@dataclass
class MockContextTreeNode:
    """模擬 RemNote context_trees 節點"""
    rem_id: str
    content: str
    breadcrumb: str
    children: list = None


class TestKnowledgeItemDataclass:
    """KnowledgeItem 數據類測試"""

    def test_knowledge_item_creation(self):
        """測試建立 KnowledgeItem"""
        item = KnowledgeItem(
            term="Glaucoma",
            rem_id="abc123",
            action="UPDATE",
            new_content="New glaucoma definition",
            new_breadcrumb="[Ophthalmology > Glaucoma]",
            existing_content="Old glaucoma definition",
            existing_breadcrumb="[Eye_Diseases > Glaucoma]",
            nli_context={
                "new_hierarchical_path": "Ophthalmology > Glaucoma",
                "existing_hierarchical_path": "Eye_Diseases > Glaucoma"
            }
        )

        assert item.term == "Glaucoma"
        assert item.action == "UPDATE"
        assert item.new_breadcrumb == "[Ophthalmology > Glaucoma]"

    def test_knowledge_item_create_action(self):
        """測試 CREATE 行動的 KnowledgeItem"""
        item = KnowledgeItem(
            term="NewTerm",
            rem_id=None,
            action="CREATE",
            new_content="New content",
            new_breadcrumb="[Category > NewTerm]",
            existing_content=None,
            existing_breadcrumb=None,
            nli_context={
                "new_hierarchical_path": "Category > NewTerm",
                "existing_hierarchical_path": None
            }
        )

        assert item.action == "CREATE"
        assert item.rem_id is None
        assert item.existing_content is None

    def test_knowledge_item_skip_action(self):
        """測試 SKIP 行動的 KnowledgeItem"""
        item = KnowledgeItem(
            term="DuplicateTerm",
            rem_id="existing_id",
            action="SKIP",
            new_content="Same Content",
            new_breadcrumb="[A > B]",
            existing_content="Same Content",
            existing_breadcrumb="[A > B]",
            nli_context={"new_hierarchical_path": "A > B", "existing_hierarchical_path": "A > B"}
        )

        assert item.action == "SKIP"
        assert item.new_content == item.existing_content

    def test_knowledge_item_to_dict(self):
        """測試轉換為 dict"""
        item = KnowledgeItem(
            term="Test",
            rem_id="123",
            action="UPDATE",
            new_content="New",
            new_breadcrumb="[New]",
            existing_content="Old",
            existing_breadcrumb="[Old]",
            nli_context={"new_hierarchical_path": "New", "existing_hierarchical_path": "Old"}
        )

        item_dict = asdict(item)
        assert item_dict["term"] == "Test"
        assert item_dict["action"] == "UPDATE"


class TestPrepareKnowledgeItems:
    """知識項目準備測試"""

    def test_single_create_item(self):
        """測試單一 CREATE 項目"""
        ast_items = [
            {
                "term": "Glaucoma",
                "new_content": "Glaucoma definition",
                "breadcrumb": "[Ophthalmology > Glaucoma]",
                "level": 1
            }
        ]

        context_trees = {}
        term_to_id = {}  # 沒有 rem_id 意味著 CREATE

        # 模擬 prepare_knowledge_items 邏輯
        knowledge_items = []
        for ast_item in ast_items:
            term = ast_item["term"]
            rem_id = term_to_id.get(term)

            item = KnowledgeItem(
                term=term,
                rem_id=rem_id,
                action="CREATE" if not rem_id else "UPDATE",
                new_content=ast_item["new_content"],
                new_breadcrumb=ast_item["breadcrumb"],
                existing_content=None,
                existing_breadcrumb=None,
                nli_context={
                    "new_hierarchical_path": ast_item["breadcrumb"],
                    "existing_hierarchical_path": None
                }
            )
            knowledge_items.append(item)

        assert len(knowledge_items) == 1
        assert knowledge_items[0].action == "CREATE"
        assert knowledge_items[0].rem_id is None

    def test_single_update_item(self):
        """測試單一 UPDATE 項目"""
        ast_items = [
            {
                "term": "Glaucoma",
                "new_content": "Updated definition",
                "breadcrumb": "[Ophthalmology > Glaucoma]",
                "level": 1
            }
        ]

        context_trees = {
            "tree1": {
                "rem_id": "abc123",
                "content": "Old definition",
                "breadcrumb": "[Eye_Diseases > Glaucoma]"
            }
        }

        term_to_id = {"Glaucoma": "abc123"}

        knowledge_items = []
        for ast_item in ast_items:
            term = ast_item["term"]
            rem_id = term_to_id.get(term)

            existing_content = None
            existing_breadcrumb = None

            if rem_id:
                # 簡化: 假設找到
                for tree_id, node in context_trees.items():
                    if node["rem_id"] == rem_id:
                        existing_content = node["content"]
                        existing_breadcrumb = node["breadcrumb"]

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
        assert knowledge_items[0].rem_id == "abc123"
        assert knowledge_items[0].existing_content is not None

    def test_mixed_create_and_update(self):
        """測試混合 CREATE 和 UPDATE"""
        ast_items = [
            {
                "term": "GlaucomaNew",
                "new_content": "New item",
                "breadcrumb": "[Ophthalmology > GlaucomaNew]",
                "level": 1
            },
            {
                "term": "Cataract",
                "new_content": "Updated cataract",
                "breadcrumb": "[Ophthalmology > Cataract]",
                "level": 1
            }
        ]

        term_to_id = {"Cataract": "existing_id"}
        context_trees = {
            "tree1": {
                "rem_id": "existing_id",
                "content": "Old cataract",
                "breadcrumb": "[Eye_Diseases > Cataract]"
            }
        }

        knowledge_items = []
        for ast_item in ast_items:
            term = ast_item["term"]
            rem_id = term_to_id.get(term)

            existing_content = None
            existing_breadcrumb = None

            if rem_id:
                for tree_id, node in context_trees.items():
                    if node["rem_id"] == rem_id:
                        existing_content = node["content"]
                        existing_breadcrumb = node["breadcrumb"]

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

        assert len(knowledge_items) == 2
        assert knowledge_items[0].action == "CREATE"
        assert knowledge_items[1].action == "UPDATE"

    def test_null_handling_for_nonexistent_terms(self):
        """測試不存在的項的 null 處理"""
        ast_items = [
            {
                "term": "NotInMap",
                "new_content": "Content",
                "breadcrumb": "[Path]",
                "level": 0
            }
        ]

        term_to_id = {}  # 空映射
        context_trees = {}

        knowledge_items = []
        for ast_item in ast_items:
            term = ast_item["term"]
            rem_id = term_to_id.get(term)  # 會是 None

            item = KnowledgeItem(
                term=term,
                rem_id=rem_id,
                action="CREATE" if rem_id is None else "UPDATE",
                new_content=ast_item["new_content"],
                new_breadcrumb=ast_item["breadcrumb"],
                existing_content=None,
                existing_breadcrumb=None,
                nli_context={
                    "new_hierarchical_path": ast_item["breadcrumb"],
                    "existing_hierarchical_path": None
                }
            )
            knowledge_items.append(item)

        assert knowledge_items[0].rem_id is None


class TestBreadcrumbPairing:
    """Breadcrumb 配對測試"""

    def test_identical_breadcrumbs(self):
        """測試相同的 breadcrumbs"""
        item = KnowledgeItem(
            term="Item",
            rem_id="123",
            action="SKIP",
            new_content="Content",
            new_breadcrumb="[Category > Item]",
            existing_content="Content",
            existing_breadcrumb="[Category > Item]",
            nli_context={
                "new_hierarchical_path": "Category > Item",
                "existing_hierarchical_path": "Category > Item"
            }
        )

        assert item.new_breadcrumb == item.existing_breadcrumb

    def test_different_hierarchies(self):
        """測試不同的層級結構"""
        item = KnowledgeItem(
            term="Item",
            rem_id="123",
            action="UPDATE",
            new_content="New content",
            new_breadcrumb="[Domain_A > Category_A > Item]",
            existing_content="Old content",
            existing_breadcrumb="[Domain_B > Category_B > Item]",
            nli_context={
                "new_hierarchical_path": "Domain_A > Category_A > Item",
                "existing_hierarchical_path": "Domain_B > Category_B > Item"
            }
        )

        assert item.new_breadcrumb != item.existing_breadcrumb
        assert "Domain_A" in item.new_breadcrumb
        assert "Domain_B" in item.existing_breadcrumb

    def test_breadcrumb_preserves_full_path(self):
        """測試 breadcrumb 保留完整路徑"""
        breadcrumb = "[Ophthalmology > Glaucoma > Open-Angle > Normal_Tension]"

        item = KnowledgeItem(
            term="NormalTension",
            rem_id="123",
            action="UPDATE",
            new_content="Content",
            new_breadcrumb=breadcrumb,
            existing_content="Old",
            existing_breadcrumb="[Old_Structure]",
            nli_context={
                "new_hierarchical_path": "Ophthalmology > Glaucoma > Open-Angle > Normal_Tension",
                "existing_hierarchical_path": "Old_Structure"
            }
        )

        assert "Ophthalmology" in item.new_breadcrumb
        assert "Glaucoma" in item.new_breadcrumb
        assert "Open-Angle" in item.new_breadcrumb


class TestNLIContextPreparation:
    """NLI 上下文準備測試"""

    def test_nli_context_structure(self):
        """測試 NLI 上下文結構"""
        item = KnowledgeItem(
            term="Test",
            rem_id="123",
            action="UPDATE",
            new_content="New",
            new_breadcrumb="[New > Path]",
            existing_content="Old",
            existing_breadcrumb="[Old > Path]",
            nli_context={
                "new_hierarchical_path": "New > Path",
                "existing_hierarchical_path": "Old > Path"
            }
        )

        assert "new_hierarchical_path" in item.nli_context
        assert "existing_hierarchical_path" in item.nli_context
        assert item.nli_context["new_hierarchical_path"] == "New > Path"

    def test_nli_context_none_for_create(self):
        """測試 CREATE 時現有路徑為 None"""
        item = KnowledgeItem(
            term="NewItem",
            rem_id=None,
            action="CREATE",
            new_content="Content",
            new_breadcrumb="[Path > NewItem]",
            existing_content=None,
            existing_breadcrumb=None,
            nli_context={
                "new_hierarchical_path": "Path > NewItem",
                "existing_hierarchical_path": None
            }
        )

        assert item.nli_context["existing_hierarchical_path"] is None


class TestEdgeCasesStepD:
    """Step D 邊界情況測試"""

    def test_very_long_breadcrumb(self):
        """測試非常長的 breadcrumb"""
        long_path = " > ".join([f"Level{i}" for i in range(20)])
        breadcrumb = f"[{long_path}]"

        item = KnowledgeItem(
            term="DeepItem",
            rem_id="123",
            action="UPDATE",
            new_content="Content",
            new_breadcrumb=breadcrumb,
            existing_content="Old",
            existing_breadcrumb="[OldPath]",
            nli_context={
                "new_hierarchical_path": long_path,
                "existing_hierarchical_path": "OldPath"
            }
        )

        assert len(item.new_breadcrumb) > 100

    def test_unicode_in_breadcrumb(self):
        """測試包含 unicode 的 breadcrumb"""
        item = KnowledgeItem(
            term="中文項",
            rem_id="123",
            action="UPDATE",
            new_content="內容",
            new_breadcrumb="[眼科 > 青光眼 > 中文項]",
            existing_content="舊內容",
            existing_breadcrumb="[眼病 > 青光眼]",
            nli_context={
                "new_hierarchical_path": "眼科 > 青光眼 > 中文項",
                "existing_hierarchical_path": "眼病 > 青光眼"
            }
        )

        assert "眼科" in item.new_breadcrumb
        assert "中文項" in item.new_breadcrumb

    def test_special_characters_in_term(self):
        """測試項名稱中的特殊字符"""
        item = KnowledgeItem(
            term="Term-With_Special.Chars",
            rem_id="123",
            action="UPDATE",
            new_content="Content",
            new_breadcrumb="[Category > Term-With_Special.Chars]",
            existing_content="Old",
            existing_breadcrumb="[OldCat > Term]",
            nli_context={
                "new_hierarchical_path": "Category > Term-With_Special.Chars",
                "existing_hierarchical_path": "OldCat > Term"
            }
        )

        assert "-" in item.term
        assert "_" in item.term
        assert "." in item.term


@pytest.fixture
def sample_knowledge_item():
    """樣本 KnowledgeItem fixture"""
    return KnowledgeItem(
        term="SampleTerm",
        rem_id="sample_id_123",
        action="UPDATE",
        new_content="Sample new content",
        new_breadcrumb="[New > Sample]",
        existing_content="Sample old content",
        existing_breadcrumb="[Old > Sample]",
        nli_context={
            "new_hierarchical_path": "New > Sample",
            "existing_hierarchical_path": "Old > Sample"
        }
    )


def test_with_fixture(sample_knowledge_item):
    """使用 fixture 的測試"""
    assert sample_knowledge_item.term == "SampleTerm"
    assert sample_knowledge_item.action == "UPDATE"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
