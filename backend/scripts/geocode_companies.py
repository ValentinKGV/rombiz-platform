"""Geocode companies using GeoNames Romanian localities data.

Strategy:
1. Download GeoNames RO.txt (populated places, feature_class='P')
2. Build a lookup: normalized_name → (lat, lng) with county-aware matching
3. Match companies by (judet, localitate) → update lat/lng

GeoNames admin1 codes for Romanian counties (ISO 3166-2:RO):
Maps two-letter GeoNames admin1 code → Romanian judet name variations.

Usage:
    python scripts/geocode_companies.py
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import asyncpg
import httpx

# ── Bootstrap ────────────────────────────────────────────────────────────────
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env", override=False)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db",
)

GEONAMES_URL = "https://download.geonames.org/export/dump/RO.zip"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
CACHE_FILE = Path("/tmp/RO.txt")
ADMIN1_CACHE = Path("/tmp/RO_admin1.txt")

# GeoNames admin1 code → judet name (Romanian)
ADMIN1_TO_JUDET: dict[str, str] = {
    "01": "ALBA", "02": "ARAD", "03": "ARGES", "04": "BACAU",
    "05": "BIHOR", "06": "BISTRITA-NASAUD", "07": "BOTOSANI",
    "08": "BRASOV", "09": "BRAILA", "10": "BUZAU",
    "11": "CARAS-SEVERIN", "12": "CLUJ", "13": "CONSTANTA",
    "14": "COVASNA", "15": "DAMBOVITA", "16": "DOLJ",
    "17": "GALATI", "18": "GORJ", "19": "HARGHITA",
    "20": "HUNEDOARA", "21": "IALOMITA", "22": "IASI",
    "23": "ILFOV", "24": "MARAMURES", "25": "MEHEDINTI",
    "26": "MURES", "27": "NEAMT", "28": "OLT",
    "29": "PRAHOVA", "30": "SATU MARE", "31": "SALAJ",
    "32": "SIBIU", "33": "SUCEAVA", "34": "TELEORMAN",
    "35": "TIMIS", "36": "TULCEA", "37": "VASLUI",
    "38": "VALCEA", "39": "VRANCEA", "40": "BUCURESTI",
    "41": "CALARASI", "42": "GIURGIU",
}

# Hard-coded coords for Bucharest sectors (GeoNames sector entries vary)
BUCHAREST_SECTORS: dict[str, tuple[float, float]] = {
    "SECTOR 1": (44.4672, 26.0750),
    "SECTOR 2": (44.4479, 26.1335),
    "SECTOR 3": (44.4203, 26.1430),
    "SECTOR 4": (44.3978, 26.1024),
    "SECTOR 5": (44.4061, 26.0571),
    "SECTOR 6": (44.4315, 26.0447),
}


def load_admin1_map() -> dict[str, str]:
    """Load GeoNames admin1 codes for Romania → normalized judet name."""
    admin1_map: dict[str, str] = {}
    if not ADMIN1_CACHE.exists():
        return admin1_map
    with open(ADMIN1_CACHE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("RO."):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            code = parts[0].split(".")[1]  # e.g. "13" from "RO.13"
            name = parts[1]  # e.g. "Cluj County"
            # Normalize: strip "County", diacritics, uppercase
            name = re.sub(r"\s+County$", "", name, flags=re.IGNORECASE)
            admin1_map[code] = _normalize(name)
    return admin1_map


def _normalize(name: str) -> str:
    """Normalize place name: uppercase, strip diacritics, remove punctuation."""
    # Normalize unicode (decompose diacritics)
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.upper()
    # Remove common prefixes used in Romanian DB (including abbreviations)
    name = re.sub(
        r"^(MUN\.|MUNICIPIUL|ORASUL|ORAS|ORS\.|OR\.|COMUNA|SAT|SECTOR\s+\d+\s+MUN\.|)\s*",
        "",
        name,
    )
    # Handle "Sector X Mun. ..." patterns
    name = re.sub(r"^SECTOR\s+\d+\s+.*", lambda m: re.sub(r"^SECTOR\s+(\d+).*", r"SECTOR \1", m.group()), name)
    # Remove "MUN." from middle of string (e.g., "SECTOR 1 MUN. BUCURESTI")
    name = re.sub(r"\s+MUN\.\s+.*", "", name)
    # Remove punctuation except spaces and hyphens
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def load_geonames(path: Path):
    """Load GeoNames data. Returns (county_map, name_map).
    
    Priority: PPLC > PPLA > PPLA2 > ... > PPL to avoid small villages
    displacing major cities with the same normalized name.
    """
    FEATURE_PRIORITY = {
        "PPLC": 0, "PPLA": 1, "PPLA2": 2, "PPLA3": 3, "PPLA4": 4,
        "PPL": 5, "PPLS": 5, "PPLR": 5, "PPLG": 5, "PPLX": 6,
    }
    county_map: dict = {}
    county_prio: dict = {}
    name_map: dict = {}
    name_prio: dict = {}

    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 12:
                continue
            if row[6] != "P":  # only populated places
                continue
            feature_code = row[7]
            prio = FEATURE_PRIORITY.get(feature_code, 10)
            name = row[1]
            try:
                lat = float(row[4])
                lng = float(row[5])
            except (ValueError, IndexError):
                continue
            admin1 = row[10]
            alt_names = row[3].split(",") if row[3] else []

            for n in [name] + alt_names:
                norm = _normalize(n)
                if not norm:
                    continue
                if admin1:
                    key = (admin1, norm)
                    if prio < county_prio.get(key, 999):
                        county_map[key] = (lat, lng)
                        county_prio[key] = prio
                if prio < name_prio.get(norm, 999):
                    name_map[norm] = (lat, lng)
                    name_prio[norm] = prio

    log.info("GeoNames: %d county+name entries, %d name-only entries",
             len(county_map), len(name_map))
    return county_map, name_map


# Judet name normalization for matching to GeoNames admin1 codes
# Build reverse map: norm_judet → admin1_code using actual GeoNames admin1 data
def build_judet_admin1_map(admin1_map: dict[str, str]) -> dict[str, str]:
    """Build norm_judet_name → admin1_code from loaded GeoNames admin1 data."""
    result: dict[str, str] = {}
    for code, norm_name in admin1_map.items():
        result[norm_name] = code
    return result


async def main() -> None:
    # Download GeoNames if needed
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        if not CACHE_FILE.exists():
            log.info("Downloading GeoNames RO.zip...")
            resp = await client.get(GEONAMES_URL)
            resp.raise_for_status()
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            zf.extract("RO.txt", path="/tmp")
            log.info("GeoNames downloaded to %s", CACHE_FILE)
        if not ADMIN1_CACHE.exists():
            log.info("Downloading GeoNames admin1 codes...")
            resp = await client.get(ADMIN1_URL)
            resp.raise_for_status()
            ADMIN1_CACHE.write_bytes(resp.content)
            log.info("Admin1 codes downloaded to %s", ADMIN1_CACHE)
    
    log.info("Using cached GeoNames: %s", CACHE_FILE)
    county_map, name_map = load_geonames(CACHE_FILE)
    admin1_map = load_admin1_map()
    judet_admin1 = build_judet_admin1_map(admin1_map)
    log.info("Admin1 map: %d judet entries", len(judet_admin1))

    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    conn = await asyncpg.connect(dsn, timeout=30)
    try:
        # Get distinct (judet, localitate) pairs without geocoding
        log.info("Fetching distinct localities to geocode...")
        pairs = await conn.fetch(
            """
            SELECT DISTINCT judet, localitate, COUNT(*) as cnt
            FROM companies
            WHERE lat IS NULL AND localitate IS NOT NULL
            GROUP BY judet, localitate
            ORDER BY cnt DESC
            """
        )
        log.info("Distinct (judet, localitate) pairs to geocode: %d", len(pairs))

        geocoded_locs: dict[tuple[str, str], tuple[float, float]] = {}
        matched = 0
        unmatched = 0

        for pair in pairs:
            judet = (pair["judet"] or "").strip()
            localitate = (pair["localitate"] or "").strip()

            coords = None

            # Bucharest sector fast-path: check RAW localitate before normalizing
            sector_m = re.search(r"Sector\s+(\d+)", localitate, re.IGNORECASE)
            if sector_m:
                sector_key = "SECTOR " + sector_m.group(1)
                coords = BUCHAREST_SECTORS.get(sector_key)

            if not coords:
                norm_localitate = _normalize(localitate)
                norm_judet = _normalize(judet)

                # Try county+name lookup using correct admin1 codes
                admin1 = judet_admin1.get(norm_judet)
                if admin1:
                    coords = county_map.get((admin1, norm_localitate))

                # Fallback to name-only lookup
                if not coords:
                    coords = name_map.get(norm_localitate)

            if coords:
                geocoded_locs[(judet, localitate)] = coords
                matched += 1
            else:
                unmatched += 1

        log.info("Locality geocoding: matched=%d, unmatched=%d", matched, unmatched)

        # Batch update companies by (judet, localitate)
        total_updated = 0
        for (judet, localitate), (lat, lng) in geocoded_locs.items():
            result = await conn.execute(
                """
                UPDATE companies
                SET lat = $1, lng = $2
                WHERE lat IS NULL AND localitate = $3
                  AND ($4 = '' OR judet = $4)
                """,
                lat, lng, localitate, judet,
            )
            n = int(result.split()[-1]) if result else 0
            total_updated += n

        after = await conn.fetchval("SELECT COUNT(*) FROM companies WHERE lat IS NOT NULL AND lat != 0")
        log.info("Done. Updated %d companies. Total geocoded: %d", total_updated, after)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
