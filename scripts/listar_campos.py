"""Lista custom fields do Jira que parecem relevantes pro briefing de simulado."""
from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.jira_client import _auth

KEYWORDS = ["data", "event", "evento", "vertical", "promo", "area", "área", "cr", "utm"]


def main() -> None:
    base, email, token = _auth()
    r = requests.get(f"{base}/rest/api/3/field", auth=(email, token), timeout=30)
    r.raise_for_status()
    fields = r.json()

    print(f"Total de campos no Jira: {len(fields)}\n")
    print("Campos com nome relevante (case-insensitive):\n")

    for f in fields:
        name = f.get("name", "")
        name_lower = name.lower()
        if any(k in name_lower for k in KEYWORDS):
            print(f"  {f.get('id', '?'):<35} {name}")


if __name__ == "__main__":
    main()
