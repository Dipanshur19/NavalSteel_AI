"""
Evidence-grounded RAG.

Retrieves the top-k most relevant chunks for a question from a local index
(see embed.py), then either:

  * calls the LLM with the RAG answer contract (prompts/rag_answer_contract.md)
    to synthesize a cited answer, or
  * (--dry-run, or no ANTHROPIC_API_KEY) returns the retrieved chunks
    directly as an "extractive" answer, so retrieval quality can be
    checked and demoed without an API key.

Either way, every answer is grounded in retrieved chunks with page
citations - the system never answers from unretrieved model memory.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from . import config
from .embed import load_index, search
from .normalize import enrich_text_with_normalized_units

RAG_PROMPT_PATH = config.PROMPTS_DIR / "rag_answer_contract.md"


def load_rag_prompt() -> str:
    return RAG_PROMPT_PATH.read_text(encoding="utf-8")


def _format_context(hits: List[tuple]) -> str:
    blocks = []
    for score, chunk in hits:
        enriched_text = enrich_text_with_normalized_units(chunk["text"])
        blocks.append(
            f"[chunk {chunk['chunk_id']}, pages {chunk['page_start']}-{chunk['page_end']}, "
            f"similarity={score:.3f}]\n{enriched_text}"
        )
    return "\n\n---\n\n".join(blocks)


def _call_gemini_rag(question: str, context: str, retries: int = 2) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    system_prompt = load_rag_prompt()
    user_message = f"Question: {question}\n\nRetrieved evidence:\n\n{context}"

    models_to_try = [
        config.GEMINI_RAG_MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
    ]

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    max_output_tokens=1200,
                ),
            )
            if response and response.text:
                return response.text
        except Exception:
            continue
    return ""


def ask_ai_metallurgist(user_prompt: str) -> str:
    """
    In-built autonomous AI Metallurgist Agent powered by Google Gemini free tier.
    Provides expert computational materials science and physical metallurgy reasoning
    out-of-the-box without requiring the end user to supply any API key.
    """
    if not config.GEMINI_API_KEY:
        return "AI Metallurgist Agent is in offline mode (GEMINI_API_KEY not configured in environment)."

    from google import genai
    from google.genai import types

    system_instruction = (
        "You are the NavalSteel AI Chief Metallurgist Agent, an expert in computational materials informatics, "
        "physical metallurgy, and the systems design of high-strength naval plate steels (e.g. BlastAlloy160, HY-80, HY-100, HSLA-115, AF1410). "
        "Ground your advice in physical principles: Ito-Bessyo cold cracking susceptibility (Pcm), Andrews Ms martensite start, "
        "nanoscale copper precipitation strengthening, secondary M2C alloy carbide hardening, and TRIP transformation toughening via retained austenite films. "
        "Keep your answers clear, rigorous, quantitative, and directly actionable for materials scientists and engineers."
    )

    models_to_try = [
        config.GEMINI_RAG_MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
    ]

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                    max_output_tokens=1500,
                )
            )
            if response and response.text:
                return response.text
        except Exception:
            continue

    return (
        "The AI Metallurgist Agent is currently operating in offline mode. "
        "Please explore the empirical physics calculations and ML surrogate predictions in Studios 1, 2, and 3."
    )


def _call_anthropic_rag(question: str, context: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system_prompt = load_rag_prompt()
    user_message = f"Question: {question}\n\nRetrieved evidence:\n\n{context}"

    response = client.messages.create(
        model=config.RAG_MODEL,
        max_tokens=1200,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    text_parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    return "".join(text_parts)


def answer_extractive(question: str, hits: List[tuple]) -> str:
    """No-API-key fallback: return the best-matching chunk(s) verbatim with
    citations, so the retrieval layer is testable end to end offline."""
    if not hits:
        return "No relevant evidence was retrieved for this question."
    lines = [f"(Extractive mode - no LLM call. Top {len(hits)} retrieved passages shown verbatim.)\n"]
    for score, chunk in hits:
        pages = f"p.{chunk['page_start']}" if chunk['page_start'] == chunk['page_end'] \
            else f"pp.{chunk['page_start']}-{chunk['page_end']}"
        enriched_text = enrich_text_with_normalized_units(chunk["text"])
        lines.append(f"[{pages}, similarity={score:.3f}]\n{enriched_text}\n")
    return "\n".join(lines)


def ask(
    question: str,
    index: Dict[str, Any],
    top_k: int = config.TOP_K,
    dry_run: bool = False,
) -> Dict[str, Any]:
    hits = search(index, question, top_k=top_k)

    if dry_run or not config.has_api_key():
        answer = answer_extractive(question, hits)
        mode = "extractive"
    else:
        context = _format_context(hits)
        provider = config.get_active_provider()
        if provider == "gemini":
            answer = _call_gemini_rag(question, context)
            mode = f"llm ({config.GEMINI_RAG_MODEL})"
        elif provider == "anthropic":
            answer = _call_anthropic_rag(question, context)
            mode = f"llm ({config.RAG_MODEL})"
        else:
            answer = answer_extractive(question, hits)
            mode = "extractive"

    return {
        "question": question,
        "mode": mode,
        "answer": answer,
        "sources": [
            {"chunk_id": c["chunk_id"], "page_start": c["page_start"],
             "page_end": c["page_end"], "similarity": s}
            for s, c in hits
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ask a question against an indexed document")
    parser.add_argument("question")
    parser.add_argument("--index", required=True, help="Path to a *.index.pkl file from embed.py")
    parser.add_argument("--top-k", type=int, default=config.TOP_K)
    parser.add_argument("--dry-run", action="store_true", help="Force extractive mode, skip the LLM call")
    args = parser.parse_args(argv)

    index = load_index(Path(args.index))
    result = ask(args.question, index, top_k=args.top_k, dry_run=args.dry_run)

    print(f"Mode: {result['mode']}")
    print(f"\nQ: {result['question']}\n")
    print(f"A: {result['answer']}\n")
    print("Sources:")
    for s in result["sources"]:
        print(f"  - chunk {s['chunk_id']}, pages {s['page_start']}-{s['page_end']}, "
              f"similarity={s['similarity']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
