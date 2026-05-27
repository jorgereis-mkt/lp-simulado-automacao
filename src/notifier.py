"""Notifier do Google Chat via incoming webhook.

Se GOOGLE_CHAT_WEBHOOK estiver vazio no .env, vira no-op (nao falha).
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK", "").strip()


def notify(text: str) -> bool:
    """Envia mensagem simples (Markdown) pro Google Chat. Retorna True se enviou."""
    if not WEBHOOK_URL:
        print("[notifier] GOOGLE_CHAT_WEBHOOK vazio, pulando notificacao")
        return False
    try:
        r = requests.post(WEBHOOK_URL, json={"text": text}, timeout=10)
        r.raise_for_status()
        return True
    except requests.RequestException as exc:
        print(f"[notifier] falhou: {exc}")
        return False


def notify_lp_criada(
    card_key: str,
    titulo: str,
    lp_link: str,
    sucesso_link: str | None = None,
    alertas: list[str] | None = None,
) -> bool:
    lines = [
        f"*Nova LP de simulado criada (rascunho)*",
        f"Card Jira: {card_key}",
        f"Titulo: {titulo}",
        f"LP: {lp_link}",
    ]
    if sucesso_link:
        lines.append(f"Sucesso: {sucesso_link}")
    if alertas:
        lines.append("")
        lines.append("*Alertas:*")
        lines.extend(f"- {a}" for a in alertas)
    return notify("\n".join(lines))


if __name__ == "__main__":
    ok = notify("Teste da automacao LP Simulado - conexao do webhook OK")
    print(f"Enviado: {ok}")
