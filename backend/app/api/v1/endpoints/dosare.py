"""
Motor Cautare Dosare - endpoint gratuit.
Foloseste CautareDosare din portalquery.just.ro SOAP API (WSDL verificat).
"""
from __future__ import annotations

from typing import Optional
from xml.etree import ElementTree as ET

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user, TokenPayload

router = APIRouter()

SOAP_URL  = "http://portalquery.just.ro/query.asmx"
SOAP_NS   = "portalquery.just.ro"
SOAP_PFXR = f"{{{SOAP_NS}}}"


def _nil(tag: str) -> str:
    return (
        f'<{tag} xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/>' 
    )


def _soap_envelope(method: str, inner_xml: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ' xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soap:Body>"
        f'<{method} xmlns="{SOAP_NS}">' 
        f"{inner_xml}"
        f"</{method}>"
        "</soap:Body>"
        "</soap:Envelope>"
    )
    return xml.encode("utf-8")


def _txt(el: ET.Element, tag: str) -> str:
    child = el.find(f"{SOAP_PFXR}{tag}")
    if child is None:
        child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _parse_dosar(d: ET.Element) -> dict:
    parti: list = []
    parti_el = d.find(f"{SOAP_PFXR}parti") or d.find("parti")
    if parti_el is not None:
        for p in parti_el:
            parti.append({
                "calitate": _txt(p, "calitateParte"),
                "denumire": _txt(p, "nume"),
            })

    sedinte: list = []
    sed_el = d.find(f"{SOAP_PFXR}sedinte") or d.find("sedinte")
    if sed_el is not None:
        for s in sed_el:
            sedinte.append({
                "data":    _txt(s, "data"),
                "ora":     _txt(s, "ora"),
                "complet": _txt(s, "complet"),
                "solutie": _txt(s, "solutie") or _txt(s, "solutieSumar"),
            })

    institutie_el = d.find(f"{SOAP_PFXR}institutie") or d.find("institutie")
    institutie = (institutie_el.text or "").strip() if institutie_el is not None else ""

    return {
        "numar":       _txt(d, "numar"),
        "instanta":    institutie,
        "departament": _txt(d, "departament"),
        "materie":     _txt(d, "categorieCazNume"),
        "obiect":      _txt(d, "obiect"),
        "stadiu":      _txt(d, "stadiuProcesualNume"),
        "data_dosar":  _txt(d, "data"),
        "parti":       parti,
        "termene":     sedinte,
    }


async def _soap_call(method: str, inner_xml: str) -> list:
    body = _soap_envelope(method, inner_xml)
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"portalquery.just.ro/{method}"',
    }
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        resp = await client.post(SOAP_URL, content=body, headers=headers)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    result_el = root.find(f".//{SOAP_PFXR}{method}Result")
    if result_el is None:
        result_el = root.find(f".//{method}Result")
    if result_el is None:
        return []

    dosare = []
    for child in result_el:
        try:
            parsed = _parse_dosar(child)
            if parsed.get("numar"):
                dosare.append(parsed)
        except Exception:
            continue
    return dosare


@router.get("/search")
async def search_dosare(
    q: str = Query(..., min_length=1, max_length=200),
    tip_cautare: str = Query("parte", pattern="^(parte|obiect|numar)$"),
    calitate: Optional[str] = Query(None, max_length=50),
    instante: Optional[str] = Query(None, max_length=500),
    materii: Optional[str] = Query(None, max_length=500),
    stadii: Optional[str] = Query(None, max_length=200),
    data_start: Optional[str] = Query(None),
    data_end: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
):
    """Cauta dosare pe portalquery.just.ro."""
    if tip_cautare == "numar":
        numar_dosar = q
        num_parte   = ""
        obiect      = ""
    elif tip_cautare == "obiect":
        numar_dosar = ""
        num_parte   = ""
        obiect      = q
    else:
        numar_dosar = ""
        num_parte   = q
        obiect      = ""

    def iso_or_nil(val: Optional[str], tag: str) -> str:
        if val:
            return f"<{tag}>{val}T00:00:00</{tag}>"
        return _nil(tag)

    inner = (
        f"<numarDosar>{numar_dosar}</numarDosar>"
        f"<obiectDosar>{obiect}</obiectDosar>"
        f"<numeParte>{num_parte}</numeParte>"
        + _nil("institutie")
        + iso_or_nil(data_start, "dataStart")
        + iso_or_nil(data_end, "dataStop")
    )

    try:
        dosare = await _soap_call("CautareDosare", inner)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Serviciu portal.just.ro indisponibil ({exc.response.status_code})",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Eroare SOAP: {str(exc)[:200]}")

    if instante:
        inst_list = [i.strip().lower() for i in instante.split(",") if i.strip()]
        dosare = [d for d in dosare if any(i in d["instanta"].lower() for i in inst_list)]

    if materii:
        mat_list = [m.strip().lower() for m in materii.split(",") if m.strip()]
        dosare = [d for d in dosare if any(m in d["materie"].lower() for m in mat_list)]

    if stadii:
        stadii_list = [s.strip().lower() for s in stadii.split(",") if s.strip()]
        dosare = [d for d in dosare if any(s in d["stadiu"].lower() for s in stadii_list)]

    if calitate and calitate.lower() not in ("orice calitate", ""):
        cal_lower = calitate.lower()
        dosare = [
            d for d in dosare
            if any(cal_lower in p["calitate"].lower() for p in d["parti"])
        ]

    total = len(dosare)
    start = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "dosare": dosare[start: start + page_size],
    }
