#!/usr/bin/env python3
"""Ticket-sale watchdog: Continente (Seleção) + FC Porto (men's football).

- Polls both sources, compares with state.json, sends Telegram alerts on:
  * Continente: NEW game found (coming soon) + flip to ON SALE (the key event,
    since Continente gives no advance warning).
  * FC Porto: NEW "bilhetes" news article for the men's senior football team.
- Stdlib only, so it runs on GitHub Actions without pip install.

Usage:
    TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python3 check.py --once
    python3 check.py --check-only        # no Telegram, just print + update state
    python3 check.py --notify-test       # send a test message to Telegram

State file (state.json) must be committed back to the repo by the workflow
so consecutive runs can diff.
"""

import argparse
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from continente import check_continente  # noqa: E402
from fcporto import check_fcporto  # noqa: E402
from press import check_press  # noqa: E402
from appstock import check_appstock  # noqa: E402
from notifier import (  # noqa: E402
    fmt_appstock,
    fmt_continente_new,
    fmt_continente_sale,
    fmt_error,
    fmt_fcporto,
    fmt_press,
    send_telegram,
)
from state import load_state, save_state  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


def load_config() -> dict:
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single check (default)")
    ap.add_argument("--check-only", action="store_true", help="no Telegram sends")
    ap.add_argument("--notify-test", action="store_true", help="send test msg")
    ap.add_argument("--no-enrich", action="store_true", help="skip FCP title fetch")
    args = ap.parse_args()

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if args.notify_test:
        r = send_telegram(bot_token, chat_id, "✅ Bot de bilhetes ativo. Vais ser avisado aqui.")
        print(json.dumps(r, ensure_ascii=False)[:300])
        return 0

    cfg = load_config()
    state_path = os.path.join(BASE, cfg.get("state_file", "state.json"))
    state = load_state(state_path)
    timeout = int(cfg.get("request_timeout", 30))

    events: list[str] = []  # telegram HTML messages
    summary: dict = {"continente": [], "fcporto": [], "errors": []}

    # ---- 1. Continente ----
    page_used = cfg.get("continente_url", "")
    try:
        urls = [cfg["continente_url"]] + cfg.get("continente_fallback_urls", [])
        games, page_used = check_continente(urls, timeout=timeout)
        summary["continente_page"] = page_used
        for g in games:
            prev = state["continente"].get(g["id"])
            prev_status = prev.get("status") if isinstance(prev, dict) else None
            summary["continente"].append(
                {"id": g["id"], "status": g["status"], "prev": prev_status}
            )
            # New game, not on sale yet -> FYI alert (so you're ready)
            if prev is None and g["status"] != "on_sale":
                if cfg.get("alert_on_coming_soon", True) and not args.check_only:
                    events.append(fmt_continente_new(g, page_used))
            # Flip to on sale (or brand-new game already on sale) -> URGENT
            if g["status"] == "on_sale" and prev_status != "on_sale":
                if cfg.get("alert_on_sale", True) and not args.check_only:
                    events.append(fmt_continente_sale(g, page_used))
            state["continente"][g["id"]] = g
    except Exception as e:  # noqa: BLE001
        summary["errors"].append(f"continente: {e}")
        traceback.print_exc()

    # ---- 2. FC Porto ----
    try:
        items = check_fcporto(
            cfg.get("fcporto_news_url", "https://www.fcporto.pt/pt/noticias"),
            timeout=timeout,
            enrich_titles=not args.no_enrich,
        )
        for it in items:
            if it.get("excluded"):
                # remember excluded too so we don't refetch titles forever
                state["fcporto"].setdefault(it["id"], it)
                continue
            is_new = it["id"] not in state["fcporto"]
            summary["fcporto"].append({"id": it["id"], "new": is_new})
            if is_new and not args.check_only:
                events.append(fmt_fcporto(it))
            state["fcporto"][it["id"]] = it
    except Exception as e:  # noqa: BLE001
        summary["errors"].append(f"fcporto: {e}")
        traceback.print_exc()

    # ---- 3. Press (Google News RSS early signal) ----
    try:
        pcfg = cfg.get("press", {})
        if pcfg.get("enabled"):
            for it in check_press(
                pcfg.get("feeds", []),
                pcfg.get("required_keywords", ["bilhete"]),
                pcfg.get("exclude_keywords", []),
                timeout=timeout,
                max_items=int(pcfg.get("max_items", 30)),
            ):
                if it.get("error"):
                    summary["errors"].append(f"press feed: {it['error'][:120]}")
                    continue
                is_new = it["id"] not in state.setdefault("press", {})
                summary.setdefault("press", []).append(
                    {"id": it["id"], "new": is_new, "title": it["title"][:80]}
                )
                if is_new and not args.check_only:
                    events.append(fmt_press(it))
                state["press"][it["id"]] = it
            # cap stored press items so state.json doesn't grow forever
            if len(state.get("press", {})) > 300:
                keep = sorted(state["press"]) [-300:]
                state["press"] = {k: state["press"][k] for k in keep}
    except Exception as e:  # noqa: BLE001
        summary["errors"].append(f"press: {e}")
        traceback.print_exc()

    # ---- 4. App stock (real availability, user-captured endpoint) ----
    try:
        acfg = cfg.get("appstock", {})
        if acfg.get("enabled") and acfg.get("url"):
            for w in check_appstock(acfg):
                prev = state.setdefault("appstock", {}).get(w["id"])
                prev_av = prev.get("available") if isinstance(prev, dict) else None
                summary.setdefault("appstock", []).append(
                    {"id": w["id"], "available": w["available"], "prev": prev_av}
                )
                if w["available"] and prev_av is not True and not args.check_only:
                    events.append(fmt_appstock(w["id"], w["raw_snippet"]))
                state["appstock"][w["id"]] = w
    except Exception as e:  # noqa: BLE001
        summary["errors"].append(f"appstock: {e}")
        traceback.print_exc()

    # ---- 5. Notify ----
    sent = 0
    notify = list(events)
    if summary["errors"] and cfg.get("alert_on_error") and not args.check_only:
        notify.append(fmt_error(summary["errors"]))
    if cfg.get("heartbeat") and not args.check_only:
        notify.append("✅ Bot check ok — sem novidades.")
    if notify and not args.check_only:
        if not bot_token or not chat_id:
            print("WARN: no Telegram creds, printing events instead:")
            for ev in notify:
                print("----\n" + ev)
        else:
            for ev in notify:
                try:
                    send_telegram(bot_token, chat_id, ev)
                    sent += 1
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
    summary["events"] = len(events)
    summary["sent"] = sent

    save_state(state_path, state)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
