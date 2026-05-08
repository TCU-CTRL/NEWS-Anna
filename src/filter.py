"""記事フィルタリング・スコアリング"""

import logging
from datetime import datetime, timezone

from src.config_loader import KeywordConfig
from src.models import Article

logger = logging.getLogger(__name__)


def deduplicate(articles: list[Article]) -> list[Article]:
    """URL重複排除 - 同一URLの記事を1件にまとめる"""
    seen: set[str] = set()
    result: list[Article] = []
    for article in articles:
        if article.url not in seen:
            seen.add(article.url)
            result.append(article)
    original = len(articles)
    filtered = original - len(result)
    if filtered:
        logger.info("Deduplicated: %d → %d articles (%d removed)", original, len(result), filtered)
    return result


def remove_invalid(articles: list[Article]) -> list[Article]:
    """タイトルまたはURLが空の記事を除外"""
    result = [a for a in articles if a.title.strip() and a.url.strip()]
    removed = len(articles) - len(result)
    if removed:
        logger.info("Removed %d invalid articles (empty title or URL)", removed)
    return result


def score_articles(
    articles: list[Article],
    keywords: KeywordConfig,
    source_weights: dict[str, float] | None = None,
) -> list[Article]:
    """キーワードスコアリング

    Scoring:
      - high_priority keyword match: +3.0 per keyword
      - medium_priority keyword match: +2.0 per keyword
      - low_priority keyword match: +0.5 per keyword
      - Time decay: within 24h → +2.0, within 48h → +1.0, else +0.0
      - Final score multiplied by source weight (default 1.0)
    """
    now = datetime.now(timezone.utc)
    weights = source_weights or {}

    scored: list[Article] = []
    for article in articles:
        text = f"{article.title} {article.summary}".lower()

        score = 0.0
        for kw in keywords.high_priority:
            if kw.lower() in text:
                score += 3.0
        for kw in keywords.medium_priority:
            if kw.lower() in text:
                score += 2.0
        for kw in keywords.low_priority:
            if kw.lower() in text:
                score += 0.5

        # Time decay bonus
        if article.published_at is not None:
            pub = article.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            hours = (now - pub).total_seconds() / 3600
            if hours <= 24:
                score += 2.0
            elif hours <= 48:
                score += 1.0

        # Source weight multiplier
        weight = weights.get(article.source, 1.0)
        score *= weight

        scored.append(
            Article(
                title=article.title,
                url=article.url,
                source=article.source,
                category=article.category,
                published_at=article.published_at,
                summary=article.summary,
                score=score,
            )
        )

    logger.info("Scored %d articles", len(scored))
    return scored


def select_top(articles: list[Article], limit: int = 10) -> list[Article]:
    """スコア降順で上位N件を選出"""
    sorted_articles = sorted(articles, key=lambda a: a.score, reverse=True)
    result = sorted_articles[:limit]
    logger.info("Selected top %d articles from %d", len(result), len(articles))
    return result
