"""Discord向けメッセージフォーマッター"""

from src.models import Article


def split_messages(text: str, limit: int = 2000) -> list[str]:
    """テキストを指定文字数で分割する。改行位置で分割を優先する"""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        # 改行位置で分割を優先
        split_pos = remaining.rfind("\n", 0, limit)
        if split_pos == -1:
            split_pos = limit
        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def format_digest(digest_text: str) -> list[str]:
    """AI要約テキストをDiscord向けに整形し、2000文字制限で分割して返す"""
    return split_messages(digest_text)


def format_fallback(articles: list[Article]) -> list[str]:
    """フォールバック用の簡易ダイジェスト生成。スコア上位5件のタイトル・サマリー・URLを表示"""
    header = "🦇 す、すまぬ…！Gemini APIが不調でうまく要約できなかったのじゃ…。代わりにRSS情報をもとに簡易ダイジェストを届けるぞ！\n\n"

    entries: list[str] = []
    for article in articles[:5]:
        summary = article.summary
        if len(summary) > 200:
            summary = summary[:197] + "..."

        entry = (
            f"**{article.title}**\n"
            f"📰 {article.source} | 📂 {article.category}\n"
            f"{summary}\n"
            f"{article.url}"
        )
        entries.append(entry)

    text = header + "\n\n".join(entries)
    return split_messages(text)
