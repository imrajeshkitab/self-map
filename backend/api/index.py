"""
Vercel Python function entry point.

Vercel's Python runtime auto-detects a FastAPI/Starlette `app` export
from a file under `api/` and bridges incoming HTTP requests to it.

We re-export `app` from the existing top-level `api.py` rather than
re-defining it here, so the FastAPI app remains the same module run
locally (via `uvicorn api:app`) and on Vercel.

Module-resolution note: when Vercel runs this file, the working
directory is the function's bundle. We insert the parent directory
(backend/) into sys.path so the sibling modules — prashna.py,
interpret.py, audit_log.py, house_mapper.py, dasha_table.py, etc. —
remain importable by name.
"""

import os
import sys

# Make backend/ siblings importable. __file__ is backend/api/index.py,
# so we add backend/ to sys.path.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Now import the FastAPI app from the existing module.
from api import app  # noqa: E402

# Vercel detects `app` automatically; explicit __all__ is just hygiene.
__all__ = ["app"]
