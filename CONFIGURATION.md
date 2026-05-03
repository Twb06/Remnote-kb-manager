# smart_logic_v5.py Configuration Guide

本文件說明 `smart_logic_v5.py` 中所有可配置的常數參數。所有常數定義於檔案開頭的 **Configuration Constants** 區塊。

## 配置區塊位置

```python
# 位於 line 34-64
# ═════════════════════════════════════════════════════════════════════════════
# Configuration Constants
# ═════════════════════════════════════════════════════════════════════════════
```

---

## 常數分類

### 1. Search & Matching Thresholds (搜尋與匹配閾值)

控制各階段的匹配準確度要求。

| 常數名稱 | 預設值 | 說明 | 調整建議 |
|---------|--------|------|---------|
| `SCORE_PERFECT_MATCH` | `10.0` | 完美標題匹配的基礎分數 | 不建議修改 |
| `SCORE_EXACT_MATCH_BONUS` | `10.0` | 正規化後完全匹配的加分 | 不建議修改 |
| `SCORE_TITLE_CASE_BONUS` | `5.0` | Title Case 完全匹配的加分 | 可調整 (3.0-7.0) |
| `THRESHOLD_MAP_LOOKUP` | `0.5` | kb_map lookup 最低接受分數 | 降低=更寬鬆 (0.3-0.7) |
| `THRESHOLD_SEARCH_ACCEPT` | `0.6` | 搜尋結果最低接受分數 | 降低=更寬鬆 (0.4-0.8) |
| `THRESHOLD_HIERARCHICAL` | `0.5` | 階層定位最低接受分數 | 降低=更寬鬆 (0.3-0.7) |

**調整範例**：
```python
# 更嚴格的匹配（減少誤判）
THRESHOLD_SEARCH_ACCEPT = 0.75
THRESHOLD_HIERARCHICAL = 0.6

# 更寬鬆的匹配（增加召回率）
THRESHOLD_MAP_LOOKUP = 0.4
THRESHOLD_SEARCH_ACCEPT = 0.5
```

---

### 2. Scoring Weights (評分權重)

控制不同因素對最終分數的影響。

| 常數名稱 | 預設值 | 說明 | 調整建議 |
|---------|--------|------|---------|
| `WEIGHT_ALIASES_EXIST` | `2.0` | 節點有別名時的加分 | 可調整 (1.0-3.0) |
| `WEIGHT_TAGS_EXIST` | `1.0` | 節點有標籤時的加分 | 可調整 (0.5-2.0) |
| `WEIGHT_SUBSTRING_OVERLAP` | `0.5` | 子字串包含的加分 | 可調整 (0.2-1.0) |
| `PENALTY_GENERIC_TERMS` | `0.3` | 通用詞彙的懲罰係數 | 降低=更嚴格 (0.1-0.5) |

**調整範例**：
```python
# 強化別名的重要性
WEIGHT_ALIASES_EXIST = 3.0

# 降低通用詞彙的權重（更嚴格過濾）
PENALTY_GENERIC_TERMS = 0.2
```

---

### 3. CLI Parameters (CLI 參數)

控制與 remnote-cli 互動的參數。

| 常數名稱 | 預設值 | 說明 | 調整建議 |
|---------|--------|------|---------|
| `CLI_SEARCH_LIMIT` | `50` | 每次搜尋最大結果數 | 增加=更完整但慢 (30-100) |
| `CLI_BRANCH_DEPTH` | `2` | 分支讀取深度 | 增加=更深層但慢 (1-3) |
| `CLI_BRANCH_CHILD_LIMIT` | `200` | 每分支最大子節點數 | 增加=更完整但慢 (100-500) |
| `CLI_TREE_DEPTH` | `6` | 完整樹讀取深度 | 增加=更完整但慢 (4-8) |
| `CLI_CROSS_VALIDATE_DEPTH` | `2` | 交叉驗證讀取深度 | 增加=更準確但慢 (2-3) |

**調整範例**：
```python
# 效能優先（更快但可能遺漏結果）
CLI_SEARCH_LIMIT = 30
CLI_BRANCH_DEPTH = 1
CLI_BRANCH_CHILD_LIMIT = 100

# 準確度優先（更慢但更完整）
CLI_SEARCH_LIMIT = 100
CLI_BRANCH_DEPTH = 3
CLI_BRANCH_CHILD_LIMIT = 500
```

---

### 4. Embedding Thresholds (嵌入閾值)

控制 sentence embeddings 的相似度判斷。

| 常數名稱 | 預設值 | 說明 | 調整建議 |
|---------|--------|------|---------|
| `EMBED_MATCH_THRESHOLD` | `0.80` | 判定為 MATCH 的最低相似度 | 降低=更容易重複 (0.70-0.90) |
| `EMBED_NEW_THRESHOLD` | `0.30` | 判定為 NEW 的最高相似度 | 提高=更嚴格 (0.20-0.40) |

**相似度區間**：
- `>= 0.80` → **MATCH** (已存在，跳過)
- `0.30 - 0.80` → **AMBIGUOUS** (需人工確認)
- `< 0.30` → **NEW** (新內容，自動加入)

**調整範例**：
```python
# 更保守（減少自動判斷，增加人工確認）
EMBED_MATCH_THRESHOLD = 0.85
EMBED_NEW_THRESHOLD = 0.25

# 更激進（增加自動判斷，減少人工確認）
EMBED_MATCH_THRESHOLD = 0.75
EMBED_NEW_THRESHOLD = 0.35
```

---

### 5. Timeouts (超時設定)

| 常數名稱 | 預設值 | 說明 | 調整建議 |
|---------|--------|------|---------|
| `DEFAULT_TIMEOUT_SECONDS` | `60` | CLI 預設超時時間（秒） | 大KB增加 (60-180) |

---

## 快速配置場景

### 場景 1: 大型知識庫 (1000+ nodes)

```python
# 增加限制與超時
CLI_SEARCH_LIMIT = 100
CLI_BRANCH_CHILD_LIMIT = 500
CLI_TREE_DEPTH = 8
DEFAULT_TIMEOUT_SECONDS = 120
```

### 場景 2: 快速原型測試

```python
# 降低限制以加快速度
CLI_SEARCH_LIMIT = 20
CLI_BRANCH_DEPTH = 1
CLI_TREE_DEPTH = 4
THRESHOLD_SEARCH_ACCEPT = 0.5
```

### 場景 3: 高精確度要求

```python
# 提高所有閾值
THRESHOLD_MAP_LOOKUP = 0.7
THRESHOLD_SEARCH_ACCEPT = 0.75
THRESHOLD_HIERARCHICAL = 0.6
EMBED_MATCH_THRESHOLD = 0.85
PENALTY_GENERIC_TERMS = 0.2
```

### 場景 4: 高召回率要求

```python
# 降低所有閾值
THRESHOLD_MAP_LOOKUP = 0.3
THRESHOLD_SEARCH_ACCEPT = 0.4
THRESHOLD_HIERARCHICAL = 0.3
EMBED_NEW_THRESHOLD = 0.35
```

---

## 修改方式

直接編輯 `smart_logic_v5.py` 開頭的常數定義區塊：

```python
# 範例：調整搜尋閾值
THRESHOLD_SEARCH_ACCEPT = 0.7  # 改為 0.7（更嚴格）
```

修改後無需重新安裝，直接執行即可生效。

---

## 除錯建議

如果遇到問題，可以按以下順序調整：

1. **找不到節點** → 降低 `THRESHOLD_*` 系列常數
2. **誤判太多** → 提高 `THRESHOLD_*` 系列常數
3. **速度太慢** → 降低 `CLI_*_LIMIT` 和 `CLI_*_DEPTH`
4. **重複內容** → 降低 `EMBED_MATCH_THRESHOLD`
5. **遺漏新內容** → 提高 `EMBED_NEW_THRESHOLD`

---

## 版本資訊

- **建立日期**: 2026-05-03
- **適用版本**: smart_logic_v5.py
- **最後更新**: 配置常數化完成
