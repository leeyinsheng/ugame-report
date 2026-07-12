import pytest
import sys
sys.path.insert(0, "Dashboard")

from aggregate import _activity_display, _bonus_for, _monthly_stats


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
        jun = result[0]
        assert jun["月份"] == "2026-06"
        assert jun["投注总额"] == 300.0
        assert jun["有效打码"] == 240.0
        assert jun["充值总额"] == 110.0
        assert jun["提现总额"] == 10.0
        assert jun["活跃会员"] == 3   # {u1,u2,u3} deduped
        assert jun["新增注册"] == 8
        assert jun["首充会员"] == 3
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
        hb = result[1]["环比"]
        assert hb["投注总额"] == 100.0       # (200/100-1)*100
        assert hb["新增注册"] == 100.0       # (20/10-1)*100
        assert hb["活跃会员"] == 0.0         # 1->1 no change

    def test_zerodiv_huanbi(self):
        result = _monthly_stats(
            [day1, day3],
            {day1: _rv(0, 0, 0, 0, 0, set()),
             day3: _rv(100, 80, 50, 0, 0, {"u1"})},
            {}, {}, {},
        )
        assert result[1]["环比"]["投注总额"] is None

    def test_progress_flag(self):
        result = _monthly_stats(
            [day1, day3],
            {day1: _rv(1, 1, 0, 0, 0, {"u1"}),
             day3: _rv(1, 1, 0, 0, 0, {"u2"})},
            {}, {}, {},
            today_ym="2026-07",
        )
        assert result[0]["进行中"] is False
        assert result[1]["进行中"] is True

    def test_empty_input(self):
        result = _monthly_stats([], {}, {}, {}, {})
        assert result == []
