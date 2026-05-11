"""
scraper_houses.py
Scrapes Vedic astrology house (bhava) significances from astroved.com and astrosage.com.
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
# Static Vedic data as fallback / seed (always inserted)
# This ensures the DB is never empty even if scraping is blocked.
# ---------------------------------------------------------------------------

VEDIC_HOUSES_SEED = [
    {
        "house_number": 1,
        "sanskrit_name": "Tanu Bhava",
        "english_name": "House of Self",
        "ruling_sign": "Aries",
        "ruling_planet": "Mars",
        "significance": (
            "The 1st house represents the self, physical body, appearance, personality, "
            "temperament, and overall health. It is the Ascendant (Lagna) and sets the "
            "foundation of the entire horoscope. It governs vitality, early childhood, "
            "character, and how one presents themselves to the world."
        ),
        "keywords": "self, body, appearance, personality, health, lagna, ascendant, vitality, identity, character",
    },
    {
        "house_number": 2,
        "sanskrit_name": "Dhana Bhava",
        "english_name": "House of Wealth",
        "ruling_sign": "Taurus",
        "ruling_planet": "Venus",
        "significance": (
            "The 2nd house governs wealth, accumulated assets, family, speech, food, "
            "face, and early education. It is called Dhana (wealth) Bhava and indicates "
            "one's financial status, savings, and material possessions. It also rules the "
            "family of origin and the power of speech."
        ),
        "keywords": "wealth, money, family, speech, food, savings, assets, possessions, finances, resources",
    },
    {
        "house_number": 3,
        "sanskrit_name": "Sahaja Bhava",
        "english_name": "House of Siblings",
        "ruling_sign": "Gemini",
        "ruling_planet": "Mercury",
        "significance": (
            "The 3rd house rules siblings, courage, communication, short journeys, "
            "writing, hands, and neighbors. It represents valor, self-effort, and the "
            "ability to initiate action. It also covers media, publishing, and all forms "
            "of communication."
        ),
        "keywords": "siblings, courage, communication, writing, travel, neighbors, media, brothers, sisters, effort",
    },
    {
        "house_number": 4,
        "sanskrit_name": "Sukha Bhava",
        "english_name": "House of Happiness",
        "ruling_sign": "Cancer",
        "ruling_planet": "Moon",
        "significance": (
            "The 4th house signifies mother, home, land, property, vehicles, happiness, "
            "and inner emotional peace. It represents roots, domestic life, real estate, "
            "and one's homeland. It is the foundation of emotional security and "
            "psychological well-being."
        ),
        "keywords": "mother, home, property, land, happiness, vehicles, real estate, domestic, roots, comfort",
    },
    {
        "house_number": 5,
        "sanskrit_name": "Putra Bhava",
        "english_name": "House of Children",
        "ruling_sign": "Leo",
        "ruling_planet": "Sun",
        "significance": (
            "The 5th house rules children, creativity, intelligence, romance, past-life "
            "merit (purva punya), education, and speculation. It governs artistic talents, "
            "entertainment, sports, and the capacity for deep thinking and mantra."
        ),
        "keywords": "children, creativity, romance, intelligence, education, speculation, arts, entertainment, love, merit",
    },
    {
        "house_number": 6,
        "sanskrit_name": "Ari Bhava",
        "english_name": "House of Enemies",
        "ruling_sign": "Virgo",
        "ruling_planet": "Mercury",
        "significance": (
            "The 6th house covers enemies, diseases, debts, service, daily work, "
            "obstacles, and legal conflicts. It also represents healing, health routines, "
            "and the capacity to overcome adversity. It governs employees and subordinates."
        ),
        "keywords": "enemies, disease, debt, service, work, health, obstacles, conflicts, healing, subordinates",
    },
    {
        "house_number": 7,
        "sanskrit_name": "Yuvati Bhava",
        "english_name": "House of Partnership",
        "ruling_sign": "Libra",
        "ruling_planet": "Venus",
        "significance": (
            "The 7th house represents marriage, business partnerships, spouse, open "
            "enemies, foreign travel, and public dealings. It is the house of relationships "
            "and contracts. It governs how one relates to others in both personal and "
            "professional contexts."
        ),
        "keywords": "marriage, spouse, partnership, business, relationships, contracts, public, foreign, husband, wife",
    },
    {
        "house_number": 8,
        "sanskrit_name": "Mrityu Bhava",
        "english_name": "House of Death and Transformation",
        "ruling_sign": "Scorpio",
        "ruling_planet": "Mars",
        "significance": (
            "The 8th house governs death, longevity, transformation, hidden matters, "
            "inheritance, occult sciences, and sudden events. It rules regeneration, "
            "research, and the deep mysteries of life. It also covers insurance, "
            "legacies, and the assets of others."
        ),
        "keywords": "death, transformation, longevity, inheritance, occult, hidden, mystery, research, secrets, rebirth",
    },
    {
        "house_number": 9,
        "sanskrit_name": "Dharma Bhava",
        "english_name": "House of Fortune",
        "ruling_sign": "Sagittarius",
        "ruling_planet": "Jupiter",
        "significance": (
            "The 9th house represents dharma, higher learning, philosophy, religion, "
            "long journeys, father, fortune, and guru. It is one of the most auspicious "
            "houses, governing spiritual wisdom, foreign lands, and one's life purpose."
        ),
        "keywords": "dharma, fortune, religion, philosophy, father, guru, travel, wisdom, higher education, spirituality",
    },
    {
        "house_number": 10,
        "sanskrit_name": "Karma Bhava",
        "english_name": "House of Career",
        "ruling_sign": "Capricorn",
        "ruling_planet": "Saturn",
        "significance": (
            "The 10th house is the house of career, profession, reputation, status, "
            "authority, and public life. It represents one's actions in the world (karma), "
            "ambitions, and achievements. It governs the relationship with the government "
            "and one's standing in society."
        ),
        "keywords": "career, profession, reputation, status, authority, ambition, job, work, business, achievement",
    },
    {
        "house_number": 11,
        "sanskrit_name": "Labha Bhava",
        "english_name": "House of Gains",
        "ruling_sign": "Aquarius",
        "ruling_planet": "Saturn",
        "significance": (
            "The 11th house signifies gains, income, elder siblings, social networks, "
            "aspirations, and fulfilment of desires. It is the house of abundance and "
            "represents all forms of profit, social circles, and large organizations."
        ),
        "keywords": "gains, income, profits, desires, social network, friends, aspirations, elder siblings, abundance, organizations",
    },
    {
        "house_number": 12,
        "sanskrit_name": "Vyaya Bhava",
        "english_name": "House of Loss and Liberation",
        "ruling_sign": "Pisces",
        "ruling_planet": "Jupiter",
        "significance": (
            "The 12th house governs losses, expenditure, isolation, foreign lands, "
            "moksha (liberation), hospitals, and the subconscious mind. It rules spiritual "
            "enlightenment, self-undoing, hidden enemies, and life behind the scenes. "
            "It also covers sleep, dreams, and the astral plane."
        ),
        "keywords": "loss, expenditure, liberation, moksha, foreign, isolation, hospital, spirituality, dreams, subconscious",
    },
]


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def fetch_page(url, retries=3, delay=2):
    """Fetch a URL with retries. Returns BeautifulSoup or None."""
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


def scrape_astroved_house(house_number):
    """Try to scrape a single house page from astroved.com."""
    ordinals = [
        "", "first", "second", "third", "fourth", "fifth", "sixth",
        "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"
    ]
    url = f"https://www.astroved.com/astropedia/en/houses/{ordinals[house_number]}-house"
    print(f"  🌐 Scraping astroved.com — House {house_number}: {url}")
    soup = fetch_page(url)
    if not soup:
        return None

    # Try to grab the main content paragraphs
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

def insert_houses(data_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0
    updated = 0

    for house in data_list:
        cursor.execute("SELECT id FROM houses WHERE house_number = ?", (house["house_number"],))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE houses SET
                    sanskrit_name = ?,
                    english_name = ?,
                    ruling_sign = ?,
                    ruling_planet = ?,
                    significance = ?,
                    keywords = ?,
                    source_url = ?
                WHERE house_number = ?
            """, (
                house.get("sanskrit_name"),
                house.get("english_name"),
                house.get("ruling_sign"),
                house.get("ruling_planet"),
                house.get("significance"),
                house.get("keywords"),
                house.get("source_url", "seed_data"),
                house["house_number"],
            ))
            updated += 1
        else:
            cursor.execute("""
                INSERT INTO houses
                    (house_number, sanskrit_name, english_name, ruling_sign,
                     ruling_planet, significance, keywords, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                house["house_number"],
                house.get("sanskrit_name"),
                house.get("english_name"),
                house.get("ruling_sign"),
                house.get("ruling_planet"),
                house.get("significance"),
                house.get("keywords"),
                house.get("source_url", "seed_data"),
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"  ✅ Houses — inserted: {inserted}, updated: {updated}")


def insert_synonyms_for_houses(houses):
    """Auto-generate synonyms from house keywords."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    count = 0

    for house in houses:
        cursor.execute("SELECT id FROM houses WHERE house_number = ?", (house["house_number"],))
        row = cursor.fetchone()
        if not row:
            continue
        entity_id = row[0]

        keywords = [kw.strip() for kw in house.get("keywords", "").split(",") if kw.strip()]
        for kw in keywords:
            # avoid duplicates
            cursor.execute("""
                SELECT id FROM synonyms
                WHERE term = ? AND entity_type = 'house' AND entity_id = ?
            """, (kw.lower(), entity_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO synonyms (term, maps_to, entity_type, entity_id)
                    VALUES (?, ?, 'house', ?)
                """, (kw.lower(), kw.lower(), entity_id))
                count += 1

    conn.commit()
    conn.close()
    print(f"  ✅ House synonyms inserted: {count}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    print("\n🏠 Scraping Houses (Bhavas)...")

    # Step 1: Always insert seed data first
    print("  📦 Inserting seed data...")
    insert_houses(VEDIC_HOUSES_SEED)

    # Step 2: Try to enrich with live scraping
    print("  🌐 Attempting live scraping to enrich descriptions...")
    enriched = 0
    for house in VEDIC_HOUSES_SEED:
        scraped = scrape_astroved_house(house["house_number"])
        if scraped and len(scraped.get("significance", "")) > len(house["significance"]):
            house["significance"] = scraped["significance"]
            house["source_url"] = scraped["source_url"]
            enriched += 1
        time.sleep(1)  # polite delay

    if enriched:
        print(f"  🔄 Enriched {enriched} house descriptions from live scraping")
        insert_houses(VEDIC_HOUSES_SEED)
    else:
        print("  ℹ️  Live scraping unavailable — seed data is complete and ready")

    # Step 3: Build synonym index
    print("  🔗 Building synonym index...")
    insert_synonyms_for_houses(VEDIC_HOUSES_SEED)

    print("✅ Houses done!\n")


if __name__ == "__main__":
    run()