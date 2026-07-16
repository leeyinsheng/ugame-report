import pytest
import sys
sys.path.insert(0, "Dashboard")

from aggregate import _activity_display, _bonus_for, _monthly_stats, _weekly_stats, daypart


class TestActivityDisplay:
    def test_known_deposit_renamed_to_daily_recharge(self):
        assert _activity_display(("充值活动", "2064338446452465664")) == "每日充值回馈"

    def test_first_deposit_renamed(self):
        assert _activity_display(("充值活动", "2072527153187643392")) == "新人首充100%豪礼"

    def test_negative_profit_renamed(self):
        assert _activity_display(("负盈利", "2064364752562868224")) == "老虎救援金"

    def test_another_negative_profit_renamed(self):
        assert _activity_display(("负盈利", "2064355390268166144")) == "真人视讯转运金"

    def test_daily_recharge_renamed(self):
        assert _activity_display(("充值活动", "2072532512957681664")) == "每日充值回馈"

    def test_unknown_activity_keeps_name(self):
        assert _activity_display(("未知活动", "999")) == "未知活动"

    def test_empty_id(self):
        assert _activity_display(("测试活动", "")) == "测试活动"


class TestBonusFor:
    def test_no_snaps_returns_none(self):
        assert _bonus_for({}, "2026-07-03") is None

    def test_single_snap_single_activity(self):
        snaps = {
            "2026-07-02": {
                ("充值活动", "2072527153187643392"): {
                    "触发": 250.0, "到帐": 250.0, "次数": 2,
                    "触发人数": 2, "领取人数": 2, "领取率": 100.0,
                },
            },
        }
        result = _bonus_for(snaps, "2026-07-02")
        assert result is not None
        assert result["as_of"] == "2026-07-02"
        assert len(result["list"]) == 1
        assert result["list"][0]["活动"] == "新人首充100%豪礼"
        assert result["list"][0]["到帐彩金"] == 250.0
        assert result["list"][0]["领取率"] == 100.0
        assert result["list"][0]["当日新增到帐"] == 250.0
        assert result["list"][0]["当日新增次数"] == 2
        assert result["summary"]["累计到帐彩金"] == 250.0

    def test_same_name_diff_id_preserved(self):
        snaps = {
            "2026-07-03": {
                ("充值活动", "2064338446452465664"): {
                    "触发": 1422.79, "到帐": 1422.79, "次数": 128,
                    "触发人数": 63, "领取人数": 63, "领取率": 100.0,
                },
                ("充值活动", "2072527153187643392"): {
                    "触发": 550.0, "到帐": 250.0, "次数": 3,
                    "触发人数": 3, "领取人数": 2, "领取率": 66.67,
                },
            },
        }
        result = _bonus_for(snaps, "2026-07-03")
        assert result is not None
        assert len(result["list"]) == 2
        names = [item["活动"] for item in result["list"]]
        assert "每日充值回馈" in names
        assert "新人首充100%豪礼" in names

    def test_same_display_name_merged(self):
        snaps = {
            "2026-07-03": {
                ("充值活动", "2064338446452465664"): {
                    "触发": 1000.0, "到帐": 800.0, "次数": 50,
                    "触发人数": 30, "领取人数": 25, "领取率": 83.33,
                },
                ("充值活动", "2072532512957681664"): {
                    "触发": 400.0, "到帐": 350.0, "次数": 15,
                    "触发人数": 10, "领取人数": 8, "领取率": 80.0,
                },
            },
        }
        result = _bonus_for(snaps, "2026-07-03")
        assert result is not None
        assert len(result["list"]) == 1, "same display name should merge into 1 item"
        item = result["list"][0]
        assert item["活动"] == "每日充值回馈"
        assert item["到帐彩金"] == 1150.0
        assert item["触发彩金"] == 1400.0
        assert item["触发人数"] == 40
        assert item["领取人数"] == 33
        assert item["兑现率"] == pytest.approx(1150 / 1400 * 100, 0.01)
        assert item["领取率"] == pytest.approx(33 / 40 * 100, 0.01)
        assert item["触发次数"] == 65
        assert item["当日新增到帐"] == 1150.0
        assert item["当日新增次数"] == 65

    def test_daily_delta(self):
        snaps = {
            "2026-07-02": {
                ("充值活动", "2072527153187643392"): {
                    "触发": 250.0, "到帐": 250.0, "次数": 2,
                    "触发人数": 2, "领取人数": 2, "领取率": 100.0,
                },
            },
            "2026-07-03": {
                ("充值活动", "2072527153187643392"): {
                    "触发": 550.0, "到帐": 250.0, "次数": 3,
                    "触发人数": 3, "领取人数": 2, "领取率": 66.67,
                },
            },
        }
        result = _bonus_for(snaps, "2026-07-03")
        assert result["list"][0]["当日新增到帐"] == 0.0
        assert result["list"][0]["当日新增次数"] == 1

    def test_no_prev_snap(self):
        snaps = {
            "2026-07-03": {
                ("充值活动", "2072527153187643392"): {
                    "触发": 550.0, "到帐": 250.0, "次数": 3,
                    "触发人数": 3, "领取人数": 2, "领取率": 66.67,
                },
            },
        }
        result = _bonus_for(snaps, "2026-07-03")
        assert result["list"][0]["当日新增到帐"] == 250.0
        assert result["list"][0]["当日新增次数"] == 3

    def test_summary_aggregation(self):
        snaps = {
            "2026-07-03": {
                ("充值活动", "2064338446452465664"): {
                    "触发": 1422.79, "到帐": 1422.79, "次数": 128,
                    "触发人数": 63, "领取人数": 63, "领取率": 100.0,
                },
                ("充值活动", "2072527153187643392"): {
                    "触发": 550.0, "到帐": 250.0, "次数": 3,
                    "触发人数": 3, "领取人数": 2, "领取率": 66.67,
                },
            },
        }
        result = _bonus_for(snaps, "2026-07-03")
        assert result["summary"]["累计到帐彩金"] == pytest.approx(1672.79)
        assert result["summary"]["整体兑现率"] == pytest.approx(1672.79 / 1972.79 * 100, 0.01)


day1, day2, day3 = "2026-06-01", "2026-06-02", "2026-07-01"


def _rv(bet=0.0, eff=0.0, pay=0.0, fs=0.0, hd=0.0, act=None, est=0.0, bn=0):
    return [bet, eff, pay, fs, hd, act or set(), est, bn]


def _cv(dep=0.0, dpn=0, dpp=None, wd=0.0, wpn=0, wpp=None):
    return [dep, dpn, dpp or set(), wd, wpn, wpp or set()]


class TestMonthlyStats:
    def test_basic_aggregation(self):
        result = _monthly_stats(
            [day1, day2, day3],
            {day1: _rv(100, 80, 90, 2, 3, {"u1", "u2"}),
             day2: _rv(200, 160, 180, 4, 6, {"u2", "u3"}),
             day3: _rv(300, 240, 270, 6, 9, {"u4"})},
            {day1: _cv(50, 1, {"u1"}),
             day2: _cv(60, 1, {"u2"}, 10),
             day3: _cv(70, 1, {"u4"}, 20)},
            {day1: 5, day2: 3, day3: 7},
            {day1: 2, day2: 1, day3: 3},
        )
        assert len(result) == 2
        jun = result[1]  # newer first, so "2026-06" is now result[1]
        jul = result[0]
        assert jun["月份"] == "2026-06"
        assert jun["投注总额"] == 300.0
        assert jun["有效打码"] == 240.0
        assert jun["充值总额"] == 110.0
        assert jun["提现总额"] == 10.0
        assert jun["活跃会员"] == 3   # {u1,u2,u3} deduped
        assert jun["新增注册"] == 8
        assert jun["首充会员"] == 3
        assert jun["GGR"] == 30.0
        assert jun["到帐彩金"] == 9.0
        assert jun["实际返水"] == 6.0
        assert jun["净利润NGR"] == pytest.approx(300 - (90+180) - (2+4) - (3+6), 0.01)

    def test_active_member_dedup(self):
        result = _monthly_stats(
            [day1, day2],
            {day1: _rv(1, 1, 0, 0, 0, {"u1", "u2"}),
             day2: _rv(1, 1, 0, 0, 0, {"u2", "u3"})},
            {}, {}, {},
        )
        assert result[0]["活跃会员"] == 3  # union, not sum

    def test_first_month_no_huanbi(self):
        result = _monthly_stats(
            [day1], {day1: _rv(100, 80, 50, 0, 0, {"u1"})}, {}, {}, {},
        )
        assert result[0]["环比"] == {}

    def test_huanbi_calculation(self):
        result = _monthly_stats(
            [day1, day3],
            {day1: _rv(100, 80, 50, 0, 0, {"u1"}, 0, 5),
             day3: _rv(200, 160, 100, 0, 0, {"u2"}, 0, 10)},
            {}, {"2026-06-01": 10, "2026-07-01": 20}, {},
        )
        assert len(result) == 2
        jul = result[0]  # newest first
        hb = jul["环比"]
        assert hb["投注总额"] == 100.0       # (200/100-1)*100
        assert hb["GGR"] == 100.0            # (100/50-1)*100
        assert hb["到帐彩金"] is None        # pv=0 → 除零
        assert hb["实际返水"] is None         # pv=0 → 除零
        assert hb["新增注册"] == 100.0       # (20/10-1)*100
        assert hb["活跃会员"] == 0.0         # 1->1 no change

    def test_zerodiv_huanbi(self):
        result = _monthly_stats(
            [day1, day3],
            {day1: _rv(0, 0, 0, 0, 0, set()),
             day3: _rv(100, 80, 50, 0, 0, {"u1"})},
            {}, {}, {},
        )
        assert result[0]["环比"]["投注总额"] is None

    def test_progress_flag(self):
        result = _monthly_stats(
            [day1, day3],
            {day1: _rv(1, 1, 0, 0, 0, {"u1"}),
             day3: _rv(1, 1, 0, 0, 0, {"u2"})},
            {}, {}, {},
            today_ym="2026-07",
        )
        assert result[0]["进行中"] is True
        assert result[1]["进行中"] is False

    def test_empty_input(self):
        result = _monthly_stats([], {}, {}, {}, {})
        assert result == []


from datetime import date as dt_date

w26_mon, w26_sun = "2026-06-22", "2026-06-28"  # Mon-Sun, W26
w27_mon, w27_wed = "2026-06-29", "2026-07-01"  # Mon-Wed, W27


class TestWeeklyStats:
    def test_basic_aggregation(self):
        result = _weekly_stats(
            [w26_mon, w26_sun, w27_mon, w27_wed],
            {w26_mon: _rv(100, 80, 90, 2, 3, {"u1", "u2"}, 0, 5),
             w26_sun: _rv(200, 160, 180, 4, 6, {"u2", "u3"}, 0, 10),
             w27_mon: _rv(50, 40, 30, 1, 0, {"u4"}, 0, 3),
             w27_wed: _rv(60, 50, 40, 0, 2, {"u5"}, 0, 4)},
            {w26_mon: _cv(80, 1, {"u1"}), w26_sun: _cv(40, 1, {"u2"}, 20),
             w27_mon: _cv(30, 1, {"u4"}), w27_wed: _cv(20, 1, {"u5"}, 10)},
            {w26_mon: 5, w26_sun: 3, w27_mon: 2, w27_wed: 1},
            {w26_mon: 2, w26_sun: 1, w27_mon: 1, w27_wed: 0},
            today=dt_date.fromisoformat("2026-07-10"),  # both weeks in past
        )
        assert len(result) == 2
        w27 = result[0]  # newer first
        w26 = result[1]
        assert w27["週次"] == "2026-W27"
        assert w26["週次"] == "2026-W26"
        assert w26["日期段"] == "06-22 → 06-28"
        assert w26["投注总额"] == 300.0
        assert w26["有效打码"] == 240.0
        assert w26["充值总额"] == 120.0
        assert w26["提现总额"] == 20.0
        assert w26["活跃会员"] == 3  # {u1,u2,u3}
        assert w26["新增注册"] == 8
        assert w26["首充会员"] == 3
        ngr26 = 300 - (90+180) - (2+4) - (3+6)
        assert w26["GGR"] == 30.0
        assert w26["到帐彩金"] == 9.0
        assert w26["实际返水"] == 6.0
        assert w26["净利润NGR"] == pytest.approx(ngr26, 0.01)
        assert w26["进行中"] is False

    def test_active_member_dedup(self):
        result = _weekly_stats(
            [w26_mon, w26_sun],
            {w26_mon: _rv(1, 1, 0, 0, 0, {"u1", "u2"}, 0, 0),
             w26_sun: _rv(1, 1, 0, 0, 0, {"u2", "u3"}, 0, 0)},
            {}, {}, {},
        )
        assert result[0]["活跃会员"] == 3

    def test_wow_calculation(self):
        result = _weekly_stats(
            [w26_mon, w27_wed],
            {w26_mon: _rv(200, 160, 100, 0, 0, {"u1"}, 0, 10),
             w27_wed: _rv(300, 240, 150, 0, 0, {"u2"}, 0, 15)},
            {}, {"2026-06-22": 10, "2026-07-01": 15}, {},
        )
        assert len(result) == 2
        wow = result[0]["前週环比%"]  # W27 newest, has环比 vs W26
        assert wow["投注总额"] == 50.0        # (300/200-1)*100
        assert wow["GGR"] == 50.0             # (150/100-1)*100
        assert wow["到帐彩金"] is None        # pv=0
        assert wow["实际返水"] is None         # pv=0
        assert wow["新增注册"] == 50.0        # (15/10-1)*100
        assert wow["活跃会员"] == 0.0         # 1->1

    def test_first_week_no_wow(self):
        result = _weekly_stats(
            [w26_mon], {w26_mon: _rv(100, 80, 50, 0, 0, {"u1"}, 0, 0)}, {}, {}, {},
        )
        assert result[0]["前週环比%"] == {}

    def test_zerodiv_wow(self):
        result = _weekly_stats(
            [w26_mon, w27_wed],
            {w26_mon: _rv(0, 0, 0, 0, 0, set()),
             w27_wed: _rv(100, 80, 50, 0, 0, {"u1"})},
            {}, {}, {},
        )
        assert result[0]["前週环比%"]["投注总额"] is None

    def test_progress_flag(self):
        result = _weekly_stats(
            [w26_mon, w27_wed],
            {w26_mon: _rv(1, 1, 0, 0, 0, {"u1"}),
             w27_wed: _rv(1, 1, 0, 0, 0, {"u2"})},
            {}, {}, {},
            today=dt_date.fromisoformat("2026-07-01"),
        )
        assert result[0]["进行中"] is True   # W27 newest, in progress
        assert result[1]["进行中"] is False

    def test_date_range(self):
        result = _weekly_stats(
            [w26_mon, w26_sun],
            {w26_mon: _rv(1, 1, 0, 0, 0, set()),
             w26_sun: _rv(1, 1, 0, 0, 0, set())},
            {}, {}, {},
        )
        assert result[0]["日期段"] == "06-22 → 06-28"
        assert result[0]["週次"] == "2026-W26"

    def test_empty_input(self):
        result = _weekly_stats([], {}, {}, {}, {})
        assert result == []


class TestDaypart:
    def test_dash_format(self):
        assert daypart("2026-06-22 16:24:15（美东时间）") == "2026-06-22"

    def test_slash_format(self):
        assert daypart("2026/07/12 01:42:26（美东时间）") == "2026-07-12"

    def test_short_date(self):
        assert daypart("2026-06-22") == "2026-06-22"

    def test_invalid(self):
        assert daypart("") == ""
        assert daypart("abc") == ""


import sys
sys.path.insert(0, "Dashboard")
from aggregate import venue_display


class TestVenueDisplay:
    def test_pp_zh_slots(self):
        assert venue_display("PP ZH SLOTS") == "PP 电子"

    def test_pp_dianzi_chinese(self):
        assert venue_display("PP电子") == "PP 电子"

    def test_pp_broken_encoding(self):
        assert venue_display("PP电\ufffd\ufffd") == "PP 电子"

    def test_wg_electronics(self):
        assert venue_display("WG电子") == "WG 电子"

    def test_wg_broken(self):
        assert venue_display("WG电\ufffd") == "WG 电子"

    def test_sports_broken(self):
        assert venue_display("体\ufffd\ufffd\ufffd") == "U 体育"

    def test_huangguan_broken(self):
        assert venue_display("皇冠\ufffd") == "皇冠体育"

    def test_panda_sports(self):
        assert venue_display("熊猫体育") == "熊猫体育"

    def test_unknown_kept_as_is(self):
        assert venue_display("未知场馆") == "未知场馆"

    def test_empty(self):
        assert venue_display("") == "其他"


import io
import sys
sys.path.insert(0, "Dashboard")
from aggregate import aggregate


def _csv_source(*files):
    """Mock source: files = [(name, content_string), ...]"""

    class MockSource:
        def iter_csv(self, only_keys=None):
            for name, content in files:
                if only_keys and name not in only_keys:
                    continue
                yield name, 0, io.StringIO(content)

    return MockSource()


BET_CSV = """派彩日期时间,本平台单号,会员ID,投注金额,有效投注,派彩金额,返水,游戏场馆
2026-06-22 10:00:00,B001,u1,100,80,90,2,PG
2026-06-22 11:00:00,B002,u2,200,160,180,4,JILI Slots
2026-06-23 09:00:00,B003,u3,300,240,270,6,PG
"""

LEDGER_CSV = """流水号,账变时间,账变类型,账变金额,会员ID
L1,2026-06-22 12:00:00,游戏返水,2,u1
L2,2026-06-22 13:00:00,活動獎勵,3,u1
L3,2026-06-23 10:00:00,游戏返水,4,u3
L4,2026-06-23 11:00:00,活動獎勵,6,u3
"""

CHARGES_CSV = """订单号,完成时间,类型,充值金额,提现金额,订单状态,会员ID
C1,2026-06-22 08:00:00,充值,50,0,成功,u1
C2,2026-06-22 09:00:00,提现,0,10,成功,u1
C3,2026-06-23 07:00:00,充值,70,0,成功,u4
"""

MEMBERS_CSV = """会员ID,注册日期时间,第一次充值成功的日期时间
u1,2026-06-22 00:00:00,2026-06-22 00:00:00
u2,2026-06-22 00:00:00,
u3,2026-06-23 00:00:00,2026-06-23 00:00:00
u4,2026-06-23 00:00:00,2026-06-23 00:00:00
"""

ACT_CSV = """活动名称,活动 ID,触发彩金总金额,到帐彩金总金额,触发彩金总次数,触发会员总人数,领取彩金会员总人数,活动领取率
每日充值回馈,2064338446452465664,100,80,10,5,4,80.0
"""


class TestAggregateSqlite:
    def test_basic_daily_aggregation(self):
        src = _csv_source(
            ("bets.csv", BET_CSV),
            ("ledger.csv", LEDGER_CSV),
            ("charges.csv", CHARGES_CSV),
            ("members.csv", MEMBERS_CSV),
        )
        out, _ = aggregate(src)
        assert "2026-06-22" in out
        assert "2026-06-23" in out

        d22 = out["2026-06-22"]
        assert d22["rev"]["投注总额"] == 300.0
        assert d22["rev"]["有效打码"] == 240.0
        assert d22["rev"]["派彩总额"] == 270.0
        assert d22["rev"]["GGR"] == 30.0
        assert d22["rev"]["彩金"] == 3.0
        assert d22["rev"]["实际返水"] == 2.0
        assert d22["rev"]["预计返水"] == 6.0
        assert d22["rev"]["注单量"] == 2
        assert d22["mem"]["活跃会员"] == 2  # u1, u2
        assert d22["cp"]["充值总额"] == 50.0
        assert d22["cp"]["提现总额"] == 10.0

        d23 = out["2026-06-23"]
        assert d23["rev"]["投注总额"] == 300.0
        assert d23["rev"]["GGR"] == 30.0
        assert d23["rev"]["彩金"] == 6.0
        assert d23["rev"]["实际返水"] == 4.0

    def test_no_duplicate_on_reimport(self):
        src = _csv_source(("bets.csv", BET_CSV))
        out1, _ = aggregate(src)
        # Re-import same data
        src2 = _csv_source(("bets.csv", BET_CSV))
        out2, _ = aggregate(src2)
        assert out1["2026-06-22"]["rev"]["投注总额"] == out2["2026-06-22"]["rev"]["投注总额"]
        assert out1["2026-06-22"]["rev"]["注单量"] == out2["2026-06-22"]["rev"]["注单量"]

    def test_incremental_only_new_files(self):
        src = _csv_source(("bets.csv", BET_CSV))
        out1, _ = aggregate(src)
        assert out1["2026-06-22"]["rev"]["注单量"] == 2

        more_bets = """派彩日期时间,本平台单号,会员ID,投注金额,有效投注,派彩金额,返水,游戏场馆
2026-06-24 10:00:00,B004,u5,400,320,360,8,WG
"""
        src2 = _csv_source(("bets.csv", BET_CSV), ("bets_new.csv", more_bets))
        out2, _ = aggregate(src2)
        assert "2026-06-24" in out2
        assert out2["2026-06-24"]["rev"]["投注总额"] == 400.0

    def test_monthly_stats_from_sqlite(self):
        src = _csv_source(
            ("bets.csv", BET_CSV),
            ("ledger.csv", LEDGER_CSV),
            ("charges.csv", CHARGES_CSV),
            ("members.csv", MEMBERS_CSV),
        )
        out, _ = aggregate(src)
        monthly = out["_meta"]["monthly"]
        assert len(monthly) == 1
        jun = monthly[0]
        assert jun["月份"] == "2026-06"
        assert jun["投注总额"] == 600.0
        assert jun["有效打码"] == 480.0
        assert jun["GGR"] == 60.0
        assert jun["到帐彩金"] == 9.0
        assert jun["实际返水"] == 6.0
        assert jun["活跃会员"] == 3  # u1,u2,u3 deduped
        assert jun["新增注册"] == 4  # u1,u2,u3,u4
        assert jun["首充会员"] == 3  # u1,u3,u4

    def test_weekly_stats_from_sqlite(self):
        src = _csv_source(
            ("bets.csv", BET_CSV),
            ("ledger.csv", LEDGER_CSV),
            ("charges.csv", CHARGES_CSV),
            ("members.csv", MEMBERS_CSV),
        )
        out, _ = aggregate(src)
        weekly = out["_meta"]["weekly"]
        assert len(weekly) == 1
        wk = weekly[0]
        assert wk["投注总额"] == 600.0
        assert wk["GGR"] == 60.0
        assert wk["到帐彩金"] == 9.0
        assert wk["实际返水"] == 6.0
        assert wk["活跃会员"] == 3

    def test_activity_bonus_from_sqlite(self):
        src = _csv_source(
            ("2026-06-22_活动.csv", ACT_CSV),
            ("bets.csv", BET_CSV),
            ("charges.csv", CHARGES_CSV),
        )
        out, _ = aggregate(src)
        bonus = out["2026-06-22"]["bonus"]
        assert bonus is not None
        assert bonus["as_of"] == "2026-06-22"
        assert len(bonus["list"]) == 1
        assert bonus["list"][0]["活动"] == "每日充值回馈"
        assert bonus["list"][0]["到帐彩金"] == 80.0

    def test_empty_source(self):
        src = _csv_source()
        out, _ = aggregate(src)
        assert "_meta" in out
        assert out["_meta"]["monthly"] == []
        assert out["_meta"]["weekly"] == []

    def test_game_venue_top(self):
        src = _csv_source(("bets.csv", BET_CSV))
        out, _ = aggregate(src)
        games = out["2026-06-22"]["game"]
        assert len(games) == 2
        assert games[0]["场馆"] == "JILI 电子"
        assert games[0]["投注总额"] == 200.0
        assert games[1]["场馆"] == "PG 电子"

    def test_loadable_module(self):
        """Smoke test: the module can be loaded without error."""
        import aggregate as _ag
        assert hasattr(_ag, "aggregate")
        assert hasattr(_ag, "_init_schema")
        assert hasattr(_ag, "_import_csv")
