"""IT Morning Digest - メインパイプラインオーケストレーター"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from src.collector import collect_articles
from src.config_loader import (
    ProfileConfig, load_keywords, load_profiles, load_sources,
)
from src.filter import (
    deduplicate, remove_already_sent, remove_invalid,
    score_articles, select_top,
)
from src.formatter import format_digest, format_fallback
from src.history import load_sent_urls, save_sent_urls
from src.notifier import send_to_discord
from src.summarizer_gemini import summarize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

DAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}


def should_run_today(
    profile: ProfileConfig, today: datetime,
) -> bool:
    """プロファイルのスケジュールに基づき今日実行すべきか判定"""
    schedule = profile.schedule.lower().strip()
    if schedule == "daily":
        return True
    if schedule.startswith("weekly:"):
        day_name = schedule.split(":", 1)[1]
        target_weekday = DAY_MAP.get(day_name)
        if target_weekday is None:
            logger.warning(
                "不明な曜日指定: %s（プロファイル: %s）",
                day_name, profile.name,
            )
            return True
        return today.weekday() == target_weekday
    logger.warning(
        "不明なスケジュール: %s（プロファイル: %s）",
        schedule, profile.name,
    )
    return True


def run_profile(
    profile: ProfileConfig, dry_run: bool = False,
) -> bool:
    """1つのプロファイルのパイプラインを実行する"""
    logger.info("--- プロファイル [%s] 開始 ---", profile.name)

    webhook_url = os.environ.get(profile.webhook_env)
    if not webhook_url:
        logger.warning(
            "プロファイル [%s] の Webhook URL（%s）が未設定",
            profile.name, profile.webhook_env,
        )
        return False

    # 1. 設定読み込み
    sources = load_sources(profile.sources)
    keywords = load_keywords(profile.keywords)
    source_weights = {s.name: s.weight for s in sources}

    # 2. RSS収集
    articles = collect_articles(sources)
    if not articles:
        logger.warning(
            "プロファイル [%s]: 記事が0件", profile.name,
        )
        return False

    # 3. フィルタリング・スコアリング
    articles = remove_invalid(articles)
    articles = deduplicate(articles)

    # 送信済み記事を除外
    sent_urls = load_sent_urls(profile.name)
    articles = remove_already_sent(articles, sent_urls)

    articles = score_articles(
        articles, keywords, source_weights,
    )
    logger.info(
        "プロファイル [%s]: フィルタ後の記事数: %d",
        profile.name, len(articles),
    )

    top_articles = select_top(articles, limit=10)

    # ドライラン
    if dry_run:
        logger.info(
            "[DRY RUN] [%s]: 設定OK, RSS OK, "
            "記事%d件, Webhook OK",
            profile.name, len(articles),
        )
        for i, a in enumerate(top_articles[:3], 1):
            logger.info(
                "[DRY RUN]   %d. [%.1f] %s (%s)",
                i, a.score, a.title, a.source,
            )
        return True

    # 日替わり重点分野
    focus_today = ""
    if profile.focus_areas:
        today = datetime.now(JST)
        idx = today.timetuple().tm_yday % len(
            profile.focus_areas
        )
        focus_today = profile.focus_areas[idx]
        logger.info(
            "プロファイル [%s]: 今日の重点分野 → %s",
            profile.name, focus_today,
        )

    # 4. AI要約
    digest = summarize(
        top_articles,
        topic_name=profile.name,
        emoji=profile.emoji,
        priority_topics=profile.priority_topics,
        focus_area=focus_today,
    )

    # 5. メッセージ整形
    if digest is not None:
        messages = format_digest(digest)
    else:
        fallback_articles = select_top(articles, limit=3)
        messages = format_fallback(fallback_articles)

    # テストモード
    if os.environ.get("DIGEST_TEST_MODE"):
        messages[0] = "**[TEST]** " + messages[0]

    # 6. Discord通知
    success = send_to_discord(messages, webhook_url=webhook_url)

    # 7. 送信済みURLを履歴に保存
    if success:
        sent_article_urls = [a.url for a in top_articles]
        save_sent_urls(profile.name, sent_article_urls)

    logger.info(
        "--- プロファイル [%s] %s ---",
        profile.name,
        "完了（通知成功）" if success else "完了（通知失敗）",
    )
    return success


def main() -> None:
    """全プロファイルのパイプラインを実行する"""
    dry_run = bool(os.environ.get("DIGEST_DRY_RUN"))
    if dry_run:
        logger.info("=== NEWS アンナちゃん ドライラン開始 ===")
    else:
        logger.info("=== NEWS アンナちゃん 開始 ===")

    try:
        profiles = load_profiles()
    except Exception:
        logger.exception("プロファイル設定の読み込みに失敗")
        sys.exit(1)

    if not profiles:
        logger.error("プロファイルが0件です")
        sys.exit(1)

    today = datetime.now(JST)

    results: dict[str, str] = {}
    for profile in profiles:
        if not should_run_today(profile, today):
            logger.info(
                "プロファイル [%s]: スケジュール対象外（%s）",
                profile.name, profile.schedule,
            )
            results[profile.name] = "⏭️ スキップ"
            continue
        try:
            success = run_profile(profile, dry_run=dry_run)
            results[profile.name] = "✅" if success else "❌"
        except Exception:
            logger.exception(
                "プロファイル [%s] でエラー発生",
                profile.name,
            )
            results[profile.name] = "❌"

    logger.info("--- 結果サマリー ---")
    for name, status in results.items():
        logger.info("  %s %s", status, name)

    logger.info(
        "=== NEWS アンナちゃん %s ===",
        "ドライラン完了" if dry_run else "完了",
    )


if __name__ == "__main__":
    main()
