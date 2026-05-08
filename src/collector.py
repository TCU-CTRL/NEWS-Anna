"""RSS/Atomフィードから記事を収集する"""

import logging
from datetime import datetime

import feedparser

from src.config_loader import SourceConfig
from src.models import Article

logger = logging.getLogger(__name__)


def collect_articles(sources: list[SourceConfig]) -> list[Article]:
    """複数のRSS/Atomフィードから記事を収集する。

    Args:
        sources: RSSソース設定のリスト

    Returns:
        収集した記事のリスト
    """
    enabled_sources = [s for s in sources if s.enabled]
    logger.info("Loading %d enabled sources (out of %d total)", len(enabled_sources), len(sources))

    articles: list[Article] = []

    for source in enabled_sources:
        try:
            feed = feedparser.parse(source.url)
            for entry in feed.entries:
                published_at: datetime | None = None
                if entry.get("published_parsed") is not None:
                    published_at = datetime(*entry.published_parsed[:6])

                articles.append(
                    Article(
                        title=entry.get("title", ""),
                        url=entry.get("link", ""),
                        source=source.name,
                        category=source.category,
                        published_at=published_at,
                        summary=entry.get("summary", ""),
                    )
                )
        except Exception:
            logger.exception("Failed to fetch feed from %s (%s)", source.name, source.url)

    logger.info("Collected %d articles in total", len(articles))
    return articles
