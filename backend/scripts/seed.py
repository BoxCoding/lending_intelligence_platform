"""Seed the store with scored customers from the synthetic AA dataset.

Usage (from backend/):
    python scripts/seed.py --n 80
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.models import AAPayload
from app.services.pipeline import process_aa_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--data", default=str(Path(__file__).resolve().parents[2] / "data" / "samples" / "aa_payloads.json"))
    args = parser.parse_args()

    payloads = json.loads(Path(args.data).read_text())[: args.n]
    tiers = {"HOT": 0, "WARM": 0, "COLD": 0}
    for raw in payloads:
        profile = process_aa_payload(AAPayload(**raw))
        tiers[profile.lead.tier] += 1
    print(f"Seeded {len(payloads)} customers -> {tiers}")


if __name__ == "__main__":
    main()
