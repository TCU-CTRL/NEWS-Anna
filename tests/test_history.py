"""送信済み記事履歴のテスト"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.history import (
    RETENTION_DAYS, load_sent_urls, save_sent_urls,
)


class TestHistory:
    def test_load_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.history.HISTORY_DIR", tmp_path,
        )
        urls = load_sent_urls("test")
        assert urls == set()

    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.history.HISTORY_DIR", tmp_path,
        )
        save_sent_urls("test", ["https://a.com", "https://b.com"])
        urls = load_sent_urls("test")
        assert urls == {"https://a.com", "https://b.com"}

    def test_append_to_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.history.HISTORY_DIR", tmp_path,
        )
        save_sent_urls("test", ["https://a.com"])
        save_sent_urls("test", ["https://b.com"])
        urls = load_sent_urls("test")
        assert urls == {"https://a.com", "https://b.com"}

    def test_expired_entries_excluded(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(
            "src.history.HISTORY_DIR", tmp_path,
        )
        old_date = (
            datetime.now(timezone.utc)
            - timedelta(days=RETENTION_DAYS + 1)
        ).isoformat()
        new_date = datetime.now(timezone.utc).isoformat()

        path = tmp_path / "test.json"
        data = [
            {"url": "https://old.com", "sent_at": old_date},
            {"url": "https://new.com", "sent_at": new_date},
        ]
        path.write_text(json.dumps(data))

        urls = load_sent_urls("test")
        assert "https://old.com" not in urls
        assert "https://new.com" in urls

    def test_cleanup_on_save(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(
            "src.history.HISTORY_DIR", tmp_path,
        )
        old_date = (
            datetime.now(timezone.utc)
            - timedelta(days=RETENTION_DAYS + 1)
        ).isoformat()

        path = tmp_path / "test.json"
        data = [
            {"url": "https://old.com", "sent_at": old_date},
        ]
        path.write_text(json.dumps(data))

        save_sent_urls("test", ["https://new.com"])

        saved = json.loads(path.read_text())
        saved_urls = [e["url"] for e in saved]
        assert "https://old.com" not in saved_urls
        assert "https://new.com" in saved_urls
