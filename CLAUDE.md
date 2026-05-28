# PaperTrail

Agentic research-paper reading companion. Students upload a paper, chat with it,
and get newer related work — with every citation and claim VERIFIED against real
scholarly databases so the LLM can't hallucinate sources. Full plan in PLAN.md.

## Stack
- Backend: Python 3.12, FastAPI, LangGraph + LangChain
- Vector store: Supabase Postgres + pgvector (hybrid: vector + tsvector BM25)
- Ingestion: DocLing (parses tables + figures, not just text)
- LLM/embeddings: OpenAI (swappable via env); optional local Qwen via LM Studio
- Scholarly APIs: OpenAlex, Crossref, Semantic Scholar (NOT Google Scholar)
- Frontend: React (Vite) + TypeScript + Tailwind
- Observability: Langfuse · Evals: DeepEval + scikit-learn
- Package mgmt: uv (Python), pnpm (frontend)

## Repo layout
backend/    FastAPI app, LangGraph graph, tools, ingestion
frontend/   Vite React app
PLAN.md     phased build plan
CLAUDE.md   this file

## Commands
- Backend dev:  uv run uvicorn backend.main:app --reload
- Backend test: uv  pytest
- Frontend dev: pnpm --dir frontend dev
- Lint:         uv run ruff check . && pnpm --dir frontend lint

## Working rules
- Build ONE phase at a time. Propose a plan + the files you'll touch BEFORE writing code.
- Write a test for each new backend module; run it before saying done.
- Never hardcode secrets — read from .env, keep .env.example updated.
- Don't add a dependency without saying why.
- Keep functions small and typed (Python type hints, TS strict).
- Conventional commits (feat:, fix:, chore:), one logical change per commit.

## Core design principles
- Verification is grounded in scholarly DBs, NOT open-web search. Three checks:
  citation EXISTS (OpenAlex/Crossref), claim SUPPORTED (NLI), paper LEGIT (retraction).
- The agent is a LangGraph: router node → retrieve / scholar_search / verify → answer,
  with a conditional edge that regenerates when a claim is flagged unsupported.
- UI is light-mode, clean, single chat column + left sidebar of past chats.
  Accent #6557D6, surfaces #FFn #EFEEEA, verified=green, flagged=amber, hallucinated=red.
