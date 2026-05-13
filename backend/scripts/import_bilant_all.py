"""
Import bilanțuri complete de la Ministerul Finanțelor (data.gov.ro)
pentru toți tipii de firme: WEB_BL_BS_SL (bilanț), WEB_UU (microîntreprinderi), WEB_IR (impozit pe venit)
Ani: 2015-2024

Acoperire estimată după import: ~80-90% din firme (față de 25.5% actual)
"""
import asyncio
import csv
import io
import logging
import os
import sys
import time
from pathlib import Path

import asyncpg
import httpx

# ── Configurare ──────────────────────────────────────────────────────────────
DB_DSN = "postgresql://rombiz_user:Rombiz2026!@localhost:5432/rombiz_db"
CACHE_DIR = Path("/data/bilant_cache")
LOG_FILE = Path("/home/aether/app/RATING/ATH-Firme/rombiz-platform/backend/logs/import_bilant_all.log")
BATCH_SIZE = 50_000
YEARS = list(range(2008, 2025))  # 2008-2024

# Dataset IDs pe data.gov.ro per an
DATASET_IDS = {
    2008: "situatii-financiare-2008",
    2009: "situatii-financiare-2009",
    2010: "situatii-financiare-2010",
    2011: "situatii-financiare-2011",
    2012: "situatii-financiare-2012",
    2013: "situatii-financiare-2013",
    2014: "situatii-financiare-2014",
    2015: "situatii_financiare_2015",
    2016: "situatii_financiare_2016",
    2017: "situatii_financiare_2017",
    2018: "situatii_financiare_2018",
    2019: "situatii_financiare_2019",
    2020: "situatii_financiare_2020",
    2021: "situatii_financiare_2021",
    2022: "situatii_financiare_2022",
    2023: "situatii_financiare2023",
    2024: "situatii_financiare_2024",
}

# Tipuri de fișiere + pattern în URL
FILE_TYPES = [
    ("bl", ["web_bl_bs_sl", "webblbsslan", "webbsblan"]),  # bilanț complet
    ("uu", ["web_uu_an", "webuuan", "webuu", "web_uu"]),   # microîntreprinderi
    ("ir", ["web_ir_an", "webiran", "webir", "web_ir"]),   # impozit pe venit
]

# Mapare coloane poziționale (0-indexed), aceleași pentru toate tipurile
# col 0: CUI, col 1: CAEN, col 2-21: I1-I20
FIELD_MAP = {
    2: "active_imobilizate",
    3: "active_circulante",
    7: "datorii_totale",
    10: "capitaluri_proprii",
    13: "cifra_afaceri",
    14: "venituri_totale",
    15: "cheltuieli_totale",
    16: "profit_brut",
    17: "pierdere_bruta",
    18: "profit_net",
    19: "pierdere_neta",
    20: "nr_salariati",
}

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── URL Discovery ─────────────────────────────────────────────────────────────
def find_url_for_type(resources: list, file_type_patterns: list, year: int) -> str | None:
    """Găsește URL-ul corect pentru un tip de fișier și an specific."""
    year_str = str(year)
    
    # Prima dată: caută fișier .txt cu pattern AND an în URL
    for res in resources:
        url = res.get("url", "").lower()
        if not url.endswith(".txt"):
            continue
        if year_str not in url:
            continue
        for pat in file_type_patterns:
            if pat in url:
                return res["url"]
    
    # A doua trecere: relaxăm — orice .txt cu pattern (fără cerința anului în URL)
    for res in resources:
        url = res.get("url", "").lower()
        if not url.endswith(".txt"):
            continue
        for pat in file_type_patterns:
            if pat in url:
                return res["url"]
    
    return None


async def get_dataset_urls(year: int) -> dict[str, str]:
    """Returnează {tip: url} pentru un an."""
    ds_name = DATASET_IDS[year]
    api_url = f"https://data.gov.ro/api/3/action/package_show?id={ds_name}"
    
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(api_url)
        if r.status_code != 200:
            log.error(f"[{year}] API error {r.status_code} for {ds_name}")
            return {}
        
        resources = r.json().get("result", {}).get("resources", [])
        result = {}
        for type_key, patterns in FILE_TYPES:
            url = find_url_for_type(resources, patterns, year)
            if url:
                result[type_key] = url
                log.info(f"[{year}] {type_key}: {url}")
            else:
                log.warning(f"[{year}] {type_key}: nu s-a găsit URL")
        
        return result


# ── Download ──────────────────────────────────────────────────────────────────
async def download_file(url: str, cache_path: Path) -> bool:
    """Descarcă fișierul la cache_path. Returnează True dacă OK."""
    if cache_path.exists() and cache_path.stat().st_size > 1_000_000:
        log.info(f"  Cache OK: {cache_path.name} ({cache_path.stat().st_size // 1_000_000}MB)")
        return True
    
    log.info(f"  Downloading {url}")
    try:
        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            async with client.stream("GET", url) as r:
                if r.status_code != 200:
                    log.error(f"  HTTP {r.status_code} pentru {url}")
                    return False
                total = 0
                with open(cache_path, "wb") as f:
                    async for chunk in r.aiter_bytes(1024 * 1024):
                        f.write(chunk)
                        total += len(chunk)
        size_mb = cache_path.stat().st_size / 1_000_000
        log.info(f"  Download OK: {cache_path.name} ({size_mb:.1f}MB)")
        return size_mb > 0.1
    except Exception as e:
        log.error(f"  Download EROARE: {e}")
        return False


# ── Parser ────────────────────────────────────────────────────────────────────
def parse_file(path: Path, year: int):
    """Parsează fișier TXT/CSV → yield dict per rând valid."""
    total = yielded = skipped = 0
    
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        for row in reader:
            total += 1
            if not row:
                continue
            
            # Skip header dacă există
            val0 = row[0].strip().upper()
            if val0 in ("CUI", "COD_FISCAL", "J_CUI", ""):
                continue
            
            # Validare CUI
            if not val0.isdigit():
                skipped += 1
                continue
            cui = int(val0)
            if cui <= 0:
                skipped += 1
                continue
            
            try:
                record = {"cui": cui, "an_fiscal": year}
                for col_idx, field_name in FIELD_MAP.items():
                    if col_idx < len(row):
                        v = row[col_idx].strip()
                        if v and v not in ("-", "N/A", "NA", "null", "NULL", ""):
                            try:
                                record[field_name] = int(float(v))
                            except (ValueError, OverflowError):
                                pass
                yielded += 1
                yield record
            except Exception:
                skipped += 1
    
    log.info(f"  Parsed {path.name}: {total} linii → {yielded} înregistrări ({skipped} ignorate)")


# ── DB Upsert ─────────────────────────────────────────────────────────────────
INSERT_SQL = """
INSERT INTO company_balance_sheets (
    cui, an_fiscal, sursa,
    cifra_afaceri, venituri_totale, cheltuieli_totale,
    profit_brut, pierdere_bruta, profit_net, pierdere_neta,
    active_imobilizate, active_circulante, datorii_totale,
    capitaluri_proprii, nr_salariati
)
VALUES (
    $1, $2, $3,
    $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15
)
ON CONFLICT (cui, an_fiscal) DO UPDATE SET
    sursa = EXCLUDED.sursa,
    cifra_afaceri = COALESCE(EXCLUDED.cifra_afaceri, company_balance_sheets.cifra_afaceri),
    venituri_totale = COALESCE(EXCLUDED.venituri_totale, company_balance_sheets.venituri_totale),
    cheltuieli_totale = COALESCE(EXCLUDED.cheltuieli_totale, company_balance_sheets.cheltuieli_totale),
    profit_brut = COALESCE(EXCLUDED.profit_brut, company_balance_sheets.profit_brut),
    pierdere_bruta = COALESCE(EXCLUDED.pierdere_bruta, company_balance_sheets.pierdere_bruta),
    profit_net = COALESCE(EXCLUDED.profit_net, company_balance_sheets.profit_net),
    pierdere_neta = COALESCE(EXCLUDED.pierdere_neta, company_balance_sheets.pierdere_neta),
    active_imobilizate = COALESCE(EXCLUDED.active_imobilizate, company_balance_sheets.active_imobilizate),
    active_circulante = COALESCE(EXCLUDED.active_circulante, company_balance_sheets.active_circulante),
    datorii_totale = COALESCE(EXCLUDED.datorii_totale, company_balance_sheets.datorii_totale),
    capitaluri_proprii = COALESCE(EXCLUDED.capitaluri_proprii, company_balance_sheets.capitaluri_proprii),
    nr_salariati = COALESCE(EXCLUDED.nr_salariati, company_balance_sheets.nr_salariati),
    updated_at = NOW()
"""


async def upsert_batch(pool: asyncpg.Pool, rows: list[dict], sursa: str) -> int:
    data = [
        (
            r["cui"], r["an_fiscal"], sursa,
            r.get("cifra_afaceri"), r.get("venituri_totale"), r.get("cheltuieli_totale"),
            r.get("profit_brut"), r.get("pierdere_bruta"), r.get("profit_net"), r.get("pierdere_neta"),
            r.get("active_imobilizate"), r.get("active_circulante"), r.get("datorii_totale"),
            r.get("capitaluri_proprii"), r.get("nr_salariati"),
        )
        for r in rows
    ]
    async with pool.acquire() as conn:
        await conn.executemany(INSERT_SQL, data)
    return len(data)


async def process_file(pool: asyncpg.Pool, path: Path, year: int, type_key: str) -> int:
    """Procesează un fișier și inserează în DB. Returnează numărul de rânduri."""
    sursa = f"MF_{type_key.upper()}_{year}"
    batch = []
    total_inserted = 0
    
    for record in parse_file(path, year):
        batch.append(record)
        if len(batch) >= BATCH_SIZE:
            total_inserted += await upsert_batch(pool, batch, sursa)
            log.info(f"  [{year}/{type_key}] Batch flushed: {total_inserted:,} total")
            batch.clear()
    
    if batch:
        total_inserted += await upsert_batch(pool, batch, sursa)
    
    log.info(f"  [{year}/{type_key}] TOTAL: {total_inserted:,} rânduri")
    return total_inserted


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("=" * 60)
    log.info("=== import_bilant_all.py pornit ===")
    log.info(f"Ani: {YEARS}")
    log.info("=" * 60)
    
    pool = await asyncpg.create_pool(DB_DSN, min_size=2, max_size=4)
    
    # Statistici de start
    start_count = await pool.fetchval("SELECT COUNT(*) FROM company_balance_sheets")
    log.info(f"Bilanțuri în DB la start: {start_count:,}")
    
    grand_total = 0
    results_summary = []
    
    for year in YEARS:
        log.info(f"\n{'─'*40}")
        log.info(f"=== AN {year} ===")
        
        # Descoperă URL-urile
        urls = await get_dataset_urls(year)
        if not urls:
            log.warning(f"[{year}] Nu s-au găsit URL-uri, skip.")
            continue
        
        year_total = 0
        for type_key, _ in FILE_TYPES:
            if type_key not in urls:
                log.warning(f"[{year}/{type_key}] URL lipsă, skip.")
                continue
            
            url = urls[type_key]
            cache_path = CACHE_DIR / f"bilant_{year}_{type_key}.txt"
            
            # Download
            ok = await download_file(url, cache_path)
            if not ok:
                log.error(f"[{year}/{type_key}] Download eșuat, skip.")
                continue
            
            # Procesare + DB
            try:
                n = await process_file(pool, cache_path, year, type_key)
                year_total += n
                grand_total += n
            except Exception as e:
                log.error(f"[{year}/{type_key}] Eroare procesare: {e}", exc_info=True)
        
        log.info(f"=== AN {year} complet: {year_total:,} rânduri ===")
        results_summary.append((year, year_total))
    
    # Statistici finale
    end_count = await pool.fetchval("SELECT COUNT(*) FROM company_balance_sheets")
    with_bs = await pool.fetchval(
        "SELECT COUNT(DISTINCT c.id) FROM companies c JOIN company_balance_sheets bs ON bs.cui=c.cui"
    )
    total_companies = await pool.fetchval("SELECT COUNT(*) FROM companies")
    
    await pool.close()
    
    log.info("\n" + "=" * 60)
    log.info("=== IMPORT COMPLET ===")
    log.info(f"Bilanțuri la start:  {start_count:,}")
    log.info(f"Bilanțuri la final:  {end_count:,}")
    log.info(f"Rânduri noi/update:  {grand_total:,}")
    log.info(f"Companii cu bilanț:  {with_bs:,} / {total_companies:,} ({100*with_bs/total_companies:.1f}%)")
    log.info("\nDetaliu pe ani:")
    for year, n in results_summary:
        log.info(f"  {year}: {n:,}")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
