"""
build_dict_embeddings.py
=========================
Encode every word in house_dictionary.json with Google's
`text-embedding-004` so house_mapper.py can do semantic nearest-neighbour
lookup for query tokens that don't have an exact / stemmed / override match.

Replaces the previous sentence-transformers (MiniLM) implementation — PyTorch
+ a local model bundle to >250 MB, exceeding Vercel's serverless function
size limit. The Google embedding API has near-identical quality at our
scale (single-word lookups), zero local model bytes, and reuses the
existing GEMINI_API_KEY.

Output: dict_embeddings.pkl
  {
    "model_name": "models/text-embedding-004",
    "task_type":  "SEMANTIC_SIMILARITY",
    "words":      [str, ...],          # parallel to `embeddings` rows
    "embeddings": ndarray (N × 768, float32, L2-normalized),
  }

Re-run anytime house_dictionary.json is regenerated. Cost is negligible:
~5,000 embedding calls = $0 on the free tier (1,500 RPM / 1.5M TPM).

Run:
    python3 build_dict_embeddings.py
"""

from __future__ import annotations
import json
import os
import pickle
import sys
import time

import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

HERE       = os.path.dirname(__file__)
DICT_PATH  = os.path.join(HERE, "house_dictionary.json")
INDEX_PATH = os.path.join(HERE, "dict_embeddings.pkl")

# Google gemini-embedding-001 — native 3072 dims; we truncate to 768 via
# `output_dimensionality` so the bundled index stays under 16 MB. 768 is
# a sweet spot: enough dimensionality to discriminate at our 5K vocabulary,
# but small enough to ship in the serverless function.
MODEL_NAME = "models/gemini-embedding-001"
TASK_TYPE  = "SEMANTIC_SIMILARITY"
OUTPUT_DIM = 768
# Google embed_content accepts a list of contents in one call, but the
# stable API caps each call at 100 items.
BATCH_SIZE = 100


def _configure() -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=key)


def main() -> int:
    _configure()

    with open(DICT_PATH, encoding="utf-8") as f:
        dictionary = json.load(f)
    words = sorted(dictionary.keys())

    print(f"Encoding {len(words):,} dictionary words with {MODEL_NAME}...")
    embeddings: list[np.ndarray] = []
    for i in range(0, len(words), BATCH_SIZE):
        batch = words[i : i + BATCH_SIZE]
        resp = genai.embed_content(
            model=MODEL_NAME,
            content=batch,
            task_type=TASK_TYPE,
            output_dimensionality=OUTPUT_DIM,
        )
        # genai returns `{"embedding": [[...], [...], ...]}` for batched input.
        batch_vecs = np.array(resp["embedding"], dtype=np.float32)
        # L2-normalize so cosine similarity = dot product at query time
        norms = np.linalg.norm(batch_vecs, axis=1, keepdims=True)
        batch_vecs = batch_vecs / np.clip(norms, 1e-12, None)
        embeddings.append(batch_vecs)
        if (i // BATCH_SIZE) % 10 == 0:
            print(f"  {i + len(batch):>5,} / {len(words):,}")
        # Gentle pacing to stay well inside 1,500 RPM
        time.sleep(0.05)

    matrix = np.vstack(embeddings)
    print(f"\nFinal index: {matrix.shape} ({matrix.nbytes / 1024 / 1024:.1f} MB)")

    with open(INDEX_PATH, "wb") as f:
        pickle.dump(
            {
                "model_name": MODEL_NAME,
                "task_type":  TASK_TYPE,
                "words":      words,
                "embeddings": matrix,
            },
            f,
        )

    print(f"Wrote {INDEX_PATH}")
    return len(words)


if __name__ == "__main__":
    print("\n🔮 Building dictionary embeddings via Google text-embedding-004...\n")
    main()
    print("✅ Done.\n")
