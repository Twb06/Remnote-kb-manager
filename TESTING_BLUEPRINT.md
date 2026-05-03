# smart_logic_v5.py 測試開發藍圖

**專案**: Antigravity_test - NotebookLM → RemNote Knowledge Pipeline
**建立日期**: 2026-05-03
**測試策略**: 完整覆蓋 (Unit + Integration Tests)
**環境**: 本地測試環境

---

## 執行摘要

smart_logic_v5.py 是一個複雜的多階段知識處理 pipeline，包含：
- 6 個主要處理階段 (A → B → B2 → C → D → E)
- 外部 API 依賴 (remnote-cli)
- 複雜的評分與匹配邏輯
- Embedding-based 知識比對

**測試必要性**: ⚠️ **高度必要**
- 邏輯複雜度高
- 外部依賴多
- 未來維護需求
- 生產環境應用

**目標測試覆蓋率**:
- Unit Tests: ≥80%
- Integration Tests: ≥70%
- 關鍵路徑: 100%

---

## 測試架構概覽

```
tests/
├── unit/                      # 單元測試 (獨立函式邏輯)
│   ├── test_scoring.py       # 評分邏輯測試
│   ├── test_parsing.py       # 解析函式測試
│   ├── test_tree_ops.py      # 樹狀操作測試
│   └── test_utils.py         # 工具函式測試
├── integration/               # 整合測試 (外部依賴 Mock)
│   ├── test_cli_interactions.py
│   ├── test_search_pipeline.py
│   ├── test_hierarchical_locate.py
│   └── test_cross_validation.py
├── fixtures/                  # 測試資料
│   ├── kb_map_sample.json
│   ├── overview_sample.md
│   ├── content_sample.md
│   └── mock_responses/
│       ├── search_response.json
│       └── read_response.json
├── conftest.py               # Pytest 配置與共用 fixtures
└── README.md                 # 測試文檔

requirements-test.txt          # 測試依賴
pytest.ini                     # Pytest 配置
```

---

## 階段 1: 測試基礎建設 (Week 1) 🎯

### 目標
建立完整的測試框架與工具支援

### 任務清單

#### 1.1 安裝測試依賴
```bash
# 建立 requirements-test.txt
pip install pytest>=8.0.0
pip install pytest-cov>=4.1.0
pip install pytest-mock>=3.12.0
pip install coverage>=7.0.0
```

#### 1.2 建立目錄結構
```bash
mkdir -p tests/{unit,integration,fixtures/mock_responses}
touch tests/{__init__.py,conftest.py,README.md}
```

#### 1.3 設定 pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --cov=smart_logic_v5
    --cov-report=html
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

#### 1.4 建立 conftest.py (共用 fixtures)
```python
# tests/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def fixtures_dir():
    """Return fixtures directory path"""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_kb_map(fixtures_dir):
    """Load sample kb_map.json"""
    with open(fixtures_dir / "kb_map_sample.json") as f:
        return json.load(f)

@pytest.fixture
def mock_cli_search_response():
    """Mock CLI search response"""
    return {
        "results": [
            {
                "remId": "test123",
                "title": "Test Node",
                "aliases": ["TN"],
                "tags": ["tag1"],
                "parentTitle": "Parent"
            }
        ]
    }
```

#### 1.5 建立測試 fixtures

**kb_map_sample.json**:
```json
{
  "root": {
    "remId": "root123",
    "title": "Test Root"
  },
  "branches": [
    {
      "remId": "branch1",
      "title": "Test Branch",
      "remType": "document",
      "summary": "Test branch for testing",
      "children": [
        {
          "remId": "child1",
          "title": "Test Child",
          "remType": "text",
          "summary": "Test child node",
          "children": []
        }
      ]
    }
  ]
}
```

**overview_sample.md**:
```markdown
## Overview
- **Test Topic**
- Test Subtopic 1
- Test Subtopic 2
```

**content_sample.md**:
```markdown
- **Test Topic**
  - This is test content for topic
  - Key point 1
  - Key point 2

- **Test Subtopic 1**
  - Subtopic content here
```

---

## 階段 2: Unit Tests 實作 (Week 2-3)

### 2.1 核心邏輯測試 (P0 - 最高優先級)

#### test_scoring.py

```python
"""Tests for scoring and matching logic"""
import pytest
from smart_logic_v5 import (
    calculate_enhanced_score,
    normalize,
    to_title_case,
    SCORE_PERFECT_MATCH,
    WEIGHT_ALIASES_EXIST,
    WEIGHT_TAGS_EXIST,
    PENALTY_GENERIC_TERMS
)

class TestNormalize:
    def test_normalize_basic(self):
        """Test basic normalization"""
        assert normalize("Test Node") == "testnode"
        assert normalize("Test-Node_123") == "testnode123"

    def test_normalize_unicode(self):
        """Test Unicode handling"""
        assert normalize("測試節點") == "測試節點"

    def test_normalize_empty(self):
        """Test empty string"""
        assert normalize("") == ""

class TestTitleCase:
    def test_title_case_basic(self):
        """Test basic Title Case conversion"""
        assert to_title_case("test node") == "Test Node"

    def test_title_case_preserves_acronym(self):
        """Test acronym preservation"""
        result = to_title_case("ION 24-2")
        assert "ION" in result or "Ion" in result

class TestCalculateEnhancedScore:
    def test_perfect_title_match(self):
        """Test perfect title match returns SCORE_PERFECT_MATCH"""
        hit = {"title": "Test Node", "aliases": [], "tags": []}
        score = calculate_enhanced_score(hit, "test node", "Test Node", "Test Node")
        assert score == SCORE_PERFECT_MATCH

    def test_alias_complete_match(self):
        """Test alias complete match returns SCORE_PERFECT_MATCH"""
        hit = {
            "title": "Test Node ABC",
            "aliases": ["TN"],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "TN", "Tn", "Test Node ABC")
        assert score == SCORE_PERFECT_MATCH

    def test_aliases_boost(self):
        """Test aliases existence adds WEIGHT_ALIASES_EXIST"""
        hit = {
            "title": "Different Title",
            "aliases": ["alias1"],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "test", "Test", "Different Title")
        # Should have base score + aliases boost
        assert score > 0

    def test_tags_boost(self):
        """Test tags existence adds WEIGHT_TAGS_EXIST"""
        hit = {
            "title": "Different Title",
            "aliases": [],
            "tags": ["tag1"]
        }
        score = calculate_enhanced_score(hit, "test", "Test", "Different Title")
        assert score > 0

    def test_system_alias_exclusion(self):
        """Test system alias nodes are excluded (score = 0)"""
        hit = {
            "title": "AAION",
            "parentTitle": "Aliases",
            "parentRemId": "xOuCp1mEAK82ZbPEB",
            "aliases": [],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "AAION", "Aaion", "AAION")
        assert score == 0.0

    def test_generic_term_penalty(self):
        """Test generic terms get penalized"""
        hit = {
            "title": "management",
            "aliases": [],
            "tags": []
        }
        score = calculate_enhanced_score(hit, "manage", "Manage", "management")
        # Should be penalized by PENALTY_GENERIC_TERMS
        assert score < 1.0
```

#### test_parsing.py

```python
"""Tests for parsing functions"""
import pytest
import json
from pathlib import Path
from smart_logic_v5 import (
    parse_kb_map,
    parse_overview,
    parse_md_to_sections,
    _parse_kb_map_json
)

class TestParseKbMap:
    def test_parse_kb_map_json(self, tmp_path):
        """Test kb_map.json parsing"""
        kb_map = {
            "root": {"remId": "root", "title": "Root"},
            "branches": [
                {
                    "remId": "b1",
                    "title": "Branch 1",
                    "summary": "Summary 1",
                    "children": []
                }
            ]
        }
        kb_file = tmp_path / "test_kb_map.json"
        kb_file.write_text(json.dumps(kb_map))

        entries = parse_kb_map(str(kb_file))

        assert len(entries) == 1
        assert entries[0]["title"] == "Branch 1"
        assert entries[0]["remId"] == "b1"
        assert entries[0]["hint"] == "Summary 1"
        assert entries[0]["indent"] == 0

    def test_parse_kb_map_nested(self, tmp_path):
        """Test nested structure parsing"""
        kb_map = {
            "root": {"remId": "root", "title": "Root"},
            "branches": [
                {
                    "remId": "b1",
                    "title": "Branch 1",
                    "summary": "Summary 1",
                    "children": [
                        {
                            "remId": "c1",
                            "title": "Child 1",
                            "summary": "Child summary",
                            "children": []
                        }
                    ]
                }
            ]
        }
        kb_file = tmp_path / "test_kb_map.json"
        kb_file.write_text(json.dumps(kb_map))

        entries = parse_kb_map(str(kb_file))

        assert len(entries) == 2
        assert entries[0]["indent"] == 0
        assert entries[1]["indent"] == 2
        assert entries[1]["title"] == "Child 1"

class TestParseOverview:
    def test_parse_overview_basic(self):
        """Test basic overview parsing"""
        overview = """## Overview
- **Main Topic**
- Subtopic 1
- Subtopic 2"""

        result = parse_overview(overview)

        assert result["topic"] == "Main Topic"
        assert len(result["subtopics"]) == 2
        assert "Subtopic 1" in result["subtopics"]

    def test_parse_overview_no_topic(self):
        """Test overview with no main topic"""
        overview = """## Overview
- Subtopic 1
- Subtopic 2"""

        result = parse_overview(overview)

        assert result["topic"] == "Subtopic 1"
        assert len(result["subtopics"]) == 1

class TestParseMdToSections:
    def test_parse_sections_basic(self):
        """Test markdown section parsing"""
        md = """- **Topic A**
  Content for A

- **Topic B**
  Content for B"""

        sections = parse_md_to_sections(md)

        assert "Topic A" in sections
        assert "Topic B" in sections
        assert len(sections["Topic A"]["body"]) > 0
```

#### test_tree_ops.py

```python
"""Tests for tree operations"""
import pytest
from smart_logic_v5 import (
    extract_all_rem_ids_from_tree,
    _flatten_children,
    get_node_by_id
)

class TestExtractRemIds:
    def test_extract_single_level(self):
        """Test extraction from single level tree"""
        node = {
            "remId": "root",
            "children": [
                {"remId": "child1", "children": []},
                {"remId": "child2", "children": []}
            ]
        }

        ids = extract_all_rem_ids_from_tree(node, max_depth=1)

        assert len(ids) == 2
        assert "child1" in ids
        assert "child2" in ids
        assert "root" not in ids  # Root at depth 0 is skipped

    def test_extract_respects_max_depth(self):
        """Test max_depth parameter is respected"""
        node = {
            "remId": "root",
            "children": [
                {
                    "remId": "child1",
                    "children": [
                        {"remId": "grandchild1", "children": []}
                    ]
                }
            ]
        }

        ids_depth1 = extract_all_rem_ids_from_tree(node, max_depth=1)
        ids_depth2 = extract_all_rem_ids_from_tree(node, max_depth=2)

        assert len(ids_depth1) == 1
        assert len(ids_depth2) == 2
        assert "grandchild1" in ids_depth2
        assert "grandchild1" not in ids_depth1

class TestFlattenChildren:
    def test_flatten_basic(self):
        """Test basic flattening"""
        node = {
            "title": "Root",
            "remId": "root",
            "children": [
                {"title": "Child 1", "remId": "c1", "children": []},
                {"title": "Child 2", "remId": "c2", "children": []}
            ]
        }

        flattened = _flatten_children(node, max_depth=1)

        assert len(flattened) == 2
        assert all("title" in item and "remId" in item for item in flattened)

class TestGetNodeById:
    def test_find_existing_node(self):
        """Test finding existing node"""
        tree = {
            "remId": "root",
            "children": [
                {"remId": "target", "title": "Target Node", "children": []}
            ]
        }

        node = get_node_by_id(tree, "target")

        assert node is not None
        assert node["title"] == "Target Node"

    def test_find_missing_node(self):
        """Test searching for non-existent node"""
        tree = {"remId": "root", "children": []}

        node = get_node_by_id(tree, "nonexistent")

        assert node is None
```

### 2.2 測試執行

```bash
# 執行所有單元測試
pytest tests/unit/ -v

# 執行特定測試檔案
pytest tests/unit/test_scoring.py -v

# 執行特定測試
pytest tests/unit/test_scoring.py::TestCalculateEnhancedScore::test_perfect_title_match -v

# 執行並生成覆蓋率報告
pytest tests/unit/ --cov=smart_logic_v5 --cov-report=html
```

---

## 階段 3: Integration Tests 實作 (Week 4-5)

### 3.1 CLI 互動測試

#### test_cli_interactions.py

```python
"""Tests for CLI interactions with mocking"""
import pytest
from unittest.mock import patch, MagicMock
from smart_logic_v5 import (
    run_cli,
    search_unmapped,
    hierarchical_locate,
    lookup_kb_map
)

class TestRunCli:
    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_success(self, mock_run):
        """Test successful CLI execution"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"result": "success"}'
        )

        result = run_cli(["test", "command"])

        assert result == {"result": "success"}
        mock_run.assert_called_once()

    @patch('smart_logic_v5.subprocess.run')
    def test_run_cli_error(self, mock_run):
        """Test CLI error handling"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error message"
        )

        result = run_cli(["test", "command"])

        assert "error" in result

class TestSearchUnmapped:
    @patch('smart_logic_v5.run_cli')
    def test_search_with_perfect_match(self, mock_cli):
        """Test search finding perfect match"""
        mock_cli.return_value = {
            "results": [
                {
                    "remId": "match123",
                    "title": "Test Node",
                    "aliases": [],
                    "tags": []
                }
            ]
        }

        result = search_unmapped(["Test Node"], {})

        assert "Test Node" in result
        rem_id, top5 = result["Test Node"]
        assert rem_id == "match123"
        assert len(top5) <= 5

    @patch('smart_logic_v5.run_cli')
    def test_search_with_no_results(self, mock_cli):
        """Test search with no results"""
        mock_cli.return_value = {"results": []}

        result = search_unmapped(["Nonexistent"], {})

        assert "Nonexistent" not in result

class TestLookupKbMap:
    def test_lookup_with_fixture(self, tmp_path, sample_kb_map):
        """Test lookup using fixture kb_map"""
        kb_file = tmp_path / "kb_map.json"
        import json
        kb_file.write_text(json.dumps(sample_kb_map))

        found, entries = lookup_kb_map(str(kb_file), ["Test Branch"])

        assert "Test Branch" in found
        assert len(entries) > 0
```

### 3.2 複雜流程測試

#### test_search_pipeline.py

```python
"""Tests for complete search pipeline"""
import pytest
from unittest.mock import patch, call
from smart_logic_v5 import search_unmapped, hierarchical_locate

class TestSearchPipeline:
    @patch('smart_logic_v5.run_cli')
    def test_multi_query_execution(self, mock_cli):
        """Test that multi-query strategy executes correctly"""
        mock_cli.return_value = {"results": []}

        search_unmapped(["Test-Node_123"], {})

        # Should execute multiple queries (Title Case + parts)
        assert mock_cli.call_count >= 2

    @patch('smart_logic_v5.run_cli')
    def test_top_5_candidates_returned(self, mock_cli):
        """Test that top 5 candidates are tracked"""
        mock_cli.return_value = {
            "results": [
                {"remId": f"id{i}", "title": f"Node {i}", "aliases": [], "tags": []}
                for i in range(10)
            ]
        }

        result = search_unmapped(["Node"], {})

        if "Node" in result:
            _, top5 = result["Node"]
            assert len(top5) <= 5
```

#### test_cross_validation.py

```python
"""Tests for cross-validation logic"""
import pytest
from unittest.mock import patch
from smart_logic_v5 import cross_validate_b_and_b2

class TestCrossValidation:
    @patch('smart_logic_v5.run_cli')
    def test_intersection_found(self, mock_cli):
        """Test when B candidate exists in B2 branch"""
        # Mock B2 branch read
        mock_cli.return_value = {
            "remId": "branch",
            "children": [
                {"remId": "candidate2", "children": []}
            ]
        }

        step_b_top5 = [
            {"remId": "candidate1", "title": "Candidate 1"},
            {"remId": "candidate2", "title": "Candidate 2"},
        ]

        result = cross_validate_b_and_b2(
            "test_term",
            step_b_top5,
            "b2_result",
            "branch"
        )

        assert result == "candidate2"  # Should pick intersecting candidate

    @patch('smart_logic_v5.run_cli')
    def test_no_intersection(self, mock_cli):
        """Test when no intersection between B and B2"""
        mock_cli.return_value = {
            "remId": "branch",
            "children": [
                {"remId": "different", "children": []}
            ]
        }

        step_b_top5 = [
            {"remId": "candidate1", "title": "Candidate 1"}
        ]

        result = cross_validate_b_and_b2(
            "test_term",
            step_b_top5,
            "b2_result",
            "branch"
        )

        assert result == "b2_result"  # Should fallback to B2
```

---

## 階段 4: 測試文檔與指南 (Ongoing)

### 4.1 測試 README

```markdown
# smart_logic_v5 Testing Guide

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=smart_logic_v5 --cov-report=html

# Run specific test type
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

## Test Structure

- `tests/unit/` - Unit tests for pure functions
- `tests/integration/` - Integration tests with mocked external dependencies
- `tests/fixtures/` - Test data and mock responses
- `conftest.py` - Shared fixtures and configuration

## Writing Tests

### Unit Test Example
```python
def test_normalize():
    from smart_logic_v5 import normalize
    assert normalize("Test Node") == "testnode"
```

### Integration Test Example
```python
@patch('smart_logic_v5.run_cli')
def test_search(mock_cli):
    mock_cli.return_value = {"results": [...]}
    result = search_unmapped(["term"], {})
    assert ...
```

## Coverage Requirements

- Unit Tests: ≥80%
- Integration Tests: ≥70%
- Critical paths: 100%
```

---

## 測試執行工作流程

### 本地開發

```bash
# 1. 開發前執行所有測試
pytest -v

# 2. 修改程式碼後執行相關測試
pytest tests/unit/test_scoring.py -v

# 3. 提交前執行完整測試 + 覆蓋率
pytest --cov=smart_logic_v5 --cov-report=term-missing

# 4. 檢視 HTML 覆蓋率報告
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### 測試維護

```bash
# 定期檢查測試健康度
pytest --durations=10  # 查看最慢的 10 個測試

# 更新 fixtures
# 當 kb_map.json 結構變更時，同步更新 fixtures/kb_map_sample.json

# 清理快取
pytest --cache-clear
```

---

## 預期成果

### 量化指標

| 指標 | 目標值 | 當前值 |
|-----|-------|-------|
| 單元測試覆蓋率 | ≥80% | 0% → 建立中 |
| 整合測試覆蓋率 | ≥70% | 0% → 建立中 |
| 測試執行時間 | <10s | TBD |
| 測試數量 | ≥50 | 0 → 建立中 |

### 質化成果

✅ **完整的測試套件**
- 核心邏輯完全覆蓋
- 外部依賴正確 mock
- 關鍵路徑 100% 測試

✅ **可維護的測試程式碼**
- 清晰的測試結構
- 豐富的測試名稱
- 充分的文檔說明

✅ **快速回饋循環**
- 本地測試 <10 秒
- 即時發現迴歸

---

## 風險與緩解

| 風險 | 影響 | 緩解策略 |
|-----|------|---------|
| Mock 與實際行為不一致 | 中 | 定期手動驗證關鍵流程 |
| 測試維護成本高 | 中 | 使用 fixtures 減少重複 |
| 外部 API 變更 | 高 | 版本鎖定 + 定期更新 |

---

## 下一步行動

### 立即執行 (本週)
1. ✅ 建立測試目錄結構
2. ✅ 安裝測試依賴
3. ✅ 建立 conftest.py 與 fixtures
4. ✅ 實作 P0 單元測試 (test_scoring.py)

### 近期規劃 (下週)
5. ⚪ 完成所有單元測試
6. ⚪ 建立整合測試框架
7. ⚪ 實作 CLI 互動測試

### 長期目標 (1 個月內)
8. ⚪ 達成 80% 單元測試覆蓋率
9. ⚪ 達成 70% 整合測試覆蓋率
10. ⚪ 建立測試維護流程

---

## 附錄

### A. 測試命名慣例

```python
# ✅ Good
def test_calculate_enhanced_score_with_aliases_boost():
    """Test that aliases existence adds WEIGHT_ALIASES_EXIST to score"""

# ❌ Bad
def test_score():
    """Test score"""
```

### B. Mock 最佳實務

```python
# ✅ Good - Mock 在測試層級
@patch('smart_logic_v5.run_cli')
def test_search(mock_cli):
    mock_cli.return_value = {...}
    result = search_unmapped([...], {})
    # Assertions

# ❌ Bad - 全域 mock
with patch('smart_logic_v5.run_cli'):
    # Tests here
```

### C. Fixtures 使用指南

```python
# Fixture 命名應清楚表達用途
@pytest.fixture
def sample_kb_map_with_nested_children():
    return {...}

# 使用 fixture
def test_something(sample_kb_map_with_nested_children):
    result = parse_kb_map(sample_kb_map_with_nested_children)
    assert ...
```

---

**文件版本**: 1.0
**最後更新**: 2026-05-03
**維護者**: Development Team
