# RemNote CLI 本地測試指南

## 目前狀態

✅ **RemNote CLI 已安裝** - 版本 0.13.0
✅ **Daemon 已啟動** - WS Port: 3002, Control Port: 3100
⚠️ **需要 RemNote Plugin 連接** - 請參考下方設定步驟

---

## 必要條件

### 1. 安裝 RemNote 應用程式

選擇以下任一方式：

**選項 A: 桌面應用程式**
- 下載: https://www.remnote.com/download
- 安裝並登入您的 RemNote 帳號

**選項 B: 瀏覽器擴展**
- Chrome/Edge: https://chrome.google.com/webstore (搜尋 "RemNote")
- 登入 RemNote Web 版: https://www.remnote.com

### 2. 安裝 RemNote Bridge Plugin

在 RemNote 中：
1. 開啟設定（Settings）
2. 找到 Plugins 或 Extensions
3. 搜尋並啟用 "RemNote Bridge" 或 "RemNote CLI Bridge"
4. 確認 plugin 顯示為 "Connected"

### 3. 驗證連接

```powershell
# 檢查連接狀態
npx remnote-cli status

# 預期輸出（成功）:
# {
#   "connected": true,
#   "version": "...",
#   "user": "..."
# }
```

---

## 測試流程

### 階段 1: 基本功能測試

```powershell
# 1. 搜尋測試
npx remnote-cli search "test" --limit 5

# 2. 建立測試 note
npx remnote-cli create "Test CLI Integration" --content "This is a test from CLI"

# 3. 讀取 note（使用上一步返回的 remId）
npx remnote-cli read <rem-id> --depth 2
```

### 階段 2: E2E Pipeline 測試

建立測試資料：

```powershell
# 建立測試目錄
New-Item -ItemType Directory -Force -Path .agents/tmp

# 建立 overview.md
@"
## Overview
- Ophthalmology
- Glaucoma
- Diabetic Retinopathy
"@ | Out-File -Encoding utf8 .agents/tmp/overview.md

# 建立 answer.md
@"
- **Glaucoma**
  - IOP management with prostaglandin analogs
  - Trabeculectomy surgical technique
  - Visual field monitoring protocols

- **Diabetic Retinopathy**
  - Classification: non-proliferative vs proliferative
  - Anti-VEGF injection protocols
  - Laser photocoagulation indications
"@ | Out-File -Encoding utf8 .agents/tmp/answer.md
```

執行 smart_logic_v5.py pipeline：

```powershell
python smart_logic_v5.py `
  --kb-map ".github/skills/remnote-kb-navigation/kb_map.json" `
  --overview-file ".agents/tmp/overview.md" `
  --content-file ".agents/tmp/answer.md"
```

### 階段 3: 真實整合測試（需要 RemNote 連接）

```powershell
# 搜尋現有知識
npx remnote-cli search "Glaucoma" --json

# 讀取特定 Rem
npx remnote-cli read <rem-id> --depth 3 --json

# 更新 Rem（追加內容）
$deltaContent = "- New treatment protocol`n- Updated guidelines"
$deltaContent | Out-File -Encoding utf8 .agents/tmp/delta_test.md
npx remnote-cli update <rem-id> --append-file ".agents/tmp/delta_test.md"

# 建立新 Rem
npx remnote-cli create --parent <parent-rem-id> --title "Test Topic" --content-file ".agents/tmp/new_test.md"
```

---

## 模擬測試（無需 RemNote 連接）

如果暫時無法設定 RemNote 連接，可使用 Mock 測試：

```powershell
# 執行 E2E 測試（使用 Mock）
pytest tests/e2e -v

# 測試特定功能
pytest tests/integration/test_cli_interactions.py -v

# 檢查覆蓋率
pytest tests/ --cov=smart_logic_v5 --cov-report=term
```

---

## 常見問題排解

### 問題 1: "Cannot connect to daemon"

**解決方案：**
```powershell
# 啟動 daemon
npx remnote-cli daemon start

# 驗證 daemon 執行
npx remnote-cli daemon status
```

### 問題 2: "RemNote plugin not connected"

**檢查清單：**
1. ✅ RemNote 應用程式已開啟並登入
2. ✅ RemNote Bridge Plugin 已安裝
3. ✅ Plugin 顯示為 "Connected" 或 "Active"
4. ✅ 防火牆允許 localhost:3002 和 3100

**重啟步驟：**
```powershell
# 停止 daemon
npx remnote-cli daemon stop

# 重新啟動
npx remnote-cli daemon start

# 檢查狀態
npx remnote-cli status
```

### 問題 3: 搜尋或讀取失敗

**調試：**
```powershell
# 使用 verbose 模式
npx remnote-cli --verbose search "test"

# 檢查錯誤訊息
npx remnote-cli status

# 確認 remId 格式正確（通常是長字串）
```

---

## 整合測試檢查清單

在執行完整 NotebookLM → RemNote workflow 前，請確認：

- [ ] RemNote CLI daemon 已啟動
- [ ] RemNote plugin 連接成功（`status` 顯示 connected: true）
- [ ] 可成功執行 `search` 命令
- [ ] 可成功執行 `read` 命令
- [ ] `kb_map.json` 已正確配置
- [ ] `.agents/tmp/` 目錄已建立
- [ ] smart_logic_v5.py 測試通過（88% 覆蓋率）

---

## 下一步

**如果 RemNote 已連接：**
1. 執行上述「階段 2: E2E Pipeline 測試」
2. 驗證 JSON 輸出包含正確的 `auto_actions`
3. 手動執行 `update` 或 `create` 命令測試
4. 在 RemNote 中確認更改

**如果暫時無法連接：**
1. E2E 測試已驗證 pipeline 邏輯（88% 覆蓋率）
2. 可先完善測試覆蓋率（目標 90%+）
3. 待 RemNote 連接後再進行真實整合驗證

---

## 參考資源

- [RemNote CLI GitHub](https://github.com/remnoteio/remnote-cli)
- [RemNote API 文檔](https://www.remnote.com/api)
- [測試報告](TESTING_PHASE4C_COMPLETION.md)
- [RemNote Daemon 設定指南](REMNOTE_DAEMON_SETUP.md)
