# v1.15 回歸測試計畫

## 測試範圍

### 1. SQLite 整合測試（新增）

- 基本雙日聚合（投注/GGR/彩金/返水/充提/會員）
- INSERT OR IGNORE 去重
- 增量導入（僅新檔案）
- 空來源
- 月/週統計正確性
- 活動彩金快照
- 場館 TOP5

### 2. 回歸測試（原有 33 項）

所有 sub-function 測試不得退步：
- `_activity_display` (7)
- `_bonus_for` (7)
- `_monthly_stats` (6)
- `_weekly_stats` (8)
- `daypart` (4)
