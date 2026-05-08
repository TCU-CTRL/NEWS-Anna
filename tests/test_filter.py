"""フィルタリング・重複排除のテスト"""

from datetime import datetime

from src.filter import deduplicate, remove_invalid
from src.models import Article


def _make_article(
    title: str = "Test",
    url: str = "https://example.com",
    source: str = "Test",
    published_at: datetime | None = None,
) -> Article:
    return Article(
        title=title,
        url=url,
        source=source,
        category="test",
        published_at=published_at,
        summary="",
    )


class TestDeduplicate:
    def test_removes_duplicate_urls(self) -> None:
        articles = [
            _make_article(title="First", url="https://example.com/1"),
            _make_article(title="Second", url="https://example.com/1"),
            _make_article(title="Third", url="https://example.com/2"),
        ]
        result = deduplicate(articles)
        assert len(result) == 2
        assert result[0].title == "First"
        assert result[1].title == "Third"

    def test_keeps_all_unique_urls(self) -> None:
        articles = [
            _make_article(url="https://example.com/1"),
            _make_article(url="https://example.com/2"),
            _make_article(url="https://example.com/3"),
        ]
        result = deduplicate(articles)
        assert len(result) == 3

    def test_empty_list(self) -> None:
        assert deduplicate([]) == []


class TestRemoveInvalid:
    def test_removes_empty_title(self) -> None:
        articles = [
            _make_article(title="", url="https://example.com"),
            _make_article(title="Valid", url="https://example.com"),
        ]
        result = remove_invalid(articles)
        assert len(result) == 1
        assert result[0].title == "Valid"

    def test_removes_empty_url(self) -> None:
        articles = [
            _make_article(title="Valid", url=""),
            _make_article(title="Valid", url="https://example.com"),
        ]
        result = remove_invalid(articles)
        assert len(result) == 1

    def test_removes_whitespace_only(self) -> None:
        articles = [
            _make_article(title="  ", url="https://example.com"),
            _make_article(title="Valid", url="   "),
        ]
        result = remove_invalid(articles)
        assert len(result) == 0
