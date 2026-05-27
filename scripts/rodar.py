"""Orquestrador end-to-end: pega card Jira e cria LP + Sucesso + notifica Chat.

Uso:
  python scripts/rodar.py MC-XXXX                # dry-run (mostra o que faria)
  python scripts/rodar.py MC-XXXX --commit       # cria LP+sucesso como rascunho TESTE
                                                 # (com prefix 'teste-automacao-' por seguranca)
  python scripts/rodar.py MC-XXXX --commit --producao  # cria SEM prefix de teste
                                                       # (slugs reais - cuidado!)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import wp_client
from src.briefing_parser import parse_briefing
from src.jira_client import fetch_issue, save_to_examples
from src.lp_creator import build_lp_payload, slugify
from src.notifier import notify_lp_criada
from src.sucesso_creator import build_sucesso_payload

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "tests" / "lp_templates"
LP_TEMPLATE_SLUG = "simulado-final-mp-al-tecnico-do-ministerio-publico-pos-edital"
SUCESSO_TEMPLATE_SLUG = "sucesso-simulados-finais-tce-sc-auditor-fiscal-de-controle-externo-pos-edital"
DEFAULT_BG_URL_CACHE = ROOT / "assets" / "backgrounds" / "_default" / "wp_url.txt"

TEST_PREFIX = "teste-automacao-"


def load_default_bg_url() -> str | None:
    if not DEFAULT_BG_URL_CACHE.exists():
        return None
    url = DEFAULT_BG_URL_CACHE.read_text(encoding="utf-8").strip()
    return url if url.startswith("http") else None


def find_existing_page(slug: str) -> dict | None:
    res = wp_client.get("pages", params={"slug": slug, "status": "any"})
    return res[0] if res else None


def create_or_update_page(payload: dict, label: str) -> dict:
    existing = find_existing_page(payload["slug"])
    if existing:
        page_id = existing["id"]
        print(f"  [{label}] slug ja existe (ID {page_id}, status={existing['status']}); atualizando...")
        return wp_client.put("pages", page_id, payload)
    print(f"  [{label}] criando nova pagina...")
    return wp_client.post("pages", data=payload)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    card_key = sys.argv[1]
    do_commit = "--commit" in sys.argv
    producao = "--producao" in sys.argv

    if producao and not do_commit:
        print("ERRO: --producao exige --commit")
        sys.exit(1)

    slug_prefix = "" if producao else TEST_PREFIX

    print(f"\n>>> rodar.py: {card_key} ({'PRODUCAO' if producao else 'TESTE'}, {'commit' if do_commit else 'dry-run'})\n")

    print("[1/5] Baixando card do Jira...")
    card = fetch_issue(card_key)
    save_to_examples(card_key, card)
    summary = card.get("fields", {}).get("summary", "")
    print(f"  Resumo: {summary[:90]}")

    print("[2/5] Parseando briefing...")
    briefing = parse_briefing(card)
    if briefing.get("is_card_matriz"):
        print("  Card MATRIZ — nao processa individual. Abortando.")
        sys.exit(1)
    print(f"  Titulo: {briefing.get('titulo_evento')}")
    print(f"  Data:   {briefing.get('data_hora_evento')}")

    print("[3/5] Montando LP...")
    lp_template = (TEMPLATES_DIR / f"{LP_TEMPLATE_SLUG}.html").read_text(encoding="utf-8")
    bg_url = load_default_bg_url()
    lp_payload = build_lp_payload(card, briefing, lp_template, bg_url=bg_url)
    lp_intern = lp_payload.pop("_internals")
    base_lp_slug = lp_payload["slug"]
    if slug_prefix:
        lp_payload["slug"] = f"{slug_prefix}{lp_payload['slug']}"
        lp_payload["title"] = f"[TESTE] {lp_payload['title']}"
    print(f"  h1='{lp_intern['concurso']}' h2='{lp_intern['cargo']}' area='{lp_intern['area']}'")
    print(f"  slug: {lp_payload['slug']}")

    print("[4/5] Montando Sucesso...")
    sucesso_template = (TEMPLATES_DIR / f"{SUCESSO_TEMPLATE_SLUG}.html").read_text(encoding="utf-8")
    sucesso_payload = build_sucesso_payload(card, briefing, sucesso_template, base_lp_slug)
    sucesso_intern = sucesso_payload.pop("_internals")
    if slug_prefix:
        sucesso_payload["slug"] = f"{slug_prefix}{sucesso_payload['slug']}"
        sucesso_payload["title"] = f"[TESTE] {sucesso_payload['title']}"
    print(f"  slug: {sucesso_payload['slug']}")

    if not do_commit:
        print("\n[DRY-RUN] Nao foi enviado pro WP. Use --commit pra criar.")
        return

    print("[5/5] Criando paginas no WP (rascunho) + notificando Chat...")
    lp_result = create_or_update_page(lp_payload, "LP")
    sucesso_result = create_or_update_page(sucesso_payload, "Sucesso")

    lp_id = lp_result.get("id")
    sucesso_id = sucesso_result.get("id")

    alertas = [
        f"Pagina de SUCESSO: botoes 'ACESSAR SIMULADO' e 'ASSISTIR CORRECAO' com URL placeholder (#) — preencher manualmente",
        f"Pagina de SUCESSO: 4 sub-cards com mesmo cargo — editar manualmente se for simulado de cargo unico vs multiplos",
        f"LP: BG usando default neutro (nao tem imagem especifica do orgao na biblioteca)",
    ]
    if producao:
        alertas.append("Modo PRODUCAO — slug sem prefix de teste; verificar antes de publicar")

    lp_edit_url = f"{wp_client.WP_URL.replace('/concursos','')}/concursos/wp-admin/post.php?post={lp_id}&action=edit"
    sucesso_edit_url = f"{wp_client.WP_URL.replace('/concursos','')}/concursos/wp-admin/post.php?post={sucesso_id}&action=edit"

    notified = notify_lp_criada(
        card_key=card_key,
        titulo=lp_payload["title"],
        lp_link=lp_edit_url,
        sucesso_link=sucesso_edit_url,
        alertas=alertas,
    )

    print(f"\n=== FIM ===")
    print(f"  LP      : ID={lp_id} status={lp_result.get('status')}")
    print(f"            {lp_edit_url}")
    print(f"  Sucesso : ID={sucesso_id} status={sucesso_result.get('status')}")
    print(f"            {sucesso_edit_url}")
    print(f"  Chat    : {'notificado' if notified else 'FALHOU'}")


if __name__ == "__main__":
    main()
