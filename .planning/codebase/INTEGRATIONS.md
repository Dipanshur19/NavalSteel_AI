---
last_mapped_commit: eb7001815a1b864d243a670b5efd231e49c272bf
last_mapped_at: 2026-11-18
---
# External Integrations

**Analysis Date:** 2026-11-18

## APIs & External Services

**Generative AI & LLM:**
- **Google Gemini API** (`google-genai` SDK) - Powers Studio 5's AI Metallurgist Agent and literature RAG synthesis.
  - SDK: `google-genai`
  - Auth: `GEMINI_API_KEY` (configured in `.env`, zero-key client experience for end users).
  - Primary Model: `gemini-3.5-flash-lite` (with cascading fallback to `gemini-3.5-flash`).

**Scholarly Literature Discovery:**
- **Semantic Scholar Graph API** (`https://api.semanticscholar.org/graph/v1/paper/search`)
  - Client: `requests`
  - Auth: Optional API key support; handles public rate limits (HTTP 429) via automatic fallback.
- **arXiv Open Access API** (`http://export.arxiv.org/api/query`)
  - Client: `urllib.request` / `requests` with XML parsing (`xml.etree.ElementTree`).
  - Auth: None (public open access).
- **Curated Naval Metallurgy Reference Library** (`src/literature_api.py`)
  - In-memory offline curated archive of core naval steel citations (Saha, Olson, Ghosh, Wilson, Thomas).

## Data Storage

**Databases:**
- None (stateless computational metallurgy workbench).

**File Storage:**
- Local filesystem only:
  - `data/seed_records/` - Canonical JSON definitions for HSLA-100, HSLA-115, HY-80, HY-100, AF1410, and BlastAlloy 160.
  - `data/vector_index/` - Serialized FAISS/TF-IDF chunk index files (`blastalloy160_saha_2004.index`).
  - `data/papers/` - Ingested dissertation PDFs and reference publications.

**Caching:**
- Streamlit in-memory cache decorators (`@st.cache_resource`, `@st.cache_data`) for surrogate model training, seed database loading, and literature queries.

## Authentication & Identity

**Auth Provider:**
- Open access research workbench (no user authentication required; designed for local deployment or enterprise internal VPN networks).

## Monitoring & Observability

**Error Tracking:**
- Structured Python exception logging; UI error boundary banners with actionable guidance.

**Health Monitoring:**
- `healthcheck.py` - Synthetic 5-point probe verifying:
  1. Python module integrity
  2. Physics empirical engine calculations ($P_{cm}, M_s$)
  3. Surrogate model inference latency and predictions
  4. Benchmark seed record validation
  5. Local HTTP status 200 response on port 8501

## CI/CD & Deployment

**Hosting:**
- Self-hosted / On-Premise via Docker (`Dockerfile`, `docker-compose.yml`).
- Streamlit Community Cloud or AWS/GCP container runner compatible.

**CI Pipeline:**
- PyTest test runner executing 52 test cases across all modules (`pytest tests/ -v`).

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY`: Required for AI Metallurgist generative Q&A and RAG synthesis.
- `GEMINI_RAG_MODEL`: Defaults to `gemini-3.5-flash-lite`.
- `GEMINI_EXTRACTION_MODEL`: Defaults to `gemini-3.5-flash-lite`.

**Secrets location:**
- `.env` in repository root (git-ignored for security).

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- None.

---

*Integration audit: 2026-11-18*
