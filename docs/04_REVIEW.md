# Code Review — 活動彩金名稱映射

## 建置與測試結果

- **語法檢查**: ✅ 全部通過（aggregate.py / server.py / sources.py / reconcile.py）
- **單元測試**: ✅ 11/11 通過（0.02s）

## 變更範圍

### `Dashboard/aggregate.py`（核心變更）

| 行數 | 變更 | 說明 |
|------|------|------|
| 141 | 更新注釋 | 活動快照 key 從 `活動名稱` 改為 `(活動名稱, 活動ID)` |
| 150-164 | 活動解析邏輯 | 新增 `活動 ID` 欄位解析，key 改為複合 tuple |
| 388-392 | `KNOWN_ACTIVITY_NAMES` | ID→顯示名稱映射表 |
| 394-397 | `_activity_display()` | 查詢映射表，未知 ID 回退原始名稱 |
| 400-439 | `_bonus_for()` | 迭代 key 改為 tuple，透過 `_activity_display` 取得顯示名稱 |

### `tests/test_aggregate.py`（新增）

11 個測試案例，涵蓋：
- 已知 ID 映射（一般充值、首次充值）
- 未知 ID 保留原名
- 空 ID 處理
- 同名不同 ID 的活動共存
- 跨日 delta 計算
- summary 彙總計算

### `pyproject.toml`（新增）

pytest 配置，`pythonpath = ["Dashboard"]`

## 審查結果

### 正確性
- 活動 CSV 的 `活動 ID` 欄位始終存在，無相容性問題
- 複合 key `(名稱, ID)` 確保同名不同 ID 的活動不會互相覆蓋
- `_activity_display()` 對未知 key 回退原始名稱，向前相容

### 邊界條件
- 活動名稱為空 → `continue` 跳過
- 活動 ID 為空 → key 為 `(名稱, "")`，獨立儲存不受影響
- 前一日 snapshot 不存在相同 key → `prev_map.get(key, {})` 回退空 dict，delta 計算安全

### 安全性
- 無用戶輸入處理，無 SQL，無命令注入風險
- OSS 讀取為唯讀操作

### 與 DESIGN.md 一致性
- 本次迭代設計於對話中確認（無獨立 DESIGN.md 版本），實作符合需求

### 測試覆蓋率
- `_activity_display()`: 100% 分支覆蓋（已知/未知/空 ID）
- `_bonus_for()`: 無 snapshot、單一活動、同名多活動、跨日 delta、無前一日 snapshot、彙總計算
- 遺漏：實際 CSV 解析的整合測試（依賴 oss2/外部檔案），建議可新增 fixture-based 測試

## 小結

變更範圍小、風險低、測試完備。**無阻塞性問題。**
