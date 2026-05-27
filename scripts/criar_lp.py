"""Cria LP de simulado a partir de um card Jira.

Default = DRY-RUN (mostra payload sem postar).
Use --commit para criar de verdade no WP como RASCUNHO.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import wp_client
from src.briefing_parser import parse_briefing
from src.lp_creator import build_lp_payload

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "tests" / "cards_exemplo"
TEMPLATES_DIR = ROOT / "tests" / "lp_templates"
TEMPLATE_SLUG = "simulado-final-mp-al-tecnico-do-ministerio-publico-pos-edital"
DEFAULT_BG_URL_CACHE = ROOT / "assets" / "backgrounds" / "_default" / "wp_url.txt"


def load_default_bg_url() -> str | None:
    if not DEFAULT_BG_URL_CACHE.exists():
        return None
    url = DEFAULT_BG_URL_CACHE.read_text(encoding="utf-8").strip()
    return url if url.startswith("http") else None


def get_bg_url_para_orgao(orgao_slug: str | None) -> tuple[str | None, str]:
    """Decide qual BG usar pra um orgao. Retorna (url, fonte)."""
    # MVP: nenhum orgao tem BG especifico ainda; sempre cai no default
    default = load_default_bg_url()
    if default:
        return default, "default-neutro"
    return None, "none"


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/criar_lp.py <CHAVE_DO_CARD> [--commit]")
        print("Default = dry-run. --commit posta como rascunho no WP.")
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
    if not card_path.exists():
        print(f"Card nao baixado: {card_path}")
        sys.exit(1)
    if not template_path.exists():
        print(f"Template nao encontrado: {template_path}")
        sys.exit(1)

    card = json.loads(card_path.read_text(encoding="utf-8"))
    template_raw = template_path.read_text(encoding="utf-8")
    briefing = parse_briefing(card)

    if briefing.get("is_card_matriz"):
        print(f"Card {card_key} eh CARD MATRIZ. Nao tem dados pra LP individual.")
        sys.exit(1)

    bg_url, bg_fonte = get_bg_url_para_orgao(None)  # MVP: sempre default
    payload = build_lp_payload(card, briefing, template_raw, bg_url=bg_url)
    intern = payload.pop("_internals")

    if slug_prefix:
        payload["slug"] = f"{slug_prefix}{payload['slug']}"
        payload["title"] = f"[TESTE] {payload['title']}"

    print(f"\n=== Briefing parseado de {card_key} ===")
    print(f"  titulo_evento     : {briefing.get('titulo_evento')}")
    print(f"  data_hora_evento  : {briefing.get('data_hora_evento')}")
    print(f"  area (briefing)   : {briefing.get('area')}")
    print(f"  vertical          : {briefing.get('vertical')}")

    print(f"\n=== Dados extraidos pra LP ===")
    print(f"  concurso (h1)     : {intern['concurso']}")
    print(f"  cargo (h2)        : {intern['cargo']}")
    print(f"  data ISO          : {intern['date_iso']}")
    print(f"  texto data        : 'dia {intern['dia']:02d} de {intern['mes_nome']}, ... as {intern['hora_aplic']:02d}:00 ... as {intern['hora_corr']:02d}:00'")
    print(f"  area form         : '{intern['area']}'")
    print(f"  bg_url            : {intern.get('bg_url') or '(nenhum — mantem do template)'}  [fonte: {bg_fonte}]")

    print(f"\n=== Payload da pagina ===")
    print(f"  title  : {payload['title']}")
    print(f"  slug   : {payload['slug']}")
    print(f"  status : {payload['status']}")
    print(f"  meta   : {payload['meta']}")
    print(f"  content: {len(payload['content'])} chars")

    if not do_commit:
        print("\n[DRY-RUN] Nao foi enviado pro WP. Use --commit pra criar como rascunho.")
        return

    if update_id:
        print(f"\nAtualizando pagina existente {update_id} via PUT...")
        result = wp_client.put("pages", update_id, payload)
    else:
        print("\nVerificando se slug ja existe no WP...")
        existing = wp_client.get("pages", params={"slug": payload["slug"], "status": "any"})
        if existing:
            e = existing[0]
            print(f"AVISO: ja existe pagina com slug={payload['slug']}:")
            print(f"  ID={e.get('id')}  status={e.get('status')}  link={e.get('link')}")
            print("Abortando para nao sobrescrever. Use --update-id=<ID> para atualizar.")
            sys.exit(2)
        print("Slug livre. Criando pagina no WP (RASCUNHO)...")
        result = wp_client.post("pages", data=payload)
    print(f"\n=== Pagina criada ===")
    print(f"  ID    : {result.get('id')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Link  : {result.get('link')}")
    print(f"  Preview (logged-in): {result.get('link')}?preview=true")


if __name__ == "__main__":
    main()
