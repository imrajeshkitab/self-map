"""emotion — Daily Emotional Analysis Engine (feat/emotional-engine).

Emotional-vector model: natal Moon + Vimshottari DBA + transit Moon →
10 emotional dimensions (0-100) + narrative, with a full step trace.
"""
from .engine import compute_emotion  # noqa: F401
