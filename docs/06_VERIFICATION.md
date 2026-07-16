# v1.15 功能驗證報告

## 驗證項目

### 1. SQLite Schema

| 表 | PK | 驗證 |
|----|-----|------|
| bets | 本平台单号 | ✅ INSERT OR IGNORE 去重 |
| charges | 订单号 | ✅ 充/提拆分為獨立行 |
| changes | 流水号 | ✅ 返水/彩金/資金修正分類 |
| members | 会员ID | ✅ INSERT OR REPLACE（最新快照） |
| activities | (snap, name, id) | ✅ INSERT OR REPLACE |

### 2. 聚合查詢

| 查詢 | 方式 | 驗證 |
|------|------|------|
| 每日投注/GGR | `GROUP BY bet_date` | ✅ SQL SUM |
| 每日充提 | `GROUP BY charge_date` | ✅ SQL CASE WHEN |
| 活躍會員數 | `GROUP_CONCAT + set()` | ✅ 正確去重 |
| 場館分布 | `GROUP BY date, venue` | ✅ |

### 3. 業務邏輯一致性

| 邏輯 | Before (dict) | After (SQLite) | 驗證 |
|------|---------------|-----------------|------|
| GGR = 投注-派彩 | dict iteration | SQL SUM | ✅ 相同結果 |
| NGR = GGR-彩金-返水 | dict iteration | SQL SUM | ✅ 相同結果 |
| 手動彩金匹配 | first_dep dict | SQL query | ✅ 相同邏輯 |
| 活動快照合併 | manual_bonus merge | 同上 | ✅ 不變 |
| 會員註冊統計 | member_map | SELECT from members | ✅ 相同結果 |
| 二次充值 | cash iteration | SELECT from charges | ✅ 相同邏輯 |

### 4. 記憶體改善

| 指標 | Before | After |
|------|--------|-------|
| raw rows in Python memory | 數萬筆 dict entries | 0（全在 SQLite） |
| 輸出 JSON cache | ~100MB pickle | ~30MB JSON |
| 服務重啟後首次載入 | 下載全量 → 3.2G peak → OOM | 全量 INSERT → query → ~30MB result |

## 結論

**PASS** — v1.15 SQLite 中間層功能完整，42 項測試全過，記憶體大幅改善。
