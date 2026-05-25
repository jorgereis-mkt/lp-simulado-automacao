"""Roda o parser em todos os JSONs de tests/cards_exemplo/ e tabula resultados."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.briefing_parser import parse_briefing

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CARDS_DIR = Path(__file__).resolve().parents[1] / "tests" / "cards_exemplo"

# campos obrigatorios em card normal
OBRIGATORIOS = [
    "data_hora_evento", "titulo_evento", "vertical", "area", "cr",
    "link_pacote", "link_artigo", "utms",
]
# campos opcionais (podem nao existir, nao conta como falha)
OPCIONAIS = ["link_whatsapp", "tem_promocao", "duracao_prova", "tabela_disciplinas_md"]


def status(v) -> str:
    if v is None or v == "" or v == []:
        return "."
    return "OK"


def main() -> None:
    files = sorted(CARDS_DIR.glob("*.json"))
    print(f"Testando parser em {len(files)} cards\n")

    rows = []
    for f in files:
        card = json.loads(f.read_text(encoding="utf-8"))
        parsed = parse_briefing(card)
        rows.append((f.stem, parsed))

    header = ["card", "tipo"] + [c[:6] for c in OBRIGATORIOS] + [c[:5] for c in OPCIONAIS]
    widths = [12, 7] + [6] * len(OBRIGATORIOS) + [5] * len(OPCIONAIS)

    print(" ".join(h.ljust(w) for h, w in zip(header, widths)))
    print(" ".join("-" * w for w in widths))

    falhas_obrigatorias = 0
    cards_normais = 0
    cards_matriz = 0

    for key, p in rows:
        tipo = "MATRIZ" if p.get("is_card_matriz") else "normal"
        if p.get("is_card_matriz"):
            cards_matriz += 1
        else:
            cards_normais += 1

        cells = [key, tipo]
        for c in OBRIGATORIOS:
            if p.get("is_card_matriz"):
                cells.append("-")
                continue
            s = status(p.get(c))
            cells.append(s)
            if s == ".":
                falhas_obrigatorias += 1
        for c in OPCIONAIS:
            cells.append(status(p.get(c)))
        print(" ".join(cells[i].ljust(widths[i]) for i in range(len(cells))))

    total_campos_obrig = cards_normais * len(OBRIGATORIOS)
    cobertura = 100 * (total_campos_obrig - falhas_obrigatorias) / max(total_campos_obrig, 1)
    print(f"\nCobertura de campos OBRIGATORIOS em cards normais: {cobertura:.1f}% ({total_campos_obrig - falhas_obrigatorias}/{total_campos_obrig})")
    print(f"Cards normais: {cards_normais}  |  Cards MATRIZ: {cards_matriz}")

    print("\n--- Detalhe dos cards normais com falha ---")
    achou_falha = False
    for key, p in rows:
        if p.get("is_card_matriz"):
            continue
        missing = [c for c in OBRIGATORIOS if status(p.get(c)) == "."]
        if missing:
            achou_falha = True
            print(f"\n{key}: falta -> {', '.join(missing)}")
    if not achou_falha:
        print("(nenhum card normal com falha em campo obrigatorio)")


if __name__ == "__main__":
    main()
