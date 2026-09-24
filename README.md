# ⚽ Futebol Ticket Bot

Warns you on Telegram the moment tickets go on sale — no advance-announcement needed.

**Sources:**
1. 🇵🇹 **Portugal national team** via **Continente** (`feed.continente.pt/fome-de-vencer`)
   - This page gives NO advance warning — it just flips from
     *"disponíveis em breve"* to a price (*"Desde € 20,00"*). The bot polls it.
   - ⚠️ The website **lags the app**: real stock (sold out or not) is only in the
     **App Cartão Continente**. See "App-only stock workaround" below.
2. 🔵⚪ **FC Porto men's senior football** via official news (`fcporto.pt/pt/noticias`)
   - Watches for new *"bilhetes"* articles, filtered to the men's first team
     (handball, basketball, women's, youth etc. are ignored via subcategory check).
3. 🗞️ **Press monitor** (Google News RSS) — early signal: every Continente sale
   is announced the same day by FPF/Record/A Bola/SAPO. Catches on-sale moments
   even when the website lags.
4. 📱 **App-stock poller** (optional, disabled by default) — polls the app's real
   stock endpoint once you capture it (guide below). This is the true fix for
   app-only availability.

Stdlib-only Python (no `pip install` needed). State in `state.json`, committed back
by the workflow so runs can diff.

## Live status (verified 2026-09-23)

| Game | Status |
|---|---|
| Portugal vs País de Gales 24/09 (Alvalade) | 🎟️ ON SALE desde € 20,00 (site; app may already be sold out!) |
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
git add -A && git commit -m "ticket bot" && git push
```
Repo → Settings → Secrets → Actions → add:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The workflow (`.github/workflows/check-tickets.yml`) runs **every 15 min**,
on every push to `main`, plus on-demand (Actions → check-tickets → Run workflow).
It commits `state.json` back so diffs persist. First run notifies current on-sale items.

### 3. Manual run
```bash
python3 check.py --once               # check + notify (needs env vars)
python3 check.py --check-only         # check, update state, no Telegram
python3 check.py --once --no-enrich   # skip FCP article detail fetch (faster)
```

## ⏰ Schedule not running every 15 min?

Checklist (most common first):

1. **Brand-new schedules take a while.** GitHub can take up to ~1h to start
   honouring a freshly pushed `schedule`, and every tick can be delayed several
   minutes under load. If the repo is < 1h old, wait through 2–3 ticks.
2. **Schedules only fire on the default branch.** Check the workflow file is on
   `main` (or your default branch) — manual "Run workflow" runs from any branch,
   schedules don't.
3. **Look in the right place:** Actions tab → left sidebar "check-tickets" →
   all runs. A red ❌ run still counts as "ran" — click it to see which step failed.
4. **Push-trigger test:** this workflow also runs on every `push` to `main`
   (except state-only commits). Push any small change — if a run appears, Actions
   works and it's purely the cron that's slow/disabled.
5. **Cron delays / pauses:** GitHub may heavily delay cron runs at peak times,
   and disables schedules after 60 days with no repo activity (re-enable with one
   manual run). Nothing to fix in code — it's platform behaviour.
6. **Still nothing after hours?** Re-save the workflow: make a trivial edit
   (e.g. a comment) and push — this re-registers the schedule.

To prove the loop works end-to-end for a day, set `"heartbeat": true` in
`config.json` (one "✅ check ok" Telegram message per run), then turn it off.

## 📱 App-only stock workaround (Continente)

The website can show "Desde € 20 / comprar" while the app is already sold out.
Three layers, easiest first:

**Layer 1 — press monitor (already on).** Same-day sale announcements from
FPF/press arrive via Google News RSS. No setup. It won't tell you about
sell-outs, but it tells you the minute sales *open* — which is when you must
buy in the app.

**Layer 2 — buy immediately on flip.** The website flip
coming-soon → on-sale still fires within minutes of the real opening, so the
Telegram alert means "open the app NOW". Ticket drops for the Seleção sell out
in hours; speed is the whole game.

**Layer 3 — poll the app's real endpoint (definitive).** Capture the stock API
call the app makes, then the bot polls it directly:

1. Android: install **HTTP Toolkit** (free), iPhone: **Proxyman** or **Stream**.
2. Route your phone through it (it installs a VPN/local proxy + CA cert).
3. Open the Cartão Continente app → go to the ticket purchase screen for a game.
4. In the capture, find the request returning stock/availability JSON
   (host will be something like `*.continente.pt` / `*.cartaocontinente.pt`).
   Note: URL, method, headers (Authorization!), and which JSON field flips
   between available/sold-out.
5. Add GitHub secrets: `APPSTOCK_HEADERS_JSON` =
   `{"Authorization": "Bearer PASTE", ...}` (and `APPSTOCK_BODY` if it's POST).
6. In `config.json`, set `appstock.enabled: true`, paste the `url`, and add a
   watch, e.g. `{"id": "selecao-noruega", "json_path": "data.available",
   "means_available": true}`. Adapt `json_path`/`means_available`
   (`true`, `">0"`, or a string to match) to the actual response shape.
7. Push → next run polls the real stock and alerts on flips to available.

Caveat: app tokens expire (days/weeks). When alerts stop / error alerts mention
`appstock`, repeat step 4–5 to refresh the secret.

## How detection works

- **Continente:** parses each game card; `game__priceGroup` (price) = `on_sale`,
  *"esgotados"* = `sold_out`, *"breve"* = `coming_soon`. Alerts on:
  new game found (so you're ready) + any flip **to** `on_sale` (urgent).
- **FC Porto:** lists `/pt/noticias/*bilhete*` slugs, fetches each detail page,
  reads `<span class="subcategory">` (`FC Porto` = men's football vs
  `Andebol`/`Basquetebol`/`Feminino`…) + subtitle. Alerts only on new men's
  senior-football items.
- **Press:** Google News RSS (`hl=pt-PT&gl=PT`, `when:7d`), keyword-filtered
  (`bilhete` required, reclamações/modalities excluded). Alerts on new matches.
- **Errors/heartbeat:** any source failure sends one ⚠️ Telegram message
  (`alert_on_error`, default on). Optional per-run ✅ heartbeat for debugging
  cadence (`heartbeat`, default off).

## Extending later
Add entries to `config.json` + a new module in `src/`. Note: `fpf.pt` and
`bilheteira.fpf.pt` sit behind Cloudflare bot protection (HTTP 403 to simple
fetchers incl. GitHub runners), so FPF coverage currently comes via the press
feed, which already includes FPF announcements.

## Limitations
- FC Porto listing shows ~27 latest articles (~1–2 days); polling every 15 min
  catches announcements while visible. A sitemap/API backfill could be added later.
- Continente page structure may change; `src/continente.py::parse_games` is the
  single place to adapt (segment-split on `game__date`).
