"""Constroi o payload da pagina de sucesso de simulado pra POST /pages."""
from __future__ import annotations

import re

from src.lp_creator import (
    MESES_PT,
    get_area_para_form,  # nao usado aqui, mas pode ser util
    parse_data_hora,
    slugify,
    split_titulo,
)

# Strings fixas do template TCE-SC que vamos substituir
TEMPLATE_TITULO_SIMULADO = "Simulados Finais TCE SC Auditor Fiscal De Controle Externo - Pós Edital"
TEMPLATE_CARGO_H1 = "Gestor Governamental - Especialidade: Administrativa"
TEMPLATE_CARGOS_H2 = ["Administração", "Ciências Contábeis", "Ciências Da Computação", "Direito"]
TEMPLATE_REALIZACAO_A = "Realização: 16 de maio"
TEMPLATE_REALIZACAO_B = "Realização: 17 de maio"
TEMPLATE_HORA_APLIC = "Horário de Aplicação: 08:00"
TEMPLATE_HORA_CORR = "Horário de Correção: 14:00"
TEMPLATE_URL_SIMULADO = "https://www.estrategiaconcursos.com.br/blog/simulado-final-concurso-tce-sc-2026/"
TEMPLATE_URL_YOUTUBE = "https://www.youtube.com/playlist?list=PL70rxKg7qWNVHXNr51hfhG7MlLIkHrmdi"


def render_sucesso_content(
    template_raw: str,
    *,
    titulo_simulado: str,
    cargo: str,
    date_iso: str,
    dia: int,
    mes_nome: str,
    hora_aplic: int,
    hora_corr: int,
) -> str:
    """Substitui as variaveis do template sucesso TCE-SC.

    MVP: todos os 4 sub-cards ficam com o mesmo cargo (mesma especialidade).
    Botoes viram '#' (placeholder) — time edita depois.
    """
    out = template_raw

    # Titulo do topo
    out = out.replace(TEMPLATE_TITULO_SIMULADO, titulo_simulado)

    # Cargo h1 repetido — usar cargo do briefing
    out = out.replace(TEMPLATE_CARGO_H1, cargo or "Cargo")

    # Cargo h2 dos 4 cards (cada um tem nome diferente no template)
    for ct in TEMPLATE_CARGOS_H2:
        out = out.replace(f"<h2>{ct}</h2>", f"<h2>{cargo or 'Cargo'}</h2>")

    # Data + horarios (blurbs)
    realizacao_str = f"Realização: {dia:02d} de {mes_nome}"
    out = out.replace(TEMPLATE_REALIZACAO_A, realizacao_str)
    out = out.replace(TEMPLATE_REALIZACAO_B, realizacao_str)
    out = out.replace(TEMPLATE_HORA_APLIC, f"Horário de Aplicação: {hora_aplic:02d}:00")
    out = out.replace(TEMPLATE_HORA_CORR, f"Horário de Correção: {hora_corr:02d}:00")

    # Botoes -> placeholders
    out = out.replace(TEMPLATE_URL_SIMULADO, "#")
    out = out.replace(TEMPLATE_URL_YOUTUBE, "#")

    return out


def build_sucesso_payload(card: dict, briefing: dict, template_raw: str, lp_slug: str) -> dict:
    titulo = briefing.get("titulo_evento") or ""
    _, cargo = split_titulo(titulo)
    date_iso, hora_aplic, hora_corr = parse_data_hora(briefing.get("data_hora_evento"))
    if not date_iso:
        raise ValueError("Nao consegui parsear data do briefing")
    dia, mes = int(date_iso[8:10]), int(date_iso[5:7])
    mes_nome = MESES_PT[mes]

    content = render_sucesso_content(
        template_raw,
        titulo_simulado=titulo,
        cargo=cargo,
        date_iso=date_iso,
        dia=dia,
        mes_nome=mes_nome,
        hora_aplic=hora_aplic,
        hora_corr=hora_corr,
    )

    sucesso_slug = f"sucesso-{lp_slug}"
    title = f"Sucesso - {titulo}"

    return {
        "title": title,
        "slug": sucesso_slug,
        "status": "draft",
        "content": content,
        "meta": {"_et_pb_use_builder": "on"},
        "_internals": {
            "cargo": cargo,
            "date_iso": date_iso,
            "dia": dia,
            "mes_nome": mes_nome,
            "hora_aplic": hora_aplic,
            "hora_corr": hora_corr,
        },
    }
