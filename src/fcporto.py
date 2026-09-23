"""Scraper for FC Porto main men's football team ticket announcements.

Strategy: the ticket platform (bilhetes.fcporto.pt) is a JS SPA, so instead
we watch the official news list https://www.fcporto.pt/pt/noticias for new
articles whose slug contains "bilhete" ("bilhetes-a-venda-para-...",
"informacao-sobre-os-bilhetes-para-...").

Only the main men's football team is kept by default: anything mentioning
modalities (andebol, basquetebol, voleibol, hoquei...), women's football,
youth or other events is classified as excluded.

Stdlib only: urllib + re.
"""

import re
import urllib.request
import html as htmlmod

HEADERS = {"User-Agent": "Mozilla/5.0 (futebol-script ticket bot)"}

# Slug/title keywords that mean "NOT men's senior football".
EXCLUDE_KEYWORDS = (
    "andebol",
    "basquetebol",
    "basket",
    "voleibol",
    "volei",
    "hoquei",
    "hóquei",
    "hockei",
    "bilhar",
    "ciclismo",
    "atletismo",
    "natacao",
    "natação",
    "feminino",
    "feminina",
    "racing-power",  # women's league opponent pattern
    "women",
    "sub-",
    "sub ",
    "juniores",
    "juvenis",
    "iniciados",
    "infantis",
    "esports",
    "dragon-force",
    "museu",
    "tour",
    "modalidades",
    "pavilh",
    "dragao-arena",
    "dragão-arena",
    "supertaca-de-basquetebol",
    "supertaça",
)


def fetch_html(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="ignore")


def list_ticket_articles(news_url: str, timeout: int = 30) -> list[dict]:
    """Return candidate ticket articles from the news listing page."""
    html = fetch_html(news_url, timeout=timeout)
    slugs = sorted(set(re.findall(r"/pt/noticias/([a-z0-9\-]+)", html)))
    out: list[dict] = []
    for slug in slugs:
        if "bilhete" not in slug:
            continue
        low = slug.lower()
        excluded = any(k in low for k in EXCLUDE_KEYWORDS)
        out.append(
            {
                "id": slug,
                "url": f"https://www.fcporto.pt/pt/noticias/{slug}",
                "slug": slug,
                "excluded": excluded,
            }
        )
    return out


def fetch_article_details(article_url: str, timeout: int = 30) -> dict:
    """Fetch article page: title + subcategory + subtitle.

    The listing page alone can't tell football from handball
    (e.g. 'FC Porto-Marítimo Madeira' is andebol). The detail page has:
      <span class="subcategory">Andebol|FC Porto|...</span>
      <h2>6.ª jornada do Campeonato Nacional de andebol ...</h2>
    Men's senior football uses subcategory 'FC Porto' + Estádio do Dragão.
    """
    try:
        html = fetch_html(article_url, timeout=timeout)
    except Exception:
        return {"title": "", "subcategory": "", "subtitle": ""}
    m = re.search(
        r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html
    )
    if m:
        title = htmlmod.unescape(m.group(1)).strip()
    else:
        mt = re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I)
        title = (
            re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", "", mt.group(1))).strip())
            if mt
            else ""
        )
    ms = re.search(
        r'class="subcategory"[^>]*>(.*?)<', html, flags=re.S | re.I
    )
    subcategory = (
        htmlmod.unescape(re.sub(r"<[^>]+>", "", ms.group(1))).strip()
        if ms
        else ""
    )
    mh = re.search(r"<h2[^>]*>(.*?)</h2>", html, flags=re.S | re.I)
    subtitle = (
        htmlmod.unescape(re.sub(r"<[^>]+>", "", mh.group(1))).strip()
        if mh
        else ""
    )
    subtitle = re.sub(r"\s+", " ", subtitle)
    return {"title": title, "subcategory": subcategory, "subtitle": subtitle}


def fetch_article_title(article_url: str, timeout: int = 30) -> str:
    """Backwards-compatible: title only."""
    return fetch_article_details(article_url, timeout=timeout).get("title", "")


# Subcategories that are NOT men's senior football.
EXCLUDE_SUBCATEGORIES = {
    "andebol",
    "basquetebol",
    "voleibol",
    "hóquei em patins",
    "hoquei em patins",
    "feminino",
    "futebol feminino",
    "dragon force",
    "museu",
    "clube",
}


def is_mens_football(title: str, slug: str, subcategory: str = "", subtitle: str = "") -> bool:
    low = f"{title} {slug} {subtitle}".lower()
    if any(k in low for k in EXCLUDE_KEYWORDS):
        return False
    sub = (subcategory or "").strip().lower()
    if sub:
        if sub in EXCLUDE_SUBCATEGORIES:
            return False
        # Men's senior football articles use subcategory "FC Porto".
        if sub not in ("fc porto", "futebol", "equipa principal"):
            return False
    # Venue heuristic: arena/pavilion = modalities, stadium = football.
    if re.search(r"dragão arena|dragao arena|pavilh", low) and "estádio do dragão" not in low:
        # ...unless the subtitle explicitly says football League/Champions
        if not re.search(r"liga (portugal|dos campeões|europa)|campeonato.*futebol|estádio do dragão", low):
            return False
    return True


def check_fcporto(
    news_url: str, timeout: int = 30, enrich_titles: bool = True
) -> list[dict]:
    """Full check: list candidates + (optionally) fetch titles for new ones."""
    candidates = list_ticket_articles(news_url, timeout=timeout)
    items: list[dict] = []
    for c in candidates:
        title, subcategory, subtitle = "", "", ""
        if enrich_titles:
            d = fetch_article_details(c["url"], timeout=timeout)
            title, subcategory, subtitle = (
                d.get("title", ""),
                d.get("subcategory", ""),
                d.get("subtitle", ""),
            )
        if not title:
            # Fallback: humanize slug
            title = c["slug"].replace("-pt-", " ").replace("-", " ").strip()
        excluded = c["excluded"] or not is_mens_football(
            title, c["slug"], subcategory, subtitle
        )
        full_title = title
        if subtitle and subtitle not in title:
            full_title = f"{title} — {subtitle}"
        items.append(
            {
                "id": c["id"],
                "url": c["url"],
                "title": full_title,
                "subcategory": subcategory,
                "excluded": excluded,
                "status": "on_sale",
            }
        )
    return items
