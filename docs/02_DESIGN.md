# v1.15 設計 — SQLite 中間層（B1 方案）

## 動機

目前 `aggregate.aggregate()` 將 OSS 所有 CSV 解析進 Python dict 後再聚合：
- 14+ 天 × 每日 7+ CSV = 100+ 檔案 → 數萬筆 raw rows 全在記憶體
- ECS 3.5G RAM 下首次載入峰值 3.2G → OOM killed
- pickle 序列化/反序列化同樣耗記憶體

## 架構變化

```
Before:
  OSS CSV → iter_csv() → [全部 parse 進 dict] → 逐日聚合 → JSON
                               ↑
                        記憶體 O(原始行數) ≈ G級

After:
  OSS CSV → iter_csv() → INSERT OR IGNORE → SQLite → SQL GROUP BY → JSON
                               ↑
                         記憶體固定 ≈ 2MB (SQLite page cache)
```

SQLite 將大量明細資料放在磁碟上，只把聚合結果（每天幾 KB）載入 Python。

## SQLite Schema

```sql
-- 注单明细（去重鍵：本平台单号）
CREATE TABLE IF NOT EXISTS bets (
    id TEXT PRIMARY KEY,
    bet_date TEXT NOT NULL,
    venue TEXT DEFAULT '',
    amount REAL DEFAULT 0,
    valid_amount REAL DEFAULT 0,
    payout REAL DEFAULT 0
);

-- 充提明细（去重鍵：订单号）
CREATE TABLE IF NOT EXISTS charges (
    order_id TEXT PRIMARY KEY,
    charge_date TEXT NOT NULL,
    type TEXT DEFAULT '',
    amount REAL DEFAULT 0
);

-- 账变记录（去重鍵：流水号）
CREATE TABLE IF NOT EXISTS changes (
    flow_id TEXT PRIMARY KEY,
    change_date TEXT NOT NULL,
    raw_type TEXT DEFAULT '',
    category TEXT DEFAULT '',     -- '返水' / '彩金' / '其他'
    amount REAL DEFAULT 0
);

-- 会员快照（最新一份快照全量替換）
CREATE TABLE IF NOT EXISTS members (
    member_id TEXT,
    register_date TEXT DEFAULT '',
    first_deposit_date TEXT DEFAULT '',
    snapshot_date TEXT DEFAULT '',
    PRIMARY KEY (member_id, snapshot_date)
);

-- 活动彩金快照（去重鍵：快照日期 + 活动ID）
CREATE TABLE IF NOT EXISTS activities (
    snapshot_date TEXT,
    activity_id TEXT,
    activity_name TEXT DEFAULT '',
    triggered_amount REAL DEFAULT 0,
    credited_amount REAL DEFAULT 0,
    member_count INTEGER DEFAULT 0,
    PRIMARY KEY (snapshot_date, activity_id)
);
```

## 資料流

```
server.py:get_summary()
  │
  ├─ 1. source.signature() → 比對快取簽名
  │
  ├─ 2. 無新檔 → 回傳快取 JSON（跟現在一樣）
  │
  ├─ 3. 有新檔 → sqlite3.connect(db_path)
  │     │
  │     ├─ source.iter_csv(only_keys=new_keys)
  │     │    逐檔讀取 → INSERT OR IGNORE 進對應 table
  │     │    （同一行邏輯，只是目標從 python dict 改為 SQLite table）
  │     │
  │     ├─ SQL 聚合查詢
  │     │    SELECT bet_date,
  │     │           SUM(amount), SUM(valid_amount), SUM(payout)
  │     │    FROM bets GROUP BY bet_date ORDER BY bet_date
  │     │    → 輸出 daily_data dict
  │     │
  │     │    類似方式查 charges / changes / members / activities
  │     │
  │     ├─ 組合回目前 _aggregate_daily() / _monthly_stats() / _weekly_stats() 格式
  │     │
  │     └─ 寫入快取（簽名 + JSON）→ 回傳
```

## 變更範圍

### 1. `aggregate.py` — 核心改寫

- **函式簽名不變**：`aggregate(source, activity_source, base=None, only_keys=None)` → `(data, intermediate)`
- **內部實作**：`base` 參數改為 sqlite3.Connection（或 db_path），不再吃 dict
  - `base=None` → 建立新 DB（TRUNCATE tables）
  - `base` 為既有 Connection → 增量 INSERT，跳過已存在的 PK
- **邏輯搬遷**：`_parse_bets()`, `_parse_charges()` 等從「append to dict」改為 `INSERT OR IGNORE`
- **聚合**：新增 `_sql_daily()`, `_sql_monthly()`, `_sql_weekly()` 用 SQL GROUP BY 取代 dict 手算
- **刪除**：不再需要大型 dict（bets={}, charges={}, changes={}, member_reg={} 等）

### 2. `server.py` — 微調

- `CACHE_DIR` 改為持久化路徑（SQLite DB 需要磁碟寫入，不能放 PrivateTmp）
- 快取邏輯不變（簽名比對 + `_save_state/_load_state` 存 JSON），但 intermediate 變成 DB path

### 3. `ugame-dashboard.service` — systemd 調整

`ProtectSystem=strict` 讓 `/usr/local/src/` 唯讀，SQLite DB 無法寫入。兩個解法：

**A) 改 `ProtectSystem=full`**（最簡單）
```
ProtectSystem=full
```
- `full` 讓 `/usr/local/src/` 可寫，`/usr/` 和 `/etc/` 唯讀
- DB 放在 `/usr/local/src/Dashboard/data.db`

**B) 開獨立可寫路徑**（安全）
```
ReadWritePaths=/var/lib/ugame-dashboard/
```
- `ProtectSystem=strict` 不變，額外開一個例外
- DB 放在 `/var/lib/ugame-dashboard/data.db`

## 記憶體改善估算

| 項目 | Before | After |
|------|--------|-------|
| raw rows in memory | 數萬筆 dict entries | 0（都在 SQLite） |
| Python 記憶體 | 500MB–3.2GB | ~30MB（僅 JSON 結果） |
| SQLite page cache | — | ~2MB（預設值，可調） |
| 磁碟用量 | pickle ~100MB | SQLite ~50MB（更緊湊） |

## 不改的檔案

- `sources.py` — OSS/本地遍歷邏輯不變
- `index.html` — 前端完全不變
- `server.py` HTTP handler — `get_summary()` 簽名不變
- `tests/` — 測試邏輯不變（mock 取代 OSS，驗證聚合輸出）
- API 回傳格式 — 跟現在完全一致

## 回退計畫

改動集中在 `aggregate.py`。若 SQLite 版本有問題：
1. `git revert` aggregate.py 回到 dict 版
2. systemd 配置改回原來
3. 重啟服務即可
