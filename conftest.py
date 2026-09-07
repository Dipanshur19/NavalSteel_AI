"""Ensures `src` is importable as a package when running `pytest` from the
project root, without needing to `pip install -e .`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
