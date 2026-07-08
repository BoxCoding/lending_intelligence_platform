"""Vercel Python serverless entrypoint.

Vercel's Python runtime auto-detects an ASGI-compatible `app` object in
this file and serves it directly (no uvicorn/mangum needed). vercel.json
routes every path to this single function.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402
