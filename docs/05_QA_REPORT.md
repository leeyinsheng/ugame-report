# Phase 5 測試計畫 & QA Report (v1.7)

## 新增測試

| # | 測試 | 覆蓋點 | 結果 |
|---|------|--------|------|
| 1 | test_basic_aggregation | 跨月彙總 8 指標 + NGR 計算 | PASS |
| 2 | test_active_member_dedup | 同月跨日活躍會員 union 去重 | PASS |
| 3 | test_first_month_no_huanbi | 首月環比為空 | PASS |
| 4 | test_huanbi_calculation | 環比公式（投注、註冊、活躍） | PASS |
| 5 | test_zerodiv_huanbi | 上月為 0 時環比 None | PASS |
| 6 | test_progress_flag | 進行中 flag（today_ym 注入） | PASS |
| 7 | test_empty_input | 空數據回傳 [] | PASS |

## 既有回歸測試

| 類別 | 數量 | 結果 |
|------|------|------|
| TestActivityDisplay | 7 | PASS |
| TestBonusFor | 7 | PASS |
| **總計** | **21** | **PASS** |

## 結論

**PASS** — 0 回歸問題。
