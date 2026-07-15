# v1.14 回歸測試計畫

## 變更範圍

- `Dashboard/aggregate.py`：`_monthly_stats` / `_weekly_stats` 加入「到帳彩金」「實際返水」欄位輸出及環比
- `Dashboard/index.html`：`MONTHLY_COLS` 加入對應欄位定義
- `tests/test_aggregate.py`：8 行新增斷言

## 測試案例

### 1. 功能正確性（既有測試）

| 測試 | 驗證項目 |
|------|---------|
| `test_basic_aggregation` (月/週) | 到帳彩金 = 9.0，實際返水 = 6.0 |
| `test_huanbi_calculation` (月) | 環比中到帳彩金為 None（pv=0 除零保護） |
| `test_wow_calculation` (週) | 週同比中到帳彩金為 None（pv=0 除零保護） |
| `test_zerodiv_huanbi` / `test_zerodiv_wow` | 一般除零保護不受影響 |

### 2. 邊界條件

- 當月/週某天無彩金或返水 → `m["彩金"]` / `m["返水"]` 為 0，round(0,2)=0.00
- 空輸入（`test_empty_input` 月/週）→ 回傳空串列，不受影響
- NGR 公式一致性：`NGR = GGR - 到帳彩金 - 實際返水`，確認既有 NGR 斷言未因新欄位移動而失效

### 3. 整合測試

- 前端 `MONTHLY_COLS` 欄位順序：投注總額 → GGR → 到帳彩金 → 實際返水 → NGR → ... （11 欄）
- 週比月多一個「日期段」欄位（12 欄）
- 後端 entry 輸出欄位順序與 MONTHLY_COLS 一致

### 4. 回歸範圍

全部 33 項測試必須 PASS，無新增測試。
