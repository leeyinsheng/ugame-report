# v1.13 設計 — 週/月統計新增 GGR 指標

## 變更範圍

只有 3 個檔案會異動：

### 1. `Dashboard/aggregate.py` — 後端彙總

**`_monthly_stats()`：**
- `months` default dict 新增 `ggr` 暫存（`0.0`）
- 彙總迴圈內：`m["ggr"] += bet - pay`
- 輸出 entry 新增 `"GGR": round(m["ggr"], 2)`
- 環比清單加入 `"GGR"` key

**`_weekly_stats()`：**
- 同上模式修改

### 2. `Dashboard/index.html` — 前端表格

- `MONTHLY_COLS` 陣列在 `['投注总额','m']` 之後、`['净利润NGR','m']` 之前插入 `['GGR','m']`

### 3. `tests/test_aggregate.py` — 測試

- 既有月/週測試斷言新增 `"GGR"` 欄位驗證

## 資料流

無架構變更，純欄位追加。

## 無需改動

- `server.py` / `sources.py` — API 結構不變
- 每日看板 — GGR 已存在
- activity/bonus 邏輯 — 不受影響
