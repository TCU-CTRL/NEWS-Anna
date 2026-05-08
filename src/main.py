"""IT Morning Digest - メインパイプラインオーケストレーター"""

import logging
import os
import sys

from src.collector import collect_articles
from src.config_loader import load_keywords, load_sources
from src.filter import deduplicate, remove_invalid, score_articles, select_top
from src.formatter import format_digest, format_fallback
from src.notifier import send_to_discord
from src.summarizer_gemini import summarize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """パイプライン全体を実行する"""
    logger.info("=== IT Morning Digest 開始 ===")

    # 1. 設定読み込み
    try:
        sources = load_sources()
        keywords = load_keywords()
    except Exception:
        logger.exception("設定ファイルの読み込みに失敗しました")
        sys.exit(1)

    # ソースweightマップを構築
    source_weights = {s.name: s.weight for s in sources}

    # 2. RSS収集
    articles = collect_articles(sources)
    if not articles:
        logger.warning("記事が1件も取得できませんでした")
        return

    # 3. フィルタリング・スコアリング
    articles = remove_invalid(articles)
    articles = deduplicate(articles)
    articles = score_articles(articles, keywords, source_weights)
    logger.info("フィルタ後の記事数: %d", len(articles))

    # AI要約用に上位10件を選出
    top_articles = select_top(articles, limit=10)

    # 4. AI要約
    digest = summarize(top_articles)

    # 5. メッセージ整形
    if digest is not None:
        messages = format_digest(digest)
    else:
        # フォールバック: スコア上位5件で簡易ダイジェスト
        fallback_articles = select_top(articles, limit=3)
        messages = format_fallback(fallback_articles)

    # テストモード: メッセージ先頭に [TEST] を付加
    if os.environ.get("DIGEST_TEST_MODE"):
        logger.info("テストモードで実行中")
        messages[0] = "**[TEST]** " + messages[0]

    # 6. Discord通知
    success = send_to_discord(messages)
    if success:
        logger.info("=== IT Morning Digest 完了（通知成功） ===")
    else:
        logger.error("=== IT Morning Digest 完了（通知失敗） ===")


if __name__ == "__main__":
    main()
