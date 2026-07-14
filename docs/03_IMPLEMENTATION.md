# v1.13 實作摘要 — 週/月統計新增 GGR 指標

## 變更檔案

### `Dashboard/aggregate.py`
- `_monthly_stats()`: 新增 `"ggr"` 暫存、累積 `m["ggr"] += bet - pay`、輸出 `"GGR"`、加入環比清單
- `_weekly_stats()`: 同上模式

### `Dashboard/index.html`
- `MONTHLY_COLS` 陣列在 `['投注总额','m']` 之後插入 `['GGR','m']`

### `tests/test_aggregate.py`
- `TestMonthlyStats.test_basic_aggregation`: 驗證 GGR = 30.0
- `TestMonthlyStats.test_huanbi_calculation`: 驗證 GGR 環比 = 100.0%
- `TestWeeklyStats.test_basic_aggregation`: 驗證 GGR = 30.0
- `TestWeeklyStats.test_wow_calculation`: 驗證 GGR 前週環比 = 50.0%

## 測試結果

33 passed
