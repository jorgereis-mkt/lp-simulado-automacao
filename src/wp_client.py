import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASSWORD")

credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
}


def get(endpoint, params=None):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/{endpoint}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def post(endpoint, data):
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/{endpoint}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


def put(endpoint, item_id, data):
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/{endpoint}/{item_id}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


def delete(endpoint, item_id, force=False):
    params = {"force": "true"} if force else None
    r = requests.delete(
        f"{WP_URL}/wp-json/wp/v2/{endpoint}/{item_id}",
        headers={"Authorization": HEADERS["Authorization"]},
        params=params,
    )
    r.raise_for_status()
    return r.json()


def upload_media(file_path, mime_type="image/webp", filename=None):
    """Faz POST /media com bytes binarios. Retorna o dict do attachment criado."""
    if filename is None:
        filename = os.path.basename(file_path)
    with open(file_path, "rb") as fh:
        data = fh.read()
    headers = {
        "Authorization": HEADERS["Authorization"],
        "Content-Type": mime_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=data, timeout=60)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    me = get("users/me")
    print(f"Conectado como: {me['name']} (ID {me['id']})")

    posts = get("posts", params={"per_page": 5, "status": "any"})
    print(f"\nUltimos {len(posts)} posts:")
    for p in posts:
        print(f"  [{p['status']}] {p['title']['rendered']} — {p['link']}")
