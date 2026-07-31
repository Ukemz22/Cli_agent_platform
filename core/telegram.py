"""
Minimal Telegram Bot API wrapper.
Only what Chapter 6 needs: sending a text message to a chat_id.
"""
import httpx

from core.config import settings


def send_telegram_message(chat_id: int, text: str) -> dict:
    """Send a plain text message to a Telegram chat. Raises on non-2xx."""
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    resp = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    resp.raise_for_status()
    return resp.json()
