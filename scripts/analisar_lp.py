"""Le uma LP do WP pelo slug e salva content.raw em tests/lp_templates/ pra analise."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import wp_client

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "lp_templates"


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/analisar_lp.py <slug-da-lp>")
        print("Ex: python scripts/analisar_lp.py simulado-final-mp-al-tecnico-do-ministerio-publico-pos-edital")
        sys.exit(1)

    slug = sys.argv[1]
    print(f"Buscando LP slug={slug} ...")

    result = wp_client.get("pages", params={"slug": slug, "context": "edit", "status": "any"})
    if not result:
        print(f"LP nao encontrada com slug={slug}")
        sys.exit(1)

    page = result[0]
    page_id = page.get("id")
    title = page.get("title", {})
    if isinstance(title, dict):
        title_text = title.get("rendered") or title.get("raw") or "(sem titulo)"
    else:
        title_text = str(title)

    raw = page.get("content", {}).get("raw", "")
    meta = page.get("meta", {}) or {}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{slug}.html"
    out_path.write_text(raw, encoding="utf-8")

    json_path = OUT_DIR / f"{slug}.json"
    json_path.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== LP carregada ===")
    print(f"ID: {page_id}")
    print(f"Titulo: {title_text}")
    print(f"Status: {page.get('status')}")
    print(f"Template: {page.get('template') or '(default)'}")
    print(f"Link: {page.get('link')}")
    print(f"Content raw: {len(raw)} chars  -> salvo em {out_path}")
    print(f"JSON completo: -> {json_path}")

    print(f"\n=== Meta (chaves Divi + form) ===")
    interesting = ["_et_pb_use_builder", "_et_pb_page_layout", "_et_pb_post_settings",
                   "_wp_page_template", "et_pb_first_image", "et_pb_old_content"]
    for k in interesting:
        if k in meta:
            v = meta[k]
            preview = v if isinstance(v, str) and len(v) < 200 else f"(len={len(str(v))})"
            print(f"  {k}: {preview}")

    print(f"\n=== Modulos Divi (et_pb_*) usados ===")
    modules = re.findall(r"\[et_pb_([a-z_]+)\b", raw)
    counts: dict[str, int] = {}
    for m in modules:
        counts[m] = counts.get(m, 0) + 1
    for mod, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  et_pb_{mod}: {n}")

    print(f"\n=== Formulario (procura por 'formulario_estrategia', 'wpcf7', 'gravity', etc.) ===")
    form_markers = ["formulario_estrategia", "wpcf7", "gform", "et_pb_contact_form", "Interesse_Area", "nomeDE2"]
    for marker in form_markers:
        if marker in raw:
            idx = raw.find(marker)
            ctx_start = max(0, idx - 50)
            ctx_end = min(len(raw), idx + 200)
            print(f"  encontrado '{marker}' em offset {idx}:")
            print(f"    ...{raw[ctx_start:ctx_end]}...")
            print()


if __name__ == "__main__":
    main()
