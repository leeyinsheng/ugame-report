# 會員數據核對工具 — 設計文檔

## v1.0

### 1. 系統架構

```
┌─────────────────────────────────────────────────────┐
│                  瀏覽器                              │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │ index.html  │    │ reconcile.html           │    │
│  │ 运营数据看板 │◀──▶│ 核對頁                   │    │
│  └─────────────┘    │ - 會員 ID 輸入            │    │
│                     │ - 結果展示 (5 區塊)       │    │
│                     │ - 異常展開明細            │    │
│                     └──────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (JSON)
┌──────────────────────▼──────────────────────────────┐
│              Dashboard Server (server.py)            │
│                                                      │
│  GET /api/summary          → aggregate.py            │
│  GET /api/reconcile?id=xxx → reconcile.py            │
│                                                      │
│  Source: sources.from_env()                          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              阿里雲 OSS                               │
│  bucket: ug-reports                                  │
│  prefix: raw-data/                                   │
│                                                      │
│  檔案命名格式：                                       │
│  - 新格式: YYYY-MM-DD_報表名.csv                     │
│  - 舊格式: 報表名_YYYYMMDD.csv / 報表名_YYYYMMDD-    │
│             YYYYMMDD.csv                             │
└─────────────────────────────────────────────────────┘
```

### 2. API 設計

#### `GET /api/reconcile?member_id={id}`

**請求：**
| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| member_id | string | 是 | 會員 ID |

**回應格式：**
```json
{
  "member_id": "123",
  "member_info": {
    "name": "xxx",
    "agent": "yyy",
    "register_date": "2026-01-01",
    "total_deposit": 10000.00,
    "total_withdraw": 5000.00,
    "total_bet": 100000.00,
    "total_winlose": -5000.00
  },
  "summary": {
    "total_checks": 15,
    "passed": 13,
    "failed": 2,
    "checks_by_category": {
      "betting": { "total": 5, "passed": 4, "failed": 1 },
      "deposit_withdraw": { "total": 1, "passed": 1, "failed": 0 },
      "account_change": { "total": 3, "passed": 3, "failed": 0 },
      "rebate": { "total": 1, "passed": 1, "failed": 0 },
      "member_summary": { "total": 5, "passed": 4, "failed": 1 }
    }
  },
  "checks": {
    "A1": {
      "name": "会员输赢公式",
      "pass": true,
      "checked": 245,
      "errors": []
    },
    "A2": {
      "name": "派彩合理性",
      "pass": false,
      "checked": 245,
      "errors": [
        { "本平台单号": "U12345", "投注金额": 100, "派彩金额": -50, "問題": "派彩金額為負數" },
        { "本平台单号": "U12346", "投注金额": 200, "派彩金额": -10, "問題": "派彩金額為負數" }
      ]
    }
  },
  "stats": {
    "bet_count": 245,
    "deposit_count": 8,
    "withdraw_count": 4,
    "account_change_count": 156,
    "total_bet_amount": 150000.00,
    "total_payout": 145000.00,
    "total_winlose": -5000.00
  }
}
```

### 3. 核對邏輯詳解

#### A. 注單核對 (`reconcile.py` → `_check_betting`)

掃描日期範圍內所有注單類 CSV 檔案，過濾目標會員 ID。

| 檢查 | 實作方式 |
|------|---------|
| A1 會員輸贏 | 每筆計算 `calc = 派彩金額 - 投注金額`，比對 `會員輸贏金額` |
| A2 派彩合理性 | 檢查 `派彩金額 < 0` 的記錄 |
| A3 有效打碼 | 檢查 `有效打碼 > 投注金額` 的記錄（若投注金額 > 0） |
| A4 時間順序 | 比較 `投注日期時間` 與 `派彩日期時間` |
| A5 單號唯一 | 對 `本平台單號` 和 `三方單號` 分別統計出現次數，找出重複 |

注單類 CSV 匹配規則：
- 新格式：`*_注单明细.csv`、`*_注单明细报表.csv`
- 舊格式：`注单明细_*.csv`、`注单明细报表_*.csv`

#### B. 充值提現核對 (`_check_deposit_withdraw`)

掃描充值提現類 CSV，過濾會員 ID。
掃描帳變類 CSV，找出該會員的充值/提現類型記錄。

| 檢查 | 實作方式 |
|------|---------|
| B1 關聯單號 | 帳變記錄中 `帳變類型` 為充值/提現的 `關聯單號`，檢查是否存在於 `充值提現明細.訂單號` |

#### C. 帳變核對 (`_check_account_change`)

掃描帳變類 CSV，按時間排序。

| 檢查 | 實作方式 |
|------|---------|
| C1 遊戲關聯 | 帳變中遊戲類型的 `關聯單號` 檢查是否存在於注單的 `本平台單號` 或 `三方單號` |
| C2 餘額連續 | 按 `帳變時間` 排序，逐筆比對 `帳變後餘額` 是否等於下一筆的 `帳變前餘額` |
| C3 帳變總和 | `(末筆帳變後餘額) - (首筆帳變前餘額) = Σ(帳變金額)` |

帳變類型判斷：
- 充值/提現類型關鍵字：包含「充值」、「提現」、「存款」、「取款」
- 遊戲類型關鍵字：包含「遊戲」、「注單」、「派彩」、「投注」

#### D. 返水核對 (`_check_rebate`)

| 檢查 | 實作方式 |
|------|---------|
| D1 返水比例 | 對每筆注單計算 `返水 / 有效打碼`，檢查是否在 [0%, 2%] 範圍內 |

#### E. 會員彙總核對 (`_check_member_summary`)

讀取最新的會員資訊匯總 CSV，取得該會員的彙總資料。

| 檢查 | 實作方式 |
|------|---------|
| E1 充值總額 | `Σ(充值提現.金額 WHERE 類型=充值) vs 會員彙總.累積充值總額` |
| E2 提現總額 | `Σ(充值提現.金額 WHERE 類型=提現) vs 會員彙總.累積提現總額` |
| E3 輸贏總額 | `Σ(注單.會員輸贏金額) vs 會員彙總.輸贏累積總額` |
| E4 注單總數 | `COUNT(注單) vs 會員彙總.注單累積總數` |
| E5 有效打碼 | `Σ(注單.有效打碼) vs 會員彙總.有效打碼累積總額` |

### 4. 前端設計

#### 頁面結構

```
reconcile.html
├── Header（比照 index.html）
│   ├── U.Game 运营数据看板
│   ├── [运营看板] [数据核對] ← 分頁導航
│   └── 数据来源: OSS
├── 搜尋區域
│   └── 會員 ID 輸入框 + [核對] 按鈕
├── 結果摘要區
│   ├── 會員資訊卡片
│   ├── 統計摘要（注單/充值/提現/帳變筆數）
│   └── 核對總結（✅ N/M / ❌ N/M）
├── A. 注單核對卡片
│   ├── A1～A5 各項結果（PASS/FAIL）
│   └── 異常明細（可展開表格）
├── B. 充值提現核對卡片
├── C. 帳變核對卡片
├── D. 返水核對卡片
└── E. 會員彙總核對卡片
```

#### 設計系統

沿用 `index.html` 的 CSS 變數與風格：
- 顏色：`--blue:#1f3864; --blue2:#2f5496; --green:#1a9e6a; --red:#d6455d`
- 卡片：白色 rounded-16px 卡片，box-shadow
- 排版：max-width 520px, mobile-first
- 字體：`-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif`

### 5. 檔案異動清單

| 檔案 | 操作 | 說明 |
|------|------|------|
| `Dashboard/reconcile.py` | 新增 | 核對邏輯主體 |
| `Dashboard/server.py` | 修改 | 加入 `/api/reconcile` 路由 |
| `Dashboard/reconcile.html` | 新增 | 核對頁前端 |
| `Dashboard/index.html` | 修改 | Header 加入導航連結 |
| `Dashboard/.env` | 已修改 | OSS endpoint 修正 |
