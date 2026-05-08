"""キーワードスコアリングのテスト"""

from datetime import datetime, timedelta, timezone

from src.config_loader import KeywordConfig
from src.filter import score_articles
from src.models import Article


def _make_keywords() -> KeywordConfig:
    return KeywordConfig(
        high_priority=["AI", "LLM"],
        medium_priority=["cloud", "API"],
        low_priority=["gadget"],
    )


def _make_article(
    title: str = "Test",
    summary: str = "",
    source: str = "Test",
    published_at: datetime | None = None,
) -> Article:
    return Article(
        title=title,
        url="https://example.com",
        source=source,
        category="test",
        published_at=published_at,
        summary=summary,
    )


class TestScoreArticles:
    def test_high_priority_keyword(self) -> None:
        articles = [_make_article(title="AI revolution")]
        result = score_articles(articles, _make_keywords())
        assert result[0].score == 3.0

    def test_medium_priority_keyword(self) -> None:
        articles = [_make_article(title="cloud computing")]
        result = score_articles(articles, _make_keywords())
        assert result[0].score == 2.0

    def test_low_priority_keyword(self) -> None:
        articles = [_make_article(title="new gadget review")]
        result = score_articles(articles, _make_keywords())
        assert result[0].score == 0.5

    def test_multiple_keywords(self) -> None:
        articles = [_make_article(title="AI and LLM advances")]
        result = score_articles(articles, _make_keywords())
        # AI: +3.0, LLM: +3.0
        assert result[0].score == 6.0

    def test_keyword_in_summary(self) -> None:
        articles = [_make_article(title="News", summary="About AI")]
        result = score_articles(articles, _make_keywords())
        assert result[0].score == 3.0

    def test_case_insensitive(self) -> None:
        articles = [_make_article(title="ai and llm")]
        result = score_articles(articles, _make_keywords())
        assert result[0].score == 6.0

    def test_no_keyword_match(self) -> None:
        articles = [_make_article(title="unrelated news")]
        result = score_articles(articles, _make_keywords())
        assert result[0].score == 0.0

    def test_time_decay_within_24h(self) -> None:
        now = datetime.now(timezone.utc)
        articles = [_make_article(title="AI news", published_at=now - timedelta(hours=12))]
        result = score_articles(articles, _make_keywords())
        # AI: +3.0, time bonus: +2.0
        assert result[0].score == 5.0

    def test_time_decay_within_48h(self) -> None:
        now = datetime.now(timezone.utc)
        articles = [_make_article(title="AI news", published_at=now - timedelta(hours=36))]
        result = score_articles(articles, _make_keywords())
        # AI: +3.0, time bonus: +1.0
        assert result[0].score == 4.0

    def test_time_decay_older_than_48h(self) -> None:
        now = datetime.now(timezone.utc)
        articles = [_make_article(title="AI news", published_at=now - timedelta(hours=72))]
        result = score_articles(articles, _make_keywords())
        # AI: +3.0, time bonus: +0.0
        assert result[0].score == 3.0

    def test_published_at_none(self) -> None:
        articles = [_make_article(title="AI news", published_at=None)]
        result = score_articles(articles, _make_keywords())
        # AI: +3.0, no time bonus
        assert result[0].score == 3.0

    def test_source_weight(self) -> None:
        articles = [_make_article(title="AI news", source="WeightedSource")]
        result = score_articles(articles, _make_keywords(), source_weights={"WeightedSource": 0.5})
        # AI: +3.0, weight: *0.5
        assert result[0].score == 1.5
