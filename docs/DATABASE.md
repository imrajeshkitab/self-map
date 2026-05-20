# Vedic Astrology Database

Local SQLite database (`vedic_astrology.db`) powering the semantic search engine.

## Houses (Bhavas) — 12 rows

| house_number | sanskrit_name | english_name | ruling_planet | keywords |
|---|---|---|---|---|
| 1 | Tanu Bhava | House of Self | Mars | self, body, appearance, personality, health, lagna, ascendant, vitality, identi… |
| 2 | Dhana Bhava | House of Wealth | Venus | wealth, money, family, speech, food, savings, assets, possessions, finances, re… |
| 3 | Sahaja Bhava | House of Siblings | Mercury | siblings, courage, communication, writing, travel, neighbors, media, brothers, … |
| 4 | Sukha Bhava | House of Happiness | Moon | mother, home, property, land, happiness, vehicles, real estate, domestic, roots… |
| 5 | Putra Bhava | House of Children | Sun | children, creativity, romance, intelligence, education, speculation, arts, ente… |
| 6 | Ari Bhava | House of Enemies | Mercury | enemies, disease, debt, service, work, health, obstacles, conflicts, healing, s… |
| 7 | Yuvati Bhava | House of Partnership | Venus | marriage, spouse, partnership, business, relationships, contracts, public, fore… |
| 8 | Mrityu Bhava | House of Death and Transformation | Mars | death, transformation, longevity, inheritance, occult, hidden, mystery, researc… |
| 9 | Dharma Bhava | House of Fortune | Jupiter | dharma, fortune, religion, philosophy, father, guru, travel, wisdom, higher edu… |
| 10 | Karma Bhava | House of Career | Saturn | career, profession, reputation, status, authority, ambition, job, work, busines… |
| 11 | Labha Bhava | House of Gains | Saturn | gains, income, profits, desires, social network, friends, aspirations, elder si… |
| 12 | Vyaya Bhava | House of Loss and Liberation | Jupiter | loss, expenditure, liberation, moksha, foreign, isolation, hospital, spirituali… |

## Planets (Grahas) — 9 rows

| english_name | sanskrit_name | rules_sign | exalted_in | debilitated_in | keywords |
|---|---|---|---|---|---|
| Sun | Surya | Leo | Aries | Libra | soul, authority, father, ego, government, leadership, vitality, king, power, co… |
| Moon | Chandra | Cancer | Taurus | Scorpio | mind, emotions, mother, home, intuition, subconscious, water, fertility, nouris… |
| Mars | Mangal | Aries, Scorpio | Capricorn | Cancer | courage, energy, ambition, brothers, property, conflict, strength, sports, mili… |
| Mercury | Budha | Gemini, Virgo | Virgo | Pisces | intelligence, communication, trade, logic, writing, learning, business, speech,… |
| Jupiter | Guru / Brihaspati | Sagittarius, Pisces | Cancer | Capricorn | wisdom, knowledge, dharma, religion, children, wealth, expansion, teacher, guru… |
| Venus | Shukra | Taurus, Libra | Pisces | Virgo | love, beauty, romance, marriage, arts, luxury, pleasure, creativity, fashion, m… |
| Saturn | Shani | Capricorn, Aquarius | Libra | Aries | discipline, karma, hard work, restriction, longevity, justice, delay, responsib… |
| Rahu | Rahu | Aquarius (co-ruler) | Gemini (or Taurus, debated) | Sagittarius (or Scorpio, debated) | obsession, illusion, foreign, technology, desire, innovation, sudden, unconvent… |
| Ketu | Ketu | Scorpio (co-ruler) | Sagittarius (or Scorpio, debated) | Gemini (or Taurus, debated) | spirituality, liberation, past life, detachment, mysticism, moksha, occult, med… |

## Zodiac Signs (Rashis) — 12 rows

| sign_number | english_name | sanskrit_name | ruling_planet | element | quality | keywords |
|---|---|---|---|---|---|---|
| 1 | Aries | Mesha | Mars | Fire | Movable (Chara) | initiative, leadership, courage, new beginnings, energy, pioneer, independent, … |
| 2 | Taurus | Vrishabha | Venus | Earth | Fixed (Sthira) | stability, wealth, beauty, pleasure, patience, reliable, luxury, food, arts, ma… |
| 3 | Gemini | Mithuna | Mercury | Air | Dual (Dwiswabhava) | communication, intellect, duality, versatility, curiosity, writing, trade, soci… |
| 4 | Cancer | Karka | Moon | Water | Movable (Chara) | nurturing, emotions, home, family, empathy, protective, intuition, sensitive, m… |
| 5 | Leo | Simha | Sun | Fire | Fixed (Sthira) | royalty, authority, creativity, leadership, confidence, generous, recognition, … |
| 6 | Virgo | Kanya | Mercury | Earth | Dual (Dwiswabhava) | analysis, service, health, perfection, meticulous, practical, detail, research,… |
| 7 | Libra | Tula | Venus | Air | Movable (Chara) | balance, justice, partnership, diplomacy, harmony, charm, relationships, mediat… |
| 8 | Scorpio | Vrishchika | Mars | Water | Fixed (Sthira) | transformation, mystery, intensity, passion, secrets, occult, depth, perception… |
| 9 | Sagittarius | Dhanu | Jupiter | Fire | Dual (Dwiswabhava) | philosophy, higher learning, travel, freedom, optimism, adventure, religion, wi… |
| 10 | Capricorn | Makara | Saturn | Earth | Movable (Chara) | ambition, discipline, career, achievement, hardworking, responsibility, goals, … |
| 11 | Aquarius | Kumbha | Saturn | Air | Fixed (Sthira) | humanitarian, innovation, community, progressive, intellectual, technology, soc… |
| 12 | Pisces | Meena | Jupiter | Water | Dual (Dwiswabhava) | spirituality, compassion, imagination, empathy, artistic, intuition, psychic, d… |

## Synonyms — 401 rows total

| entity_type | count |
|---|---|
| house | 120 |
| planet | 122 |
| zodiac | 159 |

**Sample rows:**

| term | maps_to | entity_type |
|---|---|---|
| self | self | house |
| body | body | house |
| appearance | appearance | house |
| personality | personality | house |
| health | health | house |
| lagna | lagna | house |
| ascendant | ascendant | house |
| vitality | vitality | house |
| identity | identity | house |
| character | character | house |
