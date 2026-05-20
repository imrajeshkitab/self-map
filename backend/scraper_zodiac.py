"""
scraper_zodiac.py
Scrapes Vedic astrology zodiac sign (rashi) significances.
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
# Seed data — 12 Vedic Rashis
# ---------------------------------------------------------------------------

VEDIC_ZODIAC_SEED = [
    {
        "sign_number": 1,
        "english_name": "Aries",
        "sanskrit_name": "Mesha",
        "ruling_planet": "Mars",
        "element": "Fire",
        "quality": "Movable (Chara)",
        "significance": (
            "Aries (Mesha) is the first sign of the Vedic zodiac. It represents initiative, "
            "leadership, courage, and new beginnings. Mesha natives are dynamic, energetic, "
            "and competitive. They are natural pioneers who love challenges. The sign governs "
            "the head and face. Aries people are direct, impulsive, and fiercely independent."
        ),
        "keywords": "initiative, leadership, courage, new beginnings, energy, pioneer, independent, competitive, dynamic, head",
    },
    {
        "sign_number": 2,
        "english_name": "Taurus",
        "sanskrit_name": "Vrishabha",
        "ruling_planet": "Venus",
        "element": "Earth",
        "quality": "Fixed (Sthira)",
        "significance": (
            "Taurus (Vrishabha) represents stability, material wealth, beauty, and sensual "
            "pleasure. Vrishabha natives are patient, reliable, and deeply connected to the "
            "material world. They appreciate luxury, good food, and the arts. The sign governs "
            "the neck and throat. Taurus people are determined and resistant to change."
        ),
        "keywords": "stability, wealth, beauty, pleasure, patience, reliable, luxury, food, arts, material, throat, determined",
    },
    {
        "sign_number": 3,
        "english_name": "Gemini",
        "sanskrit_name": "Mithuna",
        "ruling_planet": "Mercury",
        "element": "Air",
        "quality": "Dual (Dwiswabhava)",
        "significance": (
            "Gemini (Mithuna) represents duality, communication, intellect, and versatility. "
            "Mithuna natives are curious, witty, and adaptable. They excel in communication, "
            "writing, and trade. The sign governs the arms, hands, and shoulders. Gemini people "
            "are social, quick-thinking, and often have multiple interests simultaneously."
        ),
        "keywords": "communication, intellect, duality, versatility, curiosity, writing, trade, social, witty, arms, adaptable",
    },
    {
        "sign_number": 4,
        "english_name": "Cancer",
        "sanskrit_name": "Karka",
        "ruling_planet": "Moon",
        "element": "Water",
        "quality": "Movable (Chara)",
        "significance": (
            "Cancer (Karka) represents nurturing, emotional depth, home, and family. "
            "Karka natives are empathetic, protective, and deeply attached to their roots. "
            "They are intuitive and emotionally sensitive. The sign governs the chest, "
            "breasts, and stomach. Cancer people are natural caregivers with strong maternal instincts."
        ),
        "keywords": "nurturing, emotions, home, family, empathy, protective, intuition, sensitive, mother, caregiver, roots, domestic",
    },
    {
        "sign_number": 5,
        "english_name": "Leo",
        "sanskrit_name": "Simha",
        "ruling_planet": "Sun",
        "element": "Fire",
        "quality": "Fixed (Sthira)",
        "significance": (
            "Leo (Simha) represents royalty, authority, creativity, and self-expression. "
            "Simha natives are confident, generous, and natural leaders. They love recognition "
            "and perform well in positions of power. The sign governs the heart and upper back. "
            "Leo people are dramatic, warm-hearted, and fiercely loyal."
        ),
        "keywords": "royalty, authority, creativity, leadership, confidence, generous, recognition, power, dramatic, heart, loyal",
    },
    {
        "sign_number": 6,
        "english_name": "Virgo",
        "sanskrit_name": "Kanya",
        "ruling_planet": "Mercury",
        "element": "Earth",
        "quality": "Dual (Dwiswabhava)",
        "significance": (
            "Virgo (Kanya) represents analysis, service, health, and perfection. Kanya natives "
            "are meticulous, practical, and detail-oriented. They excel in healthcare, research, "
            "and service industries. The sign governs the digestive system and intestines. "
            "Virgo people are modest, hardworking, and critical thinkers."
        ),
        "keywords": "analysis, service, health, perfection, meticulous, practical, detail, research, healthcare, modest, hardworking",
    },
    {
        "sign_number": 7,
        "english_name": "Libra",
        "sanskrit_name": "Tula",
        "ruling_planet": "Venus",
        "element": "Air",
        "quality": "Movable (Chara)",
        "significance": (
            "Libra (Tula) represents balance, justice, partnership, and diplomacy. Tula natives "
            "are charming, fair-minded, and relationship-oriented. They are natural mediators "
            "who seek harmony in all areas of life. The sign governs the kidneys and lower back. "
            "Libra people are aesthetically inclined and often drawn to law and the arts."
        ),
        "keywords": "balance, justice, partnership, diplomacy, harmony, charm, relationships, mediation, law, aesthetics, fairness",
    },
    {
        "sign_number": 8,
        "english_name": "Scorpio",
        "sanskrit_name": "Vrishchika",
        "ruling_planet": "Mars",
        "element": "Water",
        "quality": "Fixed (Sthira)",
        "significance": (
            "Scorpio (Vrishchika) represents transformation, mystery, depth, and intensity. "
            "Vrishchika natives are passionate, secretive, and deeply perceptive. They are drawn "
            "to hidden truths, occult sciences, and psychological depth. The sign governs the "
            "reproductive organs and elimination system. Scorpio people are powerful and magnetic."
        ),
        "keywords": "transformation, mystery, intensity, passion, secrets, occult, depth, perception, power, magnetic, hidden, research",
    },
    {
        "sign_number": 9,
        "english_name": "Sagittarius",
        "sanskrit_name": "Dhanu",
        "ruling_planet": "Jupiter",
        "element": "Fire",
        "quality": "Dual (Dwiswabhava)",
        "significance": (
            "Sagittarius (Dhanu) represents philosophy, higher learning, travel, and freedom. "
            "Dhanu natives are optimistic, adventurous, and truth-seeking. They are drawn to "
            "religion, ethics, and long-distance journeys. The sign governs the hips and thighs. "
            "Sagittarius people are generous, honest, and have a natural love of wisdom."
        ),
        "keywords": "philosophy, higher learning, travel, freedom, optimism, adventure, religion, wisdom, ethics, honesty, foreign, generous",
    },
    {
        "sign_number": 10,
        "english_name": "Capricorn",
        "sanskrit_name": "Makara",
        "ruling_planet": "Saturn",
        "element": "Earth",
        "quality": "Movable (Chara)",
        "significance": (
            "Capricorn (Makara) represents ambition, discipline, career, and worldly achievement. "
            "Makara natives are hardworking, responsible, and goal-oriented. They are natural "
            "builders who achieve success through sustained effort. The sign governs the knees "
            "and bones. Capricorn people are patient, practical, and driven by long-term goals."
        ),
        "keywords": "ambition, discipline, career, achievement, hardworking, responsibility, goals, practical, patient, bones, structure",
    },
    {
        "sign_number": 11,
        "english_name": "Aquarius",
        "sanskrit_name": "Kumbha",
        "ruling_planet": "Saturn",
        "element": "Air",
        "quality": "Fixed (Sthira)",
        "significance": (
            "Aquarius (Kumbha) represents humanitarian ideals, innovation, community, and "
            "unconventional thinking. Kumbha natives are progressive, intellectual, and "
            "socially conscious. They are drawn to technology, social reform, and group "
            "endeavors. The sign governs the ankles and circulatory system. Aquarius people "
            "are independent and ahead of their time."
        ),
        "keywords": "humanitarian, innovation, community, progressive, intellectual, technology, social reform, unconventional, independent, groups",
    },
    {
        "sign_number": 12,
        "english_name": "Pisces",
        "sanskrit_name": "Meena",
        "ruling_planet": "Jupiter",
        "element": "Water",
        "quality": "Dual (Dwiswabhava)",
        "significance": (
            "Pisces (Meena) represents spirituality, compassion, imagination, and dissolution. "
            "Meena natives are empathetic, artistic, and deeply spiritual. They are intuitive "
            "and often psychic, with a strong connection to the unseen world. The sign governs "
            "the feet and lymphatic system. Pisces people are selfless, dreamlike, and compassionate."
        ),
        "keywords": "spirituality, compassion, imagination, empathy, artistic, intuition, psychic, dreams, selfless, feet, dissolution, mystical",
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


def scrape_astroved_sign(sign_name):
    url = f"https://www.astroved.com/astropedia/en/signs/{sign_name.lower()}"
    print(f"  🌐 Scraping astroved.com — {sign_name}: {url}")
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

def insert_zodiac(data_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0
    updated = 0

    for sign in data_list:
        cursor.execute("SELECT id FROM zodiac_signs WHERE sign_number = ?", (sign["sign_number"],))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE zodiac_signs SET
                    english_name = ?,
                    sanskrit_name = ?,
                    ruling_planet = ?,
                    element = ?,
                    quality = ?,
                    significance = ?,
                    keywords = ?,
                    source_url = ?
                WHERE sign_number = ?
            """, (
                sign["english_name"],
                sign.get("sanskrit_name"),
                sign.get("ruling_planet"),
                sign.get("element"),
                sign.get("quality"),
                sign.get("significance"),
                sign.get("keywords"),
                sign.get("source_url", "seed_data"),
                sign["sign_number"],
            ))
            updated += 1
        else:
            cursor.execute("""
                INSERT INTO zodiac_signs
                    (sign_number, english_name, sanskrit_name, ruling_planet,
                     element, quality, significance, keywords, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sign["sign_number"],
                sign["english_name"],
                sign.get("sanskrit_name"),
                sign.get("ruling_planet"),
                sign.get("element"),
                sign.get("quality"),
                sign.get("significance"),
                sign.get("keywords"),
                sign.get("source_url", "seed_data"),
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"  ✅ Zodiac signs — inserted: {inserted}, updated: {updated}")


def insert_synonyms_for_zodiac(signs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    count = 0

    for sign in signs:
        cursor.execute("SELECT id FROM zodiac_signs WHERE sign_number = ?", (sign["sign_number"],))
        row = cursor.fetchone()
        if not row:
            continue
        entity_id = row[0]

        all_terms = [kw.strip() for kw in sign.get("keywords", "").split(",") if kw.strip()]
        # Add Sanskrit name as synonym
        if sign.get("sanskrit_name"):
            all_terms.append(sign["sanskrit_name"].lower())
        # Add English name as synonym
        all_terms.append(sign["english_name"].lower())

        for term in all_terms:
            cursor.execute("""
                SELECT id FROM synonyms
                WHERE term = ? AND entity_type = 'zodiac' AND entity_id = ?
            """, (term.lower(), entity_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO synonyms (term, maps_to, entity_type, entity_id)
                    VALUES (?, ?, 'zodiac', ?)
                """, (term.lower(), term.lower(), entity_id))
                count += 1

    conn.commit()
    conn.close()
    print(f"  ✅ Zodiac synonyms inserted: {count}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    print("\n♈ Scraping Zodiac Signs (Rashis)...")

    print("  📦 Inserting seed data...")
    insert_zodiac(VEDIC_ZODIAC_SEED)

    print("  🌐 Attempting live scraping to enrich descriptions...")
    enriched = 0
    for sign in VEDIC_ZODIAC_SEED:
        scraped = scrape_astroved_sign(sign["english_name"])
        if scraped and len(scraped.get("significance", "")) > len(sign["significance"]):
            sign["significance"] = scraped["significance"]
            sign["source_url"] = scraped["source_url"]
            enriched += 1
        time.sleep(1)

    if enriched:
        print(f"  🔄 Enriched {enriched} zodiac descriptions from live scraping")
        insert_zodiac(VEDIC_ZODIAC_SEED)
    else:
        print("  ℹ️  Live scraping unavailable — seed data is complete and ready")

    print("  🔗 Building synonym index...")
    insert_synonyms_for_zodiac(VEDIC_ZODIAC_SEED)

    print("✅ Zodiac done!\n")


if __name__ == "__main__":
    run()