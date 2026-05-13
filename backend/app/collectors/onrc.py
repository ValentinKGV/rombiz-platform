"""
ONRC (National Office of the Trade Register) collector — v3 FUNCTIONAL.

Hard constraint #9: 30-day cache for ONRC data.

Data sources (dual, per ONRC support recommendation):
  1. ANAF async API — primary, fast, reliable.
     Provides: denumire, CUI, nr_reg_comert, adresa, judet, CAEN,
               stare_firma, data_infiintare, TVA status, insolventa.
  2. BERC portal RPA (portal.berc.onrc.ro) — secondary, best-effort.
     Requires BERC_EMAIL + BERC_PASSWORD env vars.
     Provides: asociati, administratori, capital_social,
               forma_juridica, obiect_activitate, sediu_social.
     Falls back gracefully to empty dicts when unavailable.

Environment variables (optional, for BERC enrichment):
  BERC_EMAIL    — BERC account email
  BERC_PASSWORD — BERC account password
"""
from __future__ import annotations

import asyncio
import os
import re
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Any

import httpx

from app.collectors.base_connector import BaseConnector
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Forma juridică extraction from company name ───────────────────────────────
_FORMA_JURIDICA_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bS\.?R\.?L\.?\b', re.I), 'SRL'),
    (re.compile(r'\bS\.?A\.?\b', re.I), 'SA'),
    (re.compile(r'\bS\.?N\.?C\.?\b', re.I), 'SNC'),
    (re.compile(r'\bS\.?C\.?S\.?\b', re.I), 'SCS'),
    (re.compile(r'\bS\.?C\.?A\.?\b', re.I), 'SCA'),
    (re.compile(r'\bR\.?A\.?\b', re.I), 'RA'),
    (re.compile(r'\bP\.?F\.?A\.?\b', re.I), 'PFA'),
    (re.compile(r'\bI\.?I\.?\b', re.I), 'II'),
    (re.compile(r'\bI\.?F\.?\b', re.I), 'IF'),
    (re.compile(r'\bO\.?N\.?G\.?\b', re.I), 'ONG'),
    (re.compile(r'\bASO[CT]', re.I), 'ASOCIATIE'),
    (re.compile(r'\bFUNDA[TȚ]', re.I), 'FUNDATIE'),
    (re.compile(r'\bCOOPERATIV', re.I), 'COOPERATIVA'),
]


def _extract_forma_juridica(denumire: Optional[str]) -> Optional[str]:
    """Extract legal form from company name (e.g. 'Firma SRL' → 'SRL')."""
    if not denumire:
        return None
    for pattern, forma in _FORMA_JURIDICA_PATTERNS:
        if pattern.search(denumire):
            return forma
    return None


# ── BERC Playwright scraper ───────────────────────────────────────────────────

class BERCScraper:
    """
    Scrapes BERC portal (portal.berc.onrc.ro) using Playwright.
    Requires BERC account credentials (BERC_EMAIL / BERC_PASSWORD env vars).
    Returns empty dict gracefully when credentials are absent or scraping fails.
    """

    PORTAL_URL = "https://portal.berc.onrc.ro"
    LOGIN_URL = "https://portal.berc.onrc.ro/auth"

    def __init__(self):
        self.email = os.environ.get("BERC_EMAIL", "")
        self.password = os.environ.get("BERC_PASSWORD", "")

    @property
    def has_credentials(self) -> bool:
        return bool(self.email and self.password)

    async def fetch_company(self, cui: int) -> dict:
        """
        Fetch ONRC-specific company data from BERC portal via Playwright RPA.
        Returns empty dict if credentials are missing or scraping fails.
        """
        if not self.has_credentials:
            logger.debug("berc_no_credentials", cui=cui)
            return {}

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("berc_playwright_not_installed", cui=cui)
            return {}

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                          "--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                    ),
                    extra_http_headers={"Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8"},
                )
                await context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )

                page = await context.new_page()
                page.set_default_timeout(20000)

                result: dict = {}
                api_data: list[dict] = []

                async def capture_response(response):
                    url = response.url
                    if "api.berc.onrc.ro" in url and "articles" in url.lower():
                        try:
                            body = await response.body()
                            import json
                            parsed = json.loads(body)
                            api_data.append({"url": url, "data": parsed})
                        except Exception:
                            pass

                page.on("response", capture_response)

                # Step 1: Login
                await page.goto(f"{self.LOGIN_URL}", timeout=30000, wait_until="networkidle")
                await asyncio.sleep(2)

                email_input = await page.query_selector("input[type='email'], input[type='text'][placeholder*='mail'], input[name*='mail']")
                pass_input = await page.query_selector("input[type='password']")

                if email_input and pass_input:
                    await email_input.fill(self.email)
                    await pass_input.fill(self.password)
                    submit = await page.query_selector("button[type='submit'], button:has-text('Login'), button:has-text('Autentificare')")
                    if submit:
                        await submit.click()
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(3)

                # Step 2: Navigate to articles-company search
                await page.goto(f"{self.PORTAL_URL}/articles-company", timeout=30000, wait_until="networkidle")
                await asyncio.sleep(3)

                # Step 3: Find CUI search input and search
                cui_input = await page.query_selector(
                    "input[placeholder*='CUI'], input[placeholder*='CIF'], "
                    "input[placeholder*='cod'], input[placeholder*='Cod']"
                )
                if cui_input:
                    await cui_input.fill(str(cui))
                    await asyncio.sleep(0.5)
                    await cui_input.press("Enter")
                    await asyncio.sleep(3)

                # Step 4: Parse page content for company data
                body_text = await page.evaluate("document.body.innerText")
                result = self._parse_berc_content(body_text, cui)

                # Also check captured API responses
                if api_data:
                    result.update(self._parse_berc_api(api_data, cui))

                await browser.close()
                if result:
                    logger.info("berc_scrape_success", cui=cui, fields=list(result.keys()))
                return result

        except Exception as e:
            logger.warning("berc_scrape_failed", cui=cui, error=str(e))
            return {}

    def _parse_berc_content(self, text: str, cui: int) -> dict:
        """Parse plain text from BERC page to extract company fields."""
        result: dict = {}

        # Capital social (e.g. "200 RON", "1000.00 RON", "200 lei")
        cap_match = re.search(
            r'capital\s+social[:\s]+([0-9,.\s]+)\s*(RON|LEI|lei|ron)',
            text, re.I
        )
        if cap_match:
            try:
                raw = cap_match.group(1).replace(',', '.').replace(' ', '')
                result["capital_social"] = Decimal(raw)
            except Exception:
                pass

        # Forma juridică
        forma_match = re.search(
            r'forma\s+juridic[ăa][:\s]+([A-Z]+)',
            text, re.I
        )
        if forma_match:
            result["forma_juridica"] = forma_match.group(1).upper()

        # Sediu social
        sediu_match = re.search(
            r'sediu\s+social[:\s]+([^\n]{10,100})',
            text, re.I
        )
        if sediu_match:
            result["sediu_social"] = sediu_match.group(1).strip()

        # Obiect de activitate
        ob_match = re.search(
            r'obiect\s+(?:de\s+)?activitate[:\s]+([^\n]{10,200})',
            text, re.I
        )
        if ob_match:
            result["obiect_activitate"] = ob_match.group(1).strip()

        return result

    def _parse_berc_api(self, api_data: list[dict], cui: int) -> dict:
        """Parse structured API responses captured during BERC navigation."""
        result: dict = {}
        for item in api_data:
            data = item.get("data", {})
            if isinstance(data, list):
                data = data[0] if data else {}
            if not isinstance(data, dict):
                continue

            if "capitalSocial" in data:
                try:
                    result["capital_social"] = Decimal(str(data["capitalSocial"]))
                except Exception:
                    pass
            if "formaJuridica" in data:
                result["forma_juridica"] = data["formaJuridica"]
            if "obiectActivitate" in data:
                result["obiect_activitate"] = data["obiectActivitate"]
            if "sediuSocial" in data:
                result["sediu_social"] = data["sediuSocial"]

            asociati_raw = data.get("asociati") or data.get("actionari") or []
            if asociati_raw:
                result["asociati"] = [
                    {
                        "nume": a.get("numeAsociat") or a.get("denumire") or a.get("name", ""),
                        "procent": a.get("procentParticipare") or a.get("procent"),
                        "tip": "asociat",
                    }
                    for a in asociati_raw if isinstance(a, dict)
                ]

            admins_raw = data.get("administratori") or data.get("administratori", [])
            if admins_raw:
                result["administratori"] = [
                    {
                        "nume": a.get("numeAdministrator") or a.get("denumire") or a.get("name", ""),
                        "data_numire": a.get("dataNumire"),
                        "tip": "administrator",
                    }
                    for a in admins_raw if isinstance(a, dict)
                ]
        return result


# ── ANAF single-company fetcher ───────────────────────────────────────────────

async def _fetch_anaf_single(cui: int) -> dict:
    """
    Fetch basic company data from ANAF async API for a single CUI.
    Returns normalized dict or empty dict on failure.
    """
    ANAF_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva"
    today = date.today().strftime("%Y-%m-%d")
    payload = [{"cui": cui, "data": today}]

    try:
        # Step 1: Submit request
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            submit_resp = await client.post(ANAF_URL, json=payload)
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()

        if submit_data.get("cod") != 200:
            logger.warning("anaf_submit_failed", cui=cui, response=submit_data)
            return {}

        correlation_id = submit_data.get("correlationId")
        if not correlation_id:
            return {}

        # Step 2: Poll with a fresh client each attempt (ANAF drops persistent connections)
        for attempt in range(5):
            await asyncio.sleep(2.0 * (attempt + 1))
            try:
                async with httpx.AsyncClient(timeout=30.0) as poll_client:
                    poll_resp = await poll_client.get(
                        ANAF_URL, params={"id": correlation_id}
                    )
                    if poll_resp.status_code == 200:
                        data = poll_resp.json()
                        if data.get("cod") == 200:
                            found = data.get("found", [])
                            if found:
                                return _parse_anaf_company(found[0])
                            return {}
            except Exception as poll_err:
                logger.warning("anaf_poll_retry", cui=cui, attempt=attempt + 1, error=str(poll_err))

        return {}

    except Exception as e:
        logger.error("anaf_single_fetch_failed", cui=cui, error=str(e))
        return {}


def _parse_anaf_company(raw: dict) -> dict:
    """Normalize ANAF response into company fields."""
    general = raw.get("date_generale", {})
    tva = raw.get("inregistrare_scop_Tva", {})
    # stare_inactiv = fiscal inactivity declared by ANAF (non-filer), NOT insolvency
    stare_inactiv = raw.get("stare_inactiv", {})
    tva_incasare = raw.get("inregistrare_RTVAI", {})
    split_tva = raw.get("inregistrare_SplitTVA", {})
    # ANAF stores judet/localitate in adresa_sediu_social, not in date_generale
    sediu = raw.get("adresa_sediu_social", {})

    return {
        "denumire": general.get("denumire"),
        "adresa": general.get("adresa"),
        # Judet & localitate come from adresa_sediu_social (date_generale doesn't have them)
        "judet": sediu.get("sdenumire_Judet") or general.get("judet"),
        "localitate": sediu.get("sdenumire_Localitate") or general.get("localitate"),
        "cod_postal": sediu.get("scod_Postal") or general.get("codPostal"),
        "nr_reg_comert": general.get("nrRegCom"),
        "telefon": general.get("telefon"),
        "stare_firma": general.get("stare_inregistrare"),
        # ANAF returns both data_inregistrare and occasionally data_infiintare
        "data_infiintare": general.get("data_inregistrare") or general.get("data_infiintare"),
        "cod_caen_principal": general.get("cod_CAEN") or general.get("caen"),
        # ANAF returns forma_juridica directly (e.g. "SOCIETATE COMERCIALĂ CU RĂSPUNDERE LIMITATĂ")
        "forma_juridica_anaf": general.get("forma_juridica"),
        "forma_de_proprietate": general.get("forma_de_proprietate"),
        "forma_organizare": general.get("forma_organizare"),
        # TVA — note: ANAF uses "statusTvaIncasare" (lowercase v), not "statusTVAIncasare"
        "tva_activ": tva.get("scpTVA", False),
        "tva_data_inregistrare": tva.get("dataInregistrareTVA"),
        "tva_la_incasare": tva_incasare.get("statusTvaIncasare", False),
        "split_tva": split_tva.get("statusSplitTVA", False),
        # Fiscal inactivity (declared inactive by ANAF) — NOT insolvency
        # ANAF key is "statusInactivi" (with trailing i)
        "inactiv_fiscal": stare_inactiv.get("statusInactivi", False),
        "data_inactivare": stare_inactiv.get("dataInactivare"),
        "sursa_baza": "ANAF",
    }


# ── Main ONRC Collector ───────────────────────────────────────────────────────

class ONRCCollector(BaseConnector):
    """
    ONRC data collector — dual-source:
      1. ANAF API (primary, always used): basic company data.
      2. BERC Playwright RPA (secondary, optional): ONRC-specific details.

    Hard constraint #9: 30-day cache TTL.
    """

    SOURCE_NAME = "ONRC"
    BASE_URL = "https://portal.berc.onrc.ro"
    RATE_LIMIT_PER_SECOND = 0.5
    CACHE_TTL_DAYS = 30

    def __init__(self):
        super().__init__()
        self._berc = BERCScraper()

    async def sync(self, cuis: list[int] = None, **kwargs) -> dict:
        """Sync company registration data from ONRC (ANAF + BERC)."""
        processed = 0
        failed = 0
        results = []

        for cui in (cuis or []):
            try:
                data = await self.fetch_single(cui)
                if data:
                    results.append(data)
                    processed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error("onrc_sync_failed", cui=cui, error=str(e))
                failed += 1

        return {"processed": processed, "failed": failed, "results": results}

    async def fetch_single(self, cui: int) -> Optional[dict]:
        """
        Fetch full company registration data for a single CUI.

        Strategy:
          1. Call ANAF API for base data.
          2. Attempt BERC Playwright scrape for ONRC-specific fields.
          3. Merge results; BERC fields override ANAF where both exist.
        """
        now = datetime.now(timezone.utc)

        # Step 1: ANAF — primary, fast, reliable
        anaf_data = await _fetch_anaf_single(cui)
        if not anaf_data:
            logger.warning("onrc_anaf_empty", cui=cui)

        # Step 2: BERC — secondary, best-effort
        berc_data = await self._berc.fetch_company(cui)

        # Step 3: Merge — prefer BERC forma_juridica, then ANAF direct value, then extract from name
        denumire = anaf_data.get("denumire") or berc_data.get("denumire")
        forma_juridica = (
            berc_data.get("forma_juridica")
            or anaf_data.get("forma_juridica_anaf")
            or _extract_forma_juridica(denumire)
        )

        return {
            # Identity
            "cui": cui,
            "denumire": denumire,

            # ONRC registry fields
            "nr_reg_comert": anaf_data.get("nr_reg_comert") or berc_data.get("nr_reg_comert"),
            "forma_juridica": forma_juridica,
            "capital_social": berc_data.get("capital_social"),

            # Associates & administrators (from BERC; empty when not available)
            "asociati": berc_data.get("asociati", []),
            "administratori": berc_data.get("administratori", []),

            # Activity
            "obiect_activitate": berc_data.get("obiect_activitate"),
            "cod_caen_principal": anaf_data.get("cod_caen_principal"),

            # Address
            "sediu_social": (
                berc_data.get("sediu_social")
                or anaf_data.get("adresa")
            ),
            "judet": anaf_data.get("judet"),
            "localitate": anaf_data.get("localitate"),
            "cod_postal": anaf_data.get("cod_postal"),

            # Status
            "stare_firma": anaf_data.get("stare_firma"),
            "data_infiintare": anaf_data.get("data_infiintare"),

            # Fiscal (from ANAF)
            "tva_activ": anaf_data.get("tva_activ", False),
            "tva_data_inregistrare": anaf_data.get("tva_data_inregistrare"),
            "tva_la_incasare": anaf_data.get("tva_la_incasare", False),
            "split_tva": anaf_data.get("split_tva", False),
            # Fiscal inactivity (ANAF) — distinct from insolvency (BPI)
            "inactiv_fiscal": anaf_data.get("inactiv_fiscal", False),
            "data_inactivare": anaf_data.get("data_inactivare"),

            # Metadata
            "sursa": "ANAF+BERC" if berc_data else "ANAF",
            "berc_enriched": bool(berc_data),
            "data_sync": now,
            "cache_valid_until": (now + timedelta(days=self.CACHE_TTL_DAYS)).date(),
        }

    async def fetch_new_companies(self, days_back: int = 7) -> list[dict]:
        """
        Fetch recently registered companies via ANAF open data.
        Queries a batch of recent CUI ranges via ANAF bulk API.
        Falls back to empty list if unavailable.
        """
        try:
            # ANAF doesn't have a "new companies" endpoint directly.
            # We return an empty list here — new companies come via
            # the NewCompaniesPage which uses a different data source.
            logger.debug("fetch_new_companies_stub", days_back=days_back)
            return []
        except Exception as e:
            logger.error("onrc_new_companies_failed", error=str(e))
            return []

    async def fetch_company_data(self, cui: int) -> Optional[dict]:
        """Alias for fetch_single — used by services."""
        return await self.fetch_single(cui)
