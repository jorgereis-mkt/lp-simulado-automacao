"""HTTP wrapper around rodar.py — endpoint pro n8n chamar.

Roda no Replit (ou qualquer host) e expoe:
  GET  /healthz         -> teste de vida
  POST /processar-card  -> dispara o pipeline (precisa header X-Webhook-Secret)

Variaveis de ambiente (Secrets no Replit):
  WEBHOOK_SECRET        token combinado com o n8n (obrigatorio)
  JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
  WP_URL, WP_USER, WP_APP_PASSWORD
  GOOGLE_CHAT_WEBHOOK   (opcional)
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
REPO = Path(__file__).resolve().parent


@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "lp-simulado-automacao"}


@app.post("/processar-card")
def processar_card():
    secret = os.environ.get("WEBHOOK_SECRET")
    if not secret:
        return jsonify({"error": "server misconfigured: WEBHOOK_SECRET missing"}), 500
    if request.headers.get("X-Webhook-Secret") != secret:
        return jsonify({"error": "unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    card_id = (data.get("card_id") or "").strip()
    if not card_id:
        return jsonify({"error": "card_id required in JSON body"}), 400

    args = ["python", "scripts/rodar.py", card_id, "--commit"]
    if data.get("producao") is True:
        args.append("--producao")

    try:
        result = subprocess.run(
            args, cwd=str(REPO), capture_output=True, text=True, timeout=180
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "pipeline timed out (180s)"}), 504

    payload = {
        "ok": result.returncode == 0,
        "card_id": card_id,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }
    return jsonify(payload), (200 if result.returncode == 0 else 500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
