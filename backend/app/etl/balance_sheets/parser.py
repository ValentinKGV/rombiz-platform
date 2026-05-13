"""Plain TXT parser for data.gov.ro balance sheet files.

Files (WEB_BL_BS_SL_AN{year}.txt) have NO header row.
Columns are positional — see POSITIONAL_COLUMNS in constants.py.
Delimiter: comma.  Encoding: utf-8.

Resilient to:
  - blank / non-numeric cells (→ None)
  - rows with missing or invalid CUI (skipped)
  - trailing commas / short rows
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterator

from .constants import MONETARY_FIELDS, POSITIONAL_COLUMNS

logger = logging.getLogger(__name__)


def _to_int(value: str) -> int | None:
    """Convert a cell to int; return None for empty / non-numeric."""
    v = value.strip()
    if not v or v in ("-", "N/A", "NA", "null", "NULL"):
        return None
    try:
        return int(float(v))
    except (ValueError, OverflowError):
        return None



def iter_rows(txt_path: Path, year: int) -> Iterator[dict]:
    """Yield parsed row dicts for every valid record in *txt_path*.

    The file has NO header row. Column positions are defined by
    POSITIONAL_COLUMNS in constants.py.

    Each yielded dict has at minimum: {"cui": int, "an_fiscal": int}
    plus whichever financial fields were present and non-null.

    Rows with invalid/missing CUI are skipped.
    """
    logger.info("Parsing TXT: %s", txt_path)

    total = skipped_cui = skipped_error = yielded = 0

    with open(txt_path, "r", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        for row in reader:
            total += 1
            if not row:
                continue

            # Column 0 is always CUI
            cui_raw = row[0].strip() if len(row) > 0 else ""
            if not cui_raw or not cui_raw.isdigit():
                skipped_cui += 1
                continue
            cui = int(cui_raw)
            if cui <= 0:
                skipped_cui += 1
                continue

            try:
                record: dict = {"cui": cui, "an_fiscal": year}

                for col_idx, field_name in POSITIONAL_COLUMNS.items():
                    if field_name is None or field_name == "cui":
                        continue
                    if col_idx < len(row):
                        val = _to_int(row[col_idx])
                        if val is not None:
                            record[field_name] = val

                yielded += 1
                yield record

            except Exception as exc:  # noqa: BLE001
                skipped_error += 1
                if skipped_error <= 5:
                    logger.error("Row %d unexpected error: %s — skipped", total, exc)

    logger.info(
        "Parsed year=%d: total=%d  yielded=%d  skipped_cui=%d  skipped_err=%d",
        year,
        total,
        yielded,
        skipped_cui,
        skipped_error,
    )
