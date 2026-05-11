"""
embeddings.py
Builds a semantic search index for all houses, planets, and zodiac signs
using sentence-transformers (true semantic similarity, not keyword matching).

First run will download the model (~90MB). Subsequent runs are offline.

Run this:
    python embeddings.py

Re-run anytime new content is added to the DB (e.g. after book enrichment).
"""

import sqlite3
import os
import pickle
from sentence_transformers import SentenceTransformer

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "search_index.pkl")
MODEL_NAME = "all-MiniLM-L6-v2"


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

    print(f"Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    print(f"Encoding {len(documents)} documents...")
    embeddings = model.encode(documents, normalize_embeddings=True, show_progress_bar=True)

    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"model_name": MODEL_NAME, "embeddings": embeddings, "metadata": metadata}, f)

    return len(documents)


if __name__ == "__main__":
    print("\n🔮 Building semantic search index (sentence-transformers)...")
    count = build_index()
    print(f"✅ Done — {count} entities indexed and ready\n")
