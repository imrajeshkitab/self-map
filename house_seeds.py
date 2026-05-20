"""
house_seeds.py
================
Curated seed words for each of the 12 Vedic houses.

These are the *trusted* anchors. The build script expands them via
WordNet (synonyms + direct hyponyms) into a much larger word→house
dictionary.

WHEN TO EDIT THIS FILE:
  - You spotted a noun/verb that should clearly belong to a house
    but isn't being mapped correctly.
  - Durga or Ravi sir suggested a classical addition.
  - A user query mapped to "general" when it shouldn't have.

WHEN NOT TO EDIT:
  - For a single rare word — let the WordNet synonym fallback handle it.
  - For polysemous words (e.g. "bank") — disambiguation belongs in the
    expansion script, not the seed list.

Each list = a starter set of high-confidence words for that house.
The build script will multiply each by ~10–30 derived words via WordNet.
"""

# ---------------------------------------------------------------------------
# Seeds per house. Comments cite the classical signification.
# ---------------------------------------------------------------------------

HOUSE_SEEDS: dict[int, list[str]] = {
    1: [
        # The self, body, identity, vitality, appearance, lifespan
        "self", "body", "health", "life", "identity", "personality",
        "appearance", "character", "vitality", "ego", "beginning",
        "wellbeing", "stamina", "complexion", "constitution",
    ],
    2: [
        # Wealth, family lineage, speech, food, accumulated possessions
        "money", "wealth", "income", "savings", "earnings", "finance",
        "fortune", "asset", "possession", "family", "speech", "voice",
        "food", "diet", "eating", "bank", "deposit", "treasure",
    ],
    3: [
        # Siblings, courage, hands, short journeys, writing, communication, skill
        "sibling", "brother", "sister", "courage", "effort", "valor",
        "communication", "writing", "letter", "journalism", "neighbor",
        "neighborhood", "hand", "arm", "skill", "hobby", "talent",
        "media", "newspaper", "podcast", "blog",
    ],
    4: [
        # Home, mother, comforts, vehicles, property, roots, early schooling
        "home", "house", "mother", "comfort", "vehicle", "car", "bike",
        "property", "land", "estate", "real_estate", "peace", "roots",
        "foundation", "childhood", "kindergarten", "garden", "soil",
        "dwelling", "residence",
    ],
    5: [
        # Children, creativity, intelligence, sports, romance, entertainment,
        # speculation, learning
        "child", "kid", "baby", "pregnancy", "creativity", "intelligence",
        "intellect", "romance", "dating", "infatuation", "lover",
        "sport", "game", "play", "tennis", "cricket", "football",
        "movie", "film", "cinema", "show", "entertainment", "fun",
        "hobby", "gambling", "speculation", "stock", "investment",
        "learning", "education", "study", "exam",
    ],
    6: [
        # Daily work, service, illness, debts, enemies, obstacles, pets, routine
        "work", "job", "service", "employee", "subordinate", "labor",
        "duty", "routine", "illness", "disease", "sickness", "fever",
        "pain", "injury", "debt", "loan", "borrowing", "enemy",
        "competitor", "rival", "obstacle", "lawsuit", "litigation",
        "pet", "cat", "dog",
    ],
    7: [
        # Spouse, partner, marriage, contracts, business dealings, the public
        "spouse", "partner", "marriage", "husband", "wife", "wedding",
        "fiance", "fiancee", "contract", "agreement", "deal", "treaty",
        "negotiation", "client", "customer", "buyer", "seller",
        "public", "audience", "trade",
    ],
    8: [
        # Longevity, mysteries, sudden events, surgery, inheritance, occult,
        # transformation, secrets
        "death", "longevity", "transformation", "mystery", "secret",
        "occult", "hidden", "surgery", "operation", "accident",
        "inheritance", "legacy", "insurance", "sudden", "shock",
        "research", "investigation", "intuition", "scandal",
    ],
    9: [
        # Father, guru, dharma, ethics, luck, long journeys, religion,
        # higher education
        "father", "dad", "guru", "teacher", "mentor", "religion",
        "dharma", "philosophy", "ethics", "morality", "luck", "fortune",
        "blessing", "pilgrimage", "temple", "church", "mosque",
        "long_journey", "university", "wisdom", "faith", "scripture",
    ],
    10: [
        # Career, profession, status, public reputation, government, authority
        "career", "profession", "occupation", "vocation", "status",
        "position", "rank", "authority", "boss", "manager", "promotion",
        "achievement", "reputation", "honor", "government", "politics",
        "leadership", "ambition", "office",
    ],
    11: [
        # Gains, profits, network, elder siblings, fulfilled desires,
        # hopes, community
        "gain", "profit", "yield", "return", "bonus", "friend",
        "friendship", "network", "social", "group", "community",
        "elder_brother", "elder_sister", "hope", "wish", "desire",
        "aspiration", "fulfillment", "celebration",
    ],
    12: [
        # Loss, foreign lands, expenses, sleep, dreams, isolation, charity,
        # spirituality, moksha
        "loss", "expense", "expenditure", "foreign", "abroad",
        "immigration", "exile", "hospital", "jail", "prison",
        "confinement", "sleep", "dream", "meditation", "retreat",
        "monastery", "ashram", "isolation", "solitude", "charity",
        "donation", "moksha", "salvation", "renunciation",
    ],
}


# ---------------------------------------------------------------------------
# House metadata — short labels for human-readable output
# ---------------------------------------------------------------------------

HOUSE_LABELS: dict[int, str] = {
    1:  "Self / Body",
    2:  "Wealth / Family / Speech",
    3:  "Siblings / Courage / Communication",
    4:  "Home / Mother / Property",
    5:  "Children / Creativity / Play / Romance",
    6:  "Work / Health / Debts / Enemies",
    7:  "Partner / Marriage / Contracts",
    8:  "Mystery / Transformation / Longevity",
    9:  "Father / Dharma / Luck / Higher learning",
    10: "Career / Status / Authority",
    11: "Gains / Friends / Hopes",
    12: "Loss / Foreign / Isolation / Moksha",
}


# ---------------------------------------------------------------------------
# Known polysemous words — disambiguation by explicit synset
# ---------------------------------------------------------------------------
# For words with multiple unrelated senses, force the build script to use a
# specific synset rather than guessing. Use the format "word.pos.NN".
# Example: "bank" defaults to bank.n.01 (financial), not bank.n.02 (riverbank).

SYNSET_OVERRIDES: dict[str, str] = {
    "bank":    "bank.n.01",   # financial bank (house 2)
    "stock":   "stock.n.01",  # the supply / financial sense (house 5/11)
    "office":  "office.n.01", # workplace (house 10)
    "show":    "show.n.01",   # entertainment show (house 5)
    "game":    "game.n.01",   # contest of skill (house 5)
}
