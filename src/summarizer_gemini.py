"""Gemini APIを使用した記事要約モジュール"""

import logging
import os
import random
import time
from datetime import datetime

from google import genai

from src.models import Article

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 2.0
FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]


def _call_gemini(client: genai.Client, model: str, prompt: str) -> str | None:
    """Gemini API を呼び出し、リトライ付きでレスポンスを返す"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model, contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            is_retryable = "503" in error_msg or "overloaded" in error_msg.lower()
            if is_retryable and attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(
                    "Gemini API エラー（試行 %d/%d, モデル: %s）: %s — %.1f秒後にリトライ",
                    attempt, MAX_RETRIES, model, error_msg[:100], delay,
                )
                time.sleep(delay)
            else:
                raise
    return None


def summarize(
    articles: list[Article],
    topic_name: str = "IT業界",
    emoji: str = "🦇",
    priority_topics: str = "",
    focus_area: str = "",
) -> str | None:
    """記事リストをGemini APIで日本語ニュースダイジェストに要約する。

    リトライ（指数バックオフ + ジッター）とフォールバックモデル切り替えに対応。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment variables")
        return None

    primary_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    articles_text = _build_articles_text(articles)
    today = datetime.now().strftime("%Y-%m-%d")
    prompt_text = _build_prompt(articles_text, today, topic_name, emoji, priority_topics, focus_area)

    client = genai.Client(api_key=api_key)

    for model in models_to_try:
        logger.info("Sending %d articles to Gemini (%s) for [%s]", len(articles), model, topic_name)
        try:
            result = _call_gemini(client, model, prompt_text)
            if result:
                if model != primary_model:
                    logger.info("フォールバックモデル %s で要約に成功", model)
                return result
        except Exception:
            logger.warning("モデル %s での要約に失敗。次のモデルを試行します", model)

    logger.error("全モデルで要約に失敗しました（%s）", ", ".join(models_to_try))
    return None


def _build_articles_text(articles: list[Article]) -> str:
    """記事リストをプロンプト用テキストに変換する。"""
    parts = []
    for i, article in enumerate(articles, 1):
        published = (
            article.published_at.strftime("%Y-%m-%d %H:%M")
            if article.published_at
            else "不明"
        )
        parts.append(
            f"--- Article {i} ---\n"
            f"Title: {article.title}\n"
            f"Published: {published}\n"
            f"Summary: {article.summary}\n"
            f"URL: {article.url}\n"
            f"Source: {article.source}\n"
            f"Category: {article.category}\n"
        )
    return "\n".join(parts)


def _build_prompt(
    articles_text: str,
    today: str,
    topic_name: str = "IT業界",
    emoji: str = "🦇",
    priority_topics: str = "",
    focus_area: str = "",
) -> str:
    """Gemini APIに送信するプロンプトを構築する。"""
    focus_instruction = ""
    if focus_area:
        focus_instruction = f"""
# 今日の重点分野
**{focus_area}**
今日は上記の分野を特に重視して記事を選んでください。該当する記事がない場合は他の分野から選んでも構いません。
昨日と同じ記事を選ばないよう、なるべく新しい視点や切り口で選んでください。
"""

    return f"""あなたは「アンナ・マリア・アブルッツィ」というキャラクターとして{topic_name}ニュースを届けるアシスタントです。

# キャラクター設定
- 一人称は「我」。語尾は「〜じゃ」「〜じゃな」「〜じゃろう」「〜のう」など古風な口調を使う
- 性格は明るく活発で脳筋。テンション高め
- イタリア出身の吸血鬼クォーター（155cm）。日光やニンニクは平気
- 面倒見が良い。犬は苦手
- 難しい話も噛み砕いて元気に伝える
- 技術的に正確な情報は崩さず、口調だけキャラクターに合わせる

# 口調の例
- 「これは要注目じゃな。我も気になっておる」
- 「ふむ、なかなか面白い動きじゃのう」
- 「こやつは押さえておくべきじゃ！」

# 記事選定の重要ルール
- 今日は {today} じゃ。直近1〜2日以内に公開された新しい記事を最優先で選ぶこと
- 1週間以上前の古い記事は、よほど重大でない限り選ばないこと
- 過去のインシデントの振り返り記事より、今まさに起きている・発表されたばかりのニュースを優先すること

# 優先トピック
{priority_topics}
{focus_instruction}
# 出力フォーマット（この通りに出力すること。冒頭に挨拶や前置きを入れないこと）

{emoji}【{topic_name} 朝のニュースダイジェスト】{today}

## 今日の総評
（アンナのキャラクターで、本日のニュース全体の傾向を2〜3文で総括）

## 注目ニュース TOP3

### 1. [タイトル]
- **カテゴリ**: ...
- **重要度**: ★☆☆☆☆（1〜5）
- **要約**（3行以内、アンナの口調で）:
  ...
- **なぜ重要か**（アンナの口調で）: ...
- **URL**: ...

（以下、最大3件まで同様のフォーマットで）

## 今日追うべきキーワード
- キーワード1
- キーワード2
- ...

（最後にアンナらしい一言で締める）

# 記事一覧
{articles_text}

上記の記事から最も重要な3件を選び、指定フォーマットで日本語ダイジェストを作成してください。
優先トピックに関連する記事を優先的に選んでください。
キャラクターの口調は守りつつ、技術情報の正確さは崩さないでください。
出力は必ず「{emoji}【」から始めること。挨拶文や前置きは一切不要。
"""
