"""Streaming downloader with tenacity retry and local disk cache.

Source: data.gov.ro (Ministerul Finanțelor open data portal).
Files are plain TXT (comma-delimited, no header), ~9MB each.

Usage:
    txt_path = await ensure_downloaded(year=2023)
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from .constants import (
    CACHE_DIR,
    DATA_GOV_RO_URLS,
    DATA_GOV_RO_DATASET_NAMES,
    DATA_GOV_RO_FILE_PATTERN,
    MIN_CACHE_SIZE_BYTES,
    DOWNLOAD_CHUNK_BYTES,
)

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=5.0)

# Minimum valid file size (100 KB — these files are ~9MB each, be conservative)
_MIN_VALID_SIZE = 100 * 1024


def _cache_path(year: int) -> Path:
    """Local cache file path for a given year's balance sheet TXT."""
    return CACHE_DIR / f"bilant{year}.txt"


def _is_cached(year: int) -> bool:
    p = _cache_path(year)
    return p.exists() and p.stat().st_size >= _MIN_VALID_SIZE


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _stream_to_disk(url: str, dest: Path) -> int:
    """Download *url* to *dest* using streaming. Returns bytes written."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "RomBiz-ETL/1.0 (balance-sheets importer)"},
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(tmp, "wb") as fh:
                async for chunk in resp.aiter_bytes(DOWNLOAD_CHUNK_BYTES):
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total and downloaded % (10 * 1024 * 1024) < DOWNLOAD_CHUNK_BYTES:
                        pct = downloaded / total * 100
                        logger.info(
                            "Downloading %s: %.1f%% (%d / %d bytes)",
                            dest.name,
                            pct,
                            downloaded,
                            total,
                        )

    tmp.rename(dest)
    logger.info("Saved %s (%d bytes)", dest, downloaded)
    return downloaded


async def _resolve_url_via_ckan(year: int) -> str | None:
    """Query data.gov.ro CKAN API to find the TXT download URL for *year*."""
    dataset_name = DATA_GOV_RO_DATASET_NAMES.get(year)
    if not dataset_name:
        return None

    file_pattern = DATA_GOV_RO_FILE_PATTERN.format(year=year)
    api_url = f"https://data.gov.ro/api/3/action/package_show?id={dataset_name}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True) as client:
            resp = await client.get(api_url)
            resp.raise_for_status()
            data = resp.json()

        for resource in data.get("result", {}).get("resources", []):
            url = resource.get("url") or resource.get("datagovro_download_url") or ""
            url_lower = url.lower()
            # Match the main balance sheet TXT for the correct year (not IFN, ONG, etc.)
            expected_suffix = f"an{year}.txt"
            if "web_bl_bs_sl" in url_lower and url_lower.endswith(".txt") and expected_suffix in url_lower:
                logger.info("Resolved URL for year %d via CKAN: %s", year, url)
                return url
    except Exception as exc:  # noqa: BLE001
        logger.warning("CKAN API lookup failed for year %d: %s", year, exc)

    return None


async def ensure_downloaded(year: int) -> Path:
    """Return local TXT path for *year*, downloading if not already cached.

    Tries known direct URLs first, then falls back to CKAN API discovery.
    Raises RuntimeError if all sources fail.
    """
    dest = _cache_path(year)

    if _is_cached(year):
        logger.info("Cache hit for year %d: %s", year, dest)
        return dest

    # 1. Try known direct URL first
    urls_to_try: list[str] = []
    if year in DATA_GOV_RO_URLS:
        urls_to_try.append(DATA_GOV_RO_URLS[year])

    # 2. CKAN API discovery as fallback
    ckan_url = await _resolve_url_via_ckan(year)
    if ckan_url and ckan_url not in urls_to_try:
        urls_to_try.append(ckan_url)

    last_exc: Exception | None = None
    for url in urls_to_try:
        logger.info("Downloading balance sheet for year %d from: %s", year, url)
        try:
            size = await _stream_to_disk(url, dest)
            if size >= _MIN_VALID_SIZE:
                return dest
            logger.warning(
                "Downloaded file for year %d is too small (%d bytes); skipping",
                year,
                size,
            )
            dest.unlink(missing_ok=True)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "HTTP %d for year %d from %s",
                exc.response.status_code,
                year,
                url,
            )
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("Download failed for year %d from %s: %s", year, url, exc)
            last_exc = exc

    raise RuntimeError(
        f"All download sources exhausted for year {year}. Last error: {last_exc}"
    )
