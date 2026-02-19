"""
Centralized data directory configuration.
Supports DATA_DIR env var for Home Assistant addon (maps to /config).
"""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
