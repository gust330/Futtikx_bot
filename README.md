# ⚽ Futtikx — Real-Time Football Ticket Tracker

> **Automated ticket availability monitor and Telegram alert bot for the Portugal National Football Team (Continente) and FC Porto.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](#technical-architecture)
[![Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-success.svg)](#technical-architecture)
[![Automation](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions%20(15m%20cron)-orange.svg?logo=githubactions&logoColor=white)](#automated-github-actions-workflow)
[![Alerts](https://img.shields.io/badge/Alerts-Telegram%20Bot%20API-2CA5E0.svg?logo=telegram&logoColor=white)](#telegram-setup)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## Overview

High-demand football tickets in Portugal—especially for the **Seleção Nacional** and **FC Porto**—frequently drop without advance scheduling and sell out within minutes.

**Futtikx** continuously monitors primary ticket endpoints, news portals, and app APIs, diffing availability state and dispatching instant Telegram notifications the moment tickets go live:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FUTTIKX MONITORING ENGINE                       │
├────────────────────────────────┬───────────────────────────────────────┤
│  [🇵🇹] Continente Feed          │  [🔵⚪] FC Porto Official News        │
│  · feed.continente.pt scraper  │  · fcporto.pt/pt/noticias scraper     │
│  · Detects coming_soon → on_sale│ · Filters to men's senior football   │
│  · Captures price & venue      │  · Ignores handball/basketball/youth  │
├────────────────────────────────┼───────────────────────────────────────┤
│  [🗞️] Press RSS Monitor        │  [📱] Mobile App-Stock Poller         │
│  · Google News RSS (pt-PT)     │  · Optional direct API polling        │
│  · Instant FPF press release   │  · Bypasses website web-cache lag     │
└────────────────────────────────┴───────────────────────────────────────┘
                                 │ State Diff Machine
                                 ▼
                    [⚡] state.json Persistence
                                 │
                                 ▼
               [📨] Telegram Notification Bot Dispatch
```

---

## Detection Layers

| Source | Target | Trigger Condition | Latency / Cadence |
|---|---|---|---|
| **Continente** | Portugal National Team | Card flips from *"Disponíveis em breve"* to a price (*"Desde € 20,00"*) | Every 15 min |
| **FC Porto** | Men's First Team | New article containing `"bilhete"` in the senior football category | Every 15 min |
| **Google News RSS** | FPF / A Bola / Record / O Jogo | Keyword match on ticket release press statements | Every 15 min |
| **App-Stock Poller** | Cartão Continente API | Direct inventory count checks via mobile API headers | Configurable |

---

## Technical Architecture

- **Zero Third-Party Dependencies**: Pure Python standard library (`urllib.request`, `json`, `html.parser`, `re`). Runs cleanly on any Python 3.10+ runtime without `pip install`.
- **State Machine (`state.json`)**: Tracks historical game statuses (`coming_soon`, `on_sale`, `sold_out`), timestamps, and notified hashes.
- **Git State Persistence**: GitHub Actions automatically commits `state.json` back to the default branch after state mutations, preventing alert duplicates across serverless runner instances.

---

## Setup & Configuration

### 1. Telegram Bot Setup
1. Message [@BotFather](https://t.me/BotFather) on Telegram and run `/newbot` to obtain your `TELEGRAM_BOT_TOKEN`.
2. Start a conversation with your bot.
3. Retrieve your `TELEGRAM_CHAT_ID` via `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates`.

### 2. Local Execution

```bash
# Clone the repository
git clone https://github.com/gust330/Futtikx_bot.git
cd Futtikx_bot

# Verify credentials with a test ping
TELEGRAM_BOT_TOKEN="your_token" TELEGRAM_CHAT_ID="your_chat_id" python3 check.py --notify-test

# Run a single inspection loop
TELEGRAM_BOT_TOKEN="your_token" TELEGRAM_CHAT_ID="your_chat_id" python3 check.py --once

# Run inspection without sending notifications (updates local state only)
python3 check.py --check-only
```

### 3. Automated GitHub Actions Workflow

To enable autonomous continuous monitoring:

1. Push your repository to GitHub.
2. In your repo: **Settings → Secrets and variables → Actions**, add:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot API token.
   - `TELEGRAM_CHAT_ID`: Your Telegram numeric chat ID.
3. The workflow (`.github/workflows/check-tickets.yml`) automatically triggers every 15 minutes, evaluates sources, updates `state.json`, and alerts on status changes.

---

## Project Structure

```
Futtikx_bot/
├── .github/workflows/
│   └── check-tickets.yml   # 15-minute cron runner and state commit pipeline
├── src/
│   ├── continente.py       # Continente Seleção ticket scraper
│   ├── fcporto.py          # FC Porto news parser and category filter
│   ├── press.py            # Portuguese sports media RSS monitor
│   ├── appstock.py         # App Cartão Continente reverse-engineered poller
│   ├── notifier.py         # Telegram Markdown message dispatcher
│   └── state.py            # JSON state manager and change detector
├── check.py                # Main CLI entrypoint
├── config.json             # Source URLs, keyword filters, and heartbeat settings
├── state.json              # Historical state cache
└── README.md
```

---

## Author & License

Engineered by **Gustavo Teixeira** ([@gust330](https://github.com/gust330)).  
Licensed under the [MIT License](LICENSE).
