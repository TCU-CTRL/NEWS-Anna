"""メッセージ分割のテスト"""

from src.formatter import format_fallback, split_messages
from src.models import Article


class TestSplitMessages:
    def test_short_text_not_split(self) -> None:
        text = "Hello World"
        result = split_messages(text)
        assert result == ["Hello World"]

    def test_exact_limit_not_split(self) -> None:
        text = "a" * 2000
        result = split_messages(text)
        assert len(result) == 1
        assert len(result[0]) == 2000

    def test_over_limit_split(self) -> None:
        text = "a" * 3000
        result = split_messages(text, limit=2000)
        assert len(result) == 2
        assert all(len(chunk) <= 2000 for chunk in result)

    def test_split_at_newline(self) -> None:
        # 1000文字 + 改行 + 1500文字 = 2501文字
        text = "a" * 1000 + "\n" + "b" * 1500
        result = split_messages(text, limit=2000)
        assert len(result) == 2
        assert result[0] == "a" * 1000
        assert result[1] == "b" * 1500

    def test_all_chunks_within_limit(self) -> None:
        text = "line\n" * 1000  # 5000文字
        result = split_messages(text, limit=2000)
        assert all(len(chunk) <= 2000 for chunk in result)

    def test_no_content_lost(self) -> None:
        text = "Hello\nWorld\nFoo\nBar"
        result = split_messages(text, limit=10)
        combined = "\n".join(result)
        # 分割しても全テキストが保持される
        assert "Hello" in combined
        assert "World" in combined
        assert "Foo" in combined
        assert "Bar" in combined


class TestFormatFallback:
    def test_fallback_header(self) -> None:
        articles = [
            Article(
                title="Test Article",
                url="https://example.com",
                source="Test",
                category="test",
                published_at=None,
                summary="Summary",
                score=5.0,
            )
        ]
        result = format_fallback(articles)
        assert len(result) >= 1
        assert "Gemini APIが不調" in result[0]

    def test_fallback_max_5_articles(self) -> None:
        articles = [
            Article(
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                source="Test",
                category="test",
                published_at=None,
                summary="Summary",
                score=float(i),
            )
            for i in range(10)
        ]
        result = format_fallback(articles)
        combined = "".join(result)
        # 最大5件のみ含まれる
        assert "Article 0" in combined
        assert "Article 2" in combined
        assert "Article 3" not in combined

    def test_fallback_chunks_within_limit(self) -> None:
        articles = [
            Article(
                title=f"Long Article Title {i}",
                url=f"https://example.com/{i}",
                source="Test Source",
                category="test",
                published_at=None,
                summary="A" * 200,
                score=float(i),
            )
            for i in range(5)
        ]
        result = format_fallback(articles)
        assert all(len(chunk) <= 2000 for chunk in result)
