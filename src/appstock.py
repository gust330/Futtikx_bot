"""App-stock poller: talks to the *real* availability backend.

Problem: for Continente, true stock ("sold out or not") is only visible
inside the Cartão Continente app / store backend. The Fome de Vencer website
is a lagging indicator.

Solution: capture the app's stock API call once (see README "App capture
guide" - 10 min with HTTP Toolkit on Android), then this module polls that
same endpoint from GitHub Actions using credentials stored as secrets.

Config (config.json -> "appstock"):
  {
    "enabled": false,
    "url": "https://.../api/...",
    "method": "GET",
    "headers_env": "APPSTOCK_HEADERS_JSON",   // secret: '{"Authorization":"Bearer ..."}'
    "body_env": "APPSTOCK_BODY",              // optional secret for POST
    "timeout": 30,
    "watches": [
      {"id": "selecao-noruega", "json_path": "data.stock.available",
       "means_available": true},
      {"id": "selecao-gales", "json_path": "items.0.qty",
       "means_available": ">0"}
    ]
  }

json_path: dotted path into the JSON response, numeric parts index lists.
means_available: true/false (bool compare), ">0" (number compare) or any
  string (substring match against the value).

State: previous extracted value per watch id. Alerts when a watch flips to
"available" (or appears with an available value).
"""

import json
import os
import urllib.request


def _walk(obj, path: str):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            if part not in cur:
                return None
            cur = cur[part]
        else:
            return None
    return cur


def _is_available(value, rule) -> bool:
    if value is None:
        return False
    if isinstance(rule, bool):
        if isinstance(value, bool):
            return value is rule
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "yes", "available", "disponivel", "disponível", "em_stock"):
                return rule is True
            if v in ("false", "no", "soldout", "sold_out", "esgotado", "esgotados"):
                return rule is False
        if isinstance(value, (int, float)):
            return (value > 0) is rule
        return False
    if isinstance(rule, str) and rule.startswith(">"):
        try:
            return float(value) > float(rule[1:])
        except (TypeError, ValueError):
            return False
    return str(rule).lower() in str(value).lower()


def fetch_json(url: str, method: str, headers: dict, body: bytes | None,
               timeout: int):
    req = urllib.request.Request(
        url, data=body, headers=headers or {}, method=(method or "GET").upper()
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def check_appstock(cfg: dict) -> list[dict]:
    """Return watch results: [{id, value, available, raw_snippet}]."""
    headers: dict = {}
    if cfg.get("headers_env"):
        headers = json.loads(os.environ.get(cfg["headers_env"], "") or "{}")
    headers.setdefault("User-Agent", "Mozilla/5.0 (futebol-script ticket bot)")
    headers.setdefault("Accept", "application/json")
    body = None
    if cfg.get("body_env") and os.environ.get(cfg["body_env"]):
        body = os.environ[cfg["body_env"]].encode()
    data = fetch_json(
        cfg["url"], cfg.get("method", "GET"), headers, body,
        int(cfg.get("timeout", 30)),
    )
    out: list[dict] = []
    for w in cfg.get("watches", []):
        value = _walk(data, w.get("json_path", ""))
        available = _is_available(value, w.get("means_available", True))
        out.append(
            {
                "id": str(w.get("id", w.get("json_path", "?"))),
                "value": value,
                "available": available,
                "raw_snippet": json.dumps(value, ensure_ascii=False)[:200],
            }
        )
    return out
