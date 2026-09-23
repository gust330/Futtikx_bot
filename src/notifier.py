"""Telegram notifier (stdlib only)."""

import json
import urllib.parse
import urllib.request


def send_telegram(
    bot_token: str, chat_id: str, text: str, timeout: int = 30
) -> dict:
    """Send an HTML-formatted message via Bot API. Returns parsed JSON."""
    if not bot_token or not chat_id:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def fmt_continente_sale(game: dict, page_url: str) -> str:
    return (
        "🎟️ <b>BILHETES À VENDA — Seleção Portugal (Continente)</b>\n"
        f"⚽ {game['home']} vs {game['away']}\n"
        f"📅 {game.get('weekday', '')} {game.get('date', '')}"
        f" ⏰ {game.get('time', '')}\n"
        f"📍 {game.get('location', '')}\n"
        + (f"💰 Desde {game['price']}\n" if game.get("price") else "")
        + f"🔗 <a href=\"{page_url}\">Comprar na página Continente</a>"
    )


def fmt_continente_new(game: dict, page_url: str) -> str:
    return (
        "👀 <b>Novo jogo detetado — Seleção (Continente)</b>\n"
        f"⚽ {game['home']} vs {game['away']}\n"
        f"📅 {game.get('weekday', '')} {game.get('date', '')}"
        f" ⏰ {game.get('time', '')}\n"
        f"📍 {game.get('location', '')}\n"
        f"ℹ️ Estado: {game.get('status', '')} (ainda não à venda)\n"
        f"🔗 <a href=\"{page_url}\">Ver página</a>"
    )


def fmt_fcporto(item: dict) -> str:
    return (
        "🔵⚪ <b>BILHETES FC PORTO — equipa principal</b>\n"
        f"📰 {item['title']}\n"
        f"🔗 <a href=\"{item['url']}\">Ver anúncio oficial</a>\n"
        f"🎫 <a href=\"https://bilhetes.fcporto.pt/\">bilhetes.fcporto.pt</a>"
    )
