"""Tiny JSON state store: remembers what we already alerted on."""

import json
import os


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"continente": {}, "fcporto": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("continente", {})
        data.setdefault("fcporto", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"continente": {}, "fcporto": {}}


def save_state(path: str, state: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)
