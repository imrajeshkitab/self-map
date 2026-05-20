"""
db_setup.py
Creates the SQLite database and all tables for the Vedic astrology data repository.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- HOUSES (Bhavas) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS houses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            house_number INTEGER UNIQUE NOT NULL,       -- 1 to 12
            sanskrit_name TEXT,                         -- e.g. Tanu Bhava
            english_name TEXT,                          -- e.g. House of Self
            ruling_sign TEXT,                           -- e.g. Aries
            ruling_planet TEXT,                         -- e.g. Mars
            significance TEXT,                          -- full description
            keywords TEXT,                              -- comma-separated core keywords
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- PLANETS (Grahas) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS planets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english_name TEXT UNIQUE NOT NULL,          -- e.g. Mars
            sanskrit_name TEXT,                         -- e.g. Mangal
            symbol TEXT,                                -- e.g. ♂
            rules_sign TEXT,                            -- e.g. Aries, Scorpio
            exalted_in TEXT,                            -- e.g. Capricorn
            debilitated_in TEXT,                        -- e.g. Cancer
            significance TEXT,                          -- full description
            keywords TEXT,                              -- comma-separated core keywords
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- ZODIAC SIGNS (Rashis) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zodiac_signs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sign_number INTEGER UNIQUE NOT NULL,        -- 1 to 12
            english_name TEXT UNIQUE NOT NULL,          -- e.g. Aries
            sanskrit_name TEXT,                         -- e.g. Mesha
            ruling_planet TEXT,                         -- e.g. Mars
            element TEXT,                               -- Fire, Earth, Air, Water
            quality TEXT,                               -- Movable, Fixed, Dual
            significance TEXT,                          -- full description
            keywords TEXT,                              -- comma-separated core keywords
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- SYNONYMS (for search mapping) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,                         -- user's search term, e.g. "job"
            maps_to TEXT NOT NULL,                      -- canonical keyword, e.g. "career"
            entity_type TEXT NOT NULL,                  -- "house", "planet", or "zodiac"
            entity_id INTEGER NOT NULL,                 -- FK to the relevant table
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_synonyms_term ON synonyms(term)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_synonyms_entity ON synonyms(entity_type, entity_id)")

    conn.commit()
    conn.close()
    print(f"✅ Database created at: {DB_PATH}")


if __name__ == "__main__":
    create_database()