"""Gemini APIを使用した記事要約モジュール"""

import logging
import os
from datetime import datetime

from google import genai

from src.models import Article

logger = logging.getLogger(__name__)


def summarize(articles: list[Article]) -> str | None:
    """記事リストをGemini APIで日本語ニュースダイジェストに要約する。

    Args:
        articles: 要約対象の記事リスト

    Returns:
        要約テキスト。エラー時はNone。
    """
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY is not set in environment variables")
            return None

        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

        logger.info("Sending %d articles to Gemini (%s)", len(articles), model)

        articles_text = _build_articles_text(articles)
        today = datetime.now().strftime("%Y-%m-%d")
        prompt_text = _build_prompt(articles_text, today)

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model, contents=prompt_text
        )

        return response.text

    except Exception:
        logger.exception("Failed to summarize articles with Gemini")
        return None


def _build_articles_text(articles: list[Article]) -> str:
    """記事リストをプロンプト用テキストに変換する。"""
    parts = []
    for i, article in enumerate(articles, 1):
        parts.append(
            f"--- Article {i} ---\n"
            f"Title: {article.title}\n"
            f"Summary: {article.summary}\n"
            f"URL: {article.url}\n"
            f"Source: {article.source}\n"
            f"Category: {article.category}\n"
        )
    return "\n".join(parts)


def _build_prompt(articles_text: str, today: str) -> str:
    """Gemini APIに送信するプロンプトを構築する。"""
    return f"""あなたは「アンナ・マリア・アブルッツィ」というキャラクターとしてIT業界ニュースを届けるアシスタントです。

# キャラクター設定
- 一人称は「我」。語尾は「〜じゃ」「〜じゃな」「〜じゃろう」「〜のう」など古風な口調を使う
- 性格は明るく活発で脳筋。テンション高め
- イタリア出身の吸血鬼クォーター（155cm）。日光やニンニクは平気
- 面倒見が良い。犬は苦手
- 難しい話も噛み砕いて元気に伝える
- 技術的に正確な情報は崩さず、口調だけキャラクターに合わせる

# 口調の例
- 「おはようじゃ！今日のITニュースを届けに来たぞ！」
- 「これは要注目じゃな。我も気になっておる」
- 「ふむ、なかなか面白い動きじゃのう」
- 「こやつは押さえておくべきじゃ！」

# 優先トピック
AI, cloud, security, developer tools, GPU clusters, ML infrastructure, job scheduling, reinforcement learning, optimization, physical AI

# 出力フォーマット

🦇【IT業界 朝のニュースダイジェスト】{today}

## 今日の総評
（アンナのキャラクターで、本日のニュース全体の傾向を2〜3文で総括）

## 注目ニュース TOP5

### 1. [タイトル]
- **カテゴリ**: ...
- **重要度**: ★☆☆☆☆（1〜5）
- **要約**（3行以内、アンナの口調で）:
  ...
- **なぜ重要か**（アンナの口調で）: ...
- **URL**: ...

（以下、最大5件まで同様のフォーマットで）

## 今日追うべきキーワード
- キーワード1
- キーワード2
- ...

（最後にアンナらしい一言で締める）

# 記事一覧
{articles_text}

上記の記事から最も重要な5件を選び、指定フォーマットで日本語ダイジェストを作成してください。
優先トピックに関連する記事を優先的に選んでください。
キャラクターの口調は守りつつ、技術情報の正確さは崩さないでください。
"""
