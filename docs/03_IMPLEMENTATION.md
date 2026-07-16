# v1.15 實作摘要 — SQLite 中間層

## 變更檔案

| 檔案 | 變更 |
|------|------|
| `Dashboard/aggregate.py` | 新增 `_init_schema()`, `_import_csv()`; 改寫 `aggregate()` 核心邏輯為 SQLite |
| `Dashboard/server.py` | `CACHE_DIR` 新增 `DB_PATH`; `get_summary()` 簡化（無 intermediate dict） |
| `Dashboard/ugame-dashboard.service` | `ProtectSystem=strict` → `full`（SQLite DB 需要可寫路徑） |
| `tests/test_aggregate.py` | 新增 9 項 SQLite 整合測試 |

## 架構

```
OSS CSV → _import_csv(conn) → INSERT OR IGNORE → SQLite (data.db)
                                                       ↓
                                              SQL GROUP BY 聚合
                                                       ↓
                                              rev{}, cp{} → 日常/月/週輸出
```

- SQLite DB 放在 `/usr/local/src/Dashboard/data.db`
- 5 張表：bets / charges / changes / members / activities
- `INSERT OR IGNORE` 以原始單號去重
- 記憶體用量從 G 級降到 ~30MB（僅聚合結果 JSON）

## 測試結果

42 passed（33 原有 + 9 新增 SQLite 整合測試）
