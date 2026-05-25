"""Descobre cards de LP de simulado entre 2026-01-01 e 2026-05-31 e sugere amostra diversa."""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.jira_client import search_issues

JQL = (
    'project = MC '
    'AND cf[10031] >= "2026-01-01" AND cf[10031] <= "2026-05-31" '
    'AND summary ~ "Simulado" '
    'AND summary !~ "Rodadas" '
    'AND summary !~ "CLONE" '
    'ORDER BY cf[10031] DESC'
)

FIELDS = ["summary", "status", "customfield_10031"]

VERT_RE = re.compile(r"\[([A-Z]{2,6})\]")
EXCLUDE_VERTICALS = {"ECJ", "OAB", "MIL", "EMIL", "MED", "EMED", "VEST", "EVEST"}

# quantos cards por vertical na amostra final
QUOTA = {
    "(sem vertical)": 4,
    "EE": 3,
    "ES": 2,
    "CFC": 1,
    "EEDU": 1,
}


def extract_vertical(summary: str) -> str:
    m = VERT_RE.search(summary)
    return m.group(1) if m else "(sem vertical)"


def pick_diverse(cards: list[tuple], quota: int) -> list[tuple]:
    """De uma lista ordenada por data DESC, pega quota cards distribuidos no tempo."""
    if len(cards) <= quota:
        return cards
    # divide a lista em quota fatias iguais e pega o primeiro de cada
    step = len(cards) / quota
    return [cards[int(i * step)] for i in range(quota)]


def main() -> None:
    issues = search_issues(JQL, fields=FIELDS, page_size=100, max_pages=10)
    print(f"Total: {len(issues)} cards\n")

    by_vertical: dict[str, list] = defaultdict(list)
    for issue in issues:
        summary = issue["fields"]["summary"]
        vert = extract_vertical(summary)
        if vert in EXCLUDE_VERTICALS:
            continue
        evento = (issue["fields"].get("customfield_10031") or "")[:10]
        by_vertical[vert].append((issue["key"], summary, evento))

    print(">>> AMOSTRA SUGERIDA (diversa por vertical + distribuida no tempo) <<<\n")
    selected: list[tuple] = []
    for vert, quota in QUOTA.items():
        cards = by_vertical.get(vert, [])
        picked = pick_diverse(cards, quota)
        if not picked:
            print(f"[{vert}]  (vertical sem cards no periodo)")
            continue
        print(f"[{vert}]  {len(picked)} de {len(cards)} disponiveis:")
        for key, summary, evento in picked:
            print(f"  {key}  ({evento})  {summary[:85]}")
            selected.append((key, summary, evento))
        print()

    print(f"TOTAL DA AMOSTRA: {len(selected)} cards\n")
    print("Chaves para baixar (lista pronta):")
    print("  " + " ".join(key for key, _, _ in selected))


if __name__ == "__main__":
    main()
