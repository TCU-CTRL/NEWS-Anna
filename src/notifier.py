"""Discord Webhook通知モジュール"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_to_discord(messages: list[str], webhook_url: str | None = None) -> bool:
    """Discord Webhookへメッセージリストを送信する"""
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        logger.error("Discord Webhook URL が設定されていません")
        return False

    all_ok = True
    for i, message in enumerate(messages, 1):
        try:
            resp = requests.post(url, json={
                "content": message,
                "username": "NEWSアンナちゃん",
            })
            if resp.ok:
                logger.info("Message %d/%d sent successfully", i, len(messages))
            else:
                logger.error(
                    "Message %d/%d failed: %d %s",
                    i,
                    len(messages),
                    resp.status_code,
                    resp.text,
                )
                all_ok = False
        except Exception:
            logger.exception("Message %d/%d raised an exception", i, len(messages))
            all_ok = False

    return all_ok
