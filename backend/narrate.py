"""
narrate.py
Optional LLM (Gemini) prose synthesis from a structured Prashna chart.

Falls back gracefully to a template-based summary if GEMINI_API_KEY is unset
or the API call fails. Pure deterministic data stays the source of truth —
the LLM only turns it into readable English.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  # picks up GEMINI_API_KEY from .env in project root

GEMINI_MODEL = "gemini-2.0-flash"
_configured = False


def _configure() -> bool:
    global _configured
    if _configured:
        return True
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return False
    genai.configure(api_key=key)
    _configured = True
    return True


def _template_summary(chart: dict) -> str:
    lagna = chart["lagna"]
    parts = [
        f"Lagna rises in {lagna['sign']} ({lagna['sign_sanskrit']}) at {lagna['degree']:.1f}°. "
        f"Its lord {lagna['lord']} is currently in {lagna['lord_sign']} "
        f"({lagna['lord_state']}), sitting in the {lagna['lord_house']}th house."
    ]
    notables = [p for p in chart["planets"] if p["state"] in ("exalted", "debilitated", "own")]
    if notables:
        lines = []
        for p in notables:
            tag = {"exalted": "exalted ⭐", "debilitated": "debilitated ⚠️", "own": "in its own sign 🏠"}[p["state"]]
            lines.append(f"{p['name']} is {tag} in {p['sign']}")
        parts.append("Notable placements: " + "; ".join(lines) + ".")
    return " ".join(parts)


def cosmic_pulse(chart: dict) -> dict:
    """Return {'summary': str, 'source': 'gemini' | 'template'}."""
    template = _template_summary(chart)
    if not _configure():
        return {"summary": template, "source": "template"}

    # Compact, structured prompt — chart facts in, prose out.
    facts = {
        "lagna_sign": chart["lagna"]["sign"],
        "lagna_lord": chart["lagna"]["lord"],
        "lagna_lord_sign": chart["lagna"]["lord_sign"],
        "lagna_lord_state": chart["lagna"]["lord_state"],
        "planets": [
            {
                "name": p["name"],
                "sign": p["sign"],
                "house": p["house"],
                "state": p["state"],
                "retrograde": p["retrograde"],
            }
            for p in chart["planets"]
        ],
    }

    prompt = f"""You are a Vedic astrologer writing a brief, grounded "cosmic pulse" of the moment.
Given the chart facts below, write 2–3 sentences (max 70 words) describing the overall flavor of this moment.

Rules:
- Use only the facts given. Do NOT invent placements.
- Mention the Lagna and the strongest 1–2 planets (exalted/debilitated/own sign).
- Plain English, no jargon dumps. No bullet points.
- Tone: thoughtful and observational, not predictive or dramatic.

Chart facts (JSON):
{facts}
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        if text:
            return {"summary": text, "source": "gemini"}
    except Exception as e:
        return {"summary": template, "source": "template", "error": str(e)}

    return {"summary": template, "source": "template"}
