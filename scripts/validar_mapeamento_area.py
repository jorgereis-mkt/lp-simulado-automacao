"""Valida o mapeamento [EC] Area do Jira -> area= do form WP.

Pega o customfield_10065 de cada card baixado, strippa o prefixo [VERTICAL]
e mostra o valor que iria pro form.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CARDS_DIR = Path(__file__).resolve().parents[1] / "tests" / "cards_exemplo"

VERT_PREFIX_RE = re.compile(r"^\[[A-Z]{2,6}\]\s*")


def get_value(field) -> str | None:
    """Lida com select (dict com 'value'), multi-select (list) ou string."""
    if field is None:
        return None
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        return field.get("value") or field.get("name")
    if isinstance(field, list) and field:
        first = field[0]
        return first.get("value") if isinstance(first, dict) else str(first)
    return None


def strip_prefix(area: str) -> str:
    return VERT_PREFIX_RE.sub("", area).strip()


def main() -> None:
    files = sorted(CARDS_DIR.glob("*.json"))
    print(f"Validando mapeamento [EC] Area em {len(files)} cards\n")

    for f in files:
        card = json.loads(f.read_text(encoding="utf-8"))
        summary = card.get("fields", {}).get("summary", "")[:60]
        area_field = card.get("fields", {}).get("customfield_10065")
        cr_field = card.get("fields", {}).get("customfield_10628") or card.get("fields", {}).get("customfield_10623")

        area_raw = get_value(area_field)
        area_stripped = strip_prefix(area_raw) if area_raw else None

        print(f"--- {f.stem} ---")
        print(f"  summary: {summary}")
        print(f"  [EC] Area (raw): {area_raw}")
        print(f"  Area p/ form (sem [XX] prefix): {area_stripped}")
        print()


if __name__ == "__main__":
    main()
