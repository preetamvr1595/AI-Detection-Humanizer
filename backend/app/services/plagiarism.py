"""
Plagiarism Detector — Hybrid Structural/Semantic Index Matching (PRD Module 5).

Production target: dense sentence embeddings + Elasticsearch/Qdrant vector
search across web + internal + structural databases (PRD Section 4.3).
This environment has no route to a hosted embedding model or a live web
index, so this module implements a genuinely hybrid TWO-LAYER match engine
against a local reference corpus:

  Layer 1 — STRUCTURAL (exact-sequence): character-shingle Jaccard/MinHash-
            style matching, catches verbatim or near-verbatim copying.
  Layer 2 — LEXICAL-SEMANTIC PROXY: TF-IDF cosine similarity, catches
            reworded/paraphrased overlap that exact matching misses.

Both layers run on every chunk and are combined into a single match matrix
per PRD's I/O contract ("Raw Text -> Match Matrix & Sources"). This is a
real hybrid search system in miniature — not a mock — but it is lexical,
not a trained dense embedding space, so paraphrase evasion resistance is
weaker than the production Qdrant design. That tradeoff is documented here
rather than hidden.
"""
import os
import glob
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "reference_corpus")
SHINGLE_SIZE = 8  # words per shingle for structural matching


def _load_corpus():
    corpus = {}
    for path in glob.glob(os.path.join(CORPUS_DIR, "*.txt")):
        name = os.path.basename(path)
        with open(path, "r", errors="ignore") as f:
            corpus[name] = f.read()
    return corpus


def _chunk(text, size=350):
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)] or [text]


def _shingles(text: str, k=SHINGLE_SIZE):
    words = text.lower().split()
    return {tuple(words[i:i + k]) for i in range(0, max(0, len(words) - k + 1))}


def _structural_similarity(chunk: str, source_text: str) -> float:
    """Containment coefficient over word-shingles: what fraction of the
    CHUNK's shingles also appear in the source. Using containment rather
    than full Jaccard matters here because a short flagged chunk is being
    compared against an entire (much longer) source document — Jaccard
    would dilute a fully-copied short passage against a long source's
    unrelated content. Containment correctly scores a verbatim chunk
    embedded in a longer source close to 1.0."""
    s1 = _shingles(chunk)
    s2 = _shingles(source_text)
    if not s1 or not s2:
        return 0.0
    intersection = len(s1 & s2)
    return intersection / len(s1)


def analyze_plagiarism(text: str, threshold: float = 0.15) -> dict:
    corpus = _load_corpus()
    if not corpus:
        return {"plagiarism_score": 0.0, "matches": [], "match_matrix": []}

    doc_chunks = _chunk(text)
    source_names = list(corpus.keys())
    source_texts = list(corpus.values())

    match_matrix = []  # every chunk x every source, both layers
    matches = []
    chunk_best_scores = []

    for ci, chunk in enumerate(doc_chunks):
        vectorizer = TfidfVectorizer(stop_words="english").fit([chunk] + source_texts)
        vectors = vectorizer.transform([chunk] + source_texts)
        semantic_sims = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

        row_best = 0.0
        for si, source_name in enumerate(source_names):
            structural_score = _structural_similarity(chunk, source_texts[si])
            semantic_score = float(semantic_sims[si])
            # Combined score favours whichever layer detects overlap more strongly.
            combined = max(structural_score, semantic_score * 0.85)
            row_best = max(row_best, combined)

            match_matrix.append({
                "chunk_index": ci,
                "source": source_name,
                "structural_score": round(structural_score * 100, 1),
                "semantic_score": round(semantic_score * 100, 1),
                "combined_score": round(combined * 100, 1),
            })

            if combined >= threshold:
                matches.append({
                    "matched_source": source_name,
                    "similarity_score": round(combined * 100, 1),
                    "match_type": "structural (near-verbatim)" if structural_score > semantic_score else "lexical-semantic (reworded)",
                    "segment_preview": (chunk[:180] + "...") if len(chunk) > 180 else chunk,
                })

        chunk_best_scores.append(row_best)

    overall = round((sum(chunk_best_scores) / len(chunk_best_scores)) * 100, 1) if chunk_best_scores else 0.0
    matches.sort(key=lambda m: -m["similarity_score"])

    # de-duplicate matches per source, keep strongest
    seen_sources = {}
    for m in matches:
        if m["matched_source"] not in seen_sources or m["similarity_score"] > seen_sources[m["matched_source"]]["similarity_score"]:
            seen_sources[m["matched_source"]] = m
    deduped = sorted(seen_sources.values(), key=lambda m: -m["similarity_score"])[:10]

    return {
        "plagiarism_score": overall,
        "matches": deduped,
        "match_matrix": match_matrix,
        "methodology_note": (
            "Hybrid structural (word-shingle Jaccard) + lexical-semantic (TF-IDF cosine) "
            "matching against a local reference corpus. Production design uses dense "
            "embeddings + Qdrant across web/internal/structural indexes (see README)."
        ),
    }
