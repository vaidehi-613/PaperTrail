# PaperTrail — Build Plan

> An agentic research-paper reading companion. Students upload a paper, chat with it to understand it, get newer studies that build on it, and — the core differentiator — every citation and claim is **verified against real scholarly databases** so the LLM can't hallucinate sources.

This document is written to be handed to **Claude Code**. Build one phase at a time: plan → build → validate → commit, then move on.

---

## Why this is a strong portfolio project

- Attacks a real, current problem: LLM citation hallucination. Most "chat with PDF" repos don't.
- Genuinely agentic (orchestrator + tools + reflection loop), not just RAG.
- Hits the trending checklist: agentic orchestration, sub-agents, reflection, hybrid search + rerank, multimodal, evals, observability, guardrails, MCP.
- The verifier + eval numbers are the talking point: *"catches X% of fabricated citations on a labeled test set."*

---

## Architecture

```
Student question
      │
      ▼
Orchestrator agent  ── plans, decides which tools to call, loops
      │
      ├──► Paper retriever      (hybrid search + rerank over the uploaded paper)
      ├──► Scholar search       (newer / related work via scholarly APIs)
      └──► Verifier sub-agent   (citation exists?  claim supported?  retracted?)
      │
      ▼
Verified answer with provenance
      │
      └──► if a claim is flagged unsupported → regenerate (reflection loop)
```

---

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React (Vite) + Tailwind | PDF viewer via `react-pdf`. Three-pane: paper / chat / verified related-work |
| Backend | Python + FastAPI | You already know FastAPI from SecureNet — reuse the pattern |
| Database | Supabase (Postgres + `pgvector`) | Gives auth + vector store + row-level security in one |
| Ingestion | DocLing | Parses PDFs **including tables and figures** — your multimodal edge |
| Embeddings | `text-embedding-3-small` (OpenAI) or `bge-small` (local) | Make this swappable |
| Retrieval | pgvector (dense) + Postgres `tsvector` (BM25) + RRF fusion | Then rerank top-k |
| Reranker | `bge-reranker-base` or Cohere rerank | Cross-encoder over fused candidates |
| LLM | OpenRouter / OpenAI, optional local Qwen via LM Studio | Route cheap calls to small model |
| Agent loop | Native tool-calling loop (transparent) | LangGraph optional if you want a graph; native loop reads better in interviews |
| Scholarly APIs | OpenAlex, Crossref, Semantic Scholar | Existence checks, metadata, citation graph. **Not Google Scholar** (no API, ToS) |
| Retractions | Crossref / Retraction Watch data | High-impact legitimacy signal |
| Verifier (claim) | NLI model or LLM-as-judge | support / refute / not-enough-info |
| Observability | Langfuse (open source) or LangSmith | Traces, latency, cost |
| Evals | Custom labeled set (+ RAGAS optional) | Inject fake citations; measure precision/recall |

---

## Build phases

Each phase ends with something working. Don't start the next until the current one validates.

### Phase 0 — Scaffolding
- Repo, `.env`, FastAPI skeleton, React (Vite) shell, Supabase project + `pgvector` enabled.
- Add a `CLAUDE.md` with conventions (folder layout, naming, test command).
- **Validate:** frontend hits a `/health` endpoint and renders a response.

### Phase 1 — Ingestion pipeline
- Upload PDF → DocLing parse → chunk → embed → store in pgvector.
- Store metadata per chunk: `section`, `page`, `is_table`, `is_figure`, `paper_id`.
- **Validate:** upload a paper, confirm chunks + embeddings land in the DB with metadata.

### Phase 2 — Basic RAG chat *(first demoable milestone)*
- Retrieve (vector only) → LLM answers with inline citation references → render in UI.
- **Validate:** ask a question, get a grounded answer that cites the paper's sections.

### Phase 3 — Hybrid search + reranking
- Add `tsvector` keyword search alongside vector search → fuse with reciprocal rank fusion → rerank top-k with cross-encoder.
- **Validate:** queries with exact terms (numbers, method names) retrieve the right chunk where pure vector search missed.

### Phase 4 — Agentic orchestration
- Wrap retrieval in a tool-calling loop. Tools so far: `retrieve_paper`, `scholar_search`.
- Orchestrator decides whether to retrieve from the paper, search scholarly APIs, or both.
- **Validate:** "what came after this paper?" triggers `scholar_search`; "what does section 3 say?" triggers `retrieve_paper`.

### Phase 5 — Verifier sub-agent *(the centerpiece)*
Three distinct checks — build them separately:
1. **Citation exists?** — resolve DOI/title/authors via OpenAlex/Crossref. Catches fabricated references.
2. **Paper legitimate?** — retraction check via Crossref / Retraction Watch.
3. **Claim supported?** — retrieve the cited source's relevant passage, run NLI/LLM-judge → support / refute / not-enough-info.
- Surface results as **provenance badges** (verified / flagged / not found) with the source link + snippet.
- **Reflection loop:** if a claim is flagged unsupported, regenerate the answer.
- **Validate:** feed an answer containing a real citation and a fabricated one; the fake gets flagged "not found."

### Phase 6 — "What came next" (forward citations)
- Use Semantic Scholar citation graph: papers that cite the current one, ranked by recency + relevance.
- Each suggestion runs through the citation verifier before display.
- **Validate:** related-work panel shows real newer papers with "DOI verified" badges.

### Phase 7 — Production polish
- **Prompt-injection guardrails:** treat uploaded PDF text as untrusted; separate instructions from document content, validate outputs. (Ties to your security background.)
- **Async ingestion:** move DocLing parsing to a background job (Redis queue) with status polling.
- **Auth + RLS:** Supabase auth; row-level security so users only see their own papers.
- **Cost/model routing:** small/local model for simple lookups, larger for verification.
- **Observability:** wire Langfuse traces across the whole pipeline.

### Phase 8 — Evals + README
- Build a small labeled eval set, **including deliberately injected fabricated citations**.
- Measure: verifier precision/recall on catching fakes; RAG answer faithfulness (RAGAS optional).
- Write README with **real numbers**, the architecture diagram, and an honest "future work" section.
- *Optional, on-trend:* expose `scholar_search` / `citation_verifier` / `retraction_check` as an **MCP server**.

---

## Scope discipline

**MVP (build this first, this is already impressive):** Phases 0–6 — paper Q&A with table/figure support, hybrid search + rerank, agentic orchestration, citation + claim verification with provenance, forward-citation discovery.

**Production layer:** Phases 7–8.

**Future work (README only — do NOT build now):** multi-agent full-document analysis sub-agent, text-to-SQL over structured data, multi-tenant scaling, fine-tuned NLI model.

---

## Driving Claude Code

1. Put this file in the repo root as `PLAN.md` and keep a `CLAUDE.md` with conventions + the test command.
2. Work **one phase per session**. Sample opening prompt:
   > "Read PLAN.md and CLAUDE.md. We're on Phase 3 (hybrid search + reranking). Propose a plan and the files you'll touch before writing code. Don't start until I confirm."
3. After it builds: ask it to write a test, run the validation step from the phase, then commit.
4. Keep yourself in the loop — review the diffs. The point of the project is that *you* can explain every part in an interview.

---

## Interview / README talking points

- Why hybrid search + reranking over plain cosine similarity (exact scientific terms).
- The three-part verification design (existence vs. support vs. legitimacy) — most people conflate these.
- Why verify against scholarly APIs, not the open web (open web is where hallucinations look plausible).
- The reflection loop as genuine agentic self-correction.
- Your eval numbers: fabricated-citation catch rate + answer faithfulness.
