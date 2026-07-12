# Phase 2 產品設計 — 週統計頁籤

## 概述

在現有月統計基礎上，新增「週統計」頁籤，顯示 8 項核心指標的**週度**彙總與前週環比。

## 後端設計

### `_weekly_stats(days, rev, cp, reg_by_day, fc_by_day, today=None)`

```
for each day in days:
    ym = 該日所屬 ISO 週: f"{year}-W{week:02d}"（週一至週日）
    彙總同 _monthly_stats 邏輯

每週輸出:
    週次: "2026-W27"
    日期段: "06/29 → 07/05"
    8 指標, 前週環比%, 進行中
```

**ISO 週計算**：`datetime.date.fromisoformat(d).isocalendar()[1]` → 週號（1-53）

**進行中判斷**：該週的最後一天（週日）≤ today → 已結，否則進行中

### 聚合輸出

在 `aggregate()` 中加入（同 monthly 模式）：
```python
weekly = _weekly_stats(days, rev, cp, reg_by_day, fc_by_day)
out["_meta"]["weekly"] = weekly
```

## 前端設計

### 導航列

```
[ 运营看板 | 週統計 | 月統計 ]
```

三個頁籤並列，點擊切換對應 board div。

### 週統計表格

| 週次 | 日期段 | 投注总额 | NGR | 有效打码 | 充值 | 提现 | 活跃 | 新注册 | 首充 |
|------|--------|----------|-----|----------|------|------|------|--------|------|

- 最新週在上，倒排
- 本週 ⏳ 進行中，已結 ✓
- 每格數值 + ▲/▼ 前週環比%
- 首週顯示「—」
- 橫向捲動，第一、二欄 sticky

## 檔案修改

| 檔案 | 變更 |
|------|------|
| `Dashboard/aggregate.py` | 新增 `_weekly_stats()`，aggregate() 注入 `_meta.weekly` |
| `Dashboard/index.html` | 導航列 + `weekly_board` div、`renderWeekly()`、tab 邏輯更新 |
| `tests/test_aggregate.py` | 新增 `TestWeeklyStats` 測試類 |
