"""IT Morning Digest - メインパイプラインオーケストレーター"""

import logging
import os
import sys

from src.collector import collect_articles
from src.config_loader import ProfileConfig, load_keywords, load_profiles, load_sources
from src.filter import deduplicate, remove_invalid, score_articles, select_top
from src.formatter import format_digest, format_fallback
from src.notifier import send_to_discord
from src.summarizer_gemini import summarize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_profile(profile: ProfileConfig, dry_run: bool = False) -> bool:
    """1つのプロファイルのパイプラインを実行する"""
    logger.info("--- プロファイル [%s] 開始 ---", profile.name)

    # Webhook URL を環境変数から取得
    webhook_url = os.environ.get(profile.webhook_env)
    if not webhook_url:
        logger.warning(
            "プロファイル [%s] の Webhook URL（%s）が未設定のためスキップ",
            profile.name,
            profile.webhook_env,
        )
        return False

    # 1. 設定読み込み
    sources = load_sources(profile.sources)
    keywords = load_keywords(profile.keywords)
    source_weights = {s.name: s.weight for s in sources}

    # 2. RSS収集
    articles = collect_articles(sources)
    if not articles:
        logger.warning("プロファイル [%s]: 記事が1件も取得できませんでした", profile.name)
        return False

    # 3. フィルタリング・スコアリング
    articles = remove_invalid(articles)
    articles = deduplicate(articles)
    articles = score_articles(articles, keywords, source_weights)
    logger.info("プロファイル [%s]: フィルタ後の記事数: %d", profile.name, len(articles))

    # AI要約用に上位10件を選出
    top_articles = select_top(articles, limit=10)

    # ドライランモード: RSS取得・フィルタまで確認して終了
    if dry_run:
        logger.info("[DRY RUN] プロファイル [%s]: 設定OK, RSS取得OK, 記事%d件, Webhook設定OK",
                     profile.name, len(articles))
        logger.info("[DRY RUN] スコア上位3件:")
        for i, a in enumerate(top_articles[:3], 1):
            logger.info("[DRY RUN]   %d. [%.1f] %s (%s)", i, a.score, a.title, a.source)
        logger.info("[DRY RUN] Gemini API呼び出し・Discord送信はスキップ")
        return True

    # 4. AI要約
    digest = summarize(
        top_articles,
        topic_name=profile.name,
        emoji=profile.emoji,
        priority_topics=profile.priority_topics,
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
        logger.exception("プロファイル設定の読み込みに失敗しました")
        sys.exit(1)

    if not profiles:
        logger.error("プロファイルが1件も定義されていません")
        sys.exit(1)

    results: dict[str, bool] = {}
    for profile in profiles:
        try:
            results[profile.name] = run_profile(profile, dry_run=dry_run)
        except Exception:
            logger.exception("プロファイル [%s] でエラーが発生しました", profile.name)
            results[profile.name] = False

    # 結果サマリー
    logger.info("--- 結果サマリー ---")
    for name, success in results.items():
        status = "✅" if success else "❌"
        logger.info("  %s %s", status, name)

    logger.info("=== NEWS アンナちゃん %s ===", "ドライラン完了" if dry_run else "完了")


if __name__ == "__main__":
    main()
