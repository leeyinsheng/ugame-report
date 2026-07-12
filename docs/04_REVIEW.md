# Phase 4 Code Review (v1.7)

## 變更範圍

看板新增月統計頁籤：後端月度彙總 + 前端頁籤切換與渲染。

## 修改檔案

| 檔案 | 變更 |
|------|------|
| `Dashboard/aggregate.py` | 新增 `_monthly_stats()` 函數（月度彙總 8 項指標 + 環比）；aggregate() 內呼叫並注入 `_meta.monthly` |
| `Dashboard/index.html` | 導航列新增「月統計」頁籤；新增 `monthly_board` div；JS: `switchTab()`, `renderMonthly()` |
| `tests/test_aggregate.py` | 新增 `TestMonthlyStats` 類別 7 項測試 |

## 審查結果

### 正確性 ✅
- 月度金額：各日 sum 正確（投注、有效、派彩、彩金、返水、充值、提現）
- NGR = 月投注 − 月派彩 − 月彩金 − 月返水（用月末總額計算，等同每日 NGR sum）
- 活躍會員：union of per-day sets（跨日去重），非簡單 sum
- 環比 = (本月/上月 − 1) × 100%，上月為 0 時回傳 None
- 進行中 flag 由 `today_ym` 控制（支援測試注入）

### 邊界條件 ✅
- 空輸入 → 回傳 []
- 單月 → 環比為空 dict
- 上月值為 0 → 環比為 None（前端顯示「— 首月」）
- 當月無數據日 → 不影響彙總（get 預設值）

### 安全性 ✅
- 無外部輸入風險

### 前端 ✅
- tab 切換：hide daily board + datenav，show monthly board
- initial load 預設 daily tab
- 負值 NGR 顯示紅色

## 結論

**APPROVED** — 21 項測試全過，邊界覆蓋完整。
