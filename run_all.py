"""
run_all.py
Master script — runs the full pipeline:
  1. Creates the database schema
  2. Scrapes houses (bhavas)
  3. Scrapes planets (grahas)
  4. Scrapes zodiac signs (rashis)
  5. Prints a summary of what was built

Usage:
    python run_all.py

Optional — search the database after building:
    python run_all.py --search "career"
"""

import sys
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")


def print_banner():
    print("\n" + "=" * 55)
    print("   🪐 Vedic Astrology Data Repository Builder")
    print("=" * 55)


def print_summary():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM houses")
    houses = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM planets")
    planets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM zodiac_signs")
    zodiac = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM synonyms")
    synonyms = cursor.fetchone()[0]

    conn.close()

    print("\n" + "=" * 55)
    print("📊 Database Summary")
    print("=" * 55)
    print(f"  🏠 Houses (Bhavas):      {houses}/12")
    print(f"  🪐 Planets (Grahas):     {planets}/9")
    print(f"  ♈ Zodiac Signs (Rashis): {zodiac}/12")
    print(f"  🔗 Synonym entries:       {synonyms}")
    print(f"  💾 Database location:     {DB_PATH}")
    print("=" * 55)


def search(query):
    """Search across all entities using the synonym index."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    q = query.lower().strip()

    print(f"\n🔍 Search results for: '{query}'")
    print("-" * 45)

    # Direct synonym lookup
    cursor.execute("""
        SELECT DISTINCT entity_type, entity_id
        FROM synonyms
        WHERE term LIKE ?
    """, (f"%{q}%",))
    matches = cursor.fetchall()

    if not matches:
        print("  No results found.")
        conn.close()
        return

    for entity_type, entity_id in matches:
        if entity_type == "house":
            cursor.execute("""
                SELECT house_number, sanskrit_name, english_name, keywords
                FROM houses WHERE id = ?
            """, (entity_id,))
            row = cursor.fetchone()
            if row:
                print(f"\n  🏠 House {row[0]} — {row[1]} ({row[2]})")
                print(f"     Keywords: {row[3]}")

        elif entity_type == "planet":
            cursor.execute("""
                SELECT english_name, sanskrit_name, keywords
                FROM planets WHERE id = ?
            """, (entity_id,))
            row = cursor.fetchone()
            if row:
                print(f"\n  🪐 Planet — {row[0]} ({row[1]})")
                print(f"     Keywords: {row[2]}")

        elif entity_type == "zodiac":
            cursor.execute("""
                SELECT english_name, sanskrit_name, keywords
                FROM zodiac_signs WHERE id = ?
            """, (entity_id,))
            row = cursor.fetchone()
            if row:
                print(f"\n  ♈ Zodiac — {row[0]} ({row[1]})")
                print(f"     Keywords: {row[2]}")

    conn.close()


def run_pipeline():
    print_banner()

    # Step 1: Database setup
    print("\n📁 Step 1/4 — Setting up database...")
    from db_setup import create_database
    create_database()

    # Step 2: Houses
    print("\n📁 Step 2/4 — Houses (Bhavas)...")
    from scraper_houses import run as run_houses
    run_houses()

    # Step 3: Planets
    print("\n📁 Step 3/4 — Planets (Grahas)...")
    from scraper_planets import run as run_planets
    run_planets()

    # Step 4: Zodiac
    print("\n📁 Step 4/4 — Zodiac Signs (Rashis)...")
    from scraper_zodiac import run as run_zodiac
    run_zodiac()

    # Summary
    print_summary()
    print("\n✅ All done! Your Vedic astrology database is ready.")
    print("   Tip: Run  python run_all.py --search 'career'  to test a search.\n")


if __name__ == "__main__":
    if "--search" in sys.argv:
        idx = sys.argv.index("--search")
        if idx + 1 < len(sys.argv):
            search(sys.argv[idx + 1])
        else:
            print("Please provide a search term: python run_all.py --search 'career'")
    else:
        run_pipeline()