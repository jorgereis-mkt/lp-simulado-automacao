"""Gera as 2 imagens placeholder pra assets/backgrounds/_default/ (desktop + mobile).

Cor: gradient azul Estrategia (#221E51 -> #1C003C). Texto discreto avisando
que e placeholder e precisa ser substituido.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "backgrounds" / "_default"

# Estrategia: azul escuro/roxo
COLOR_TOP = (34, 30, 81)     # #221E51
COLOR_BOTTOM = (28, 0, 60)   # #1C003C
TEXT_COLOR = (255, 255, 255)


def gradient_image(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), COLOR_TOP)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(COLOR_TOP[0] * (1 - t) + COLOR_BOTTOM[0] * t)
        g = int(COLOR_TOP[1] * (1 - t) + COLOR_BOTTOM[1] * t)
        b = int(COLOR_TOP[2] * (1 - t) + COLOR_BOTTOM[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def add_text(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    try:
        font_big = ImageFont.truetype("arial.ttf", int(h * 0.04))
        font_small = ImageFont.truetype("arial.ttf", int(h * 0.022))
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    title = "Background provisorio"
    sub = "Substituir por imagem do orgao"

    bbox = draw.textbbox((0, 0), title, font=font_big)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((w - tw) // 2, (h - th) // 2 - int(h * 0.03)), title, fill=TEXT_COLOR, font=font_big)

    bbox2 = draw.textbbox((0, 0), sub, font=font_small)
    sw = bbox2[2] - bbox2[0]
    draw.text(((w - sw) // 2, (h + th) // 2 + int(h * 0.005)), sub, fill=(180, 180, 200), font=font_small)
    return img


def make(name: str, w: int, h: int) -> Path:
    img = gradient_image(w, h)
    img = add_text(img)
    out = OUT_DIR / f"{name}.webp"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out, "WEBP", quality=85)
    print(f"  {out.name}: {w}x{h}  ({out.stat().st_size // 1024} KB)")
    return out


def main() -> None:
    print(f"Gerando placeholders em {OUT_DIR}")
    make("desktop", 1920, 1080)
    make("mobile", 1080, 1920)


if __name__ == "__main__":
    main()
