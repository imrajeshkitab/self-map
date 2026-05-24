"""
search.py
Semantic search engine — finds closest matches for any query among
houses / planets / zodiac signs via Google embedding similarity.

Migrated from sentence-transformers (PyTorch, ~500MB bundle, doesn't
fit Vercel's serverless function size limit) to Google's
`gemini-embedding-001` accessed through the existing google-generativeai
SDK. Same architecture: pre-built embedding index on disk + a single
query-time embedding API call + dot-product over the index.

Usage:
    python search.py "career and money"
    python search.py "relationship problems"
    python search.py "spiritual growth"
"""

import os
import sys
import pickle
import numpy as np

INDEX_PATH = os.path.join(os.path.dirname(__file__), "search_index.pkl")

_index = None
_genai_configured = False


def _ensure_genai_configured() -> bool:
    """Configure the Google generative-ai SDK once. Returns False if no
    GEMINI_API_KEY is set."""
    global _genai_configured
    if _genai_configured:
        return True
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        _genai_configured = True
        return True
    except Exception:
        return False


def load_index():
    """Lazy-load the pre-built embedding index (parallel to house_mapper)."""
    global _index
    if _index is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(
                "Search index not found. Run: python embeddings.py"
            )
        with open(INDEX_PATH, "rb") as f:
            _index = pickle.load(f)
    return _index


def _embed_query(query: str, model_name: str, task_type: str, output_dim: int) -> np.ndarray | None:
    """Embed a query via Google's embedding API + L2-normalise. Returns
    None if the SDK isn't configured or the call fails — callers should
    treat that as "search unavailable" and degrade gracefully."""
    if not _ensure_genai_configured():
        return None
    try:
        import google.generativeai as genai
        resp = genai.embed_content(
            model=model_name,
            content=query,
            task_type=task_type,
            output_dimensionality=output_dim,
        )
        vec = np.array(resp["embedding"], dtype=np.float32)
        n = float(np.linalg.norm(vec))
        return vec / max(n, 1e-12)
    except Exception:
        return None


def _rank_all(query: str):
    index = load_index()
    embeddings = index["embeddings"]
    metadata = index["metadata"]

    query_vec = _embed_query(
        query,
        model_name=index.get("model_name", "models/gemini-embedding-001"),
        task_type=index.get("task_type", "RETRIEVAL_QUERY"),
        output_dim=int(embeddings.shape[1]),
    )
    if query_vec is None:
        return []   # graceful degradation if embeddings aren't available

    scores = embeddings @ query_vec  # cosine sim (vectors are normalized)

    ranked = []
    for i in np.argsort(scores)[::-1]:
        item = metadata[i].copy()
        item["score"] = round(float(scores[i]), 4)
        ranked.append(item)
    return ranked


def semantic_search(query: str, top_k: int = 5) -> list:
    """Pure ranking — top_k results by similarity, any category."""
    return _rank_all(query)[:top_k]


def trinity_search(query: str, top_k: int = 5, min_score: float = 0.20) -> dict:
    """
    Returns one best house + planet + zodiac (the Vedic trinity) on top,
    each only if it clears `min_score`. Then ranked overflow below,
    deduped against the trinity picks.
    """
    ranked = _rank_all(query)

    trinity = {"house": None, "planet": None, "zodiac": None}
    used_keys = set()
    for r in ranked:
        t = r["type"]
        if trinity.get(t) is None and r["score"] >= min_score:
            trinity[t] = r
            used_keys.add((t, r["id"]))
        if all(trinity[k] is not None for k in trinity):
            break

    overflow = [r for r in ranked if (r["type"], r["id"]) not in used_keys][:top_k]

    return {"trinity": trinity, "overflow": overflow}


def print_results(query, results):
    print(f"\n🔍 Query: '{query}'")
    print("=" * 55)
    for i, r in enumerate(results, 1):
        bar = "█" * max(0, int(r["score"] * 30))
        print(f"\n#{i}  Score: {r['score']:.2%}  {bar}")
        if r["type"] == "house":
            print(f"  🏠 House {r['house_number']} — {r['sanskrit_name']} ({r['english_name']})")
            print(f"     Ruled by: {r['ruling_planet']}")
        elif r["type"] == "planet":
            print(f"  🪐 {r['english_name']} ({r['sanskrit_name']})")
            print(f"     Rules: {r['rules_sign']}")
        elif r["type"] == "zodiac":
            print(f"  ♈ {r['english_name']} ({r['sanskrit_name']})")
            print(f"     Element: {r['element']} | Ruled by: {r['ruling_planet']}")
        print(f"     Keywords: {r['keywords']}")
    print()


def print_trinity(query, data):
    print(f"\n🔍 Query: '{query}'  (trinity mode)")
    print("=" * 55)
    print("\n— THE VEDIC TRINITY —")
    for slot in ("house", "planet", "zodiac"):
        r = data["trinity"][slot]
        if r is None:
            print(f"\n  [{slot.upper()}]  no confident match")
            continue
        print(f"\n  [{slot.upper()}]  Score: {r['score']:.2%}")
        if slot == "house":
            print(f"  🏠 House {r['house_number']} — {r['sanskrit_name']} ({r['english_name']})")
        elif slot == "planet":
            print(f"  🪐 {r['english_name']} ({r['sanskrit_name']})")
        else:
            print(f"  ♈ {r['english_name']} ({r['sanskrit_name']})")
        print(f"     Keywords: {r['keywords']}")
    if data["overflow"]:
        print("\n— ALSO RELATED —")
        print_results(query, data["overflow"])
    else:
        print()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "career"
    data = trinity_search(query, top_k=5)
    print_trinity(query, data)
