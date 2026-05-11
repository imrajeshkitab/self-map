"""
scraper_planets.py
Scrapes Vedic astrology planet (graha) significances.
Stores results in the SQLite database.
"""

import requests
import sqlite3
import os
import time
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Seed data — 9 Vedic Grahas (includes Rahu & Ketu, the shadow planets)
# ---------------------------------------------------------------------------

VEDIC_PLANETS_SEED = [
    {
        "english_name": "Sun",
        "sanskrit_name": "Surya",
        "symbol": "☉",
        "rules_sign": "Leo",
        "exalted_in": "Aries",
        "debilitated_in": "Libra",
        "significance": (
            "The Sun (Surya) is the king of the planetary cabinet in Vedic astrology. "
            "It represents the soul (atma), authority, father, ego, government, leadership, "
            "and vitality. A strong Sun gives confidence, power, and recognition. "
            "It rules the heart, spine, and eyes. The Sun signifies one's life force, "
            "self-expression, and relationship with authority figures and the state."
        ),
        "keywords": "soul, authority, father, ego, government, leadership, vitality, king, power, confidence, recognition, health, spine",
    },
    {
        "english_name": "Moon",
        "sanskrit_name": "Chandra",
        "symbol": "☽",
        "rules_sign": "Cancer",
        "exalted_in": "Taurus",
        "debilitated_in": "Scorpio",
        "significance": (
            "The Moon (Chandra) is the queen of the planetary cabinet. It governs the "
            "mind, emotions, mother, home, intuition, and subconscious. The Moon rules "
            "water, nourishment, fertility, and public life. A strong Moon gives emotional "
            "stability, nurturing qualities, and a strong connection to one's roots. "
            "It rules the chest, lungs, and bodily fluids."
        ),
        "keywords": "mind, emotions, mother, home, intuition, subconscious, water, fertility, nourishment, feelings, mood, mental health",
    },
    {
        "english_name": "Mars",
        "sanskrit_name": "Mangal",
        "symbol": "♂",
        "rules_sign": "Aries, Scorpio",
        "exalted_in": "Capricorn",
        "debilitated_in": "Cancer",
        "significance": (
            "Mars (Mangal) is the commander of the planetary army. It represents courage, "
            "energy, ambition, drive, brothers, property, and conflict. Mars governs "
            "physical strength, sports, surgery, engineering, and the military. "
            "It rules blood, muscles, and the bone marrow. A strong Mars gives determination "
            "and the ability to overcome obstacles."
        ),
        "keywords": "courage, energy, ambition, brothers, property, conflict, strength, sports, military, surgery, anger, passion, drive",
    },
    {
        "english_name": "Mercury",
        "sanskrit_name": "Budha",
        "symbol": "☿",
        "rules_sign": "Gemini, Virgo",
        "exalted_in": "Virgo",
        "debilitated_in": "Pisces",
        "significance": (
            "Mercury (Budha) is the prince of the planetary cabinet. It rules intelligence, "
            "communication, trade, logic, writing, and learning. Mercury governs the nervous "
            "system, skin, and speech. It signifies business acumen, analytical ability, "
            "and the power of discrimination. A strong Mercury gives sharp intellect and "
            "excellent communication skills."
        ),
        "keywords": "intelligence, communication, trade, logic, writing, learning, business, speech, intellect, analysis, education, commerce",
    },
    {
        "english_name": "Jupiter",
        "sanskrit_name": "Guru / Brihaspati",
        "symbol": "♃",
        "rules_sign": "Sagittarius, Pisces",
        "exalted_in": "Cancer",
        "debilitated_in": "Capricorn",
        "significance": (
            "Jupiter (Guru/Brihaspati) is the guru of the gods and the most benefic planet "
            "in Vedic astrology. It represents wisdom, knowledge, dharma, religion, "
            "children, wealth, and expansion. Jupiter governs teachers, priests, higher "
            "education, law, and philosophy. It rules the liver, hips, and thighs. "
            "A strong Jupiter blesses with prosperity, wisdom, and spiritual growth."
        ),
        "keywords": "wisdom, knowledge, dharma, religion, children, wealth, expansion, teacher, guru, philosophy, law, prosperity, spirituality, luck",
    },
    {
        "english_name": "Venus",
        "sanskrit_name": "Shukra",
        "symbol": "♀",
        "rules_sign": "Taurus, Libra",
        "exalted_in": "Pisces",
        "debilitated_in": "Virgo",
        "significance": (
            "Venus (Shukra) is the guru of the asuras and the planet of love and beauty. "
            "It governs romance, marriage, arts, luxury, pleasure, and material comforts. "
            "Venus rules the reproductive system, kidneys, and throat. It signifies "
            "creativity, aesthetics, fashion, music, and the ability to enjoy life. "
            "A strong Venus brings charm, artistic talent, and harmonious relationships."
        ),
        "keywords": "love, beauty, romance, marriage, arts, luxury, pleasure, creativity, fashion, music, relationships, aesthetics, comfort",
    },
    {
        "english_name": "Saturn",
        "sanskrit_name": "Shani",
        "symbol": "♄",
        "rules_sign": "Capricorn, Aquarius",
        "exalted_in": "Libra",
        "debilitated_in": "Aries",
        "significance": (
            "Saturn (Shani) is the judge and karmic planet. It represents discipline, "
            "hard work, karma, restrictions, longevity, and old age. Saturn governs "
            "servants, the masses, agriculture, and justice. It rules the bones, teeth, "
            "and knees. A strong Saturn gives perseverance, responsibility, and the ability "
            "to achieve through sustained effort. It teaches through challenges and delays."
        ),
        "keywords": "discipline, karma, hard work, restriction, longevity, justice, delay, responsibility, perseverance, agriculture, old age, servant",
    },
    {
        "english_name": "Rahu",
        "sanskrit_name": "Rahu",
        "symbol": "☊",
        "rules_sign": "Aquarius (co-ruler)",
        "exalted_in": "Gemini (or Taurus, debated)",
        "debilitated_in": "Sagittarius (or Scorpio, debated)",
        "significance": (
            "Rahu is the North Node of the Moon and a shadow planet (chaya graha). "
            "It represents obsession, illusion, foreign elements, technology, and worldly "
            "desires. Rahu amplifies whatever it touches and causes sudden events. It "
            "governs unconventional paths, innovation, manipulation, and mass trends. "
            "Rahu is associated with materialism, ambition beyond limits, and karmic lessons "
            "related to desire and attachment."
        ),
        "keywords": "obsession, illusion, foreign, technology, desire, innovation, sudden, unconventional, ambition, materialism, karma, north node",
    },
    {
        "english_name": "Ketu",
        "sanskrit_name": "Ketu",
        "symbol": "☋",
        "rules_sign": "Scorpio (co-ruler)",
        "exalted_in": "Sagittarius (or Scorpio, debated)",
        "debilitated_in": "Gemini (or Taurus, debated)",
        "significance": (
            "Ketu is the South Node of the Moon and a shadow planet (chaya graha). "
            "It represents spirituality, liberation, past-life karma, detachment, and "
            "mysticism. Ketu causes sudden losses that lead to spiritual growth. It governs "
            "moksha, occult sciences, meditation, and healing. Ketu dissolves the material "
            "and pushes toward transcendence. It is associated with saints, healers, and "
            "enlightened beings."
        ),
        "keywords": "spirituality, liberation, past life, detachment, mysticism, moksha, occult, meditation, healing, transcendence, south node, enlightenment",
    },
]


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def fetch_page(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            print(f"  ⚠️  HTTP {resp.status_code} for {url}")
        except Exception as e:
            print(f"  ⚠️  Attempt {attempt + 1} failed: {e}")
        time.sleep(delay)
    return None


def scrape_astroved_planet(planet_name):
    """Try to scrape planet page from astroved.com."""
    url = f"https://www.astroved.com/astropedia/en/planets/{planet_name.lower()}"
    print(f"  🌐 Scraping astroved.com — {planet_name}: {url}")
    soup = fetch_page(url)
    if not soup:
        return None

    content_div = soup.find("div", class_="entry-content") or soup.find("article")
    if not content_div:
        return None

    paragraphs = content_div.find_all("p")
    text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50)
    if len(text) < 100:
        return None

    return {"significance": text[:2000], "source_url": url}


# ---------------------------------------------------------------------------
# Database insertion
# ---------------------------------------------------------------------------

def insert_planets(data_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0
    updated = 0

    for planet in data_list:
        cursor.execute("SELECT id FROM planets WHERE english_name = ?", (planet["english_name"],))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE planets SET
                    sanskrit_name = ?,
                    symbol = ?,
                    rules_sign = ?,
                    exalted_in = ?,
                    debilitated_in = ?,
                    significance = ?,
                    keywords = ?,
                    source_url = ?
                WHERE english_name = ?
            """, (
                planet.get("sanskrit_name"),
                planet.get("symbol"),
                planet.get("rules_sign"),
                planet.get("exalted_in"),
                planet.get("debilitated_in"),
                planet.get("significance"),
                planet.get("keywords"),
                planet.get("source_url", "seed_data"),
                planet["english_name"],
            ))
            updated += 1
        else:
            cursor.execute("""
                INSERT INTO planets
                    (english_name, sanskrit_name, symbol, rules_sign,
                     exalted_in, debilitated_in, significance, keywords, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                planet["english_name"],
                planet.get("sanskrit_name"),
                planet.get("symbol"),
                planet.get("rules_sign"),
                planet.get("exalted_in"),
                planet.get("debilitated_in"),
                planet.get("significance"),
                planet.get("keywords"),
                planet.get("source_url", "seed_data"),
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"  ✅ Planets — inserted: {inserted}, updated: {updated}")


def insert_synonyms_for_planets(planets):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    count = 0

    for planet in planets:
        cursor.execute("SELECT id FROM planets WHERE english_name = ?", (planet["english_name"],))
        row = cursor.fetchone()
        if not row:
            continue
        entity_id = row[0]

        # Add Sanskrit name as synonym too
        all_terms = [kw.strip() for kw in planet.get("keywords", "").split(",") if kw.strip()]
        if planet.get("sanskrit_name"):
            for name in planet["sanskrit_name"].split("/"):
                all_terms.append(name.strip().lower())

        for term in all_terms:
            cursor.execute("""
                SELECT id FROM synonyms
                WHERE term = ? AND entity_type = 'planet' AND entity_id = ?
            """, (term.lower(), entity_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO synonyms (term, maps_to, entity_type, entity_id)
                    VALUES (?, ?, 'planet', ?)
                """, (term.lower(), term.lower(), entity_id))
                count += 1

    conn.commit()
    conn.close()
    print(f"  ✅ Planet synonyms inserted: {count}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    print("\n🪐 Scraping Planets (Grahas)...")

    print("  📦 Inserting seed data...")
    insert_planets(VEDIC_PLANETS_SEED)

    print("  🌐 Attempting live scraping to enrich descriptions...")
    enriched = 0
    for planet in VEDIC_PLANETS_SEED:
        scraped = scrape_astroved_planet(planet["english_name"])
        if scraped and len(scraped.get("significance", "")) > len(planet["significance"]):
            planet["significance"] = scraped["significance"]
            planet["source_url"] = scraped["source_url"]
            enriched += 1
        time.sleep(1)

    if enriched:
        print(f"  🔄 Enriched {enriched} planet descriptions from live scraping")
        insert_planets(VEDIC_PLANETS_SEED)
    else:
        print("  ℹ️  Live scraping unavailable — seed data is complete and ready")

    print("  🔗 Building synonym index...")
    insert_synonyms_for_planets(VEDIC_PLANETS_SEED)

    print("✅ Planets done!\n")


if __name__ == "__main__":
    run()