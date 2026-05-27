"""Constroi o payload da LP de simulado pra POST /pages do WP."""
from __future__ import annotations

import re

VERT_PREFIX_RE = re.compile(r"^\[[A-Z]{2,6}\]\s*")

MESES_PT = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def strip_vert_prefix(s: str) -> str:
    return VERT_PREFIX_RE.sub("", s).strip()


def split_titulo(titulo: str) -> tuple[str, str]:
    """De 'Simulado <Etapa> <CONCURSO> [- CARGO ...] - Edital' devolve (concurso, cargo)."""
    t = titulo
    t = re.sub(r"^\d+[ºoa°]?\s*", "", t)
    t = re.sub(r"^Simulado[s]?\s+\w+\s+", "", t, count=1)
    t = re.sub(r"\s*-\s*(Pr[éeè]|P[óoò]s)-?\s*Edital\s*$", "", t, flags=re.IGNORECASE)
    parts = [p.strip() for p in t.split(" - ") if p.strip()]
    if not parts:
        return titulo, ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " - ".join(parts[1:])


def parse_data_hora(s: str | None) -> tuple[str | None, int, int]:
    """De 'DD/MM/AAAA, aplicação 8h e correção 14h' devolve (YYYY-MM-DD, hora_aplic, hora_corr)."""
    if not s:
        return None, 8, 14
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if not m:
        return None, 8, 14
    dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
    date_iso = f"{ano:04d}-{mes:02d}-{dia:02d}"
    aplic_m = re.search(r"aplica[cç][aã]o\s*(\d{1,2})h", s, re.IGNORECASE)
    corr_m = re.search(r"corre[cç][aã]o\s*(\d{1,2})h", s, re.IGNORECASE)
    aplic = int(aplic_m.group(1)) if aplic_m else 8
    corr = int(corr_m.group(1)) if corr_m else 14
    return date_iso, aplic, corr


def get_area_para_form(card: dict) -> str | None:
    """Pega [EC] Area (customfield_10065) do card e remove o prefixo [XX]."""
    field = card.get("fields", {}).get("customfield_10065")
    if not field:
        return None
    if isinstance(field, dict):
        val = field.get("value") or field.get("name")
    elif isinstance(field, list) and field:
        first = field[0]
        val = first.get("value") if isinstance(first, dict) else str(first)
    else:
        val = str(field)
    return strip_vert_prefix(val) if val else None


def slugify(s: str) -> str:
    s = s.lower()
    table = str.maketrans({
        "á": "a", "à": "a", "â": "a", "ã": "a", "ä": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "ô": "o", "õ": "o", "ö": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "ñ": "n",
    })
    s = s.translate(table)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def render_lp_content(
    template_raw: str,
    *,
    concurso: str,
    cargo: str,
    date_iso: str,
    dia: int,
    mes_nome: str,
    hora_aplic: int,
    hora_corr: int,
    area: str,
    bg_url: str | None = None,
) -> str:
    """Substitui variaveis do template MP-AL pra construir o content da LP nova.

    Se bg_url for fornecido, substitui o background_image do template (que e
    especifico do concurso de origem do template) — IMPORTANTE pra nao reusar
    imagem de outro concurso (ver feedback-lp-bg-nunca-outro-concurso).
    """
    out = template_raw

    out = re.sub(r"<h1>MP AL</h1>", f"<h1>{concurso}</h1>", out)
    out = re.sub(
        r"<h2>T[éeè]cnico Do Minist[ée]rio P[uú]blico</h2>",
        f"<h2>{cargo}</h2>" if cargo else "<h2></h2>",
        out,
    )

    novo_paragrafo = (
        f"Realizaremos no dia {dia:02d} de {mes_nome}, "
        f"um simulado gratuito com aplicação às {hora_aplic:02d}:00 "
        f"(horário de Brasília) e correção ao vivo, no mesmo dia, "
        f"às {hora_corr:02d}:00 (horário de Brasília) pelo nosso canal no YouTube."
    )
    out = re.sub(r"<h2>Realizaremos[^<]+</h2>", f"<h2>{novo_paragrafo}</h2>", out)

    out = re.sub(
        r'date_time="2026-05-09 08:00"',
        f'date_time="{date_iso} {hora_aplic:02d}:00"',
        out,
    )

    out = re.sub(r'\barea="Tribunais"', f'area="{area}"', out)

    if bg_url:
        out = re.sub(
            r'background_image="[^"]+BACKGROUND-MP-AL-LP\.webp"',
            f'background_image="{bg_url}"',
            out,
        )

    return out


def build_lp_payload(card: dict, briefing: dict, template_raw: str, bg_url: str | None = None) -> dict:
    titulo = briefing.get("titulo_evento") or ""
    concurso, cargo = split_titulo(titulo)
    date_iso, hora_aplic, hora_corr = parse_data_hora(briefing.get("data_hora_evento"))
    if not date_iso:
        raise ValueError("Nao consegui parsear data do briefing")
    dia, mes = int(date_iso[8:10]), int(date_iso[5:7])
    mes_nome = MESES_PT[mes]
    area = get_area_para_form(card) or "(SEM AREA)"

    content = render_lp_content(
        template_raw,
        concurso=concurso,
        cargo=cargo,
        date_iso=date_iso,
        dia=dia,
        mes_nome=mes_nome,
        hora_aplic=hora_aplic,
        hora_corr=hora_corr,
        area=area,
        bg_url=bg_url,
    )

    slug = slugify(titulo)

    return {
        "title": titulo,
        "slug": slug,
        "status": "draft",
        "content": content,
        "meta": {"_et_pb_use_builder": "on"},
        "_internals": {
            "concurso": concurso,
            "cargo": cargo,
            "date_iso": date_iso,
            "dia": dia,
            "mes_nome": mes_nome,
            "hora_aplic": hora_aplic,
            "hora_corr": hora_corr,
            "area": area,
            "bg_url": bg_url,
        },
    }
