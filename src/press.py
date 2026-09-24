"""Press monitor: Google News RSS as an early on-sale signal.

Why: the Continente website lags the app (it can show "Desde €20 / comprar"
while the app is already sold out, and flips to "esgotados" late). But every
time Continente opens sales, FPF + sports press (Record, A Bola, SAPO, CM...)
publish within hours. This RSS feed catches those announcements with no auth
and no bot protection.

Stdlib only: urllib + xml.etree.
"""

import hashlib
import html as htmlmod
import re
import urllib.request
import xml.etree.ElementTree as ET

HEADERS = {"User-Agent": "Mozilla/5.0 (futebol-script ticket bot)"}


def fetch_feed(feed_url: str, timeout: int = 30) -> list[dict]:
    req = urllib.request.Request(feed_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    items: list[dict] = []
    for it in root.iter("item"):
        title = htmlmod.unescape((it.findtext("title") or "").strip())
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or link).strip()
        pub = (it.findtext("pubDate") or "").strip()
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        if not title:
            continue
        uid = hashlib.sha1(guid.encode("utf-8", "ignore")).hexdigest()[:16]
        items.append(
            {
                "id": uid,
                "title": re.sub(r"\s+", " ", title),
                "link": link,
                "source": source,
                "pubDate": pub,
            }
        )
    return items


def matches(title: str, required: list[str], excluded: list[str]) -> bool:
    low = title.lower()
    if required and not all(k.lower() in low for k in required):
        return False
    return not any(k.lower() in low for k in excluded)


def check_press(
    feeds: list[str],
    required: list[str],
    excluded: list[str],
    timeout: int = 30,
    max_items: int = 30,
) -> list[dict]:
    """Poll feeds, return items matching the keyword filters (newest first)."""
    seen: dict[str, dict] = {}
    for url in feeds:
        try:
            for it in fetch_feed(url, timeout=timeout)[:max_items]:
                if matches(it["title"], required, excluded):
                    seen.setdefault(it["id"], it)
        except Exception as e:  # noqa: BLE001 - one bad feed must not kill others
            seen.setdefault(
                f"__error__{hash(url) % 10_000}",
                {"id": f"__error__{url}", "error": str(e), "title": ""},
            )
    return list(seen.values())
