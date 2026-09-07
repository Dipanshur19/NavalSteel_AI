"""Central configuration for NavalSteel AI.

Loads settings from a .env file (see .env.example) so API keys never end up
hard-coded or committed to git.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root regardless of current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Paths -------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTRACTED_DIR = DATA_DIR / "extracted"
INDEX_DIR = DATA_DIR / "index"
SCHEMA_PATH = PROJECT_ROOT / "schema" / "materials.schema.json"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

for d in (RAW_DIR, PROCESSED_DIR, EXTRACTED_DIR, INDEX_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- API / model settings ----------------------------------------------
# LLM Provider: "auto" (default: uses Gemini if key is set, otherwise Anthropic),
# "gemini", or "anthropic".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()

# Google Gemini (Free tier available at https://aistudio.google.com/app/apikey)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_EXTRACTION_MODEL = os.getenv("GEMINI_EXTRACTION_MODEL", "gemini-3.6-flash")
GEMINI_RAG_MODEL = os.getenv("GEMINI_RAG_MODEL", "gemini-3.6-flash")

# Anthropic Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "claude-sonnet-4-6")
RAG_MODEL = os.getenv("RAG_MODEL", "claude-sonnet-4-6")

# --- Embedding backend ---------------------------------------------------
# "tfidf"  -> scikit-learn TF-IDF vectors. No internet access needed after
#             the initial `pip install`, works fully offline. Default.
# "sbert"  -> sentence-transformers embeddings. Higher retrieval quality,
#             but downloads a model from Hugging Face on first use.
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "tfidf")
SBERT_MODEL_NAME = os.getenv("SBERT_MODEL_NAME", "all-MiniLM-L6-v2")

# --- Chunking -------------------------------------------------------------
CHUNK_SIZE_CHARS = int(os.getenv("CHUNK_SIZE_CHARS", "1800"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "200"))

# --- Retrieval -------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "5"))


def get_active_provider() -> str:
    """Determine the active LLM provider: 'gemini', 'anthropic', or 'none'."""
    if LLM_PROVIDER == "gemini":
        return "gemini" if GEMINI_API_KEY else "none"
    if LLM_PROVIDER == "anthropic":
        return "anthropic" if ANTHROPIC_API_KEY else "none"
    # Auto mode: prioritize Gemini if key exists, then Anthropic
    if GEMINI_API_KEY:
        return "gemini"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    return "none"


def has_api_key() -> bool:
    return get_active_provider() != "none"
