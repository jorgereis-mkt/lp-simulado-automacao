"""Faz upload do BG default neutro no WP (POST /media).

Salva a URL retornada em assets/backgrounds/_default/wp_url.txt pra reutilizacao.
Roda apenas 1 vez (idempotente: pula se ja houver URL salva).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import wp_client

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
BG_FILE = ROOT / "assets" / "backgrounds" / "_default" / "desktop.webp"
URL_CACHE = ROOT / "assets" / "backgrounds" / "_default" / "wp_url.txt"


def main() -> None:
    if not BG_FILE.exists():
        print(f"BG file nao existe: {BG_FILE}")
        sys.exit(1)

    if URL_CACHE.exists():
        existing = URL_CACHE.read_text(encoding="utf-8").strip()
        if existing.startswith("http"):
            print(f"URL ja em cache (pulando upload): {existing}")
            return

    print(f"Fazendo upload de {BG_FILE.name} ({BG_FILE.stat().st_size // 1024} KB)...")
    result = wp_client.upload_media(
        str(BG_FILE),
        mime_type="image/webp",
        filename="bg-default-lp-simulado.webp",
    )
    url = result.get("source_url")
    media_id = result.get("id")
    if not url:
        print("Upload retornou sem source_url:")
        print(result)
        sys.exit(1)
    URL_CACHE.write_text(url, encoding="utf-8")
    print(f"\nUpload OK")
    print(f"  Media ID: {media_id}")
    print(f"  URL: {url}")
    print(f"  Cache salvo em: {URL_CACHE}")


if __name__ == "__main__":
    main()
