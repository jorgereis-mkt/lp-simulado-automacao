# lp-simulado-automacao

Automação para criar Landing Pages de simulado no WordPress (Divi) a partir de cards do Jira do time de Marketing da Estratégia Concursos.

## Princípio

Automação **cria como rascunho**. Humano revisa e publica.

## Pipeline

```
Jira (card MC-xxxx)
  → jira_client: lê o card
  → briefing_parser: extrai campos da seção "Marketing,"
  → disciplines_ai: parseia tabela de disciplinas via Claude API
  → wordpress_client: clona template Divi e preenche
  → rascunho no WP + comentário no card
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # depois preencher credenciais
```

## Estrutura

- `src/` — código
- `tests/cards_exemplo/` — JSONs reais dos 4 cards de exemplo (não commitados)
- `docs/` — documentação interna do projeto

Briefing completo: ver `BRIEFING_PROJETO.md` (fora do repo, na pasta de Downloads).
