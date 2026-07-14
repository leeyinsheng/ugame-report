# v1.13 回歸測試計畫

## 測試範圍

### 單元測試（共 33 項）
- `TestActivityDisplay` (7): 活動名稱映射
- `TestBonusFor` (7): 活動彩金計算邏輯
- `TestMonthlyStats` (7): 月統計彙總 + GGR 新增斷言
- `TestWeeklyStats` (9): 週統計彙總 + GGR 新增斷言
- `TestDaypart` (4): 日期格式解析

### API 驗證
- `/api/summary` 回傳 `_meta.monthly.*.GGR` 存在且值正確
- `/api/summary` 回傳 `_meta.weekly.*.GGR` 存在且值正確

### 前端驗證（部署後）
- 月統計分頁顯示 GGR 欄位
- 週統計分頁顯示 GGR 欄位
- GGR 欄位位於投注總額之後、NGR 之前
- GGR 負值顯示紅色
