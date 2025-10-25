"""Load the smart_advisor_seed.json fixture into the database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


from app.config import get_settings

# TODO: Implement actual seed loading once ORM wiring is complete.


def main() -> None:
    parser = argparse.ArgumentParser(description="Load seed data into the Smart Advisor database")
    parser.add_argument("seed_file", nargs="?", default="smart_advisor_seed.json")
    args = parser.parse_args()
    seed_path = Path(args.seed_file)
    if not seed_path.exists():
        raise SystemExit(f"Seed file not found: {seed_path}")
    payload = json.loads(seed_path.read_text())
    print(f"Loaded {len(payload)} objects from {seed_path}; persistence TODO")


if __name__ == "__main__":
    main()
