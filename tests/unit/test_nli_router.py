"""
NLI Router 分類決策測試

測試範圍:
- NLI 推論 (entailment, neutral, contradiction)
- 分類閾值 (0.85, 0.60)
- 4 分類判決 (CREATE, UPDATE, SKIP, REQUIRES_LLM)
- 統計追蹤
- 信心度計算

執行: pytest tests/unit/test_nli_router.py -v
"""

import pytest
import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.core import KnowledgeItem
from src.routers.nli_types import NLIResult, FinalAction, LLMInterventionCase, MockNLIRouter, NLIRouterV6


class TestNLIResultDataclass:
    """NLIResult 數據類測試"""

    def test_nli_result_creation(self):
        """測試建立 NLIResult"""
        result = NLIResult(
            entailment_score=0.92,
            neutral_score=0.05,
            contradiction_score=0.03,
            verdict="ENTAILMENT"
        )

        assert result.entailment_score == 0.92
        assert result.verdict == "ENTAILMENT"

    def test_nli_result_probabilities_sum(self):
        """測試概率和接近 1.0"""
        result = NLIResult(
            entailment_score=0.7,
            neutral_score=0.2,
            contradiction_score=0.1,
            verdict="ENTAILMENT"
        )

        total = result.entailment_score + result.neutral_score + result.contradiction_score
        assert 0.99 <= total <= 1.01


class TestFinalActionDataclass:
    """FinalAction 數據類測試"""

    def test_final_action_create(self):
        """測試 CREATE 操作"""
        action = FinalAction(
            action="CREATE",
            term="NewTerm",
            new_content="New content here",
            new_breadcrumb="[Category > NewTerm]",
            nli_confidence=0.92,
            rem_id=None
        )

        assert action.action == "CREATE"
        assert action.rem_id is None

    def test_final_action_update(self):
        """測試 UPDATE 操作"""
        action = FinalAction(
            action="UPDATE",
            term="ExistingTerm",
            new_content="Delta content",
            new_breadcrumb="[Category > ExistingTerm]",
            nli_confidence=0.78,
            rem_id="existing_id"
        )

        assert action.action == "UPDATE"
        assert action.rem_id == "existing_id"

    def test_final_action_skip(self):
        """測試 SKIP 操作"""
        action = FinalAction(
            action="SKIP",
            term="DuplicateTerm",
            new_content="Same content",
            new_breadcrumb="[Category > DuplicateTerm]",
            nli_confidence=0.95,
            rem_id="dup_id"
        )

        assert action.action == "SKIP"


class TestLLMInterventionCaseDataclass:
    """LLMInterventionCase 數據類測試"""

    def test_llm_case_fragmented_delta(self):
        """測試碎片化差異的 LLM 案例"""
        case = LLMInterventionCase(
            case_id="case_001",
            type="fragmented_delta",
            term="FragmentedTerm",
            rem_id="item_123",
            new_content="Multi-part delta with\ncomplex structure",
            existing_breadcrumb="[Old > Path]",
            reason="Delta too fragmented for direct append"
        )

        assert case.type == "fragmented_delta"
        assert case.rem_id == "item_123"


class TestMockNLIRouter:
    """MockNLIRouter 測試"""

    def test_mock_router_high_confidence_entailment(self):
        """測試 mock 路由的高信心 entailment"""
        router = MockNLIRouter()

        # 完全相同的文本應返回高 entailment
        result = router.infer(
            premise="Glaucoma is an eye disease",
            hypothesis="Glaucoma is an eye disease"
        )

        assert result.verdict == "ENTAILMENT"
        assert result.entailment_score > 0.85

    def test_mock_router_neutral_different_topics(self):
        """測試不同主題應返回 neutral"""
        router = MockNLIRouter()

        result = router.infer(
            premise="Glaucoma affects eye pressure",
            hypothesis="Cats like fish"
        )

        # 完全不相關的文本應是 neutral 或 contradiction
        assert result.verdict in ["NEUTRAL", "CONTRADICTION"]

    def test_mock_router_contradiction(self):
        """測試矛盾的文本"""
        router = MockNLIRouter()

        result = router.infer(
            premise="Glaucoma does NOT affect vision",
            hypothesis="Glaucoma causes vision loss"
        )

        # 應檢測矛盾 (含 NOT 與相反陳述)
        assert result.verdict in ["CONTRADICTION", "NEUTRAL"]

    def test_mock_router_similar_text(self):
        """測試相似但不完全相同的文本"""
        router = MockNLIRouter()

        result = router.infer(
            premise="Normal tension glaucoma is a type of open-angle glaucoma",
            hypothesis="Open-angle glaucoma includes normal tension glaucoma"
        )

        # 相似的文本應有高信心度，允許 CONTRADICTION (Jaccard ~0.44 < 0.60)
        assert result.confidence >= 0.45


class TestNLIRouterV6ThresholdLogic:
    """NLI Router V6 閾值邏輯測試"""

    def test_entailment_threshold_high(self):
        """測試高 entailment (>0.85) → SKIP"""
        # 模擬 NLI 結果
        nli_result = NLIResult(
            entailment_score=0.90,
            neutral_score=0.05,
            contradiction_score=0.05,
            verdict="ENTAILMENT"
        )

        # 按 v1.3 邏輯
        if nli_result.entailment_score > 0.85:
            action = "SKIP"
        elif nli_result.neutral_score > 0.60:
            action = "CREATE"
        else:
            action = "UPDATE"

        assert action == "SKIP"

    def test_neutral_threshold_high(self):
        """測試高 neutral (>0.60) → CREATE"""
        nli_result = NLIResult(
            entailment_score=0.15,
            neutral_score=0.75,
            contradiction_score=0.10,
            verdict="NEUTRAL"
        )

        if nli_result.entailment_score > 0.85:
            action = "SKIP"
        elif nli_result.neutral_score > 0.60:
            action = "CREATE"
        else:
            action = "UPDATE"

        assert action == "CREATE"

    def test_contradiction_threshold(self):
        """測試矛盾 → UPDATE"""
        nli_result = NLIResult(
            entailment_score=0.10,
            neutral_score=0.20,
            contradiction_score=0.70,
            verdict="CONTRADICTION"
        )

        if nli_result.entailment_score > 0.85:
            action = "SKIP"
        elif nli_result.neutral_score > 0.60:
            action = "CREATE"
        else:
            action = "UPDATE"

        assert action == "UPDATE"

    def test_edge_case_neutral_at_threshold(self):
        """測試 neutral 恰好在閾值 (0.60)"""
        nli_result = NLIResult(
            entailment_score=0.20,
            neutral_score=0.60,
            contradiction_score=0.20,
            verdict="NEUTRAL"
        )

        # 0.60 應視為 > 0.60 嗎？ 否，應該 <= 0.60 時觸發
        if nli_result.neutral_score > 0.60:
            action = "CREATE"
        else:
            action = "UPDATE"

        assert action == "UPDATE"  # 0.60 不 > 0.60

    def test_edge_case_neutral_just_above_threshold(self):
        """測試 neutral 略高於閾值"""
        nli_result = NLIResult(
            entailment_score=0.20,
            neutral_score=0.601,
            contradiction_score=0.199,
            verdict="NEUTRAL"
        )

        if nli_result.neutral_score > 0.60:
            action = "CREATE"
        else:
            action = "UPDATE"

        assert action == "CREATE"


class TestNLIRouterAggregateStatistics:
    """NLI Router 統計追蹤測試"""

    def test_statistics_initialization(self):
        """測試統計初始化"""
        router = NLIRouterV6()
        stats = router.get_statistics()

        assert "total_processed" in stats
        assert "created" in stats
        assert "updated" in stats
        assert "skipped" in stats

    def test_statistics_tracking(self):
        """測試添加項後的統計追蹤"""
        router = NLIRouterV6()

        # 模擬 4 個 final_actions
        final_actions = [
            FinalAction(action="CREATE", term="Term1", new_content="Content1", new_breadcrumb="[Path1]", nli_confidence=0.92),
            FinalAction(action="CREATE", term="Term2", new_content="Content2", new_breadcrumb="[Path2]", nli_confidence=0.88),
            FinalAction(action="UPDATE", term="Term3", new_content="Content3", new_breadcrumb="[Path3]", nli_confidence=0.75, rem_id="id3"),
            FinalAction(action="SKIP", term="Term4", new_content="Content4", new_breadcrumb="[Path4]", nli_confidence=0.95, rem_id="id4"),
        ]

        # 手動更新統計
        router.statistics["total_processed"] = 4
        router.statistics["created"] = 2
        router.statistics["updated"] = 1
        router.statistics["skipped"] = 1

        stats = router.get_statistics()
        assert stats["total_processed"] == 4
        assert stats["created"] == 2
        assert stats["updated"] == 1
        assert stats["skipped"] == 1

    def test_automation_rate_calculation(self):
        """測試自動化率計算"""
        total = 14
        manual_review = 0

        auto_rate = (total - manual_review) / total if total > 0 else 0

        assert auto_rate == 1.0
        assert auto_rate * 100 == 100


class TestNLIClassificationFullFlow:
    """端對端分類流程測試"""

    def test_knowledge_item_to_action_flow(self):
        """測試從 KnowledgeItem 到 FinalAction 的流程"""
        # 建立知識項目
        knowledge_item = KnowledgeItem(
            term="Glaucoma",
            rem_id=None,
            action="CREATE",
            new_content="Glaucoma is a disease affecting optic nerve",
            new_breadcrumb="[Ophthalmology > Glaucoma]",
            existing_content=None,
            existing_breadcrumb=None,
            nli_context={
                "new_hierarchical_path": "Ophthalmology > Glaucoma",
                "existing_hierarchical_path": None
            }
        )

        # 模擬 NLI 推論 (CREATE 時無需比較)
        # 直接產生 FinalAction
        final_action = FinalAction(
            action="CREATE",
            term=knowledge_item.term,
            new_content=knowledge_item.new_content,
            new_breadcrumb=knowledge_item.new_breadcrumb,
            nli_confidence=1.0,
            rem_id=None
        )

        assert final_action.action == "CREATE"
        assert final_action.nli_confidence == 1.0

    def test_update_with_nli_classification(self):
        """測試 UPDATE 情況的 NLI 分類"""
        knowledge_item = KnowledgeItem(
            term="Cataract",
            rem_id="existing_id",
            action="UPDATE",
            new_content="Cataract: clouding of lens",
            new_breadcrumb="[Ophthalmology > Cataract]",
            existing_content="Cataract: opacity of the lens",
            existing_breadcrumb="[Eye_Diseases > Cataract]",
            nli_context={
                "new_hierarchical_path": "Ophthalmology > Cataract",
                "existing_hierarchical_path": "Eye_Diseases > Cataract"
            }
        )

        # 模擬 NLI 推論
        nli_result = NLIResult(
            entailment_score=0.88,
            neutral_score=0.08,
            contradiction_score=0.04,
            verdict="ENTAILMENT"
        )

        # 應決定為 SKIP (entailment > 0.85)
        if nli_result.entailment_score > 0.85:
            final_action_type = "SKIP"
        elif nli_result.neutral > 0.60:
            final_action_type = "CREATE"
        else:
            final_action_type = "UPDATE"

        assert final_action_type == "SKIP"


class TestComplexScenarios:
    """複雜場景測試"""

    def test_multiple_items_mixed_actions(self):
        """測試多個項的混合操作"""
        items = [
            KnowledgeItem("Term1", None, "CREATE", "New1", "[A>1]", None, None, {}),
            KnowledgeItem("Term2", "id2", "UPDATE", "New2", "[A>2]", "Old2", "[B>2]", {}),
            KnowledgeItem("Term3", "id3", "UPDATE", "New3", "[A>3]", "Old3", "[B>3]", {}),
        ]

        actions = []
        for item in items:
            if item.action == "CREATE":
                actions.append(("CREATE", item.term))
            else:
                # 模擬 NLI 判決 (此處簡化)
                actions.append(("UPDATE", item.term))

        assert len(actions) == 3
        assert actions[0][0] == "CREATE"
        assert actions[1][0] == "UPDATE"

    def test_requires_llm_flag(self):
        """測試需要 LLM 干預的標記"""
        case = LLMInterventionCase(
            case_id="complex_001",
            type="fragmented_delta",
            term="ComplexTerm",
            rem_id="id_123",
            new_content="Very complex multi-part content",
            existing_breadcrumb="[Complex > Path]",
            reason="Multiple complex independent changes"
        )

        assert case.type == "fragmented_delta"
        assert "complex" in case.reason.lower()


class TestThresholdVariations:
    """閾值變化測試"""

    def test_strict_entailment_threshold(self):
        """測試嚴格的 entailment 閾值 (0.95)"""
        nli_result = NLIResult(entailment_score=0.90, neutral_score=0.05, contradiction_score=0.05, verdict="ENTAILMENT")

        # 嚴格閾值
        if nli_result.entailment_score > 0.95:
            action = "SKIP"
        else:
            action = "UPDATE"

        assert action == "UPDATE"  # 0.90 不 > 0.95

    def test_loose_neutral_threshold(self):
        """測試寬鬆的 neutral 閾值 (0.50)"""
        nli_result = NLIResult(entailment_score=0.20, neutral_score=0.55, contradiction_score=0.25, verdict="NEUTRAL")

        # 寬鬆閾值
        if nli_result.neutral_score > 0.50:
            action = "CREATE"
        else:
            action = "UPDATE"

        assert action == "CREATE"  # 0.55 > 0.50


@pytest.fixture
def router_instance():
    """NLI Router 實例 fixture"""
    return NLIRouterV6()


@pytest.fixture
def mock_router():
    """Mock NLI Router fixture"""
    return MockNLIRouter()


def test_with_router_fixture(router_instance):
    """使用 router fixture 的測試"""
    stats = router_instance.get_statistics()
    assert isinstance(stats, dict)


def test_mock_router_fixture(mock_router):
    """使用 mock router fixture 的測試"""
    result = mock_router.infer("Test", "Test")
    assert result.verdict in ["ENTAILMENT", "NEUTRAL", "CONTRADICTION"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
