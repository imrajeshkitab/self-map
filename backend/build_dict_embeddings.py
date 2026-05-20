"""
build_dict_embeddings.py
=========================
Encode every word in house_dictionary.json with sentence-transformers so
that house_mapper.py can do semantic nearest-neighbour lookup for query
tokens that don't have an exact / stemmed / override match.

Output: dict_embeddings.pkl
  {
    "model_name": "all-MiniLM-L6-v2",
    "words":      [str, ...],          # parallel to `embeddings` rows
    "embeddings": ndarray (N × 384, float32, L2-normalized),
  }

Re-run this any time house_dictionary.json is regenerated.

Memory: ~7.8 MB on disk for 5K words × 384 dims × 4 bytes.
First run downloads the model (~90 MB).
"""

import json
import os
import pickle

from sentence_transformers import SentenceTransformer

HERE       = os.path.dirname(__file__)
DICT_PATH  = os.path.join(HERE, "house_dictionary.json")
INDEX_PATH = os.path.join(HERE, "dict_embeddings.pkl")
MODEL_NAME = "all-MiniLM-L6-v2"


def main() -> int:
    with open(DICT_PATH, encoding="utf-8") as f:
        dictionary = json.load(f)

    words = sorted(dictionary.keys())
    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Encoding {len(words):,} dictionary words...")
    embeddings = model.encode(
        words,
        normalize_embeddings=True,   # so cosine sim = dot product later
        show_progress_bar=True,
        batch_size=128,
    )

    with open(INDEX_PATH, "wb") as f:
        pickle.dump(
            {"model_name": MODEL_NAME, "words": words, "embeddings": embeddings},
            f,
        )

    print(f"\nWrote {INDEX_PATH} — {len(words):,} words × {embeddings.shape[1]} dims")
    return len(words)


if __name__ == "__main__":
    print("\n🔮 Building dictionary word embeddings for semantic matching...\n")
    main()
    print("✅ Done.\n")
