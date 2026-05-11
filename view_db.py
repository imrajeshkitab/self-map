"""
view_db.py
Pretty-print the Vedic Astrology DB in a human-readable form.

Usage:
    python3 view_db.py            # print to terminal
    python3 view_db.py --md       # also write DATABASE.md (shareable)
"""

import sqlite3
import os
import sys
import textwrap

DB_PATH = os.path.join(os.path.dirname(__file__), "vedic_astrology.db")
MD_PATH = os.path.join(os.path.dirname(__file__), "DATABASE.md")

WRAP = 70  # wrap long text columns


def short(text, n=WRAP):
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def fetch(query):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    conn.close()
    return cols, rows


# ---------------------------------------------------------------------------
# Terminal printing
# ---------------------------------------------------------------------------

def print_table(title, cols, rows, col_widths):
    line = "+".join("-" * (w + 2) for w in col_widths)
    print(f"\n{'═' * len(line)}")
    print(f"  {title}  ({len(rows)} rows)")
    print("═" * len(line))
    header = " | ".join(c.ljust(w) for c, w in zip(cols, col_widths))
    print(header)
    print("-" * len(header))
    for row in rows:
        cells = [short(v, w) for v, w in zip(row, col_widths)]
        print(" | ".join(c.ljust(w) for c, w in zip(cells, col_widths)))


def print_terminal():
    cols, rows = fetch(
        "SELECT house_number, sanskrit_name, english_name, ruling_planet, keywords FROM houses ORDER BY house_number"
    )
    print_table("HOUSES (Bhavas)", cols, rows, [4, 18, 28, 14, 50])

    cols, rows = fetch(
        "SELECT english_name, sanskrit_name, rules_sign, exalted_in, keywords FROM planets ORDER BY id"
    )
    print_table("PLANETS (Grahas)", cols, rows, [10, 14, 22, 14, 50])

    cols, rows = fetch(
        "SELECT sign_number, english_name, sanskrit_name, ruling_planet, element, quality, keywords FROM zodiac_signs ORDER BY sign_number"
    )
    print_table("ZODIAC SIGNS (Rashis)", cols, rows, [4, 12, 12, 14, 6, 16, 45])

    cols, rows = fetch("SELECT entity_type, COUNT(*) FROM synonyms GROUP BY entity_type")
    print_table("SYNONYMS (summary)", ["entity_type", "count"], rows, [12, 8])


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def md_table(cols, rows):
    out = ["| " + " | ".join(cols) + " |",
           "|" + "|".join("---" for _ in cols) + "|"]
    for row in rows:
        cells = [short(v, 80).replace("|", "\\|").replace("\n", " ") for v in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def write_md():
    sections = []

    sections.append("# Vedic Astrology Database\n")
    sections.append("Local SQLite database (`vedic_astrology.db`) powering the semantic search engine.\n")

    cols, rows = fetch(
        "SELECT house_number, sanskrit_name, english_name, ruling_planet, keywords FROM houses ORDER BY house_number"
    )
    sections.append(f"## Houses (Bhavas) — {len(rows)} rows\n")
    sections.append(md_table(cols, rows) + "\n")

    cols, rows = fetch(
        "SELECT english_name, sanskrit_name, rules_sign, exalted_in, debilitated_in, keywords FROM planets ORDER BY id"
    )
    sections.append(f"## Planets (Grahas) — {len(rows)} rows\n")
    sections.append(md_table(cols, rows) + "\n")

    cols, rows = fetch(
        "SELECT sign_number, english_name, sanskrit_name, ruling_planet, element, quality, keywords FROM zodiac_signs ORDER BY sign_number"
    )
    sections.append(f"## Zodiac Signs (Rashis) — {len(rows)} rows\n")
    sections.append(md_table(cols, rows) + "\n")

    cols, rows = fetch("SELECT entity_type, COUNT(*) FROM synonyms GROUP BY entity_type")
    sections.append(f"## Synonyms — {sum(r[1] for r in rows)} rows total\n")
    sections.append(md_table(["entity_type", "count"], rows) + "\n")

    # A small sample of synonyms
    cols, rows = fetch("SELECT term, maps_to, entity_type FROM synonyms LIMIT 10")
    sections.append("**Sample rows:**\n")
    sections.append(md_table(cols, rows) + "\n")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))

    print(f"\n📄 Wrote {MD_PATH}")


if __name__ == "__main__":
    print_terminal()
    if "--md" in sys.argv:
        write_md()
