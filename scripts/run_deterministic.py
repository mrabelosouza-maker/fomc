"""Deterministic build entry point.

    python scripts/run_deterministic.py [--as-of YYYY-MM-DD] [--no-ribbon]

Reads data/extracted/ + registry/roster.json and writes results/.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fomc import build  # noqa: E402


def cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=None, help="recency-weighting reference date")
    ap.add_argument("--no-ribbon", action="store_true", help="skip FRED macro ribbon")
    args = ap.parse_args()
    build.main(as_of=args.as_of, with_ribbon=not args.no_ribbon)


if __name__ == "__main__":
    cli()
