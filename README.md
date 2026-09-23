# ⚽ Futebol Ticket Bot

Warns you on Telegram the moment tickets go on sale — no advance-announcement needed.

**Current scope (as requested):**
1. 🇵🇹 **Portugal national team** via **Continente** (`feed.continente.pt/fome-de-vencer`)
   - This page gives NO advance warning — it just flips from
     *"disponíveis em breve"* to a price (*"Desde € 20,00"*). The bot polls it.
2. 🔵⚪ **FC Porto men's senior football** via official news (`fcporto.pt/pt/noticias`)
   - Watches for new *"bilhetes"* articles, filtered to the men's first team
     (handball, basketball, women's, youth etc. are ignored via subcategory check).

Stdlib-only Python (no `pip install` needed). State in `state.json`, committed back
by the workflow so runs can diff.

## Live status (verified 2026-09-23)

| Game | Status |
|---|---|
| Portugal vs País de Gales 24/09 (Alvalade) | 🎟️ ON SALE desde € 20,00 |
| Portugal vs Noruega 04/10 (Dragão) | 👀 coming soon — bot will alert on flip |
| FC Porto men's football | no ticket news on page 1 right now (only andebol/basket/feminino, correctly ignored) |

## Setup (5 min)

### 1. Create a Telegram bot
1. Chat with [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.
2. Start a chat with your new bot (press Start).
3. Get your chat ID: open `https://api.telegram.org/bot<TOKEN>/getUpdates`
   after sending the bot a message, copy `"id"` from `"chat"`.

Test locally:
```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python3 check.py --notify-test
```

### 2. Push to GitHub + add secrets
```bash
git init && git add -A && git commit -m "ticket bot" && git push
```
Repo → Settings → Secrets → Actions → add:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The workflow (`.github/workflows/check-tickets.yml`) runs **every 15 min**
plus on-demand (Actions → check-tickets → Run workflow). It commits
`state.json` back so diffs persist. First run notifies current on-sale items.

### 3. Manual run
```bash
python3 check.py --once            # check + notify (needs env vars)
python3 check.py --check-only      # check, update state, no Telegram
python3 check.py --once --no-enrich  # skip FCP article detail fetch (faster)
```

## How detection works

- **Continente:** parses each game card; `game__priceGroup` (price) = `on_sale`,
  *"esgotados"* = `sold_out`, *"breve"* = `coming_soon`. Alerts on:
  new game found (so you're ready) + any flip **to** `on_sale` (urgent).
- **FC Porto:** lists `/pt/noticias/*bilhete*` slugs, fetches each detail page,
  reads `<span class="subcategory">` (`FC Porto` = men's football vs
  `Andebol`/`Basquetebol`/`Feminino`…) + subtitle. Alerts only on new men's
  senior-football items.

## Extending later
Add entries to `config.json` + a new module in `src/` (e.g. `benfica.py`,
`fpf.py` — FPF sells national-team tickets *before* Continente, good early signal).
`check.py` is structured for extra sources.

## Limitations
- FC Porto listing shows ~27 latest articles (~1–2 days); polling every 15 min
  catches announcements while visible. A sitemap/API backfill could be added later.
- Continente page structure may change; `src/continente.py::parse_games` is the
  single place to adapt (segment-split on `game__date`).
