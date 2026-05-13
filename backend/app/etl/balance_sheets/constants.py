"""Constants: URL templates, cache directory, column-name mapping.

Data source: data.gov.ro open data portal (Ministerul Finanțelor).
Files are plain-text CSVs with comma separators, NO header row.
Column order is: CUI, CAEN, i1..i20 per the accompanying .csv spec file.

Column mapping for the positional (headerless) TXT format:
  col 0: CUI
  col 1: CAEN code
  col 2: i1  - active_imobilizate
  col 3: i2  - active_circulante
  col 4: i3  - stocuri (ignored)
  col 5: i4  - creante (ignored)
  col 6: i5  - casa_conturi (ignored)
  col 7: i6  - cheltuieli_avans (ignored)
  col 8: i7  - datorii_totale
  col 9: i8  - venituri_avans (ignored)
  col 10: i9 - provizioane (ignored)
  col 11: i10 - capitaluri_proprii
  col 12: i11 - capital_subscris (ignored)
  col 13: i12 - patrimoniu_regie (ignored)
  col 14: i13 - cifra_afaceri
  col 15: i14 - venituri_totale
  col 16: i15 - cheltuieli_totale
  col 17: i16 - profit_brut
  col 18: i17 - pierdere_bruta
  col 19: i18 - profit_net
  col 20: i19 - pierdere_neta
  col 21: i20 - nr_salariati
"""
from __future__ import annotations

from pathlib import Path

# ── Local cache ──────────────────────────────────────────────────────────────
CACHE_DIR: Path = Path("/data/bilant_cache")

# ── data.gov.ro direct download URLs (confirmed working 2025-05) ─────────────
# Format: plain TXT, comma-delimited, no header
# Resource UUIDs resolved via CKAN API: resource_show?id={uuid}
DATA_GOV_RO_URLS: dict[int, str] = {
    2024: "https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/f89140dc-20dd-494f-912a-d1a482188885/download/web_bl_bs_sl_an2024.txt",
    2023: "https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/5ed47b6f-f8a2-4ca8-a272-692aff4fe9e4/download/web_bl_bs_sl_an2023.txt",
    2022: "https://data.gov.ro/dataset/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/b35fab04-f101-42d7-a765-8f41728b373a/download/web_bl_bs_sl_an2022.txt",
    2021: "https://data.gov.ro/dataset/f8353c0e-fee9-4aa3-b26d-be0e96c328a7/resource/d0a42232-5aa0-425a-b264-67184e8ded5f/download/web_bl_bs_sl_an2021.txt",
    2020: "https://data.gov.ro/dataset/e977e5b9-0a1f-46ac-8cb8-f856a011a8ed/resource/00618bb2-b8b7-4861-95f0-184871aab230/download/web_bl_bs_sl_an2020.txt",
    2019: "https://data.gov.ro/dataset/0be1e2aa-8399-4cfc-beab-bf516fcc8f16/resource/983c2a11-360c-4e42-a441-2ab13310592d/download/web_bl_bs_sl_an2019.txt",
    2018: "https://data.gov.ro/dataset/a9c6dd10-dee2-46e9-aa3f-58dea0e50396/resource/aa694624-d14a-4cc9-9a09-9eaa7c97a0ab/download/webblbsslan2018.txt",
    2017: "https://data.gov.ro/dataset/f3c94174-4991-4d25-b183-663370908de3/resource/b00a63a0-4916-459a-a5d8-34cc68d34e86/download/webblbsslan2017.txt",
    2016: "https://data.gov.ro/dataset/e6274edc-fe36-4a79-ba73-c05711b70d80/resource/a71a4687-84eb-4d5d-a315-3dc38f4ea97f/download/webblbsslan2016.txt",
    2015: "https://data.gov.ro/dataset/6a021146-6a0d-4262-8b0e-2b43aa79bca7/resource/098a544a-2ced-418c-ac93-f72b4a8c1c5a/download/webblbsslan2015.txt",
    2014: "https://data.gov.ro/dataset/77ea3bbe-a533-4db0-8647-d380a75a39b5/resource/5563f94a-8ca3-4739-8036-75ed9bb386aa/download/webblbsslan2014.txt",
    2013: "https://data.gov.ro/dataset/a5f153b7-2d56-47e5-b2b8-6aef383f6185/resource/5d505675-3639-484b-97a3-1132655230e3/download/webblbsslan2013.txt",
    2012: "https://data.gov.ro/dataset/20e2efd2-ead2-4d18-bf44-50ac49509a52/resource/a6d0ac17-4df9-4796-87f1-c06b52846bd5/download/webblbsslan2012.txt",
    2011: "https://data.gov.ro/dataset/3043db7b-b272-4f42-a511-587e5bd3ad09/resource/7e50c588-2a6b-4671-9740-d48459c8e6b0/download/webblbsslan2011.txt",
    2010: "https://data.gov.ro/dataset/609ed4cd-6513-4f4b-a412-e3cf7007720d/resource/5430975c-01a5-4187-9f19-8526e817ad13/download/webblbsslan2010.txt",
    2009: "https://data.gov.ro/dataset/5c57f607-c9ed-459a-84b7-dafcba0db069/resource/99a5b745-f230-4b1d-b263-f7c86733e383/download/webblbsslan2009.txt",
    # 2008: web2008.txt has a different format (not WEB_BL_BS_SL); skipped
}

# CKAN API endpoint for resolving URLs dynamically
DATA_GOV_RO_CKAN_API: str = "https://data.gov.ro/api/3/action/package_search"

# Dataset name patterns for each year on data.gov.ro
DATA_GOV_RO_DATASET_NAMES: dict[int, str] = {
    2008: "situatii_financiare_2008",
    2009: "situatii_financiare_2009",
    2010: "situatii_financiare_2010",
    2011: "situatii_financiare_2011",
    2012: "situatii_financiare_2012",
    2013: "situatii_financiare_2013",
    2014: "situatii_financiare_2014",
    2015: "situatii_financiare_2015",
    2016: "situatii_financiare_2016",
    2017: "situatii_financiare_2017",
    2018: "situatii_financiare_2018",
    2019: "situatii_financiare_2019",
    2020: "situatii_financiare_2020",
    2021: "situatii_financiare_2021",
    2022: "situatii_financiare_2022",
    2023: "situatii_financiare2023",  # note: no underscore before year
    2024: "situatii_financiare_2024",
}

# File name pattern within each dataset (the main balance sheet TXT)
DATA_GOV_RO_FILE_PATTERN: str = "web_bl_bs_sl_an{year}.txt"

# ── Positional column mapping (0-indexed) for headerless TXT files ───────────
# Maps column index → CompanyBalanceSheet field name (None = ignored)
POSITIONAL_COLUMNS: dict[int, str | None] = {
    0: "cui",
    1: None,   # CAEN code
    2: "active_imobilizate",
    3: "active_circulante",
    4: None,   # stocuri
    5: None,   # creante
    6: None,   # casa si conturi la banci
    7: None,   # cheltuieli in avans
    8: "datorii_totale",
    9: None,   # venituri in avans
    10: None,  # provizioane
    11: "capitaluri_proprii",
    12: None,  # capital subscris varsat
    13: None,  # patrimoniul regiei
    14: "cifra_afaceri",
    15: "venituri_totale",
    16: "cheltuieli_totale",
    17: "profit_brut",
    18: "pierdere_bruta",
    19: "profit_net",
    20: "pierdere_neta",
    21: "nr_salariati",
}

# ── Legacy URL templates (kept for backward compatibility / manual imports) ──
URL_TEMPLATES: list[str] = [
    "https://static.anaf.ro/static/10/Anaf/Informatii_R/bilant{year}.zip",
]

# ── Years to attempt when no explicit year is given ─────────────────────────
DEFAULT_YEARS: list[int] = list(range(2009, 2025))

# ── CSV parsing ─────────────────────────────────────────────────────────────
# Delimiters tried in order for auto-detection
CANDIDATE_DELIMITERS: list[str] = ["|", ";", "\t", ","]

# Encodings tried in order
CANDIDATE_ENCODINGS: list[str] = ["utf-8", "cp1250", "iso-8859-2", "latin-1"]

# Minimum byte-size for a cached file to be considered valid (5 MB)
MIN_CACHE_SIZE_BYTES: int = 5 * 1024 * 1024

# Streaming chunk size for download
DOWNLOAD_CHUNK_BYTES: int = 1024 * 1024  # 1 MB

# Upsert batch size (rows flushed to DB at once)
UPSERT_BATCH_SIZE: int = 5_000

# ── Column-name alias map ────────────────────────────────────────────────────
# Keys   : all lowercase, stripped, known header variants from ANAF/MF files
# Values : CompanyBalanceSheet field name
COLUMN_ALIASES: dict[str, str] = {
    # ── CUI / company identifier ─────────────────────────────────────
    "cui": "cui",
    "cod_fiscal": "cui",
    "cod_unic_inregistrare": "cui",
    "cif": "cui",
    "j_cui": "cui",

    # ── Cifra de afaceri ─────────────────────────────────────────────
    "cifra_afaceri": "cifra_afaceri",
    "cifra_de_afaceri_neta": "cifra_afaceri",
    "cifra_afaceri_neta": "cifra_afaceri",
    "ca": "cifra_afaceri",
    "i_ca": "cifra_afaceri",
    "caf_net": "cifra_afaceri",
    "i10": "cifra_afaceri",
    "i010": "cifra_afaceri",
    "i0010": "cifra_afaceri",
    "ind_ca": "cifra_afaceri",

    # ── Venituri totale ──────────────────────────────────────────────
    "venituri_totale": "venituri_totale",
    "total_venituri": "venituri_totale",
    "vt": "venituri_totale",
    "i_vt": "venituri_totale",
    "i20": "venituri_totale",
    "i020": "venituri_totale",
    "i0020": "venituri_totale",

    # ── Cheltuieli totale ────────────────────────────────────────────
    "cheltuieli_totale": "cheltuieli_totale",
    "total_cheltuieli": "cheltuieli_totale",
    "ct": "cheltuieli_totale",
    "i_ct": "cheltuieli_totale",
    "i22": "cheltuieli_totale",
    "i022": "cheltuieli_totale",
    "i0022": "cheltuieli_totale",

    # ── Profit brut ──────────────────────────────────────────────────
    "profit_brut": "profit_brut",
    "rezultat_brut_profit": "profit_brut",
    "pb": "profit_brut",
    "i49": "profit_brut",
    "i049": "profit_brut",
    "i0049": "profit_brut",

    # ── Pierdere bruta ───────────────────────────────────────────────
    "pierdere_bruta": "pierdere_bruta",
    "rezultat_brut_pierdere": "pierdere_bruta",
    "pierdere_brut": "pierdere_bruta",
    "i50": "pierdere_bruta",
    "i050": "pierdere_bruta",
    "i0050": "pierdere_bruta",

    # ── Profit net ───────────────────────────────────────────────────
    "profit_net": "profit_net",
    "rezultat_net_profit": "profit_net",
    "pn": "profit_net",
    "i57": "profit_net",
    "i057": "profit_net",
    "i0057": "profit_net",
    "profit_pierdere_net_profit": "profit_net",

    # ── Pierdere neta ────────────────────────────────────────────────
    "pierdere_neta": "pierdere_neta",
    "rezultat_net_pierdere": "pierdere_neta",
    "pp": "pierdere_neta",
    "i58": "pierdere_neta",
    "i058": "pierdere_neta",
    "i0058": "pierdere_neta",
    "profit_pierdere_net_pierdere": "pierdere_neta",

    # ── Total active ─────────────────────────────────────────────────
    "total_active": "total_active",
    "total_active_nete": "total_active",
    "active_totale": "total_active",
    "ta": "total_active",
    "i_ta": "total_active",
    "i37": "total_active",
    "i037": "total_active",
    "i0037": "total_active",

    # ── Active imobilizate ───────────────────────────────────────────
    "active_imobilizate": "active_imobilizate",
    "imobilizari": "active_imobilizate",
    "ai": "active_imobilizate",
    "i_ai": "active_imobilizate",
    "i01": "active_imobilizate",
    "i001": "active_imobilizate",

    # ── Active circulante ────────────────────────────────────────────
    "active_circulante": "active_circulante",
    "ac": "active_circulante",
    "i_ac": "active_circulante",
    "i16": "active_circulante",
    "i016": "active_circulante",

    # ── Capitaluri proprii ───────────────────────────────────────────
    "capitaluri_proprii": "capitaluri_proprii",
    "capital_propriu": "capitaluri_proprii",
    "capitaluri": "capitaluri_proprii",
    "cp": "capitaluri_proprii",
    "i_cp": "capitaluri_proprii",
    "i38": "capitaluri_proprii",
    "i038": "capitaluri_proprii",
    "i0038": "capitaluri_proprii",

    # ── Datorii totale ───────────────────────────────────────────────
    "datorii_totale": "datorii_totale",
    "total_datorii": "datorii_totale",
    "dt": "datorii_totale",
    "i_dt": "datorii_totale",
    "dat_tot": "datorii_totale",
    "i40": "datorii_totale",
    "i040": "datorii_totale",
    "i0040": "datorii_totale",

    # ── Datorii termen lung ──────────────────────────────────────────
    "datorii_termen_lung": "datorii_termen_lung",
    "datorii_pe_termen_lung": "datorii_termen_lung",
    "dtl": "datorii_termen_lung",
    "i_dtl": "datorii_termen_lung",
    "i26": "datorii_termen_lung",
    "i026": "datorii_termen_lung",

    # ── Număr salariați ──────────────────────────────────────────────
    "nr_salariati": "nr_salariati",
    "numar_salariati": "nr_salariati",
    "numar_mediu_salariati": "nr_salariati",
    "nr_med_sal": "nr_salariati",
    "ns": "nr_salariati",
    "i_ns": "nr_salariati",
    "nr_sal": "nr_salariati",
    "i32": "nr_salariati",
    "i032": "nr_salariati",
    "i0032": "nr_salariati",
    "salariati": "nr_salariati",
    "angajati": "nr_salariati",
}

# Fields that represent monetary values (stored as integer RON)
MONETARY_FIELDS: frozenset[str] = frozenset({
    "cifra_afaceri",
    "venituri_totale",
    "cheltuieli_totale",
    "profit_brut",
    "pierdere_bruta",
    "profit_net",
    "pierdere_neta",
    "total_active",
    "active_imobilizate",
    "active_circulante",
    "capitaluri_proprii",
    "datorii_totale",
    "datorii_termen_lung",
})
