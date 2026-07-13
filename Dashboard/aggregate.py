# -*- coding: utf-8 -*-
"""
U.Game 运营数据看板 —— 原始数据聚合引擎

读取 raw-data/ 下的后台导出 CSV，按「数据统计日规则」聚合为每日运营指标。
支持的 4 种原始文件（按表头自动识别，文件名无关）：
  1. 注单明细        —— 含「派彩日期时间 / 本平台单号 / 投注金额 ...」
  2. 充提款/充提现明细 —— 含「完成时间 / 充值金额 / 提现金额 / 订单状态 ...」
  3. 账变记录报表      —— 含「账变类型 / 账变金额 / 账变时间 ...」（返水、彩金来源）
  4. 会员信息汇总报表  —— 含「注册日期时间 / 第一次充值成功的日期时间 ...」（累计快照）

统计口径（见项目 CLAUDE.md）：
  · 注单统计日 = 派彩日期时间（结算日），非投注时间
  · 充提统计日 = 完成时间，仅统计「成功」订单
  · 账变统计日 = 账变时间
去重：注单按「本平台单号」、充提按「订单号」、账变按「流水号」去重，
      因此重复 / 跨日范围文件多次上传也不会重复计算。
"""
import csv, os, re
from datetime import date, timedelta


def num(s):
    """解析金额：去千分位逗号，空 / -- / 非法 -> 0.0"""
    s = (s or "").replace(",", "").strip()
    if s in ("", "--", "-"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def daypart(s):
    """日期时间 '2026-06-22 16:24:15（美东时间）' 或 '2026/07/12 01:42:26' -> '2026-06-22'"""
    s = (s or "").strip()
    if len(s) >= 10 and s[4] in ("-", "/"):
        return s[:10].replace("/", "-")
    return ""


def pct(s):
    """'15.38%' / '100%' -> 15.38 / 100.0"""
    s = (s or "").replace("%", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def date_from_name(name):
    """活动文件内无日期字段，快照日期取自文件名：2026-06-23_活动.csv / 活动_20260623.csv"""
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", name or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


# 游戏场馆原始名 -> 看板展示名（键统一用小写匹配；不在表内的场馆原样显示）。
# WG / WG电子 等同义写法都映射到同一展示名，会自动合并为一条。
VENUE_DISPLAY = {
    "pg": "PG 电子",
    "jili slots": "JILI 电子",
    "jili poker": "JILI 棋牌",
    "jili fish": "JILI 捕鱼",
    "pp zh slots": "PP 电子",
    "wg": "WG 电子", "wg电子": "WG 电子", "wg電子": "WG 电子",
    "db_live": "DB 视讯",
    "体育": "U 体育", "體育": "U 体育",
    "qixing": "七星视讯",
    "cg labs": "U 独家",
    "six": "极光彩票",
    # 以下场馆数据中出现但未在对应表内，暂用默认名（如需改名请补充）：
    "皇冠体育": "皇冠体育", "皇冠體育": "皇冠体育",
    "沙巴体育": "沙巴体育", "沙巴體育": "沙巴体育",
}


def venue_display(name):
    raw = (name or "").strip()
    return VENUE_DISPLAY.get(raw.lower(), raw or "其他")


def _has(cols, *names):
    return all(n in cols for n in names)


def _one(cols, *names):
    """names 中任一列存在即为真（用于兼容『账变/帐变』等同义异写列名）。"""
    return any(n in cols for n in names)


def pick(row, *names):
    """取 row 中第一个存在的列值（兼容多种表头写法）；都不存在返回 None。"""
    for n in names:
        if n in row:
            return row.get(n)
    return None


def classify(cols):
    """按表头列名识别文件类型，返回类型字符串或 None。

    兼容两套后台导出格式：
      · 简体「账变…/有效投注/订单状态/充值金额」
      · 繁体或异写「帐变…/有效打码/状态/单一金额列」
    """
    cols = set(cols or [])
    if _has(cols, "派彩日期时间", "本平台单号", "投注金额"):
        return "bet"
    if _one(cols, "账变类型", "帐变类型") and _one(cols, "账变金额", "帐变金额") \
            and _one(cols, "账变时间", "帐变时间"):
        return "ledger"
    if _has(cols, "订单号", "完成时间", "类型") and _one(cols, "订单状态", "状态"):
        return "cashflow"
    if _has(cols, "注册日期时间", "第一次充值成功的日期时间"):
        return "member"
    if _one(cols, "活动名称", "活動名稱") and _one(cols, "到帐彩金总金额", "到帳彩金總金額"):
        return "activity"
    return None


def aggregate(source, activity_source=None):
    """聚合数据源中的 CSV，返回 { 'YYYY-MM-DD': {rev,mem,cp} }（按日期排序）。

    source 可以是：
      · 字符串（本地目录路径，自动包成 LocalSource）
      · 任意带 .iter_csv() 的数据源对象（LocalSource / OssSource）
    activity_source: 可选，独立的活动数据源（如 OSS 不同前缀）
    """
    if isinstance(source, str):
        from sources import LocalSource
        source = LocalSource(source)

    # 去重容器
    bets = {}        # 本平台单号 -> (派彩日, 会员ID, 投注, 有效, 派彩)
    ledger = {}      # 流水号    -> (日, 类型, 金额)
    cash = {}        # 订单号    -> (日, 充值, 提现, 会员ID)
    member_rows = None      # 取最新的会员快照（缓存其行）
    member_key = None       # 对应排序键（mtime / last_modified）
    activity_snaps = {}     # 快照日 -> {(活动名称, 活动ID): {触发,到帐,次数,触发人数,领取人数,领取率}}（累计值）

    for name, order_key, f in source.iter_csv():
        with f:
            r = csv.DictReader(f)
            kind = classify(r.fieldnames or [])
            if kind is None:
                continue
            if kind == "activity":
                snap = date_from_name(name)   # 活动文件日期取自文件名
                if snap:
                    m = activity_snaps.setdefault(snap, {})
                    for row in r:
                        nm = (pick(row, "活动名称", "活動名稱") or "").strip()
                        aid = (pick(row, "活动 ID", "活動 ID", "活動ID") or "").strip()
                        if not nm:
                            continue
                        key = (nm, aid)
                        m[key] = {
                            "触发": num(pick(row, "触发彩金总金额", "觸發彩金總金額")),
                            "到帐": num(pick(row, "到帐彩金总金额", "到帳彩金總金額")),
                            "次数": int(num(pick(row, "触发彩金总次数", "觸發彩金總次數"))),
                            "触发人数": int(num(pick(row, "触发会员总人数", "觸發會員總人數"))),
                            "领取人数": int(num(pick(row, "领取彩金会员总人数", "領取彩金會員總人數"))),
                            "领取率": pct(pick(row, "活动领取率", "活動領取率")),
                        }
                continue
            if kind == "member":
                if member_key is None or order_key > member_key:
                    member_key, member_rows = order_key, list(r)
                continue
            for row in r:
                if kind == "bet":
                    k = row.get("本平台单号") or ""
                    if not k:
                        continue
                    # 有效打码列名三种写法：有效投注 / 有效投注金额 / 有效打码
                    # 返水列名：返水 / 预计返水 / 預計返水（新导出为"返水"）
                    bets[k] = (daypart(row.get("派彩日期时间")), row.get("会员ID") or "",
                               num(row.get("投注金额")),
                               num(pick(row, "有效投注", "有效投注金额", "有效打码")),
                               num(row.get("派彩金额")),
                               num(pick(row, "返水", "预计返水", "預計返水")),
                               (pick(row, "游戏场馆", "遊戲場館") or "其他").strip() or "其他")
                elif kind == "ledger":
                    k = row.get("流水号") or ""
                    if not k:
                        continue
                    ledger[k] = (daypart(pick(row, "账变时间", "帐变时间")),
                                 (pick(row, "账变类型", "帐变类型") or ""),
                                 num(pick(row, "账变金额", "帐变金额")))
                elif kind == "cashflow":
                    # 状态列两种写法；成功口径含「成功 / 已成功 / 已完成」，排除失败
                    status = (pick(row, "订单状态", "状态") or "").strip()
                    if not ("成功" in status or "完成" in status):
                        continue
                    k = row.get("订单号") or ""
                    if not k:
                        continue
                    if "充值金额" in row or "提现金额" in row:   # 有独立充值/提现金额列
                        dep, wd = num(row.get("充值金额")), num(row.get("提现金额"))
                    else:                                        # 单一金额列：靠「类型」判方向
                        amt = num(row.get("金额")); t = row.get("类型") or ""
                        dep = amt if "充" in t else 0.0
                        wd = amt if "提" in t else 0.0
                    cash[k] = (daypart(row.get("完成时间")), dep, wd, row.get("会员ID") or "")

    # 从独立活动数据源补充活动快照
    if activity_source:
        for name, order_key, f in activity_source.iter_csv():
            with f:
                r = csv.DictReader(f)
                kind = classify(r.fieldnames or [])
                if kind != "activity":
                    continue
                snap = date_from_name(name)
                if snap:
                    m = activity_snaps.setdefault(snap, {})
                    for row in r:
                        nm = (pick(row, "活动名称", "活動名稱") or "").strip()
                        aid = (pick(row, "活动 ID", "活動 ID", "活動ID") or "").strip()
                        if not nm:
                            continue
                        key = (nm, aid)
                        m[key] = {
                            "触发": num(pick(row, "触发彩金总金额", "觸發彩金總金額")),
                            "到帐": num(pick(row, "到帐彩金总金额", "到帳彩金總金額")),
                            "次数": int(num(pick(row, "触发彩金总次数", "觸發彩金總次數"))),
                            "触发人数": int(num(pick(row, "触发会员总人数", "觸發會員總人數"))),
                            "领取人数": int(num(pick(row, "领取彩金会员总人数", "領取彩金會員總人數"))),
                            "领取率": pct(pick(row, "活动领取率", "活動領取率")),
                        }

    # ---- 按日汇总 ----
    # rev: [投注, 有效, 派彩, 实际返水(账变), 彩金, set(活跃会员), 预计返水(注单), 注单量]
    rev = {}
    cp = {}    # 日 -> [充值额, 充值笔, set(充值人), 提现额, 提现笔, set(提现人)]

    def _rev(d):
        return rev.setdefault(d, [0.0, 0.0, 0.0, 0.0, 0.0, set(), 0.0, 0])

    def _cp(d):
        return cp.setdefault(d, [0.0, 0, set(), 0.0, 0, set()])

    game = {}  # 日 -> {游戏场馆: [投注总额, 派彩总额, 有效打码, 注单量]}

    for d, mid, bet, eff, payout, est, venue in bets.values():
        if not d:
            continue
        a = _rev(d)
        a[0] += bet; a[1] += eff; a[2] += payout
        a[5].add(mid)
        a[6] += est                    # 预计返水（来自注单明细）
        a[7] += 1                      # 注单量
        gv = game.setdefault(d, {}).setdefault(venue_display(venue), [0.0, 0.0, 0.0, 0])
        gv[0] += bet; gv[1] += payout; gv[2] += eff; gv[3] += 1

    for d, t, amt in ledger.values():
        if not d:
            continue
        a = _rev(d)
        if "返水" in t:                                   # 返水 / 遊戲返水 / 游戏返水
            a[3] += amt
        elif any(w in t for w in ("活动", "活動", "彩金", "奖励", "獎勵")):  # 彩金 / 活動獎勵
            a[4] += amt

    for d, dep, wd, mid in cash.values():
        if not d:
            continue
        a = _cp(d)
        if dep > 0:
            a[0] += dep; a[1] += 1; a[2].add(mid)
        if wd > 0:
            a[3] += wd; a[4] += 1; a[5].add(mid)

    # ---- 会员快照：每日新增注册 / 首充 / 累计注册 ----
    reg_by_day = {}     # 日 -> 当日注册数
    fc_by_day = {}      # 日 -> 当日首充会员数
    firstcharge = {}    # 会员ID -> 首充日（首充留存同期群）
    regdate = {}        # 会员ID -> 注册日（注册留存同期群）
    if member_rows:
        for row in member_rows:
            mid = (pick(row, "会员ID", "会员 ID") or "").strip()
            rd = daypart(row.get("注册日期时间"))
            if rd:
                reg_by_day[rd] = reg_by_day.get(rd, 0) + 1
                if mid:
                    regdate[mid] = rd
            fd = daypart(row.get("第一次充值成功的日期时间"))
            if fd:
                fc_by_day[fd] = fc_by_day.get(fd, 0) + 1
                if mid:
                    firstcharge[mid] = fd

    # 全部出现过的运营日
    days = sorted(set(rev) | set(cp))
    monthly = _monthly_stats(days, rev, cp, reg_by_day, fc_by_day)
    weekly = _weekly_stats(days, rev, cp, reg_by_day, fc_by_day)
    # 累计注册需覆盖到每个运营日（按注册日 <= 当日累计）
    reg_days_sorted = sorted(reg_by_day)

    def cum_reg(day):
        return sum(n for rd, n in reg_by_day.items() if rd <= day)

    def cum_fc(day):   # 累计充值会员：首充日 <= 当日的会员数
        return sum(n for fd, n in fc_by_day.items() if fd <= day)

    out = {}
    cum_dep = 0.0
    cum_wd = 0.0
    for d in days:
        rv = rev.get(d, [0.0, 0.0, 0.0, 0.0, 0.0, set(), 0.0, 0])
        cv = cp.get(d, [0.0, 0, set(), 0.0, 0, set()])
        bet_t, eff_t, pay_t, fs_t, hd_t, act, est_t, bet_n = rv
        ggr = bet_t - pay_t
        ngr = ggr - hd_t - fs_t        # NGR 用实际返水(账变)，非预计返水
        active = len(act)
        cum = cum_reg(d)
        new_reg = reg_by_day.get(d, 0)
        first_charge = fc_by_day.get(d, 0)
        dep_t, dep_n, dep_p, wd_t, wd_n, wd_p = cv
        cum_dep += dep_t
        cum_wd += wd_t
        dep_people = len(dep_p); wd_people = len(wd_p)

        def safe(n, dlen):
            return round(n / dlen, 2) if dlen else 0.0

        out[d] = {
            "rev": {
                "投注总额": round(bet_t, 2), "注单量": bet_n,
                "有效打码": round(eff_t, 2),
                "派彩总额": round(pay_t, 2), "GGR": round(ggr, 2),
                "彩金": round(hd_t, 2),
                "预计返水": round(est_t, 2), "实际返水": round(fs_t, 2),
                "NGR": round(ngr, 2),
                "平台整体杀率": safe(ggr * 100, eff_t),  # = GGR/有效打码 = 平台输赢/有效打码
                "净利率": safe(ngr * 100, eff_t),
            },
            "mem": {
                "累计注册": cum, "累计充值会员": cum_fc(d),
                "注册转充值率": safe(cum_fc(d) * 100, cum),   # 累计充值会员/累计注册
                "新增注册": new_reg, "活跃会员": active,
                "首充会员": first_charge,
                "新客首充率": safe(first_charge * 100, new_reg),
                "活跃率": safe(active * 100, cum),
                "人均投注": safe(bet_t, active),
                "人均充值": safe(dep_t, dep_people),
                "ARPU": safe(ngr, active),
            },
            "cp": {
                "充值总额": round(dep_t, 2), "累计充值总额": round(cum_dep, 2),
                "充值笔数": dep_n, "充值人数": dep_people,
                "提现总额": round(wd_t, 2), "累计提现总额": round(cum_wd, 2),
                "提现笔数": wd_n, "提现人数": wd_people,
                "充提差额": round(dep_t - wd_t, 2),
                "充提比率": round(dep_t / wd_t, 2) if wd_t else 0.0,
            },
            "game": _top_games(game.get(d, {}), bet_t),
            "venue_trends": _venue_trends(game.get(d, {})),
            "bonus": _bonus_for(activity_snaps, d),
        }

    # ---- 会员留存（D1-14，经典第N日 · 充值/提现/下注任一 · 全期合并）----
    # 双口径：首充同期群 + 注册同期群
    active_days = {}            # 会员ID -> set(有活动日：投注 / 充值 / 提现)
    for d2, mid, *_ in bets.values():
        if d2:
            active_days.setdefault(mid, set()).add(d2)          # 下注
    for d2, dep, wd, mid in cash.values():
        if d2 and (dep > 0 or wd > 0):
            active_days.setdefault(mid, set()).add(d2)          # 充值 / 提现
    covered = set(days)         # 覆盖天数 = 运营日（含注单+充提）
    out["_meta"] = {
        "retention": {
            "首充": _retention(firstcharge, active_days, covered, max_n=14),
            "注册": _retention(regdate, active_days, covered, max_n=14),
        },
        "monthly": monthly,
        "weekly": weekly,
        "首充会员数": len(firstcharge),
        "注册会员数": len(regdate),
    }
    return out


def _monthly_stats(days, rev, cp, reg_by_day, fc_by_day, today_ym=None):
    """月度彙總 8 項核心指標，附環比變化。"""
    from collections import defaultdict
    from datetime import date as dt_date

    if today_ym is None:
        today_ym = dt_date.today().isoformat()[:7]

    months = defaultdict(lambda: {
        "投注额": 0.0, "派彩额": 0.0, "有效打码": 0.0,
        "彩金": 0.0, "返水": 0.0, "活跃_set": set(),
        "充值额": 0.0, "提现额": 0.0,
        "新增注册": 0, "首充会员": 0,
    })

    for d in days:
        ym = d[:7]
        m = months[ym]
        rv = rev.get(d, [0.0, 0.0, 0.0, 0.0, 0.0, set(), 0.0, 0])
        cv = cp.get(d, [0.0, 0, set(), 0.0, 0, set()])
        bet, eff, pay, fs, hd, act, _est, _bn = rv
        dep, _dpn, _dpp, wd, _wpn, _wpp = cv

        m["投注额"] += bet
        m["派彩额"] += pay
        m["有效打码"] += eff
        m["彩金"] += hd
        m["返水"] += fs
        m["充值额"] += dep
        m["提现额"] += wd
        m["活跃_set"].update(act)
        m["新增注册"] += reg_by_day.get(d, 0)
        m["首充会员"] += fc_by_day.get(d, 0)

    sorted_months = sorted(months.keys())
    result = []

    for i, ym in enumerate(sorted_months):
        m = months[ym]
        ngr = m["投注额"] - m["派彩额"] - m["彩金"] - m["返水"]
        active = len(m["活跃_set"])

        entry = {
            "月份": ym,
            "投注总额": round(m["投注额"], 2),
            "净利润NGR": round(ngr, 2),
            "有效打码": round(m["有效打码"], 2),
            "充值总额": round(m["充值额"], 2),
            "提现总额": round(m["提现额"], 2),
            "活跃会员": active,
            "新增注册": m["新增注册"],
            "首充会员": m["首充会员"],
            "环比": {},
            "进行中": ym == today_ym,
        }

        if i > 0:
            prev = result[i - 1]
            for k in ["投注总额", "净利润NGR", "有效打码", "充值总额", "提现总额",
                      "活跃会员", "新增注册", "首充会员"]:
                pv = prev[k]
                cv = entry[k]
                entry["环比"][k] = round((cv / pv - 1) * 100, 2) if pv else None

        result.append(entry)

    result.reverse()
    return result


def _weekly_stats(days, rev, cp, reg_by_day, fc_by_day, today=None):
    """週度彙總（ISO 週一至週日），附前週環比。"""
    from collections import defaultdict
    from datetime import date as dt_date, timedelta

    if today is None:
        today = dt_date.today()

    weeks = defaultdict(lambda: {
        "投注额": 0.0, "派彩额": 0.0, "有效打码": 0.0,
        "彩金": 0.0, "返水": 0.0, "活跃_set": set(),
        "充值额": 0.0, "提现额": 0.0,
        "新增注册": 0, "首充会员": 0,
    })

    for d in days:
        dt = dt_date.fromisoformat(d)
        iso = dt.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        m = weeks[wk]
        rv = rev.get(d, [0.0, 0.0, 0.0, 0.0, 0.0, set(), 0.0, 0])
        cv = cp.get(d, [0.0, 0, set(), 0.0, 0, set()])
        bet, eff, pay, fs, hd, act, _est, _bn = rv
        dep, _dpn, _dpp, wd, _wpn, _wpp = cv

        m["投注额"] += bet
        m["派彩额"] += pay
        m["有效打码"] += eff
        m["彩金"] += hd
        m["返水"] += fs
        m["充值额"] += dep
        m["提现额"] += wd
        m["活跃_set"].update(act)
        m["新增注册"] += reg_by_day.get(d, 0)
        m["首充会员"] += fc_by_day.get(d, 0)

    sorted_weeks = sorted(weeks.keys())
    result = []

    for i, wk in enumerate(sorted_weeks):
        m = weeks[wk]
        ngr = m["投注额"] - m["派彩额"] - m["彩金"] - m["返水"]
        active = len(m["活跃_set"])
        week_days = [d for d in days if d[:4] == wk[:4] and
                     dt_date.fromisoformat(d).isocalendar()[1] == int(wk[6:])]
        date_range = f"{week_days[0][5:]}" if week_days else ""
        if len(week_days) >= 2:
            date_range += f" → {week_days[-1][5:]}"

        entry = {
            "週次": wk,
            "日期段": date_range,
            "投注总额": round(m["投注额"], 2),
            "净利润NGR": round(ngr, 2),
            "有效打码": round(m["有效打码"], 2),
            "充值总额": round(m["充值额"], 2),
            "提现总额": round(m["提现额"], 2),
            "活跃会员": active,
            "新增注册": m["新增注册"],
            "首充会员": m["首充会员"],
            "前週环比%": {},
        }
        # 進行中：該週最後一天（週日）> today
        entry["进行中"] = week_days and dt_date.fromisoformat(week_days[-1]) >= today

        if i > 0:
            prev = result[i - 1]
            for k in ["投注总额", "净利润NGR", "有效打码", "充值总额", "提现总额",
                      "活跃会员", "新增注册", "首充会员"]:
                pv = prev[k]
                cv = entry[k]
                entry["前週环比%"][k] = round((cv / pv - 1) * 100, 2) if pv else None

        result.append(entry)

    result.reverse()
    return result


def _retention(cohort, active_days, covered, max_n=7):
    """经典第N日留存（充值/提现/下注任一，合并全部同期群）。
    分母=同期群日+N 当天在数据覆盖范围内的会员；分子=该日有活动的会员。"""
    if not cohort or not covered:
        return []
    maxday = max(covered)

    def parse(s):
        return date(int(s[:4]), int(s[5:7]), int(s[8:10]))

    maxd = parse(maxday)
    out = []
    for n in range(1, max_n + 1):
        num = den = 0
        for mid, base in cohort.items():
            target = parse(base) + timedelta(days=n)
            if target > maxd:
                continue                          # 未观察（截尾）
            ts = target.isoformat()
            if ts not in covered:
                continue                          # 该日无运营数据，不计入分母
            den += 1
            if ts in active_days.get(mid, ()):    # 当天有充值/提现/下注任一
                num += 1
        out.append({
            "D": n,
            "rate": round(num / den * 100, 2) if den else None,
            "num": num, "den": den,
        })
    return out


# 活动ID -> 显示名称映射
KNOWN_ACTIVITY_NAMES = {
    ("充值活动", "2064338446452465664"): "每日充值回馈",
    ("充值活动", "2072527153187643392"): "新人首充100%豪礼",
    ("充值活动", "2072532512957681664"): "每日充值回馈",
    ("负盈利", "2064364752562868224"): "老虎救援金",
    ("负盈利", "2064355390268166144"): "真人视讯转运金",
}


def _activity_display(key):
    nm, aid = key
    return KNOWN_ACTIVITY_NAMES.get(key, nm)


def _bonus_for(snaps, d):
    """活动彩金领取情况：取截至 d 的最新快照(累计)，并与前一快照相减得当日新增。"""
    if not snaps:
        return None
    dates = sorted(snaps)
    cur = None
    for sd in dates:
        if sd <= d:
            cur = sd
        else:
            break
    if cur is None:
        return None
    prev = None
    for sd in dates:
        if sd < cur:
            prev = sd
        else:
            break
    cur_map = snaps[cur]
    prev_map = snaps.get(prev, {}) if prev else {}

    merged = {}
    for key, s in cur_map.items():
        p = prev_map.get(key, {})
        display = _activity_display(key)
        g = merged.setdefault(display, {
            "到帐彩金": 0.0, "触发彩金": 0.0,
            "触发人数": 0, "领取人数": 0, "触发次数": 0,
            "当日新增到帐": 0.0, "当日新增次数": 0,
        })
        g["到帐彩金"] += s["到帐"]
        g["触发彩金"] += s["触发"]
        g["触发人数"] += s["触发人数"]
        g["领取人数"] += s["领取人数"]
        g["触发次数"] += s["次数"]
        g["当日新增到帐"] += s["到帐"] - p.get("到帐", 0.0)
        g["当日新增次数"] += s["次数"] - p.get("次数", 0)

    items = []
    tot_credit = tot_trig = 0.0
    tot_claim_people = 0
    tot_new_credit = 0.0
    for display, g in merged.items():
        credit, trig = g["到帐彩金"], g["触发彩金"]
        items.append({
            "活动": display,
            "到帐彩金": round(credit, 2), "触发彩金": round(trig, 2),
            "兑现率": round(credit / trig * 100, 2) if trig else 0.0,
            "触发人数": g["触发人数"], "领取人数": g["领取人数"],
            "领取率": round(g["领取人数"] / g["触发人数"] * 100, 2) if g["触发人数"] else 0.0,
            "触发次数": g["触发次数"],
            "当日新增到帐": round(g["当日新增到帐"], 2),
            "当日新增次数": g["当日新增次数"],
        })
        tot_credit += credit; tot_trig += trig
        tot_claim_people += g["领取人数"]; tot_new_credit += g["当日新增到帐"]
    items.sort(key=lambda x: x["到帐彩金"], reverse=True)
    return {
        "as_of": cur,
        "summary": {
            "累计到帐彩金": round(tot_credit, 2),
            "当日新增到帐彩金": round(tot_new_credit, 2),
            "领取会员": tot_claim_people,
            "整体兑现率": round(tot_credit / tot_trig * 100, 2) if tot_trig else 0.0,
        },
        "list": items,
    }


def _venue_trends(venues):
    """返回當日所有場館的完整走勢指標（含有效打碼、注單量、會員輸贏）。"""
    out = {}
    for name, (bet, payout, eff, count) in venues.items():
        out[name] = {
            "投注总额": round(bet, 2),
            "派彩总额": round(payout, 2),
            "有效打码": round(eff, 2),
            "注单量": int(count),
            "平台输赢": round(bet - payout, 2),     # 正=平台赢
            "会员输赢": round(payout - bet, 2),     # 正=会员赢
            "杀率": round((bet - payout) / eff * 100, 2) if eff else 0.0,  # 平台输赢/有效打码，正=平台赢
        }
    return out


def _top_games(venues, total_bet, n=10):
    """按投注总额取 TOP n 个游戏场馆，附派彩、平台输赢(GGR)、投注占比。"""
    top = sorted(venues.items(), key=lambda kv: kv[1][0], reverse=True)[:n]
    out = []
    for name, (bet, payout, eff, count) in top:
        out.append({
            "场馆": name,
            "投注总额": round(bet, 2),
            "派彩总额": round(payout, 2),
            "平台输赢": round(bet - payout, 2),     # 正=平台赢
            "占比": round(bet / total_bet * 100, 2) if total_bet else 0.0,
        })
    return out


if __name__ == "__main__":
    import json, sys
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "raw-data")
    print(json.dumps(aggregate(d), ensure_ascii=False, indent=2))
