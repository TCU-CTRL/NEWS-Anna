"""送信済み記事の履歴管理"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_DIR = Path("data/history")
RETENTION_DAYS = 30


def _history_path(profile_name: str) -> Path:
    """プロファイル名から履歴ファイルパスを返す"""
    safe_name = profile_name.replace(" ", "_").replace("/", "_")
    return HISTORY_DIR / f"{safe_name}.json"


def load_sent_urls(profile_name: str) -> set[str]:
    """送信済みURLのセットを読み込む（期限切れエントリは除外）"""
    path = _history_path(profile_name)
    if not path.exists():
        return set()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        cutoff_str = cutoff.isoformat()
        urls = {
            entry["url"]
            for entry in data
            if entry.get("sent_at", "") >= cutoff_str
        }
        logger.info(
            "履歴読み込み [%s]: %d件（%d日以内）",
            profile_name, len(urls), RETENTION_DAYS,
        )
        return urls
    except Exception:
        logger.exception(
            "履歴ファイルの読み込みに失敗 [%s]", profile_name,
        )
        return set()


def save_sent_urls(profile_name: str, urls: list[str]) -> None:
    """送信した記事のURLを履歴に追記し、期限切れを削除する"""
    path = _history_path(profile_name)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "既存の履歴ファイルが破損。新規作成します [%s]",
                profile_name,
            )

    now = datetime.now(timezone.utc).isoformat()
    for url in urls:
        existing.append({"url": url, "sent_at": now})

    # 1ヶ月より古いエントリを削除
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    cutoff_str = cutoff.isoformat()
    before = len(existing)
    existing = [
        e for e in existing
        if e.get("sent_at", "") >= cutoff_str
    ]
    expired = before - len(existing)
    if expired:
        logger.info(
            "履歴クリーンアップ [%s]: %d件の期限切れを削除",
            profile_name, expired,
        )

    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "履歴保存 [%s]: %d件追記（合計%d件）",
        profile_name, len(urls), len(existing),
    )
