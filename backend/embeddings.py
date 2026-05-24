"""
embeddings.py
Builds a semantic search index for all houses, planets, and zodiac signs
using Google's `gemini-embedding-001` (the same model used for the
word-to-house dictionary's semantic fallback).

Migrated from sentence-transformers — PyTorch + a local model bundle to
>250MB, exceeding Vercel's serverless function size limit. Same idea,
just a network call per item at build time instead of local inference.

Re-run anytime new content is added to the DB (e.g. after book enrichment).

Run:
    python embeddings.py
"""

import sqlite3
import os
import pickle
import sys
import time

import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

DB_PATH    = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "search_index.pkl")

# Same model + truncated dimensionality as the dictionary index. Using the
# RETRIEVAL_DOCUMENT task type for what we encode here (the canonical
# descriptions); query-time uses RETRIEVAL_QUERY (asymmetric retrieval,
# the right pair for "find docs matching a query"). 768 dims keeps the
# bundled index small.
MODEL_NAME = "models/gemini-embedding-001"
TASK_TYPE  = "RETRIEVAL_DOCUMENT"
OUTPUT_DIM = 768
BATCH_SIZE = 100


def build_rich_text(entity_type, row):
    if entity_type == "house":
        return (
            f"House {row[1]} ({row[2]} / {row[3]}) in Vedic astrology, "
            f"ruled by {row[4]}. Significance: {row[5]}. Keywords: {row[6]}."
        )
    elif entity_type == "planet":
        return (
            f"Planet {row[1]} ({row[2]}) in Vedic astrology, rules {row[3]}. "
            f"Significance: {row[4]}. Keywords: {row[5]}."
        )
    elif entity_type == "zodiac":
        return (
            f"Zodiac sign {row[1]} ({row[2]}) in Vedic astrology, "
            f"ruled by {row[3]}, element {row[4]}, quality {row[5]}. "
            f"Significance: {row[6]}. Keywords: {row[7]}."
        )


def build_index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    documents = []
    metadata = []

    cursor.execute("SELECT id, house_number, sanskrit_name, english_name, ruling_planet, significance, keywords FROM houses")
    for row in cursor.fetchall():
        documents.append(build_rich_text("house", row))
        metadata.append({"type": "house", "id": row[0], "house_number": row[1], "sanskrit_name": row[2], "english_name": row[3], "ruling_planet": row[4], "significance": row[5], "keywords": row[6]})

    cursor.execute("SELECT id, english_name, sanskrit_name, rules_sign, significance, keywords FROM planets")
    for row in cursor.fetchall():
        documents.append(build_rich_text("planet", row))
        metadata.append({"type": "planet", "id": row[0], "english_name": row[1], "sanskrit_name": row[2], "rules_sign": row[3], "significance": row[4], "keywords": row[5]})

    cursor.execute("SELECT id, english_name, sanskrit_name, ruling_planet, element, quality, significance, keywords FROM zodiac_signs")
    for row in cursor.fetchall():
        documents.append(build_rich_text("zodiac", row))
        metadata.append({"type": "zodiac", "id": row[0], "english_name": row[1], "sanskrit_name": row[2], "ruling_planet": row[3], "element": row[4], "quality": row[5], "significance": row[6], "keywords": row[7]})

    conn.close()

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY not set.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=key)

    print(f"Encoding {len(documents)} documents with {MODEL_NAME}...")
    all_vecs: list[np.ndarray] = []
    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        resp = genai.embed_content(
            model=MODEL_NAME,
            content=batch,
            task_type=TASK_TYPE,
            output_dimensionality=OUTPUT_DIM,
        )
        vecs = np.array(resp["embedding"], dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.clip(norms, 1e-12, None)
        all_vecs.append(vecs)
        time.sleep(0.05)
    embeddings = np.vstack(all_vecs)

    with open(INDEX_PATH, "wb") as f:
        pickle.dump(
            {
                "model_name": MODEL_NAME,
                "task_type":  TASK_TYPE,
                "embeddings": embeddings,
                "metadata":   metadata,
            },
            f,
        )

    print(f"Index shape: {embeddings.shape}  ({embeddings.nbytes / 1024:.1f} KB)")
    return len(documents)


if __name__ == "__main__":
    print("\n🔮 Building semantic search index via Google text-embedding-005...")
    count = build_index()
    print(f"✅ Done — {count} entities indexed and ready\n")
