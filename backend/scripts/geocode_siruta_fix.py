#!/usr/bin/env python3
"""
Fix geocoding for companies with ONRC-format compound locality strings.

ONRC stores locality as compound strings like:
  "Sat Floreşti Com. Floreşti"  → extract "Floreşti"
  "Mun. Satu Mare"               → extract "Satu Mare"
  "Sat Dudu Com. Chiajna"        → try "Dudu" then "Chiajna"
  "Loc. Eforie Nord Orş. Eforie" → extract "Eforie Nord"
  "Com. Dumbrăveni"              → extract "Dumbrăveni"
  "Orş. Bragadiru"               → extract "Bragadiru"

Matches against existing GeoNames cache at /tmp/RO.txt
Uses same normalization as geocode_companies.py (strip diacritics, lowercase)
"""
from __future__ import annotations

import asyncio
import asyncpg
import csv
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path

DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
GEONAMES_CACHE = Path("/tmp/RO.txt")
LOG_FILE = Path(__file__).parent.parent / "logs" / "geocode_siruta_fix.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# GeoNames admin1 → judet mapping (same as geocode_companies.py)
ADMIN1_TO_JUDET: dict[str, list[str]] = {
    "01": ["ALBA"], "02": ["ARAD"], "03": ["ARGES", "ARGEŞ"],
    "04": ["BACAU", "BACĂU"], "05": ["BIHOR"],
    "06": ["BISTRITA-NASAUD", "BISTRIŢA-NĂSĂUD", "BISTRITA NASAUD"],
    "07": ["BOTOSANI", "BOTOŞANI"], "08": ["BRAILA", "BRĂILA"],
    "09": ["BRASOV", "BRAŞOV"], "10": ["BUCURESTI", "BUCUREȘTI", "ILFOV"],
    "11": ["BUZAU", "BUZĂU"], "12": ["CALARASI", "CĂLĂRAŞI"],
    "13": ["CARAS-SEVERIN", "CARAŞ-SEVERIN", "CARAS SEVERIN"],
    "14": ["CLUJ"], "15": ["CONSTANTA", "CONSTANŢA"],
    "16": ["COVASNA"], "17": ["DAMBOVITA", "DÂMBOVIŢA"],
    "18": ["DOLJ"], "19": ["GALATI", "GALAŢI"],
    "20": ["GIURGIU"], "21": ["GORJ"],
    "22": ["HARGHITA"], "23": ["HUNEDOARA"],
    "24": ["IALOMITA", "IALOMIŢA"], "25": ["IASI", "IAŞI"],
    "26": ["ILFOV"], "27": ["MARAMURES", "MARAMUREŞ"],
    "28": ["MEHEDINTI", "MEHEDINŢI"], "29": ["MURES", "MUREŞ"],
    "30": ["NEAMT", "NEAMŢ"], "31": ["OLT"],
    "32": ["PRAHOVA"], "33": ["SALAJ", "SĂLAJ"],
    "34": ["SATU MARE"], "35": ["SIBIU"],
    "36": ["SUCEAVA"], "37": ["TELEORMAN"],
    "38": ["TIMIS", "TIMIŞ"], "39": ["TULCEA"],
    "40": ["VASLUI"], "41": ["VALCEA", "VÂLCEA"],
    "42": ["VRANCEA"],
}
# build reverse: normalized_judet → admin1 set
JUDET_TO_ADMIN1: dict[str, set[str]] = {}
for code, names in ADMIN1_TO_JUDET.items():
    for n in names:
        JUDET_TO_ADMIN1.setdefault(n, set()).add(code)


def normalize(s: str) -> str:
    """Lowercase + remove diacritics + collapse whitespace."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


# Regex patterns to extract locality name from ONRC compound strings
# Order matters - try most specific first
PATTERNS = [
    # "Sat X Com. Y" / "Sat X Orş. Y" / "Sat X Mun. Y" → group1=X, group2=Y
    re.compile(r'^Sat\s+(.+?)\s+(?:Com\.|Orş\.|Mun\.|Oraș)\s+(.+)$', re.IGNORECASE),
    # "Loc. X Orş. Y" / "Loc. X Com. Y" → group1=X, group2=Y
    re.compile(r'^Loc\.\s+(.+?)\s+(?:Com\.|Orş\.|Mun\.|Oraș)\s+(.+)$', re.IGNORECASE),
    # "Mun. X" → group1=X
    re.compile(r'^Mun\.\s+(.+)$', re.IGNORECASE),
    # "Com. X" → group1=X
    re.compile(r'^Com\.\s+(.+)$', re.IGNORECASE),
    # "Orş. X" / "Oraș X" → group1=X
    re.compile(r'^(?:Orş\.|Oraș)\s+(.+)$', re.IGNORECASE),
    # "Sat X" (no commune suffix) → group1=X
    re.compile(r'^Sat\s+(.+)$', re.IGNORECASE),
    # "Loc. X" → group1=X
    re.compile(r'^Loc\.\s+(.+)$', re.IGNORECASE),
]


def extract_candidates(localitate: str) -> list[str]:
    """Return list of candidate locality names to try, most specific first."""
    candidates = []
    for pattern in PATTERNS:
        m = pattern.match(localitate)
        if m:
            groups = m.groups()
            for g in groups:
                name = g.strip().rstrip(".")
                if name and name not in candidates:
                    candidates.append(name)
            break  # use first matching pattern
    # Always also try the raw string (might already be clean)
    raw = localitate.strip()
    if raw not in candidates:
        candidates.append(raw)
    return candidates


def load_geonames() -> dict[tuple[str, str], tuple[float, float]]:
    """Load GeoNames cache → {(admin1_code, norm_name): (lat, lng)}"""
    log.info("Loading GeoNames from %s", GEONAMES_CACHE)
    lookup: dict[tuple[str, str], tuple[float, float]] = {}
    # Also build name-only lookup for fallback
    name_lookup: dict[str, tuple[float, float]] = {}

    with open(GEONAMES_CACHE, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 15:
                continue
            feature_class = parts[6]
            if feature_class != "P":  # only populated places
                continue
            name = parts[1]
            alt_names = parts[3]
            lat = parts[4]
            lng = parts[5]
            admin1 = parts[10]
            try:
                lat_f, lng_f = float(lat), float(lng)
            except ValueError:
                continue

            all_names = [name] + ([a for a in alt_names.split(",") if a] if alt_names else [])
            for n in all_names:
                norm = normalize(n)
                key = (admin1, norm)
                if key not in lookup:
                    lookup[key] = (lat_f, lng_f)
                if norm not in name_lookup:
                    name_lookup[norm] = (lat_f, lng_f)

    log.info("Loaded %d GeoNames entries (%d unique names)", len(lookup), len(name_lookup))
    return lookup, name_lookup


def find_coords(
    candidates: list[str],
    judet_norm: str,
    lookup: dict,
    name_lookup: dict,
) -> tuple[float, float] | None:
    admin1_codes = JUDET_TO_ADMIN1.get(judet_norm.upper(), set())

    for candidate in candidates:
        norm = normalize(candidate)
        # Try county-specific first
        for code in admin1_codes:
            coords = lookup.get((code, norm))
            if coords:
                return coords
        # Fallback: any county
        coords = name_lookup.get(norm)
        if coords:
            return coords
    return None


async def main() -> None:
    lookup, name_lookup = load_geonames()

    conn = await asyncpg.connect(DSN)

    # Get distinct (judet, localitate) with missing geocodes
    log.info("Fetching distinct ungeocoded localities...")
    rows = await conn.fetch("""
        SELECT judet, localitate, COUNT(*) as cnt
        FROM companies
        WHERE lat IS NULL
          AND localitate IS NOT NULL AND localitate != ''
          AND judet IS NOT NULL AND judet != ''
        GROUP BY judet, localitate
        ORDER BY cnt DESC
    """)
    log.info("Found %d distinct (judet, localitate) combinations to process", len(rows))

    # Build locality → coords mapping
    resolved: dict[tuple[str, str], tuple[float, float]] = {}
    unresolved = 0

    for row in rows:
        judet = row["judet"]
        localitate = row["localitate"]
        key = (judet, localitate)

        candidates = extract_candidates(localitate)
        coords = find_coords(candidates, normalize(judet), lookup, name_lookup)
        if coords:
            resolved[key] = coords
        else:
            unresolved += 1

    log.info("Resolved: %d | Unresolved: %d", len(resolved), unresolved)

    if not resolved:
        log.warning("Nothing to update")
        await conn.close()
        return

    # Update in per-judet batches to avoid deadlock with concurrent ANAF import
    log.info("Updating companies in per-judet batches...")

    # Group resolved by judet
    by_judet: dict[str, list[tuple[str, float, float]]] = {}
    for (j, l), (lat, lng) in resolved.items():
        by_judet.setdefault(j, []).append((l, lat, lng))

    total_updated = 0
    judete = sorted(by_judet.keys())
    for judet in judete:
        entries = by_judet[judet]
        # Retry on deadlock up to 5 times
        for attempt in range(5):
            try:
                await conn.execute("CREATE TEMP TABLE IF NOT EXISTS _geo_fix (judet text, localitate text, lat numeric, lng numeric)")
                await conn.execute("DELETE FROM _geo_fix")
                await conn.executemany(
                    "INSERT INTO _geo_fix VALUES ($1, $2, $3, $4)",
                    [(judet, l, lat, lng) for l, lat, lng in entries]
                )
                result = await conn.execute("""
                    UPDATE companies c
                    SET lat = g.lat, lng = g.lng
                    FROM _geo_fix g
                    WHERE c.judet = g.judet AND c.localitate = g.localitate AND c.lat IS NULL
                """)
                cnt = int(result.split()[-1])
                total_updated += cnt
                log.info("Judet %-25s: %d localities → %d companies updated", judet, len(entries), cnt)
                break
            except asyncpg.DeadlockDetectedError:
                if attempt < 4:
                    wait = 5 * (attempt + 1)
                    log.warning("Deadlock on judet %s (attempt %d), retrying in %ds...", judet, attempt+1, wait)
                    await asyncio.sleep(wait)
                else:
                    log.error("Deadlock persists for judet %s after 5 attempts, skipping", judet)

    log.info("Total updated %d companies with lat/lng", total_updated)

    await conn.close()
    log.info("DONE")


if __name__ == "__main__":
    asyncio.run(main())
