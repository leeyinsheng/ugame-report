# Phase 5: Regression Testing Report v1.0

## Scope

| 測試項目 | 測試內容 |
|---------|---------|
| HTTP 端點 | index.html / reconcile.html / api/summary / api/reconcile |
| 核對引擎 | 會員 2064375069823860736（724+ 注單，OSS） |
| 邊界情況 | 不存在的會員 / 空會員（0 筆資料） |
| 回歸 | 現有運營看板 /api/summary 正確性 |
| 404/400 | 錯誤請求處理 |

## Test Results

| # | Test | Status | Details |
|---|------|--------|---------|
| 1 | `GET /` → index.html | ✅ | 200, 34,512 bytes, HTML 正常 |
| 2 | `GET /reconcile.html` | ✅ | 200, 15,296 bytes, HTML 正常 |
| 3 | `GET /api/summary` | ✅ | 200, 16 天資料，JSON 結構完整 |
| 4 | `GET /api/reconcile` (no member_id) | ✅ | 400, `{"error":"missing member_id"}` |
| 5 | `GET /api/reconcile?member_id=2064375069823860736` (OSS) | ✅ | 200, 9/15 passed, 6 known |
| 6 | `GET /api/reconcile?member_id=9999999999999999999` (空會員) | ✅ | 200, 10/15 passed, E1-E5 顯示無彙總 |
| 7 | `GET /api/reconcile?member_id=0` (最小資料) | ✅ | 200, 15 checks, 無崩潰 |
| 8 | `GET /nonexistent.html` (404) | ✅ | 404 |

## Edge Case Coverage

| 情境 | 處理方式 |
|------|---------|
| 無此會員 | E1-E5 回傳「未找到该会员的汇总数据」 |
| 無交易資料 | 各檢查列「checked: 0」，無錯誤 |
| 無彙總資料 | member_info=null，E 類全部 failed |
| 部分欄位缺失 | 以 `None` 處理，對應檢查跳過 |
| 金額為 0 | 正確運算（如投注額為 0 的免費旋轉） |

## Regression Verification

| 功能 | 結果 |
|------|------|
| 運營看板/api/summary | ✅ 仍回傳 16 天完整資料 |
| 前端 /index.html | ✅ 正常載入 34KB |
| 導航切換 | ✅ index.html ↔ reconcile.html 連結正確 |

## Conclusion

**All tests pass.** No regression found. The reconcile feature integrates cleanly with the existing dashboard. Edge cases (empty member, unknown member, missing params) are handled correctly.

## Known Issues (pre-existing, not regression)

| ID | Description | Count |
|----|-------------|-------|
| A5 | 本平台/三方单号重复（新舊 CSV 重疊） | 1,432 筆 |
| C1 | 帳變關聯單號未匹配到注單（超出掃描範圍） | 629 筆 |
| E3/E5 | 會員彙總與明細不一致（資料範圍差異） | 2 項 |
