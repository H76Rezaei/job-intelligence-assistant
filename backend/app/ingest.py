"""Fetch new jobs from all sources: python -m app.ingest [--source NAME]"""

import argparse
import logging
import sys

from app.database import SessionLocal
from app.ingestion.run import run_ingestion
from app.ingestion.settings import load_settings
from app.ingestion.sources.bundesagentur import Bundesagentur

SOURCES = {"bundesagentur": Bundesagentur}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch new jobs from the job sources.")
    parser.add_argument("--source", choices=sorted(SOURCES), help="run only this source")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        settings = load_settings()
    except FileNotFoundError as error:
        print(f"Search settings not found: {error.filename}")
        print("Copy config/search.example.toml to config/search.toml and fill it in.")
        return 1
    if not settings.keywords or not settings.centers:
        print("Add at least one keyword and one center to your search settings.")
        return 1

    names = [args.source] if args.source else list(SOURCES)
    with SessionLocal() as session:
        run = run_ingestion(session, settings, [SOURCES[name]() for name in names])

    print(f"\nIngestion run {run.id}")
    for name, counts in run.counts.items():
        if counts["failed"]:
            print(f"  {name}: FAILED ({counts['failed']})")
        else:
            print(
                f"  {name}: {counts['fetched']} fetched, {counts['new']} new, "
                f"{counts['known']} already known, "
                f"{counts['skipped_non_germany']} skipped outside Germany, "
                f"{counts['detail_errors']} detail errors"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
