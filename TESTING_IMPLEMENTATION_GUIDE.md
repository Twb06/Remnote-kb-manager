# smart_logic_v5.py 測試實施指南

**版本**: 3.0
**日期**: 2026-05-03
**狀態**: ✅ 階段 1 完成，✅ 階段 2 完成（60% 覆蓋率），✅ 階段 3 完成（70% 覆蓋率達標）

---

## 📋 目錄

1. [專案概況](#專案概況)
2. [階段 1 完成狀況](#階段-1-完成狀況)
3. [階段 2 完成狀況](#階段-2-完成狀況)
4. [階段 3 完成狀況](#階段-3-完成狀況)
5. [測試撰寫範例](#測試撰寫範例)
6. [常見問題排解](#常見問題排解)
7. [下一步行動](#下一步行動)

---

## 專案概況

### 當前測試覆蓋率（✅ 70% 目標達成）

```bash
$ pytest tests/ --cov=smart_logic_v5 --cov-report=term

Name                  Stmts   Miss  Cover
-----------------------------------------
smart_logic_v5.py       549    166    70%
-----------------------------------------
TOTAL                   549    166    70%
```

**完整進展歷程：** 34% → 60% (Phase 2) → 68% → **70% (Phase 3)** ✅

### 測試統計

- **總測試數**: 102 個（從 48 → 59 → 77 → 100 → 102）
- **通過測試**: 102 個 (100%)
- **失敗測試**: 0 個
- **測試類型分佈**:
  - 單元測試: 67 個
---

## 階段 1 完成狀況

### ✅ 已完成項目

#### 1. 測試框架建設

```
✅ requirements-test.txt     # 測試依賴清單
✅ pytest.ini                # Pytest 配置
✅ tests/conftest.py         # 共用 fixtures 與配置
✅ tests/README.md           # 測試文檔
```

#### 2. 測試目錄結構

```
tests/
├── unit/                          ✅ 單元測試目錄
│   ├── test_scoring.py           ✅ 15 個評分邏輯測試
│   ├── test_parsing.py           ✅ 12 個解析函式測試
│   ├── test_tree_ops.py          ✅ 7 個樹狀操作測試
│   └── test_utils.py             ✅ 4 個工具函式測試
├── integration/                   ✅ 整合測試目錄
│   └── test_cli_interactions.py  ✅ 6 個 CLI 互動測試
├── fixtures/                      ✅ 測試資料目錄
│   ├── kb_map_sample.json        ✅ KB map 範例
│   ├── overview_sample.md        ✅ Overview 範例
│   ├── content_sample.md         ✅ Content 範例
│   └── mock_responses/           ✅ Mock CLI 回應
│       ├── search_response.json
│       └── read_response.json
├── conftest.py                    ✅ 共用配置
└── README.md                      ✅ 測試文檔
```

#### 3. 測試依賴安裝

```bash
✅ pytest==9.0.3
✅ pytest-cov==7.1.0
✅ pytest-mock==3.15.1
✅ pytest-benchmark==5.2.3
✅ pytest-html==4.2.0
```

#### 4. 驗證測試

```bash
$ pytest --collect-only
collected 48 items

$ pytest tests/ -q
48 passed in 0.32s
```

---

## 階段 2 完成狀況

✅ **狀態：已完成 - 60% 覆蓋率目標達成**

階段 2 目標：**完成 P0 單元測試與工作流程整合測試，達成 ≥60% 覆蓋率**

### 完成的測試擴展

| 函式名稱 | 原始測試數 | 新增測試數 | 最終測試數 | 狀態 |
|---------|-----------|-----------|-----------|------|
| `calculate_enhanced_score()` | 7 | +4 | 11 | ✅ 完成 |
| `extract_all_rem_ids_from_tree()` | 5 | +2 | 7 | ✅ 完成 |
| `parse_kb_map()` | 4 | +4 | 8 | ✅ 完成 |
| `parse_overview()` | 4 | +2 | 6 | ✅ 完成 |
| `parse_md_to_sections()` | 4 | +2 | 6 | ✅ 完成 |
| `lookup_kb_map()` | 0 | +4 | 4 | ✅ 新增 |
| `search_unmapped()` | 0 | +5 | 5 | ✅ 新增 |
| `hierarchical_locate()` | 0 | +3 | 3 | ✅ 新增 |
| `cross_validate_b_and_b2()` | 0 | +3 | 3 | ✅ 新增 |
| `read_context_tree()` | 0 | +2 | 2 | ✅ 新增 |
| **總計** | **48** | **+29** | **77** | **✅** |

### 覆蓋率進展

```
Phase 0 (基準)：         48 測試 → 34% 覆蓋率
Phase 2A (P0 單元)：     59 測試 → 34% 覆蓋率 (+11 測試)
Phase 2B (工作流程)：    76 測試 → 58% 覆蓋率 (+17 測試, +24%)
Phase 2B (最終衝刺)：    77 測試 → 60% 覆蓋率 (+1 測試, +2%)
```

### 關鍵成就

#### 1. 核心工作流程函式已完全測試
- ✅ lookup_kb_map() - KB 地圖術語匹配
- ✅ search_unmapped() - CLI 搜尋與前 5 追蹤
- ✅ hierarchical_locate() - 基於分支的發現
- ✅ cross_validate_b_and_b2() - 交集驗證
- ✅ read_context_tree() - 上下文樹讀取

#### 2. 邊緣情況處理完善
- ✅ 空/None 值處理
- ✅ 格式錯誤數據容忍
- ✅ 單字元術語跳過
- ✅ 通用術語懲罰
- ✅ 舊版 SKILL.md 格式支援

#### 3. 測試品質指標
- ✅ 100% 測試通過率（77/77）
- ✅ Mock 策略有效（subprocess/CLI）
- ✅ Fixture 結構完整（9 個共享 fixtures）
- ✅ 覆蓋率報告完善（terminal + HTML）

### 詳細完成報告

請參閱：[TESTING_PHASE2_COMPLETION.md](TESTING_PHASE2_COMPLETION.md)

---

## 階段 3 完成狀況

✅ **狀態：已完成 - 70% 覆蓋率目標達成**

階段 3 目標：**提升覆蓋率至 70%，完成 Step D/E 輔助函式測試**

### 完成的測試擴展

| 測試檔案 | 測試類別 | 新增測試數 | 覆蓋函式 | 狀態 |
|---------|--------|-----------|---------|------|
| **test_helpers.py** | TestMapDestinations | 6 | map_destinations() | ✅ 新增 |
| **test_helpers.py** | TestGetNodeById | 7 | get_node_by_id() | ✅ 新增 |
| **test_helpers.py** | TestExtractKnowledgeLines | 10 | extract_knowledge_lines() | ✅ 新增 |
| **test_helpers.py** | TestCompareKnowledge | 2 | compare_knowledge() 邊界 | ✅ 新增 |
| **總計** | **4 測試類別** | **+25** | **4 個函式** | **✅** |

### 覆蓋率進展（Phase 2 → Phase 3）

```
Phase 2 完成：         77 測試 → 60% 覆蓋率
Phase 3 第一輪：       100 測試 → 68% 覆蓋率 (+23 測試, +8%)
Phase 3 第二輪：       102 測試 → 70% 覆蓋率 (+2 測試, +2%)
累計提升：            +36% (34% → 70%)
```

### 關鍵成就

#### 1. Step D/E 輔助函式完全測試
- ✅ map_destinations() - 目標映射決策（UPDATE vs CREATE）
- ✅ get_node_by_id() - 遞迴節點查找（支援 remId/_id 變體）
- ✅ extract_knowledge_lines() - 知識行扁平化提取
- ✅ compare_knowledge() - 邊界條件處理

#### 2. 複雜邏輯覆蓋
- ✅ 父節點推斷邏輯（主題優先 → 兄弟父節點）
- ✅ 多種節點欄位變體（remId/_id, children/contentStructured）
- ✅ 深層遞迴樹遍歷（3+ 層巢狀）
- ✅ 多行內容處理（分割、過濾空行、去除空白）

#### 3. 務實的測試策略
- ✅ 對於內部導入的函式（compare_knowledge），優先測試邊界條件
- ✅ 避免過度複雜的 mock 設定（SentenceTransformer）
- ✅ 測試覆蓋率/工作量比優化（2 個測試覆蓋 ~12 行）

### 詳細完成報告

請參閱：[TESTING_PHASE3_COMPLETION.md](TESTING_PHASE3_COMPLETION.md)

---

## 階段 2 實施歷程（已廢棄）

<details>
<summary>點擊查看原始實施指南（已完成）</summary>

階段 2 目標：**完成 P0 單元測試，達成 ≥60% 單元測試覆蓋率**

### 優先級 P0 函式清單

| 函式名稱 | 當前測試數 | 需要測試數 | 優先級 | 預估時間 |
|---------|-----------|-----------|-------|---------|
| `calculate_enhanced_score()` | 7 | +3 | P0 | 30 min |
| `extract_all_rem_ids_from_tree()` | 5 | +2 | P0 | 20 min |
| `parse_kb_map()` | 4 | +3 | P0 | 30 min |
| `parse_overview()` | 4 | +2 | P0 | 20 min |
| `parse_md_to_sections()` | 4 | +2 | P0 | 20 min |
| `normalize()` | 5 | 完成 ✓ | - | - |
| `to_title_case()` | 5 | 完成 ✓ | - | - |

### 實施步驟

#### Step 1: 增強 `calculate_enhanced_score()` 測試

**目標**: 增加 3 個測試案例，覆蓋邊界條件

**新增測試**:

```python
# 在 tests/unit/test_scoring.py 的 TestCalculateEnhancedScore 類別中新增

def test_score_with_empty_aliases_and_tags(self):
    """Test scoring with explicitly empty aliases and tags lists"""
    hit = {
        "title": "Node Title",
        "aliases": [],
        "tags": []
    }
    score = calculate_enhanced_score(hit, "node", "Node", "Node Title")

    # Should still calculate base score without errors
    assert score >= 0
    assert score < SCORE_PERFECT_MATCH

def test_score_with_multiple_aliases_matching(self):
    """Test that multiple aliases don't cause duplicate bonuses"""
    hit = {
        "title": "Full Name",
        "aliases": ["FN", "FullName", "Full Name"],
        "tags": []
    }

    score1 = calculate_enhanced_score(hit, "FN", "Fn", "Full Name")
    score2 = calculate_enhanced_score(hit, "FullName", "Fullname", "Full Name")

    # Both should return SCORE_PERFECT_MATCH (alias complete match)
    assert score1 == SCORE_PERFECT_MATCH
    assert score2 == SCORE_PERFECT_MATCH

def test_score_generic_term_with_other_boosts(self):
    """Test that generic term penalty is applied even with aliases/tags"""
    hit = {
        "title": "management approach",
        "aliases": ["mgmt"],
        "tags": ["general"]
    }
    score = calculate_enhanced_score(hit, "manage", "Manage", "management approach")

    # Should be penalized despite having aliases and tags
    # Exact assertion depends on implementation details
    assert score < 5.0  # Should be significantly reduced
```

**執行測試**:

```bash
pytest tests/unit/test_scoring.py::TestCalculateEnhancedScore -v
```

---

#### Step 2: 增強 `extract_all_rem_ids_from_tree()` 測試

**目標**: 增加 2 個測試案例，測試深度嵌套與性能

**新增測試**:

```python
# 在 tests/unit/test_tree_ops.py 的 TestExtractRemIds 類別中新增

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
    assert len(ids_depth5) > len(ids_depth3)
    assert "level_4" in ids_depth5
    assert "level_4" not in ids_depth3

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
        pytest.fail("Should handle missing 'children' key gracefully")
```

**執行測試**:

```bash
pytest tests/unit/test_tree_ops.py::TestExtractRemIds -v
```

---

#### Step 3: 增強 `parse_kb_map()` 測試

**目標**: 測試 SKILL.md 向後相容性與大型檔案處理

**新增測試**:

```python
# 在 tests/unit/test_parsing.py 的 TestParseKbMap 類別中新增

def test_parse_kb_map_backward_compatibility_skill_md(self, tmp_path):
    """Test parsing legacy SKILL.md format"""
    skill_md = """  Node 1 (remId123) [Hint for node 1]
    Child 1.1 (child123) [Child hint]
  Node 2 (remId456) [Hint for node 2]"""

    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(skill_md, encoding="utf-8")

    entries = parse_kb_map(str(skill_file))

    # Should parse SKILL.md format
    assert len(entries) == 3
    # Check that indentation is preserved
    assert entries[0]["indent"] == 2
    assert entries[1]["indent"] == 4
    assert entries[2]["indent"] == 2

def test_parse_kb_map_with_special_characters(self, tmp_path):
    """Test parsing kb_map with special characters in titles"""
    kb_map = {
        "root": {"remId": "root", "title": "Root"},
        "branches": [
            {
                "remId": "b1",
                "title": "Node with (parentheses) & symbols",
                "summary": "Summary with 'quotes' and \"double quotes\"",
                "children": []
            }
        ]
    }
    kb_file = tmp_path / "test_kb_map.json"
    kb_file.write_text(json.dumps(kb_map), encoding="utf-8")

    entries = parse_kb_map(str(kb_file))

    assert len(entries) == 1
    assert "parentheses" in entries[0]["title"]
    assert "quotes" in entries[0]["hint"]

def test_parse_kb_map_large_file(self, tmp_path):
    """Test parsing large kb_map with 100+ nodes"""
    branches = []
    for i in range(100):
        branches.append({
            "remId": f"node_{i}",
            "title": f"Node {i}",
            "summary": f"Summary {i}",
            "children": []
        })

    kb_map = {
        "root": {"remId": "root", "title": "Root"},
        "branches": branches
    }
    kb_file = tmp_path / "large_kb_map.json"
    kb_file.write_text(json.dumps(kb_map), encoding="utf-8")

    entries = parse_kb_map(str(kb_file))

    # Should handle large files efficiently
    assert len(entries) == 100
```

**執行測試**:

```bash
pytest tests/unit/test_parsing.py::TestParseKbMap -v
```

---

#### Step 4: 增強 `parse_overview()` 與 `parse_md_to_sections()` 測試

**目標**: 測試邊界條件與複雜 Markdown 結構

**新增測試** (在 `tests/unit/test_parsing.py`):

```python
# TestParseOverview 類別

def test_parse_overview_with_nested_bullets(self):
    """Test overview with nested bullet structure"""
    overview = """## Overview
- **Main Topic**
  - Sub-bullet under main
  - Another sub-bullet
- Subtopic 1
- Subtopic 2"""

    result = parse_overview(overview)

    # Should handle nested structure
    assert result["topic"] == "Main Topic"
    assert len(result["subtopics"]) >= 2

def test_parse_overview_no_overview_header(self):
    """Test overview without ## Overview header"""
    overview = """- **Main Topic**
- Subtopic 1"""

    result = parse_overview(overview)

    # Should still parse without header
    assert "Main Topic" in result.get("topic", "")


# TestParseMdToSections 類別

def test_parse_sections_with_empty_sections(self):
    """Test parsing with some empty sections"""
    md = """- **Section A**
  - Content here

- **Section B**

- **Section C**
  - More content"""

    sections = parse_md_to_sections(md)

    # Should handle empty sections
    assert "Section A" in sections
    assert "Section C" in sections

def test_parse_sections_with_nested_bold(self):
    """Test parsing with nested bold markers"""
    md = """- **Section A**
  - Point with **emphasized** text
  - Another point"""

    sections = parse_md_to_sections(md)

    # Should parse correctly despite nested bold
    assert "Section A" in sections
```

**執行測試**:

```bash
pytest tests/unit/test_parsing.py::TestParseOverview -v
pytest tests/unit/test_parsing.py::TestParseMdToSections -v
```

---

### 驗證覆蓋率

完成所有 P0 測試後，執行覆蓋率檢查：

```bash
# 執行所有單元測試並生成覆蓋率報告
pytest tests/unit/ --cov=smart_logic_v5 --cov-report=html --cov-report=term

# 檢視 HTML 報告
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
```

**目標覆蓋率**: ≥60% (階段 2), ≥80% (最終目標)

---

## 測試撰寫範例

### 單元測試範本

```python
import pytest
from smart_logic_v5 import function_to_test

@pytest.mark.unit
class TestFunctionName:
    """Test suite for function_to_test()"""

    def test_basic_functionality(self):
        """Test basic expected behavior"""
        result = function_to_test(input_data)
        assert result == expected_output

    def test_edge_case_empty_input(self):
        """Test handling of empty input"""
        result = function_to_test("")
        assert result is not None

    def test_error_handling(self):
        """Test that invalid input raises appropriate error"""
        with pytest.raises(ValueError):
            function_to_test(invalid_input)
```

### 整合測試範本

```python
import pytest
from unittest.mock import patch, MagicMock
from smart_logic_v5 import function_with_external_dependency

@pytest.mark.integration
class TestIntegrationWorkflow:
    """Test suite for workflow involving external dependencies"""

    @patch('smart_logic_v5.subprocess.run')
    def test_workflow_success(self, mock_subprocess):
        """Test successful workflow with mocked CLI"""
        # Setup mock
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='{"result": "success"}'
        )

        # Execute
        result = function_with_external_dependency(args)

        # Verify
        assert result is not None
        mock_subprocess.assert_called_once()

    @patch('smart_logic_v5.subprocess.run')
    def test_workflow_failure_handling(self, mock_subprocess):
        """Test error handling when CLI fails"""
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stderr="Error message"
        )

        result = function_with_external_dependency(args)

        # Should handle error gracefully
        assert "error" in result or result is None
```

---

## 常見問題排解

### Q1: 測試執行失敗 - "smart_logic_v5.py not available"

**原因**: 測試無法導入 `smart_logic_v5.py` 模組

**解決方案**:

```bash
# 確保在專案根目錄執行測試
cd C:\Users\a0301\Documents\Projects\Antigravity_test

# 確認 smart_logic_v5.py 存在
ls smart_logic_v5.py

# 執行測試
pytest tests/
```

---

### Q2: 測試通過但覆蓋率為 0%

**原因**: Coverage 未正確追蹤程式碼執行

**解決方案**:

```bash
# 使用 --cov 參數指定程式碼來源
pytest tests/ --cov=smart_logic_v5 --cov-report=term

# 或使用 pytest.ini 配置（已設定）
pytest tests/
```

---

### Q3: Mock 不生效 - 測試仍呼叫實際 CLI

**原因**: Mock 路徑錯誤或 patch 位置不正確

**解決方案**:

```python
# ❌ 錯誤 - Patch 原始模組
@patch('subprocess.run')
def test_wrong(mock_run):
    ...

# ✅ 正確 - Patch 被測試模組中的 import
@patch('smart_logic_v5.subprocess.run')
def test_correct(mock_run):
    ...
```

---

### Q4: Fixture 無法使用 - "fixture not found"

**原因**: Fixture 定義在錯誤的 conftest.py 位置

**解決方案**:

```bash
# Fixture 應定義在 tests/conftest.py（已正確設定）
# 如果仍有問題，檢查 pytest.ini 中的 testpaths

# 驗證 fixture 可用
pytest --fixtures tests/
```

---

### Q5: 測試太慢 - 如何加速？

**解決方案**:

```bash
# 1. 只執行特定標記的測試
pytest -m unit           # 只執行單元測試（通常較快）
pytest -m "not slow"     # 跳過標記為 slow 的測試

# 2. 使用多核心執行（需要 pytest-xdist）
pip install pytest-xdist
pytest -n auto

# 3. 停用覆蓋率（測試開發階段）
pytest tests/ --no-cov
```

---

## 下一步行動

### 本週任務 (Week 2)

1. ✅ **完成階段 1** - 測試框架建設
2. ⚪ **執行階段 2** - 增強 P0 單元測試
   - [ ] 增強 `calculate_enhanced_score()` 測試 (+3 tests)
   - [ ] 增強 `extract_all_rem_ids_from_tree()` 測試 (+2 tests)
   - [ ] 增強 `parse_kb_map()` 測試 (+3 tests)
   - [ ] 增強 `parse_overview()` 測試 (+2 tests)
   - [ ] 增強 `parse_md_to_sections()` 測試 (+2 tests)
3. ⚪ **驗證覆蓋率** - 達成 ≥60% 單元測試覆蓋率

### 下週任務 (Week 3)

4. ⚪ **階段 3** - 增強整合測試
   - [ ] 增強 `search_unmapped()` 整合測試
   - [ ] 增強 `hierarchical_locate()` 整合測試
   - [ ] 新增 `cross_validate_b_and_b2()` 整合測試
   - [ ] 新增 `lookup_kb_map()` 完整流程測試

5. ⚪ **階段 4** - 達成 ≥80% 單元測試覆蓋率

---

## 測試最佳實務提醒

### ✅ DO - 應該做

- ✅ 每個測試只測一個功能點
- ✅ 使用清晰的測試名稱描述測試內容
- ✅ 測試邊界條件與錯誤處理
- ✅ 使用 fixtures 共享測試資料
- ✅ 定期執行覆蓋率檢查

### ❌ DON'T - 不應該做

- ❌ 測試依賴執行順序
- ❌ 測試內修改全域狀態
- ❌ 使用硬編碼的絕對路徑
- ❌ 測試過度依賴實際外部資源
- ❌ 忽略測試失敗訊息

---

## 聯繫與支援

如有測試相關問題，請參考：

- **測試策略文檔**: [TESTING_BLUEPRINT.md](../TESTING_BLUEPRINT.md)
- **測試 README**: [tests/README.md](./README.md)
- **配置指南**: [CONFIGURATION.md](../CONFIGURATION.md)
- **Pytest 官方文檔**: https://docs.pytest.org/

---

**文件版本**: 1.0
**最後更新**: 2026-05-03
**階段狀態**: 階段 1 完成 ✅ | 階段 2 準備中 ⚪
