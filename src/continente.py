"""Scraper for Portugal national-team tickets sold via Continente.

Source: https://feed.continente.pt/fome-de-vencer

Page behaviour observed (Sep 2026):
- Each game shows home/away, date, competition/location and EITHER
  a price block ("Desde € 20,00" + comprar) meaning ON SALE,
  OR a notification message:
    "Os bilhetes para este jogo estarão disponíveis em breve." (coming soon)
    "Os bilhetes para este jogo encontram-se esgotados." (sold out)

There is no advance-sale announcement, so polling this page is the only
way to catch the moment it flips to on-sale.

Stdlib only: urllib + re (no bs4 needed).
"""

import re
import unicodedata
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (futebol-script ticket bot)"}


def fetch_html(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # page declares utf-8; fall back gracefully
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s


def parse_games(html: str, source_url: str) -> list[dict]:
    """Extract game cards from the Continente page HTML.

    Robust approach: split the page at each ``game__date`` marker. Each
    segment then holds one game (date, teams, location + price/notification).
    """
    games: list[dict] = []
    starts = [m.start() for m in re.finditer(r'<div class="game__date">', html)]
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else s + 12000
        seg = html[s:e]

        m_date = re.search(r'<div class="game__date">(.*?)</div>', seg, flags=re.S)
        date_txt = strip_tags(m_date.group(1)) if m_date else ""
        dm = re.search(
            r"(\w+)?\s*(\d{1,2}/\d{1,2})\s*\|\s*(\d{1,2}:\d{2})", date_txt
        )
        weekday = dm.group(1) if dm else ""
        date = dm.group(2) if dm else date_txt
        time = dm.group(3) if dm else ""

        teams = re.findall(r'<p class="game__teamName">(.*?)</p>', seg, flags=re.S)
        home = strip_tags(teams[0]) if len(teams) > 0 else ""
        away = strip_tags(teams[1]) if len(teams) > 1 else ""
        if not home and not away:
            continue

        loc_m = re.search(r'<p class="game__location">(.*?)</p>', seg, flags=re.S)
        location = strip_tags(loc_m.group(1)) if loc_m else ""

        status = "coming_soon"
        price = ""
        if "game__priceGroup" in seg:
            pm = re.search(r"€\s*([\d.,]+)", seg)
            price = f"€ {pm.group(1)}" if pm else "on sale"
            status = "on_sale"
        else:
            notif_m = re.search(
                r'<div class="notificationMsg[^"]*".*?<p>(.*?)</p>', seg, flags=re.S
            )
            msg = strip_tags(notif_m.group(1)).lower() if notif_m else ""
            if "esgot" in msg:
                status = "sold_out"
            elif "breve" in msg:
                status = "coming_soon"
            elif msg:
                status = "coming_soon"

        gid = slugify(f"{home}-vs-{away}-{date}-{time}")
        games.append(
            {
                "id": gid or slugify(f"{home}-{away}"),
                "home": home,
                "away": away,
                "date": date,
                "time": time,
                "weekday": weekday,
                "location": location,
                "status": status,
                "price": price,
                "source": source_url,
            }
        )
    return games


def check_continente(urls: list[str], timeout: int = 30) -> tuple[list[dict], str]:
    """Try primary + fallback URLs, return (games, url_used)."""
    last_err: Exception | None = None
    for url in urls:
        try:
            html = fetch_html(url, timeout=timeout)
            games = parse_games(html, url)
            if games:
                return games, url
            # Empty parse counts as failure -> try next URL
            last_err = ValueError(f"no games parsed from {url}")
        except Exception as e:  # noqa: BLE001 - report all fetch errors
            last_err = e
    raise RuntimeError(f"Continente fetch failed: {last_err}")
