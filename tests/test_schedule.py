"""スケジュール判定のテスト"""

from datetime import datetime, timezone, timedelta

from src.config_loader import ProfileConfig
from src.main import should_run_today

JST = timezone(timedelta(hours=9))


def _make_profile(schedule: str = "daily") -> ProfileConfig:
    return ProfileConfig(
        name="Test",
        sources="",
        keywords="",
        webhook_env="",
        emoji="",
        topic="",
        priority_topics="",
        schedule=schedule,
    )


class TestShouldRunToday:
    def test_daily_always_runs(self) -> None:
        profile = _make_profile("daily")
        # 月曜でも日曜でも実行
        monday = datetime(2026, 5, 11, 7, 30, tzinfo=JST)  # 月曜
        sunday = datetime(2026, 5, 17, 7, 30, tzinfo=JST)  # 日曜
        assert should_run_today(profile, monday) is True
        assert should_run_today(profile, sunday) is True

    def test_weekly_mon_runs_on_monday(self) -> None:
        profile = _make_profile("weekly:mon")
        monday = datetime(2026, 5, 11, 7, 30, tzinfo=JST)
        assert should_run_today(profile, monday) is True

    def test_weekly_mon_skips_on_tuesday(self) -> None:
        profile = _make_profile("weekly:mon")
        tuesday = datetime(2026, 5, 12, 7, 30, tzinfo=JST)
        assert should_run_today(profile, tuesday) is False

    def test_weekly_fri_runs_on_friday(self) -> None:
        profile = _make_profile("weekly:fri")
        friday = datetime(2026, 5, 15, 7, 30, tzinfo=JST)
        assert should_run_today(profile, friday) is True

    def test_weekly_fri_skips_on_saturday(self) -> None:
        profile = _make_profile("weekly:fri")
        saturday = datetime(2026, 5, 16, 7, 30, tzinfo=JST)
        assert should_run_today(profile, saturday) is False

    def test_unknown_schedule_defaults_to_daily(self) -> None:
        profile = _make_profile("biweekly")
        monday = datetime(2026, 5, 11, 7, 30, tzinfo=JST)
        assert should_run_today(profile, monday) is True
