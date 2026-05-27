"""Cria a pagina de sucesso de simulado a partir de um card Jira.

Default = DRY-RUN. --commit posta como rascunho. --slug-prefix=X prefixa.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import wp_client
from src.briefing_parser import parse_briefing
from src.lp_creator import slugify
from src.sucesso_creator import build_sucesso_payload

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "tests" / "cards_exemplo"
TEMPLATES_DIR = ROOT / "tests" / "lp_templates"
TEMPLATE_SLUG = "sucesso-simulados-finais-tce-sc-auditor-fiscal-de-controle-externo-pos-edital"


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/criar_sucesso.py <CHAVE_DO_CARD> [--commit] [--slug-prefix=X] [--update-id=N]")
        sys.exit(1)

    card_key = sys.argv[1]
    do_commit = "--commit" in sys.argv
    slug_prefix = ""
    update_id: int | None = None
    for arg in sys.argv[2:]:
        if arg.startswith("--slug-prefix="):
            slug_prefix = arg.split("=", 1)[1]
        elif arg.startswith("--update-id="):
            update_id = int(arg.split("=", 1)[1])

    card_path = CARDS_DIR / f"{card_key}.json"
    template_path = TEMPLATES_DIR / f"{TEMPLATE_SLUG}.html"
    if not card_path.exists() or not template_path.exists():
        print(f"Faltam arquivos: {card_path} ou {template_path}")
        sys.exit(1)

    card = json.loads(card_path.read_text(encoding="utf-8"))
    template_raw = template_path.read_text(encoding="utf-8")
    briefing = parse_briefing(card)

    if briefing.get("is_card_matriz"):
        print(f"Card {card_key} eh MATRIZ. Nao monta sucesso individual.")
        sys.exit(1)

    lp_slug = slugify(briefing.get("titulo_evento") or "")
    payload = build_sucesso_payload(card, briefing, template_raw, lp_slug)
    intern = payload.pop("_internals")

    if slug_prefix:
        payload["slug"] = f"{slug_prefix}{payload['slug']}"
        payload["title"] = f"[TESTE] {payload['title']}"

    print(f"\n=== Briefing parseado ===")
    print(f"  titulo: {briefing.get('titulo_evento')}")
    print(f"  data:   {briefing.get('data_hora_evento')}")

    print(f"\n=== Dados extraidos pra sucesso ===")
    print(f"  cargo: {intern['cargo']}")
    print(f"  realizacao: dia {intern['dia']:02d} de {intern['mes_nome']}")
    print(f"  aplicacao : {intern['hora_aplic']:02d}:00")
    print(f"  correcao  : {intern['hora_corr']:02d}:00")

    print(f"\n=== Payload da pagina sucesso ===")
    print(f"  title  : {payload['title']}")
    print(f"  slug   : {payload['slug']}")
    print(f"  status : {payload['status']}")
    print(f"  meta   : {payload['meta']}")
    print(f"  content: {len(payload['content'])} chars")

    if not do_commit:
        print("\n[DRY-RUN] Sem postar. Use --commit pra criar.")
        return

    if update_id:
        print(f"\nAtualizando pagina existente {update_id}...")
        result = wp_client.put("pages", update_id, payload)
    else:
        existing = wp_client.get("pages", params={"slug": payload["slug"], "status": "any"})
        if existing:
            e = existing[0]
            print(f"AVISO: ja existe pagina com slug={payload['slug']}:")
            print(f"  ID={e.get('id')}  status={e.get('status')}")
            print("Use --update-id={} pra sobrescrever.".format(e.get("id")))
            sys.exit(2)
        print("\nCriando pagina sucesso no WP (RASCUNHO)...")
        result = wp_client.post("pages", data=payload)

    print(f"\n=== Sucesso ===")
    print(f"  ID    : {result.get('id')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Link  : {result.get('link')}")


if __name__ == "__main__":
    main()
