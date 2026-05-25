"""Cliente Jira: busca de um card por chave e search via JQL."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


def _auth() -> tuple[str, str, str]:
    load_dotenv()
    base_url = os.environ["JIRA_BASE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]
    return base_url, email, token


def fetch_issue(issue_key: str) -> dict:
    base_url, email, token = _auth()
    url = f"{base_url}/rest/api/3/issue/{issue_key}"
    response = requests.get(url, auth=(email, token), timeout=30)
    response.raise_for_status()
    return response.json()


def search_issues(
    jql: str,
    fields: list[str] | None = None,
    page_size: int = 100,
    max_pages: int = 10,
) -> list[dict]:
    base_url, email, token = _auth()
    url = f"{base_url}/rest/api/3/search/jql"
    fields = fields or ["summary", "created", "status"]

    issues: list[dict] = []
    next_token: str | None = None
    for _ in range(max_pages):
        body: dict = {"jql": jql, "fields": fields, "maxResults": page_size}
        if next_token:
            body["nextPageToken"] = next_token
        response = requests.post(url, json=body, auth=(email, token), timeout=60)
        response.raise_for_status()
        data = response.json()
        issues.extend(data.get("issues", []))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    return issues


def save_to_examples(issue_key: str, data: dict) -> Path:
    out_dir = Path(__file__).resolve().parents[1] / "tests" / "cards_exemplo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{issue_key}.json"
    out_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m src.jira_client <CHAVE_DO_CARD>")
        print("Exemplo: python -m src.jira_client MC-1035151")
        sys.exit(1)

    issue_key = sys.argv[1]
    data = fetch_issue(issue_key)
    path = save_to_examples(issue_key, data)

    summary = data.get("fields", {}).get("summary", "(sem resumo)")
    print(f"Card {issue_key} salvo em: {path}")
    print(f"Resumo do card: {summary}")


if __name__ == "__main__":
    main()
