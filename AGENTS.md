1. EXCEL 文檔要注意欄位寬度大小以及考慮閱讀便利性
2. 任何文檔更動時，要以版本迭代的方式進行，並且文檔迭代要以 v1.0, v1.1 ...etc 方式命名
3. 博彩遊戲類別區分：真人視訊、老虎機、棋牌、體育、彩票、U獨家（CG Labs）
4. 業務邏輯公式：
   - 會員輸贏 = 派彩金額 - 投注金額（正數=會員贏，負數=會員輸）
   - 平台輸贏 = 投注金額 - 派彩金額（正數=平台贏，負數=平台輸）
   - 淨輸贏(平台) = 投注金額 - 派彩金額 - 彩金 - 返水
   - 有效投注金額 = 有效打碼，但不等同投注金額（已按RTP折算）
5. 日期格式：yyyy-mm-dd；如帶時間則為 yyyy-mm-dd HH:MM:SS（24小時制）
6. 電子老虎機的遊戲因為有免費旋轉所以投注金額可以是 0
7. 有效投注(有效打碼) 必須小於或等於投注金額
8. 派彩金額必須是大於或等於 0
9. 相同的遊戲供應商，三方平台的注單單號必須是唯一值
10. 我方平台的注單單號必須是系統唯一值
11. 返水比例大都是有效打碼的 0% 到 2% 之間。
12. 數據統計日規則：
   - 注單統計日 = 注單結算日期時間（派彩日期時間），非投注日期時間
   - 充值提現統計日 = 交易單完成的日期時間（完成時間），非申請時間
13. 報表數字格式：
   - 金額類：小數點後 2 位（如 1,234.56）
   - 人數/筆數/單量等計數類：整數（如 1,234）
14. 期末餘額 − 期初餘額 = 所有帳變金額總和
15. 帳變中的充值提現的關聯單號，必須可以對應到充值提現明細的單號
16. 帳變中的遊戲的關聯單號，必須可以對應到注單明細中的本平台單號或是三方平台單號
17. 派彩时间一定大於或等於投注时间


# AI 協同開發流程

## 階段流程

共 8 個階段，循序執行，不可跳過。

| Phase | 名稱 | 執行者 | 產出 |
|-------|------|--------|------|
| 0 | 需求釐清 | AI | `docs/00_CLARIFICATION.md` |
| 1 | 產品發想 | 我 | `docs/01_PRD.md` |
| 2 | 產品設計 | 我 + AI | `docs/02_DESIGN.md` + `docs/prototype/design.html` |
| 3 | 功能開發 + UT | AI | `src/` + `tests/`（unit test，全部必須通過）|
| 4 | Code Review | AI | `docs/04_REVIEW.md` |
| 5 | 回歸測試 | AI | `docs/05_TEST_PLAN.md` + `docs/05_QA_REPORT.md` |
| 6 | 功能驗證 | AI | `docs/06_VERIFICATION.md` |
| 7 | 用戶驗收 | 我 | 簽核 / 退回 |

## 啟動規則

AI 每次啟動時：

1. 讀取 `docs/STATUS.md`，確認當前在哪一階段
2. 對 STATUS.md 標記為 `⏳`（進行中）的階段，跑 `git log --oneline` 確認前方所有文檔有 commit 紀錄
3. 若前方文檔未更新 → 擋住並告知「前方文檔無更新，請先完成 Phase N」
4. 若前方文檔已更新 → 逐一讀取前方文檔後開始執行
5. 若這是 Phase 0 或使用者下了沒有階段脈絡的新指令 → 輸出你的理解 + 假設 + 模糊點（見下方 Phase 0），等你確認後才繼續
6. 使用 `skill` 工具掃描可用 skills，載入與當前階段匹配的 skills（參考 Phase Skill Binding）

## 階段轉換規則

| 轉換 | 上階段執行者 | 觸發方式 |
|------|-------------|---------|
| Phase 0 → 1 | AI | 我說「確認」或「進 phase 1」或描述 PRD 意圖 |
| Phase 1 → 2 | 我 | 我說「進 phase 2」 |
| Phase 2 → 3 | 我 + AI | 我說「進 phase 3」 |
| Phase 3 → 4 | AI | **AI 自動觸發** |
| Phase 4 → 5 | AI | **AI 自動觸發** |
| Phase 5 → 6 | AI | **AI 自動觸發** |
| Phase 6 → 7 | AI | AI 更新 STATUS.md，等我說「驗收」 |

## 完成動作

每個階段完成時 AI 須做：

1. **commit** 本階段所有產出到 git
2. **更新** `docs/STATUS.md`：該階段設為 ✅，下一階段設為 ⏳
3. **告知**我當前已完成，並提示下一階段名稱

## Phase 0 — 需求釐清

Phase 0 是強制性的釐清步驟，每當有新任務、請求或指令到來時自動啟動。**AI 必須先釐清再行動。**

### 步驟 1 — 輸出理解

撰寫 `docs/00_CLARIFICATION.md`，包含三個區塊：

**我對目標的理解：**
- 最終要達成的結果是什麼？
- 目標對象是誰？
- 要解決什麼問題？

**我的假設：**
- 技術選擇、限制、取捨
- 範圍邊界（包含什麼、明確排除什麼）
- 我自行替你決定的隱含假設

**盲點 / 模糊點：**
- 我不確定的項目，明確列出
- 需要你輸入的開放性問題
- 矛盾或不完整的資訊

### 步驟 2 — 等待確認

停下來，將釐清文件呈現給你。在收到你的確認或修正之前，**不得採取任何實作行動**。

- 若你確認 → 進入 Phase 1（或當前階段）
- 若你修正 → 更新 `docs/00_CLARIFICATION.md`，再次等待確認
- 若任務極為瑣碎（如「修正一個 typo」）→ 用一行話帶過即可跳過 Phase 0

### 關卡

**在你確認 AI 的理解之前，不得進行任何功能開發、設計或程式碼編輯。**

## Phase 3 環境建置

進入 Phase 3 時，AI 必須先建立開發環境才能開始寫程式：

### 步驟 1 — 檢測

讀取 `02_DESIGN.md` 與專案檔案，判斷語言、框架、套件管理器與測試框架。

### 步驟 2 — 初始化

若專案尚未初始化：
- 建立 `package.json`、`pyproject.toml`、`Cargo.toml`、`pom.xml` 或對應檔案
- 透過對應的套件管理器安裝相依套件（npm、pip/uv、cargo、maven/gradle 等）
- 配置測試框架（vitest、jest、pytest、cargo test、JUnit 等）
- 用一個簡單的通過測試確認測試執行器可正常運作

### 步驟 3 — TDD 循環

每個功能單元：
1. 寫一個會失敗的測試
2. 寫最少程式碼讓它通過
3. 執行測試確認通過
4. 重構（若需要）

開發環境必須保持可運作 — 任何時候 `test` 指令都能正常執行。

## Phase 4 Code Review

進入 Phase 4 時，AI 必須在真實開發環境中驗證程式碼，再進行 review：

### 步驟 1 — 建置與測試

在 Phase 3 建立的開發環境中執行：
- 建置/編譯專案（`npm run build`、`mvn compile`、`cargo build` 等）
- 執行 Phase 3 的所有 unit test — 必須全部通過
- 檢查 lint 或型別錯誤

### 步驟 2 — Review

載入 `/review` skill（以及語言相關的 review skills）後分析：
- 程式正確性、安全性問題、邊界條件
- 與 DESIGN.md 的一致性
- 測試覆蓋率 — 測試是否有意義，而非只是空殼
- 文件完整性

### 步驟 3 — 產出報告

撰寫 `docs/04_REVIEW.md`，包含：
- 建置與測試結果摘要
- 發現的問題，依嚴重程度排序
- 若建置或測試失敗 → 將 STATUS.md 中 Phase 3 標為 ⏳，擋住流程

## Phase 5 測試關卡

Phase 5 是硬關卡 — 測試沒全過就不能進 Phase 6。

### 步驟 1 — 設計測試計畫

AI 讀取 `02_DESIGN.md`（設計規格）與 `src/` + `tests/`（實作），撰寫 `docs/05_TEST_PLAN.md`，涵蓋：

- 根據 DESIGN.md 推導的功能測試案例
- 邊界條件、錯誤路徑
- 元件之間的整合點
- 回歸測試範圍

### 步驟 2 — 執行

AI 執行所有測試：
- Phase 3 的 unit test
- 步驟 1 設計的整合測試
- 端到端流程

### 關卡

- **全部通過** → 更新 STATUS.md，進 Phase 6
- **任一失敗** → AI 將 STATUS.md 中 Phase 3 標為 ⏳ 並註明失敗項目，擋住流程。我說「進 phase 3」修正後，重跑 Phase 4 → 5

## 回溯修正

任何階段發現問題時：

1. AI 更新 STATUS.md：需要修正的階段改為 ⏳，註明原因
2. 告知我哪些階段需要重新執行
3. 我確認後說「進 phase N」，AI 讀取前方所有文檔 + review/report/test plan 文檔後開始修正
4. 修正完成 commit → 更新 STATUS.md ✅
5. 重新執行後續階段（Phase 4 → 5 → 6）

**Phase 5 測試失敗**一律退回 Phase 3（需修正實作）。修正後重跑 Phase 4 → 5（含測試設計關卡）。

## 目錄結構

```
docs/
├── STATUS.md               ← 階段狀態追蹤
├── 00_CLARIFICATION.md     ← Phase 0 產出（理解 + 假設 + 模糊點）
├── 01_PRD.md               ← Phase 1 產出
├── 02_DESIGN.md            ← Phase 2 產出
├── prototype/
│   └── design.html         ← Phase 2 HTML 原型
├── 03_IMPLEMENTATION.md    ← Phase 3 AI 自產摘要
├── 04_REVIEW.md            ← Phase 4 產出
├── 05_TEST_PLAN.md         ← Phase 5 測試設計
├── 05_QA_REPORT.md         ← Phase 5 測試結果
└── 06_VERIFICATION.md     ← Phase 6 產出
src/                        ← Phase 3 產出
tests/                      ← Phase 3 產出
```

## 流程示意

```
[AI] Phase 0 ──確認──→ [我] Phase 1 ──我說──→ [我+AI] Phase 2 ──我說──→ [AI] Phase 3
                                                        │ 自動
                                                        v
                                                [AI] Phase 4
                                                        │ 自動
                                                        v
                                            ┌── [AI] Phase 5 ──┐
                                            │  測試設計關卡      │
                                            └─── 全部通過? ─────┘
                                             yes│        │no (→ P3)
                                                v
                                        [AI] Phase 6
                                                │ AI 告知完成
                                                v
                                        [我] Phase 7 ──簽核通過──→ 結案
                                                │
                                                └──退回→ 回溯修正 Phase N
```

## Phase Skill Binding

每個階段開始時，掃描可用 skills 並透過 `skill` 工具載入匹配的 skills。舉例來說，如果測試相關 skills（如 playwright）存在，優先使用而非自己從頭做。

### gstack skills

| Phase | 名稱 | 執行者 | gstack Skill |
|-------|------|--------|-------------|
| 0 | 需求釐清 | AI | `/spec`（原型化規格，分五階段）|
| 1 | 產品發想 | 我 | `/office-hours`（選用，AI 協助挑戰想法）|
| 2 | 產品設計 | 我 + AI | `/design-consultation` → `/design-html` |
| 3 | 功能開發 + UT | AI | `/spec` + TDD |
| 4 | Code Review | AI | `/review` |
| 5 | 回歸測試 | AI | `/qa` + `/benchmark`（測試設計 → 執行）|
| 6 | 功能驗證 | AI | `/browse` |
| 7 | 用戶驗收 | 我 | `/ship`（選用，簽核通過後部署）|

### 語言 / 框架 skills

進入 Phase 3 或 Phase 5 時，同時掃描語言相關 skills 並載入。AI 應使用這些 skill 來確保最佳實踐、設計模式與 coding standard。

| Phase | 觸發條件 | 掃描目標 |
|-------|---------|---------|
| 0 | 任何新指令 | `spec`（規格撰寫）、`brainstorming`、`skill-creator`、`doc-coauthoring` |
| 3 | 從 DESIGN.md 判斷語言/框架 | `typescript-advanced-types`、`vercel-react-best-practices`、`java-springboot`、Python skills 等 |
| 5 | 執行測試階段 | playwright、jest、pytest、`python-testing-patterns` 等 |

**規則：** 若匹配的 skill 存在且任務符合其描述，載入它並遵循其指引。不要重新實作 skill 已提供的內容。

## 行為準則

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. 先釐清再行動（先跑 Phase 0）

**Always run Phase 0 before any work.** 如果在對話中途收到新指令，且你還未確認你的理解，先執行 Phase 0 再寫任何一行程式碼。

明確說出你的假設。如果不確定，就問。
如果有多種解讀，全部列出來 — 不要默默選一個。
如果有更簡單的做法，說出來。必要時提出異議。
如果某件事不清楚，停下來。說出困惑的是什麼。提問。

如果任務真的非常簡單（「重新命名這個變數」、「修正這個 typo」），一行話帶過即可。但如果你在猶豫它算不算簡單 — 那它就不簡單 — 執行 Phase 0。

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

