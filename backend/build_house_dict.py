"""
build_house_dict.py
====================
Expand the curated seeds in `house_seeds.py` into a full word → house
dictionary, using WordNet's synonym + hyponym graph.

For each seed word:
  1. Find its WordNet synset(s) — or use SYNSET_OVERRIDES if disambiguation needed
  2. Add all synonyms in those synsets (synonym lemmas)
  3. Add all direct hyponyms (more-specific terms: "sport" → tennis, cricket, …)
  4. Each derived word inherits the seed's house number
  5. Conflicts (word maps to multiple houses) are kept as a list

Outputs:
  - house_dictionary.json   — machine-readable, full record per word
  - house_dictionary.tsv    — spreadsheet-friendly: word, houses, source

Run:
  python3 build_house_dict.py
"""

from __future__ import annotations
import json
import re
from collections import defaultdict
from pathlib import Path

import nltk
from nltk.corpus import wordnet as wn

from house_seeds import HOUSE_SEEDS, HOUSE_LABELS, SYNSET_OVERRIDES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_wordnet():
    """Download WordNet if not present (idempotent)."""
    try:
        wn.synsets("test")
    except LookupError:
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)


def _clean_lemma(name: str) -> str:
    """Normalize a WordNet lemma name: 'long_journey' → 'long journey'."""
    return name.replace("_", " ").strip().lower()


def _is_useful_word(word: str) -> bool:
    """Filter out noise: very short, numeric, hyphenated proper nouns, etc."""
    if len(word) < 2:
        return False
    if re.search(r"[0-9]", word):
        return False
    if word.count(" ") > 2:        # very long phrases tend to be noise
        return False
    return True


def _expand_seed(word: str) -> tuple[set[str], list[str]]:
    """Return (derived_words, notes) for one seed.

    Pulls synonyms (lemmas in each synset) and direct hyponyms (one level).
    """
    notes = []
    derived: set[str] = {word.replace("_", " ").lower()}  # always include the seed itself

    # Pick the synsets to expand from
    if word in SYNSET_OVERRIDES:
        synsets = [wn.synset(SYNSET_OVERRIDES[word])]
        notes.append(f"override→{SYNSET_OVERRIDES[word]}")
    else:
        # Take noun + verb synsets; skip adjectives (they're rarely topical)
        synsets = wn.synsets(word.replace(" ", "_"), pos=wn.NOUN) \
                + wn.synsets(word.replace(" ", "_"), pos=wn.VERB)

    if not synsets:
        notes.append("no_wordnet_match")
        return derived, notes

    # Cap to 3 senses per word to avoid explosion on very polysemous terms
    for synset in synsets[:3]:
        # 1. Synonyms (lemmas in this synset)
        for lemma in synset.lemmas():
            w = _clean_lemma(lemma.name())
            if _is_useful_word(w):
                derived.add(w)

        # 2. Direct hyponyms (more-specific children)
        for hyponym in synset.hyponyms():
            for lemma in hyponym.lemmas():
                w = _clean_lemma(lemma.name())
                if _is_useful_word(w):
                    derived.add(w)

    return derived, notes


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_dictionary() -> dict:
    """Return the full word → record mapping."""
    _ensure_wordnet()

    # word → { houses: set, sources: list of (seed, house) }
    table: dict[str, dict] = defaultdict(lambda: {"houses": set(), "sources": []})

    # Per-house derivation log (for human review)
    per_house_derived: dict[int, set[str]] = defaultdict(set)

    print("Expanding seeds...\n")
    for house, seeds in HOUSE_SEEDS.items():
        print(f"  H{house:>2d} {HOUSE_LABELS[house]}")
        for seed in seeds:
            derived, notes = _expand_seed(seed)
            note_str = f"  [{', '.join(notes)}]" if notes else ""
            print(f"      • {seed:<22s} → {len(derived):>3d} words{note_str}")
            for word in derived:
                table[word]["houses"].add(house)
                table[word]["sources"].append({
                    "seed": seed.replace("_", " "),
                    "house": house,
                })
                per_house_derived[house].add(word)
        print()

    # Finalize: pick primary_house (the first house that introduced it = seed priority)
    # and convert sets to sorted lists for JSON serialization.
    output = {}
    for word, rec in table.items():
        houses = sorted(rec["houses"])
        # primary house = the house of the FIRST source that introduced this word
        primary = rec["sources"][0]["house"]
        output[word] = {
            "primary_house": primary,
            "houses": houses,
            "ambiguous": len(houses) > 1,
            "sources": rec["sources"],
        }

    # Summary stats
    print("─" * 60)
    print(f"Total unique words: {len(output):,}")
    print(f"Ambiguous (mapped to >1 house): {sum(1 for r in output.values() if r['ambiguous']):,}")
    print()
    print("Per-house word count (after dedup):")
    for h in sorted(per_house_derived.keys()):
        print(f"  H{h:>2d}  {HOUSE_LABELS[h]:<45s} {len(per_house_derived[h]):>4d} words")

    return output


def write_outputs(table: dict, out_dir: Path):
    json_path = out_dir / "house_dictionary.json"
    tsv_path  = out_dir / "house_dictionary.tsv"

    with json_path.open("w") as f:
        json.dump(table, f, indent=2, sort_keys=True)

    with tsv_path.open("w") as f:
        f.write("word\tprimary_house\thouses\tambiguous\tsources\n")
        for word in sorted(table.keys()):
            rec = table[word]
            sources_str = "; ".join(f"{s['seed']}(H{s['house']})" for s in rec["sources"][:5])
            f.write(
                f"{word}\t{rec['primary_house']}\t"
                f"{','.join(map(str, rec['houses']))}\t"
                f"{'yes' if rec['ambiguous'] else 'no'}\t"
                f"{sources_str}\n"
            )

    print(f"\nWrote: {json_path}")
    print(f"Wrote: {tsv_path}")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    table = build_dictionary()
    write_outputs(table, here)
