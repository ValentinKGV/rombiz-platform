"""CLI entry point for manual / ad-hoc runs.

Usage:
    python -m app.etl.balance_sheets.run --year 2023
    python -m app.etl.balance_sheets.run --year 2023 --year 2022
    python -m app.etl.balance_sheets.run --all
    python -m app.etl.balance_sheets.run --all --from-year 2020

Environment:
    DATABASE_URL  — async PostgreSQL DSN (read from .env if present)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# ── Bootstrap environment before any app imports ─────────────────────────────
_backend_root = Path(__file__).resolve().parents[3]  # …/backend/
sys.path.insert(0, str(_backend_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_backend_root / ".env", override=False)
except ImportError:
    pass  # python-dotenv optional at CLI level

# ── App imports (after dotenv) ────────────────────────────────────────────────
from app.core.logging import setup_logging  # noqa: E402
from app.etl.balance_sheets.constants import DEFAULT_YEARS  # noqa: E402
from app.etl.balance_sheets.pipeline import run_year, run_years  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.etl.balance_sheets.run",
        description="Import MF/ANAF annual balance sheets into PostgreSQL.",
    )
    p.add_argument(
        "--year",
        type=int,
        action="append",
        dest="years",
        metavar="YYYY",
        help="Fiscal year to import (repeatable). E.g. --year 2023 --year 2022",
    )
    p.add_argument(
        "--all",
        action="store_true",
        help=f"Import all default years ({DEFAULT_YEARS[0]}–{DEFAULT_YEARS[-1]})",
    )
    p.add_argument(
        "--from-year",
        type=int,
        default=None,
        metavar="YYYY",
        help="When used with --all, start from this year (inclusive)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return p


async def _main(years: list[int]) -> int:
    results = await run_years(years)
    exit_code = 0
    print("\n── Results ─────────────────────────────────────────────")
    for r in results:
        status = "OK" if r.success else "FAIL"
        print(f"  [{status}] {r}")
        if not r.success:
            exit_code = 1
    print(f"\nTotal years processed: {len(results)}")
    return exit_code


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # ── Resolve target years ─────────────────────────────────────────
    if args.all:
        years = DEFAULT_YEARS[:]
        if args.from_year is not None:
            years = [y for y in years if y >= args.from_year]
        if not years:
            logger.error("No years match --from-year %s", args.from_year)
            sys.exit(1)
    elif args.years:
        years = sorted(set(args.years))
    else:
        parser.print_help()
        print("\nError: specify --year YYYY or --all", file=sys.stderr)
        sys.exit(1)

    logger.info("Target years: %s", years)
    exit_code = asyncio.run(_main(years))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
