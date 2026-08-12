# smart_logic_v5 測試套件

本目錄包含 `smart_logic_v5.py` 的完整測試套件，涵蓋單元測試與整合測試。

**✅ 測試狀態：136 個測試全部通過 | 75% 覆蓋率達標 | E2E 測試就緒**

## 測試統計

- **總測試數：** 136 個
- **單元測試：** 73 個
- **整合測試：** 54 個
- **E2E 測試：** 9 個 ✨新增
- **覆蓋率：** 75% (410/549 行)
- **通過率：** 100% (136/136)
- **測試進展：** 34% → 60% → 70% → 75% (+41%)
- **CI/CD：** ✅ GitHub Actions 整合完成

## 快速開始

### 安裝測試依賴

```bash
# 確保虛擬環境啟動
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
./antigravitytest-env/Scripts/Activate.ps1

# 安裝測試相關套件
pip install -r requirements-test.txt
```

### 執行測試

```bash
# 執行所有測試
pytest

# 執行特定類型的測試
pytest -m unit              # 只執行單元測試
pytest -m integration       # 只執行整合測試
pytest -m e2e               # 只執行 E2E 測試 ✨新增

# 執行特定檔案
pytest tests/unit/test_scoring.py -v
pytest tests/integration/test_workflows.py -v

# 執行特定測試
pytest tests/unit/test_scoring.py::TestNormalize::test_normalize_basic -v

# 執行並生成覆蓋率報告
pytest --cov=smart_logic_v5 --cov-report=html
pytest --cov=smart_logic_v5 --cov-report=term-missing  # 顯示未覆蓋行
```

### 檢視覆蓋率報告

```bash
# Windows
start htmlcov/index.html

# macOS/Linux
open htmlcov/index.html
```

## 測試結構

```
tests/
├── unit/                          # 單元測試 (純函式邏輯9 測試) ⬆️
│   ├── test_parsing.py           # 解析函式測試 (21 測試) ⬆️
│   ├── test_tree_ops.py          # 樹狀操作測試 (9 測試)
│   ├── test_utils.py             # 工具函式與常數測試 (4 測試)
│   ├── test_helpers.py           # Step D/E 輔助函式測試 (29 測試)
│   └── test_cli_error_handling.py # CLI 錯誤處理測試 (6 測試) ✨新增
│
├── integration/                   # 整合測試 (外部依賴 Mock)
│   ├── test_cli_interactions.py  # CLI 互動流程測試 (6 測試)
│   └── test_workflows.py         # 工作流程整合測試 (28 測試) ⬆️
│
├── e2e/                           # E2E 測試 (真實環境) ✨新增
│   ├── conftest.py               # E2E fixtures
│   ├── test_pipeline.py          # run_pipeline() E2E 測試 (6 測試)
│   ├── test_cli_entry.py         # CLI 入口測試 (3 測試)
│   └── fixtures/                 # E2E 測試資料
│       ├── e2e_kb_map.json       # E2E KB map
│       ├── e2e_overview.md       # E2E overview
│       └── e2e_content.md        # E2E content)
│   └── test_workflows.py         # 工作流程整合測試 (17 測試)
│
├── fixtures/                      # 測試資料
│   ├── kb_map_sample.json        # KB map 範例資料
│   ├── overview_sample.md        # Overview 範例
│   ├── content_sample.md         # Content 範例
│   └── mock_responses/           # Mock CLI 回應
│       ├── search_response.json
│       └── rea

- **test_cli_error_handling.py**: CLI 錯誤處理 ✨新增
  - run_cli() JSON 解析錯誤
  - 空輸出處理
  - subprocess 異常捕獲
  - Timeout 異常處理
d_response.json
│
├── conftest.py                    # Pytest 配置與共用 fixtures
└── README.md                      # 本文件
```

## 測試類型

### 單元測試 (`@pytest.mark.unit`)

測試獨立函式邏輯，無外部依賴：

- **test_scoring.py**: 評分邏輯
  - `normalize()` - 字串正規化
  - `to_title_case()` - Title Case 轉換
  - `calculate_enhanced_score()` - 增強評分演算法

- **test_parsing.py**: 解析函式
  - `parse_kb_map()` - KB map 解析
  - `parse_overview()` - Overview 解析
  - `parse_md_to_sections()` - Markdown 段落解析

- **test_tree_ops.py**: 樹狀操作
  - `extract_all_rem_ids_from_tree()` - 樹狀 ID 提取

- **test_utils.py**: 工具函式
  - 配置常數驗證
  - 輔助函式測試

### 整合測試 (`@pytest.mark.integration`)


- **test_workflows.py**: 工作流程整合 ⬆️ 28 測試
  - 階層定位錯誤處理
  - 交叉驗證邊界情境
  - 低品質搜尋結果處理
  - 分支選擇邏輯

### E2E 測試 (`@pytest.mark.e2e`) ✨新增

測試完整流程，使用真實 RemNote daemon 整合：

- **test_pipeline.py**: Pipeline E2E 測試
  - `run_pipeline()` 完整成功路徑
  - 缺少詞彙處理
  - 空 overview 處理
  - 混合結果驗證
  - 嵌入比較邏輯
  - JSON 輸出結構驗證

- **test_cli_entry.py**: CLI 入口測試
  - CLI subprocess 執行
  - 缺少參數錯誤處理
  - Timeout 選項測試

**執行 E2E 測試**:

```bash
# 需要 RemNote daemon 啟動
pytest tests/e2e -v

# 跳過需要 RemNote daemon 的測試
pytest tests/e2e -v -m "not skip"
```

詳細 RemNote daemon 設定請參考 [docs/remnote/REMNOTE_DAEMON_SETUP.md](../docs/remnote/REMNOTE_DAEMON_SETUP.md)。
測試工作流程，使用 Mock 模擬外部依賴：

- **test_cli_interactions.py**: CLI 互動
  - `run_cli()` - subprocess CLI 呼叫
  - `search_unmapped()` - 搜尋工作流程
  - `hierarchical_locate()` - 階層定位流程
  - `cross_validate_b_and_b2()` - 交叉驗證邏輯

## 共用 Fixtures

在 `conftest.py` 中定義的共用測試資料：

```python
# 基本 fixtures
fixtures_dir          # 測試資料目錄路徑
sample_kb_map         # 範例 KB map 結構
sample_overview_md    # 範例 overview markdown
sample_content_md     # 範例 content markdown

# Mock responses
mock_cli_search_response  # Mock search CLI 回應
mock_cli_read_response    # Mock read CLI 回應
sample_tree_node          # 範例樹狀節點結構

# 配置
configuration_constants   # 配置常數清單
```

## 撰寫新測試

### 單元測試範例

```python
import pytest
from smart_logic_v5 import normalize

@pytest.mark.unit
class TestNormalize:
    def test_basic_normalization(self):
        """Test basic string normalization"""
        assert normalize("Test Node") == "testnode"

    def test_empty_string(self):
        """Test empty string handling"""
        assert normalize("") == ""
```

### 整合測試範例

```python
import pytest
from unittest.mock import patch
from smart_logic_v5 import run_cli

@pytest.mark.integration
class TestRunCli:
    @patch('smart_logic_v5.subprocess.run')
    def test_cli_success(self, mock_run):
        """Test successful CLI execution"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"result": "success"}'
        )

        result = run_cli(["test", "command"])
        assert result is not None
```

## 測試命名慣例

✅ **良好的測試名稱**:
```python
def test_calculate_enhanced_score_with_aliases_boost():
    """Test that aliases existence adds WEIGHT_ALIASES_EXIST to score"""
```

❌ **不良的測試名稱**:
```python
def test_score():
    """Test score"""
```

### 命名規則

1. **函式名稱**: `test_<function_name>_<specific_scenario>`
2. **Docstring**: 清楚說明測試目的與預期行為
3. **類別名稱**: `Test<FunctionName>` 或 `Test<Feature>`

## 覆蓋率目標

| 測試類型 | 目標覆蓋率 | 當前覆蓋率 |
|---------|-----------|-----------|
| 單元測試 | ≥80% | 建立中 |
| 整合測試 | ≥70% | 建立中 |
| 關鍵路徑 | 100% | 建立中 |

## 常見問題

### Q: 為什麼有些測試被跳過？

A: 如果 `smart_logic_v5.py` 不存在或無法導入，相關測試會被標記為 `skip`。確保該檔案存在於正確路徑。

### Q: 如何 Mock remnote-cli？

A: 使用 `@patch('smart_logic_v5.subprocess.run')` 來 Mock subprocess 呼叫：

```python
@patch('smart_logic_v5.subprocess.run')
def test_cli_mock(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='...')
```

### Q: 如何測試 SentenceTransformer？

A: 使用 `@patch('smart_logic_v5.SentenceTransformer')` 來 Mock embedding model。

### Q: 測試執行很慢怎麼辦？

A: 使用標記來只執行快速測試：
```bash
pytest -m "unit and not slow"
```

## 持續整合 (未來)

目前測試僅在本地環境執行。未來可考慮整合：
- GitHub Actions
- Pre-commit hooks
- 自動覆蓋率報告

## 參考資料

- [pytest 文檔](https://docs.pytest.org/)
- [pytest-cov 使用指南](https://pytest-cov.readthedocs.io/)
- [unittest.mock 指南](https://docs.python.org/3/library/unittest.mock.html)
- [TESTING_BLUEPRINT.md](../TESTING_BLUEPRINT.md) - 完整測試策略

## 維護者

如有測試相關問題，請參考 `TESTING_BLUEPRINT.md` 或聯繫開發團隊。

---

**最後更新**: 2026-05-03
**測試框架版本**: pytest 8.0.0+
