"""
RootOps — Embedding & Reranking Service

Wraps sentence-transformers for:
  1. Dense vector embeddings  — domain-separated spaces.
     - Code domain:  jinaai/jina-embeddings-v2-base-code (768-dim)
       Trained on code + English text with 8192-token context.
     - Log/Doc domain: configurable via LOG_EMBEDDING_MODEL_NAME.
       Falls back to the code model when not set.

     Domain separation prevents code tokens and log prose from pulling
     each other's rankings. Retrieval merges results via cross-encoder
     re-ranking rather than cosine similarity across a single space.

  2. Cross-encoder reranking  — cross-encoder/ms-marco-MiniLM-L-6-v2
     Reads query + candidate chunk *together*, far more precise than
     bi-encoder similarity alone. Applied after initial vector retrieval.

  3. Embedding versioning — each vector is tagged with EMBEDDING_MODEL_VERSION
     from config so blue/green index migration is safe when the model changes.

Embeddings run in a ThreadPoolExecutor to avoid blocking the FastAPI async
event loop. Thread workers share model memory (no duplication), making this
safe on VMs with limited RAM. Reranking runs in the same pool.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_pool = ThreadPoolExecutor(max_workers=settings.EMBED_WORKERS)

# ── Concurrency rate-limit ────────────────────────────────────────
# Cap how many embed_text / embed_batch calls can run concurrently.
# This prevents a burst of queries from saturating the embedding thread
# pool and causing OOM on constrained VMs.
# Value: EMBED_WORKERS * 3 gives queuing room while preventing pile-up.
_embed_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Return the shared embedding concurrency semaphore (lazy init)."""
    global _embed_semaphore
    if _embed_semaphore is None:
        limit = max(settings.EMBED_WORKERS * 3, 6)
        _embed_semaphore = asyncio.Semaphore(limit)
        logger.debug("Embedding semaphore initialised: limit=%d", limit)
    return _embed_semaphore

# Per-thread model caches — loaded once per worker.
_embed_cache: dict[str, SentenceTransformer] = {}
_rerank_cache: dict[str, CrossEncoder] = {}


def _get_embed_model(model_name: str) -> SentenceTransformer:
    if model_name not in _embed_cache:
        logger.info("Loading embedding model: %s", model_name)
        model = SentenceTransformer(model_name, trust_remote_code=True)

        # Hard-cap the token sequence length sent to the transformer.
        # The jina-v2 model supports 8192 tokens, but attention memory
        # is O(n²) per sequence — a single 8k-token chunk can consume
        # several GB.  Truncating to 512 tokens (≈2000 chars of code)
        # keeps peak memory per sequence well under control while
        # preserving enough semantic signal for retrieval.
        max_seq = settings.EMBED_MAX_SEQ_LENGTH
        if max_seq and max_seq > 0:
            old_max = getattr(model, "max_seq_length", None)
            model.max_seq_length = max_seq
            logger.info(
                "Capped model max_seq_length: %s → %d tokens",
                old_max, max_seq,
            )

        _embed_cache[model_name] = model
    return _embed_cache[model_name]


def _get_rerank_model(model_name: str) -> CrossEncoder:
    if model_name not in _rerank_cache:
        logger.info("Loading reranker model: %s", model_name)
        _rerank_cache[model_name] = CrossEncoder(model_name)
    return _rerank_cache[model_name]


def _model_for_domain(domain: str) -> str:
    """
    Return the model name for a given domain.
    Domains: "code" (default) | "log" | "doc"
    Log and doc domains use LOG_EMBEDDING_MODEL_NAME when set,
    otherwise fall back to the code model.
    """
    if domain in ("log", "doc") and settings.LOG_EMBEDDING_MODEL_NAME:
        return settings.LOG_EMBEDDING_MODEL_NAME
    return settings.EMBEDDING_MODEL_NAME


# ── Embedding ─────────────────────────────────────────────────────

def _do_embed_text(text: str, model_name: str) -> list[float]:
    model = _get_embed_model(model_name)
    embedding = model.encode(text, normalize_embeddings=True)
    return np.float16(embedding).tolist()


def _do_embed_batch(texts: list[str], model_name: str, batch_size: int) -> list[list[float]]:
    model = _get_embed_model(model_name)
    # Cap internal batch_size to limit peak tensor memory.
    # The jina-v2 model with 8192-token context can use several GB when
    # encoding many long sequences simultaneously (attention is O(n²)).
    # Use the configurable EMBED_ENCODE_BATCH_SIZE (default 16) so
    # resource-constrained VMs can lower it via env var.
    safe_bs = min(batch_size, settings.EMBED_ENCODE_BATCH_SIZE)
    embeddings = model.encode(
        texts,
        batch_size=safe_bs,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 50,
    )
    return [np.float16(e).tolist() for e in embeddings]


async def embed_text(text: str, domain: str = "code") -> list[float]:
    """Embed a single text string into a domain-specific dense vector.

    Uses a semaphore to cap concurrent embedding calls and prevent
    thread-pool saturation on memory-constrained VMs.
    """
    model_name = _model_for_domain(domain)
    loop = asyncio.get_running_loop()
    async with _get_semaphore():
        return await loop.run_in_executor(_pool, _do_embed_text, text, model_name)


async def embed_batch(texts: list[str], batch_size: int = 32, domain: str = "code") -> list[list[float]]:
    """Embed a list of texts into dense vectors using the domain-appropriate model.

    Uses a semaphore to cap concurrent embedding calls.
    """
    if not texts:
        return []
    model_name = _model_for_domain(domain)
    loop = asyncio.get_running_loop()
    async with _get_semaphore():
        return await loop.run_in_executor(_pool, _do_embed_batch, texts, model_name, batch_size)


# ── Reranking ─────────────────────────────────────────────────────

def _do_rerank(query: str, candidates: list[str], model_name: str) -> list[float]:
    """Score (query, candidate) pairs with a cross-encoder. Higher = more relevant."""
    model = _get_rerank_model(model_name)
    pairs = [[query, c] for c in candidates]
    scores: list[float] = model.predict(pairs).tolist()
    return scores


async def rerank(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    """Rerank retrieved chunks by cross-encoder relevance score.

    Takes more candidates than needed, scores each (query, chunk_content) pair,
    returns the top_k most relevant — significantly more precise than
    cosine similarity alone.

    Args:
        query:  The user's original question (not the HyDE variant).
        chunks: List of chunk dicts with a 'content' key.
        top_k:  Number of chunks to return after reranking.

    Returns:
        The top_k chunks, sorted by reranker score descending, with a
        'rerank_score' key added to each dict.
    """
    if not chunks or not settings.RERANKER_ENABLED:
        return chunks[:top_k]

    candidates = [c.get("content", "") for c in chunks]
    loop = asyncio.get_running_loop()

    try:
        scores = await loop.run_in_executor(
            _pool, _do_rerank, query, candidates, settings.RERANKER_MODEL
        )
    except Exception as exc:
        logger.warning("Reranker failed (%s) — skipping reranking", exc)
        return chunks[:top_k]

    scored = sorted(
        zip(chunks, scores), key=lambda x: x[1], reverse=True
    )
    result = []
    for chunk, score in scored[:top_k]:
        result.append({**chunk, "rerank_score": round(float(score), 4)})
    return result


# ── Validation ────────────────────────────────────────────────────

def validate_embedding_dimension(model_name: str, expected_dim: int) -> None:
    """Verify the model's output dimension matches EMBEDDING_DIMENSION.

    Called once at startup. A mismatch (e.g. swapping models without
    running the migration) silently corrupts vector queries — better to
    abort immediately with a clear message.
    """
    model = _get_embed_model(model_name)
    actual_dim = model.get_sentence_embedding_dimension()
    if actual_dim != expected_dim:
        raise RuntimeError(
            f"Embedding dimension mismatch: model '{model_name}' produces "
            f"{actual_dim}-dim vectors but EMBEDDING_DIMENSION={expected_dim}. "
            f"Run migration 0003 (alembic upgrade head) and re-ingest, "
            f"or update EMBEDDING_DIMENSION in .env to match."
        )
    logger.info("Embedding dimension validated: %s → %d-dim ✓", model_name, actual_dim)


def current_model_version() -> str:
    """Return the configured embedding model version tag (e.g. 'v1', 'v2')."""
    return settings.EMBEDDING_MODEL_VERSION
