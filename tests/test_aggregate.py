import pytest
import sys
sys.path.insert(0, "Dashboard")

from aggregate import _activity_display, _bonus_for


class TestActivityDisplay:
    def test_known_deposit_renamed_to_general(self):
        assert _activity_display(("充值活动", "2064338446452465664")) == "一般充值"

    def test_first_deposit_renamed(self):
        assert _activity_display(("充值活动", "2072527153187643392")) == "首次充值"

    def test_unknown_activity_keeps_name(self):
        assert _activity_display(("负盈利", "2064364752562868224")) == "负盈利"

    def test_other_deposit_keeps_name(self):
        assert _activity_display(("充值活动", "2072532512957681664")) == "充值活动"

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
        assert result["list"][0]["活动"] == "首次充值"
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
        assert "一般充值" in names
        assert "首次充值" in names

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
