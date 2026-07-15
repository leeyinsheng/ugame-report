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
17. 派彩时间一定大於投注时间


# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

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
