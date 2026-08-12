"""
nli_router.py - NLI Router v1.3

統一 NLI 路由系統，完全替代 v5 的複雜邏輯：
- 接收 knowledge_items（來自 Step D，雙邊帶 breadcrumb）
- 執行 NLI 推理判斷
- 輸出 4 類動作：CREATE / UPDATE / SKIP / REQUIRES_LLM
- 完全消除 ambiguous 項（0% manual review）

Key Points:
✅ 使用 breadcrumb 增強 premise/hypothesis
✅ 3 級閾值判斷：Entailment (>0.85) → SKIP，Neutral (>0.60) → CREATE，else → UPDATE
✅ 無人工審查分類
✅ 完整審計日誌
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from src.pipeline.core import KnowledgeItem, ActionType


@dataclass
class NLIResult:
    """NLI 推理結果"""
    entailment_score: float = 0.0    # Entailment 概率
    neutral_score: float = 0.0       # Neutral 概率
    contradiction_score: float = 0.0 # Contradiction 概率
    verdict: str = "NEUTRAL"         # ENTAILMENT / NEUTRAL / CONTRADICTION
    confidence: float = 0.0          # 最高分數


@dataclass
class FinalAction:
    """NLI Router 的最終動作"""
    action: str  # CREATE / UPDATE / SKIP / REQUIRES_LLM
    term: str
    rem_id: Optional[str] = None

    # 內容
    new_content: str = ""
    new_breadcrumb: str = ""
    existing_content: Optional[str] = None
    existing_breadcrumb: Optional[str] = None

    # NLI 判斷
    nli_confidence: float = 0.0
    nli_verdict: str = ""
    nli_reason: str = ""

    # 差異（若為 UPDATE）
    delta_content: Optional[str] = None
    delta_confidence: float = 0.0

    # 審計
    cost_usd: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        """序列化為字典"""
        return {
            "action": self.action,
            "term": self.term,
            "rem_id": self.rem_id,
            "new_content": self.new_content,
            "new_breadcrumb": self.new_breadcrumb,
            "existing_content": self.existing_content,
            "existing_breadcrumb": self.existing_breadcrumb,
            "nli_confidence": self.nli_confidence,
            "nli_verdict": self.nli_verdict,
            "nli_reason": self.nli_reason,
            "delta_content": self.delta_content,
            "delta_confidence": self.delta_confidence,
            "cost_usd": self.cost_usd
        }


@dataclass
class LLMInterventionCase:
    """需要 LLM 干預的特殊案例"""
    case_id: str
    type: str  # fragmented_delta / context_mismatch / complexity_high
    term: str
    rem_id: str

    new_content: str = ""
    existing_content: str = ""
    new_breadcrumb: str = ""
    existing_breadcrumb: str = ""

    reason: str = ""
    suggested_action: str = ""  # CREATE / UPDATE / SKIP
    intervention_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "type": self.type,
            "term": self.term,
            "rem_id": self.rem_id,
            "new_content": self.new_content,
            "existing_content": self.existing_content,
            "new_breadcrumb": self.new_breadcrumb,
            "existing_breadcrumb": self.existing_breadcrumb,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "intervention_notes": self.intervention_notes
        }


class MockNLIRouter:
    """
    模擬 NLI 推理器 (暫時版本)

    在正式實作中應使用 microsoft/deberta-v3-small:
    ```
    from transformers import pipeline
    self.nli = pipeline(
        "zero-shot-classification",
        model="microsoft/deberta-v3-small",
        device=-1  # CPU
    )
    ```
    """

    def __init__(self):
        print("[NLI Router] 使用模擬推理器 (暫時版本)")
        print("[NLI Router] 提示: 正式版本應使用 microsoft/deberta-v3-small")

    def predict(self, premise: str, hypothesis: str) -> NLIResult:
        """
        執行 NLI 推理

        Args:
            premise: 前提 (existing content)
            hypothesis: 假設 (new content)

        Returns:
            NLIResult: 推理結果
        """
        # 簡單啟發式規則 (暫時版本)
        # 正式版本應使用 NLI 模型

        # 計算文本相似度 (簡化實作)
        premise_tokens = set(premise.lower().split())
        hypothesis_tokens = set(hypothesis.lower().split())

        if not premise_tokens or not hypothesis_tokens:
            # 空文本 → 中立
            return NLIResult(
                neutral_score=0.7,
                verdict="NEUTRAL",
                confidence=0.7
            )

        intersection = len(premise_tokens & hypothesis_tokens)
        union = len(premise_tokens | hypothesis_tokens)
        jaccard = intersection / union if union > 0 else 0

        # 基於相似度的啟發式判斷
        if jaccard > 0.85:
            return NLIResult(
                entailment_score=0.92,
                neutral_score=0.06,
                contradiction_score=0.02,
                verdict="ENTAILMENT",
                confidence=0.92
            )
        elif jaccard > 0.60:
            return NLIResult(
                entailment_score=0.45,
                neutral_score=0.40,
                contradiction_score=0.15,
                verdict="NEUTRAL",
                confidence=0.45
            )
        else:
            return NLIResult(
                entailment_score=0.20,
                neutral_score=0.30,
                contradiction_score=0.50,
                verdict="CONTRADICTION",
                confidence=0.50
            )

    def infer(self, premise: str, hypothesis: str, use_cache: bool = True) -> NLIResult:
        """
        執行 NLI 推論 (相容 RealNLIRouter 介面)

        委託給 predict() 並返回相同格式的結果

        Args:
            premise: 前提文本
            hypothesis: 假設文本
            use_cache: 是否使用快取 (Mock 版本忽略此參數)

        Returns:
            NLIResult: 推論結果
        """
        return self.predict(premise, hypothesis)


class NLIRouterV6:
    """
    NLI Router v1.3: 統一分類所有 knowledge_items

    分類邏輯：
    1. 對於每個 knowledge_item，執行 NLI 推理
    2. 使用 breadcrumb 增強 premise 和 hypothesis
    3. 根據 NLI 結果和閾值判斷動作：
       - Entailment >0.85 → SKIP (已存在)
       - Neutral >0.60 → CREATE (新項目)
       - Else → UPDATE (需更新)
    4. 複雜情況 → REQUIRES_LLM
    """

    def __init__(self, use_mock: bool = True):
        """
        初始化 NLI Router

        Args:
            use_mock: 若 True，使用模擬推理器；否則使用真實模型
        """
        self.use_mock = use_mock

        if use_mock:
            self.nli = MockNLIRouter()
        else:
            # 正式版本：載入 deberta-v3-small
            # 需要 pip install transformers torch
            try:
                from transformers import pipeline
                print("[NLI Router] 載入 microsoft/deberta-v3-small...")
                self.nli = pipeline(
                    "zero-shot-classification",
                    model="microsoft/deberta-v3-small",
                    device=-1  # CPU
                )
            except ImportError:
                print("[NLI Router] 警告: 缺少 transformers/torch，轉用模擬推理器")
                self.use_mock = True
                self.nli = MockNLIRouter()

        # 設定
        self.entailment_threshold = 0.85
        self.neutral_threshold = 0.60
        self.complexity_threshold = 0.50  # 當信心度 < 50% 時考慮 LLM 干預

        # 統計
        self.statistics = {
            "total_processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "requires_llm": 0,
            "ambiguous_rate": 0.0,
            "avg_nli_confidence": 0.0
        }

        self.llm_cases = []
        self.final_actions = []

    def apply_nli_routing(
        self,
        knowledge_items: List[KnowledgeItem]
    ) -> dict:
        """
        對所有 knowledge_items 執行 NLI 路由

        Args:
            knowledge_items: Step D 的輸出

        Returns:
            {
                "final_actions": [...],           # CREATE/UPDATE/SKIP 動作
                "requires_llm_intervention": [...],  # REQUIRES_LLM 案例
                "statistics": {...}
            }
        """
        print("\n" + "="*60)
        print("[START] NLI Router v1.3 開始執行")
        print("="*60 + "\n")

        self.final_actions = []
        self.llm_cases = []

        total_confidence = 0

        for idx, item in enumerate(knowledge_items):
            print(f"[{idx+1}/{len(knowledge_items)}] 處理: {item.term}")

            if item.action == "CREATE":
                # CREATE 項目：直接創建（新項目無需比較）
                action = FinalAction(
                    action="CREATE",
                    term=item.term,
                    rem_id=None,
                    new_content=item.new_content,
                    new_breadcrumb=item.new_breadcrumb,
                    nli_confidence=1.0,
                    nli_verdict="N/A",
                    nli_reason="新項目，無需比較"
                )
                self.final_actions.append(action)
                self.statistics["created"] += 1
                total_confidence += 1.0

            elif item.action == "UPDATE":
                # UPDATE 項目：執行 NLI 推理
                action = self._process_update_item(item)
                total_confidence += action.nli_confidence

                if action.action == "REQUIRES_LLM":
                    self.llm_cases.append(action)
                    self.statistics["requires_llm"] += 1
                else:
                    self.final_actions.append(action)
                    if action.action == "UPDATE":
                        self.statistics["updated"] += 1
                    elif action.action == "SKIP":
                        self.statistics["skipped"] += 1

        # 計算統計
        self.statistics["total_processed"] = len(knowledge_items)
        self.statistics["avg_nli_confidence"] = (
            total_confidence / len(knowledge_items) if knowledge_items else 0
        )
        self.statistics["ambiguous_rate"] = 0.0  # v1.3: 完全消除 ambiguous

        print("\n" + "="*60)
        print("[OK] NLI Router 執行完成")
        print(f"   CREATE: {self.statistics['created']}")
        print(f"   UPDATE: {self.statistics['updated']}")
        print(f"   SKIP: {self.statistics['skipped']}")
        print(f"   REQUIRES_LLM: {self.statistics['requires_llm']}")
        print(f"   平均信心度: {self.statistics['avg_nli_confidence']:.2%}")
        print("="*60 + "\n")

        return {
            "final_actions": self.final_actions,
            "requires_llm_intervention": self.llm_cases,
            "statistics": self.statistics
        }

    def _process_update_item(self, item: KnowledgeItem) -> FinalAction:
        """
        處理 UPDATE 項目：執行 NLI 推理並決策
        """
        # 如果沒有現有內容，降級為 CREATE
        if not item.existing_content:
            return FinalAction(
                action="CREATE",
                term=item.term,
                rem_id=None,
                new_content=item.new_content,
                new_breadcrumb=item.new_breadcrumb,
                nli_confidence=1.0,
                nli_verdict="N/A",
                nli_reason="無現有內容，降級為 CREATE"
            )

        # 使用 breadcrumb 增強输入
        premise = f"[{item.existing_breadcrumb}] {item.existing_content}" if item.existing_breadcrumb else item.existing_content
        hypothesis = f"[{item.new_breadcrumb}] {item.new_content}" if item.new_breadcrumb else item.new_content

        # 執行 NLI 推理
        nli_result = self.nli.predict(premise, hypothesis)

        # 決策邏輯
        if nli_result.entailment_score > self.entailment_threshold:
            # 高重疊 → SKIP
            action_type = "SKIP"
            reason = f"已存在相似內容 (Entailment {nli_result.confidence:.2%})"
        elif nli_result.neutral_score > self.neutral_threshold:
            # 中度重疊 → CREATE (因為是新內容)
            action_type = "CREATE"
            reason = f"需要新建項目 (Neutral {nli_result.confidence:.2%})"
        else:
            # 低重疊 → UPDATE
            action_type = "UPDATE"
            reason = f"需要更新現有項目 (Contradiction {nli_result.confidence:.2%})"

        # 檢查複雜性
        if nli_result.confidence < self.complexity_threshold and action_type != "SKIP":
            # 信心度過低 → 需要 LLM 干預
            action_type = "REQUIRES_LLM"
            reason = f"複雜情況，信心度不足: {nli_result.confidence:.2%}"

        action = FinalAction(
            action=action_type,
            term=item.term,
            rem_id=item.rem_id,
            new_content=item.new_content,
            new_breadcrumb=item.new_breadcrumb,
            existing_breadcrumb=item.existing_breadcrumb,
            nli_confidence=nli_result.confidence,
            nli_verdict=nli_result.verdict,
            nli_reason=reason
        )

        if action_type == "UPDATE":
            # 計算差異
            action.delta_content = self._compute_delta(item.existing_content, item.new_content)
            action.delta_confidence = max(0, 1 - nli_result.entailment_score)

        return action

    def _compute_delta(self, existing: str, new: str) -> str:
        """
        計算語義差異 (簡化版)

        正式版應使用 SemanticDiffEngine
        """
        # 暫時實作：僅返回新內容
        # 正式版本應進行文本比較並提取差異
        return new

    def get_statistics(self) -> dict:
        """返回統計信息"""
        return self.statistics.copy()

    def export_final_actions(self, format: str = "json") -> str:
        """
        匯出最終動作

        Args:
            format: "json" | "csv"

        Returns:
            序列化字符串
        """
        if format == "json":
            return json.dumps(
                [action.to_dict() for action in self.final_actions],
                ensure_ascii=False,
                indent=2
            )
        else:
            raise NotImplementedError(f"Format {format} not implemented")


# ============================================================================
# 測試與範例
# ============================================================================

def main(argv: Optional[List[str]] = None):
    import argparse
    import sys
    import json
    from pathlib import Path

    # Fallback to demo if no arguments are provided
    if (argv is None and len(sys.argv) == 1) or (argv is not None and len(argv) == 0):
        print("[INFO] Running demo mode with mock data (use --help to see CLI options)...")
        # 建立測試 knowledge_items
        test_items = [
            KnowledgeItem(
                term="Glaucoma",
                rem_id="rem_001",
                action="UPDATE",
                new_content="青光眼是眼壓升高導致視神經損傷的疾病",
                new_breadcrumb="[Ophthalmology > Glaucoma]",
                new_breadcrumb_parts=["Ophthalmology", "Glaucoma"],
                existing_content="高眼壓相關疾病",
                existing_breadcrumb="[眼科疾病 > 青光眼]",
                existing_breadcrumb_parts=["眼科疾病", "青光眼"],
                nli_context={
                    "new_hierarchical_path": "Ophthalmology > Glaucoma",
                    "existing_hierarchical_path": "眼科疾病 > 青光眼"
                }
            ),
            KnowledgeItem(
                term="Normal Tension Glaucoma",
                rem_id=None,
                action="CREATE",
                new_content="眼壓正常但仍有視神經損傷",
                new_breadcrumb="[Ophthalmology > Glaucoma > Normal Tension]",
                new_breadcrumb_parts=["Ophthalmology", "Glaucoma", "Normal Tension"]
            ),
            KnowledgeItem(
                term="Open-Angle Glaucoma",
                rem_id="rem_002",
                action="UPDATE",
                new_content="慢性進行性青光眼類型",
                new_breadcrumb="[Ophthalmology > Glaucoma > Open-Angle]",
                new_breadcrumb_parts=["Ophthalmology", "Glaucoma", "Open-Angle"],
                existing_content="慢性青光眼",
                existing_breadcrumb="[眼科疾病 > 青光眼 > 開角型]",
                existing_breadcrumb_parts=["眼科疾病", "青光眼", "開角型"],
                nli_context={
                    "new_hierarchical_path": "Ophthalmology > Glaucoma > Open-Angle",
                    "existing_hierarchical_path": "眼科疾病 > 青光眼 > 開角型"
                }
            )
        ]

        # 執行 NLI Router
        router = NLIRouterV6(use_mock=True)
        result = router.apply_nli_routing(test_items)

        # 顯示結果
        print("\n[RESULTS] 最終動作:")
        for action in result["final_actions"]:
            print(f"  [{action.action}] {action.term} - 信心度: {action.nli_confidence:.2%}")

        if result["requires_llm_intervention"]:
            print(f"\n[INTERVENTION] 需要 LLM 干預: {len(result['requires_llm_intervention'])} 項")

        # 顯示統計
        print(f"\n[STATS] 統計:")
        for key, value in result["statistics"].items():
            print(f"  {key}: {value}")
        return

    parser = argparse.ArgumentParser(
        description="NLIRouterV6 (Mock/DeBERTa) CLI — Run classification on single pairs or batch JSON files"
    )
    parser.add_argument(
        "--premise", "-p",
        type=str,
        help="Premise text for single NLI inference."
    )
    parser.add_argument(
        "--hypothesis", "-y",
        type=str,
        help="Hypothesis text for single NLI inference."
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        help="Path to a JSON file containing a list of KnowledgeItem dictionaries."
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("mock_routing_output.json"),
        help="Path to write the routing results JSON (default: mock_routing_output.json)."
    )
    parser.add_argument(
        "--use-mock",
        type=bool,
        default=True,
        help="Whether to use the mock heuristic router instead of DeBERTa (default: True)."
    )

    args = parser.parse_args(argv)

    # Validate combinations
    if args.premise or args.hypothesis:
        if not args.premise or not args.hypothesis:
            print("Error: Both --premise and --hypothesis must be provided for single-pair inference.", file=sys.stderr)
            sys.exit(1)
        
        # Execute single pair NLI prediction using NLIRouterV6's underlying router
        router = NLIRouterV6(use_mock=args.use_mock)
        result = router.nli.infer(args.premise, args.hypothesis)
        
        output_dict = {
            "premise": args.premise,
            "hypothesis": args.hypothesis,
            "verdict": result.verdict,
            "confidence": result.confidence,
            "scores": {
                "entailment": result.entailment_score,
                "neutral": result.neutral_score,
                "contradiction": result.contradiction_score
            }
        }
        print(json.dumps(output_dict, ensure_ascii=False, indent=2))
        return

    if args.input:
        if not args.input.exists():
            print(f"Error: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)

        # Load input knowledge items JSON
        raw_data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        knowledge_items = [KnowledgeItem(**item_dict) for item_dict in raw_data]

        router = NLIRouterV6(use_mock=args.use_mock)
        routing_result = router.apply_nli_routing(knowledge_items)

        # Serialize results
        final_actions_serialized = [action.to_dict() for action in routing_result["final_actions"]]
        requires_llm_serialized = [case.to_dict() for case in routing_result["requires_llm_intervention"]]
        
        output_dict = {
            "pipeline_version": "v0.3-mock-standalone",
            "statistics": routing_result["statistics"],
            "detailed_output": {
                "final_actions": final_actions_serialized,
                "llm_interventions": requires_llm_serialized
            }
        }

        args.output.write_text(
            json.dumps(output_dict, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n[nli_types] Routing results written to: {args.output}")
        return

    print("Error: You must provide either (--premise and --hypothesis) OR --input.", file=sys.stderr)
    parser.print_usage(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
