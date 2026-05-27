"""Compara 2 LPs salvas em tests/lp_templates e mostra as diferencas estruturais."""
from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "tests" / "lp_templates"

# regex para extrair conteudo de [et_pb_text ...]conteudo[/et_pb_text]
TEXT_RE = re.compile(r"\[et_pb_text\b[^\]]*\](.*?)\[/et_pb_text\]", re.DOTALL)
# atributos de [formulario_estrategia ...]
FORM_RE = re.compile(r"\[formulario_estrategia\b([^\]]*)\]")
# atributos de [et_pb_countdown_timer ...]
COUNTDOWN_RE = re.compile(r"\[et_pb_countdown_timer\b([^\]]*)\]")
# src de imagens
IMG_RE = re.compile(r'\[et_pb_image\b[^\]]*src="([^"]+)"')
# titulo (h1 ou h2 dentro de et_pb_text)
HEADING_RE = re.compile(r"<(h[12])[^>]*>(.*?)</\1>", re.DOTALL)
# button_url de et_pb_button
BUTTON_RE = re.compile(r"\[et_pb_button\b[^\]]*button_url=\"([^\"]+)\"[^\]]*button_text=\"([^\"]*)\"")


def parse_attrs(s: str) -> dict[str, str]:
    return dict(re.findall(r'(\w+)="([^"]*)"', s))


def extract_features(raw: str) -> dict:
    textos = [t.strip() for t in TEXT_RE.findall(raw)]
    headings = []
    for t in textos:
        for tag, content in HEADING_RE.findall(t):
            clean = re.sub(r"<[^>]+>", " ", content).strip()
            clean = re.sub(r"\s+", " ", clean)
            if clean:
                headings.append((tag, clean))

    forms = [parse_attrs(a) for a in FORM_RE.findall(raw)]
    countdowns = [parse_attrs(a) for a in COUNTDOWN_RE.findall(raw)]
    imgs = IMG_RE.findall(raw)
    buttons = BUTTON_RE.findall(raw)

    return {
        "len": len(raw),
        "texts": textos,
        "headings": headings,
        "forms": forms,
        "countdowns": countdowns,
        "imgs": imgs,
        "buttons": buttons,
    }


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python scripts/comparar_lps.py <slug-A> <slug-B>")
        sys.exit(1)

    a_slug, b_slug = sys.argv[1], sys.argv[2]
    a_raw = (TEMPLATES_DIR / f"{a_slug}.html").read_text(encoding="utf-8")
    b_raw = (TEMPLATES_DIR / f"{b_slug}.html").read_text(encoding="utf-8")

    a = extract_features(a_raw)
    b = extract_features(b_raw)

    print(f"A: {a_slug}  ({a['len']} chars)")
    print(f"B: {b_slug}  ({b['len']} chars)\n")

    print("=== HEADINGS (h1/h2) ===")
    for i in range(max(len(a["headings"]), len(b["headings"]))):
        ha = a["headings"][i] if i < len(a["headings"]) else ("--", "(falta)")
        hb = b["headings"][i] if i < len(b["headings"]) else ("--", "(falta)")
        same = "==" if ha == hb else "<>"
        print(f"  [{i}] {same}")
        print(f"      A {ha[0]}: {ha[1][:90]}")
        print(f"      B {hb[0]}: {hb[1][:90]}")

    print("\n=== FORMS ===")
    for i, (fa, fb) in enumerate(zip(a["forms"], b["forms"])):
        print(f"  Form {i}:")
        keys = sorted(set(fa.keys()) | set(fb.keys()))
        for k in keys:
            va, vb = fa.get(k, "(missing)"), fb.get(k, "(missing)")
            marker = "  " if va == vb else "<<"
            print(f"    {marker} {k}: A='{va}' | B='{vb}'")

    print("\n=== COUNTDOWN TIMERS ===")
    for i, (ca, cb) in enumerate(zip(a["countdowns"], b["countdowns"])):
        keys = sorted(set(ca.keys()) | set(cb.keys()))
        for k in keys:
            va, vb = ca.get(k, "(missing)"), cb.get(k, "(missing)")
            if va != vb:
                print(f"    <<  {k}: A='{va[:60]}' | B='{vb[:60]}'")

    print("\n=== IMAGENS (src) ===")
    for i in range(max(len(a["imgs"]), len(b["imgs"]))):
        ia = a["imgs"][i] if i < len(a["imgs"]) else "(falta)"
        ib = b["imgs"][i] if i < len(b["imgs"]) else "(falta)"
        same = "==" if ia == ib else "<>"
        print(f"  [{i}] {same}")
        print(f"      A: {ia[:90]}")
        print(f"      B: {ib[:90]}")

    print("\n=== BUTTONS (url, text) ===")
    for i, (ba_, bb_) in enumerate(zip(a["buttons"], b["buttons"])):
        same_url = "==" if ba_[0] == bb_[0] else "<>"
        same_txt = "==" if ba_[1] == bb_[1] else "<>"
        print(f"  [{i}] url{same_url} text{same_txt}")
        print(f"      A: url={ba_[0][:80]}  text='{ba_[1][:60]}'")
        print(f"      B: url={bb_[0][:80]}  text='{bb_[1][:60]}'")

    print("\n=== TEXTOS COMPLETOS DIFERENTES ===")
    common_count = 0
    diff_count = 0
    for i in range(max(len(a["texts"]), len(b["texts"]))):
        ta = a["texts"][i] if i < len(a["texts"]) else ""
        tb = b["texts"][i] if i < len(b["texts"]) else ""
        if ta == tb:
            common_count += 1
        else:
            diff_count += 1
            print(f"\n  Bloco de texto {i}:")
            print(f"    A: {ta[:200]}...")
            print(f"    B: {tb[:200]}...")

    print(f"\nResumo: {common_count} blocos de texto IGUAIS, {diff_count} DIFERENTES")


if __name__ == "__main__":
    main()
