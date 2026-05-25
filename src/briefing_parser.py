"""Parser do briefing dos cards de simulado.

Etapa 3: converte a description do Jira (ADF) em texto e extrai campos
da secao 'Marketing,' como dicionario estruturado.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# ============================================================
# ADF -> texto
# ============================================================

def _render_text_node(node: dict) -> str:
    txt = node.get("text", "")
    for mark in node.get("marks", []):
        mtype = mark.get("type")
        mattrs = mark.get("attrs", {})
        if mtype == "strong":
            txt = f"**{txt}**"
        elif mtype == "em":
            txt = f"*{txt}*"
        elif mtype == "code":
            txt = f"`{txt}`"
        elif mtype == "link":
            url = mattrs.get("href", "")
            txt = f"[{txt}]({url})"
    return txt


def adf_to_text(node, depth: int = 0) -> str:
    if node is None:
        return ""
    if isinstance(node, list):
        return "".join(adf_to_text(n, depth) for n in node)
    if not isinstance(node, dict):
        return ""

    ntype = node.get("type", "")
    content = node.get("content", [])
    attrs = node.get("attrs", {})

    if ntype == "text":
        return _render_text_node(node)
    if ntype == "hardBreak":
        return "\n"
    if ntype == "mention":
        return attrs.get("text") or f"@{attrs.get('id', '?')}"
    if ntype == "emoji":
        return attrs.get("text") or attrs.get("shortName", "")
    if ntype == "inlineCard":
        return attrs.get("url", "")
    if ntype == "doc":
        return adf_to_text(content, depth)
    if ntype == "paragraph":
        return adf_to_text(content, depth) + "\n"
    if ntype == "heading":
        return "#" * attrs.get("level", 1) + " " + adf_to_text(content, depth) + "\n"
    if ntype in ("bulletList", "orderedList"):
        return adf_to_text(content, depth + 1)
    if ntype == "listItem":
        indent = "  " * max(depth - 1, 0)
        inner = adf_to_text(content, depth).rstrip("\n")
        return f"{indent}- {inner}\n"
    if ntype == "table":
        return adf_to_text(content, depth) + "\n"
    if ntype == "tableRow":
        cells = [adf_to_text(c.get("content", []), depth).strip().replace("\n", " ") for c in content]
        return "| " + " | ".join(cells) + " |\n"
    if ntype in ("tableCell", "tableHeader"):
        return adf_to_text(content, depth)
    if ntype == "blockquote":
        inner = adf_to_text(content, depth).rstrip("\n")
        return "\n".join("> " + line for line in inner.split("\n")) + "\n"
    if ntype == "codeBlock":
        return "```\n" + adf_to_text(content, depth) + "```\n"
    if ntype == "rule":
        return "\n---\n"
    return adf_to_text(content, depth)


# ============================================================
# Extracao de campos
# ============================================================

def normalize(text: str) -> str:
    """Remove negrito ** e colapsa espacos."""
    return text.replace("**", "")


def extract_marketing_section(normalized_text: str) -> str:
    """Retorna o trecho a partir de 'Marketing,' ate antes do proximo bloco de equipe."""
    start = re.search(r"Marketing\s*,", normalized_text)
    if not start:
        return ""
    section = normalized_text[start.end():]
    # corta no proximo bloco identificavel
    end = re.search(
        r"(?im)^\s*(Audiovisual\s*,|Lan[cç]amento\s*,|Produ[cç][aã]o\s*,|---+)\s*",
        section,
    )
    if end:
        section = section[:end.start()]
    return section


def _field_value(text: str, label: str) -> str | None:
    """Captura 'Label: valor' (case insensitive)."""
    pattern = rf"{re.escape(label)}\s*[:?]?\s*:\s*([^\n]*)"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    val = m.group(1).strip().rstrip(".,;")
    return val or None


def _first_value(text: str, labels: list[str]) -> str | None:
    for lab in labels:
        v = _field_value(text, lab)
        if v:
            return v
    return None


def _parse_sim_nao(value: str | None) -> bool | None:
    if not value:
        return None
    v = value.strip().lower()
    if v.startswith("s"):
        return True
    if v.startswith("n"):
        return False
    return None


def _extract_url_from_label(text: str, label: str) -> str | None:
    """Extrai a primeira URL na mesma linha de 'Label:'."""
    pattern = rf"{re.escape(label)}\s*:\s*([^\n]*)"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    line = m.group(1)
    # para a URL em espaco, ), ], ", ' ou * (markdown bold)
    url_m = re.search(r"https?://[^\s)\]\"'*]+", line)
    if not url_m:
        return None
    return url_m.group(0).rstrip(".,;")


def extract_utms(section: str) -> list[str]:
    """Extrai as UTMs (linha de tabela apos 'UTMs:')."""
    m = re.search(r"UTMs[^\n]*\n([^\n]+)", section, re.IGNORECASE)
    if not m:
        return []
    line = m.group(1).strip()
    if not line.startswith("|"):
        return []
    return [c.strip() for c in line.strip("|").split("|") if c.strip()]


def extract_duracao(full_text: str) -> str | None:
    """Extrai duracao da prova do P.S 1 (ex: '4h30', '5h')."""
    m = re.search(r"P\.?\s*S\s*1\s*:?[^.\n]*?(\d+h\d{0,2})", full_text, re.IGNORECASE)
    return m.group(1) if m else None


def extract_disciplinas(full_text: str) -> str | None:
    """Localiza e devolve o bloco de tabela de disciplinas (linhas consecutivas que comecam com '|')."""
    lines = full_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and re.search(r"\bDisciplina\b", line, re.IGNORECASE):
            start = i
            break
    if start is None:
        return None
    end = start
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    return "\n".join(lines[start:end]) or None


# ============================================================
# API principal
# ============================================================

def is_card_matriz(card: dict) -> bool:
    summary = card.get("fields", {}).get("summary", "") or ""
    return "[CARD MATRIZ]" in summary.upper() or "CARD MATRIZ" in summary.upper()


def parse_briefing(card: dict) -> dict:
    """Recebe o card Jira completo e devolve campos estruturados.

    Cards do tipo MATRIZ tem estrutura diferente (agregam sub-cards) e
    sao retornados com is_card_matriz=True e sub_titulos preenchido.
    """
    summary = card.get("fields", {}).get("summary", "") or ""
    description = card.get("fields", {}).get("description")

    if isinstance(description, (dict, list)):
        text = adf_to_text(description)
    else:
        text = str(description or "")
    full = normalize(text)
    section = extract_marketing_section(full)

    matriz = is_card_matriz(card)

    if matriz:
        # cards matriz nao tem campos individuais; extrai apenas titulos agregados
        return {
            "is_card_matriz": True,
            "summary": summary,
            "sub_titulos": _extract_sub_titulos(section),
            "duracao_prova": extract_duracao(full),
        }

    return {
        "is_card_matriz": False,
        "summary": summary,
        "data_hora_evento": _first_value(section, ["Data/hora do Evento", "Data/hora Do Evento"]),
        "titulo_evento": _first_value(section, ["Título do Evento", "Titulo do Evento"]),
        "vertical": _first_value(section, ["Vertical"]),
        "tem_promocao": _parse_sim_nao(_first_value(section, ["Tem promoção?", "Tem Promoção?", "Tem promocao?"])),
        "area": _first_value(section, ["Área", "Area"]),
        "cr": _first_value(section, ["CR"]),
        "utms": extract_utms(section),
        "link_pacote": _extract_url_from_label(section, "Link do pacote"),
        "link_artigo": _extract_url_from_label(section, "Link do artigo"),
        "link_whatsapp": _extract_url_from_label(section, "Link do WhatsApp"),
        "duracao_prova": extract_duracao(full),
        "tabela_disciplinas_md": extract_disciplinas(full),
    }


def _extract_sub_titulos(section: str) -> list[str]:
    """Para cards MATRIZ: extrai a lista de titulos sob 'Titulos do Eventos:'."""
    m = re.search(r"T[ií]tulos\s+do[s]?\s+Evento[s]?\s*:\s*\n?", section, re.IGNORECASE)
    if not m:
        return []
    block = section[m.end():]
    # corta no proximo === ou linha em branco dupla
    end = re.search(r"\n===|\n\s*\n", block)
    if end:
        block = block[:end.start()]
    return [line.strip() for line in block.splitlines() if line.strip()]


def load_card(card_key: str) -> dict:
    path = Path(__file__).resolve().parents[1] / "tests" / "cards_exemplo" / f"{card_key}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Uso: python -m src.briefing_parser <CHAVE_DO_CARD>")
        sys.exit(1)

    card = load_card(sys.argv[1])
    parsed = parse_briefing(card)

    preview = {k: v for k, v in parsed.items() if k != "tabela_disciplinas_md"}
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    tabela = parsed.get("tabela_disciplinas_md")
    if tabela:
        print(f"\ntabela_disciplinas_md: (presente, {len(tabela)} chars)")
    elif not parsed.get("is_card_matriz"):
        print("\ntabela_disciplinas_md: (NAO encontrada)")


if __name__ == "__main__":
    main()
