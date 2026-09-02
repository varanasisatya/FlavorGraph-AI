# ruff: noqa: E402, I001
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.flavorgraph import FlavorGraphEngine  # noqa: E402


if __name__ == "__main__":
    engine = FlavorGraphEngine(ROOT / "data" / "recipes.json", ROOT / "data" / "ingredient_profiles.json")
    print(json.dumps(engine.evaluate(k=3), indent=2))
