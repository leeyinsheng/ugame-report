# v1.14 實作摘要 — 週/月統計新增到帳彩金與實際返水

## 變更檔案

### `Dashboard/aggregate.py`
- `_monthly_stats()`: entry 新增 `"到帐彩金"`、`"实际返水"`；環比清單新增對應 key
- `_weekly_stats()`: 同上

### `Dashboard/index.html`
- `MONTHLY_COLS` 插入 `['到帐彩金','m'],['实际返水','m']`（GGR 後、NGR 前）

### `tests/test_aggregate.py`
- 4 項斷言驗證到帳彩金與實際返水值

## 測試結果

33 passed
