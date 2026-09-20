#!/usr/bin/env python3
"""Launch the City Fly FastAPI review desk (login + articles + sources + settings)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hk_city.desk.app import main

if __name__ == "__main__":
    raise SystemExit(main())
