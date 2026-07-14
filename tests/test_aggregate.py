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
