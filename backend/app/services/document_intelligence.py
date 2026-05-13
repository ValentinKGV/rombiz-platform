"""
Document Intelligence — Branch 18.

Sub-modules:
  18.1  Document Classifier       — Classify uploaded documents by type
  18.2  Financial Statement Parser— Extract structured data from balance sheets
  18.3  Contract Analyzer         — Key clause extraction from contracts
  18.4  Entity Extraction         — NER on Romanian business documents
  18.5  Document Comparison       — Diff analysis between document versions
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Document type patterns ──────────────────────────────────────────
DOCUMENT_PATTERNS = {
    "BILANT": [r"bilan[tț]", r"situati[ie]\s+financiar", r"total\s+activ", r"capitaluri\s+proprii"],
    "CONTRACT": [r"contract", r"p[aă]r[tț]i\s+contractant", r"clauze", r"obliga[tț]i"],
    "FACTURA": [r"factur[aă]", r"furnizor", r"cump[aă]r[aă]tor", r"TVA", r"total\s+de\s+plat"],
    "CERTIFICAT_FISCAL": [r"certificat\s+fiscal", r"obliga[tț]ii\s+bugetar", r"ANAF"],
    "ACT_CONSTITUTIV": [r"act\s+constitutiv", r"statut", r"asocia[tț]i", r"capital\s+social"],
    "CERERE_OFERTA": [r"cerere\s+de\s+ofert", r"specifica[tț]i", r"pre[tț]\s+unitar"],
    "RAPORT_AUDIT": [r"raport.*audit", r"auditor", r"opinie", r"conformitate"],
    "HOTARARE_AGA": [r"hot[aă]r[aâ]re.*AGA", r"adunare.*general", r"ac[tț]ionar"],
}

FINANCIAL_KEYWORDS = {
    "cifra_afaceri": [r"cifra\s+de\s+afaceri", r"venituri\s+totale", r"turnover"],
    "profit_net": [r"profit\s+net", r"rezultat\s+net", r"net\s+income"],
    "total_active": [r"total\s+activ", r"active\s+totale", r"total\s+assets"],
    "total_datorii": [r"total\s+datorii", r"datorii\s+totale", r"total\s+liabilities"],
    "capitaluri_proprii": [r"capitaluri\s+proprii", r"equity", r"capital\s+propriu"],
    "nr_angajati": [r"num[aă]r.*angaja[tț]i", r"salaria[tț]i", r"employees"],
}

CONTRACT_CLAUSES = {
    "valoare": [r"valoare.*contract", r"pre[tț].*total", r"sum[aă].*(\d[\d.,]+)"],
    "durata": [r"durat[aă].*contract", r"perioad[aă].*(\d+)\s*(luni|ani|zile)"],
    "penalitati": [r"penalit[aă][tț]i", r"daune.*interese", r"clauze?\s+penal"],
    "reziliere": [r"rezilier", r"încetare.*contract", r"denun[tț]are"],
    "forta_majora": [r"for[tț][aă]\s+major[aă]", r"caz\s+fortuit"],
    "confidentialitate": [r"confiden[tț]ialitate", r"secret\s+comercial"],
    "jurisdictie": [r"jurisdic[tț]ie", r"competen[tț][aă]", r"tribunal", r"instan[tț][aă]"],
}


# ═══════════════════════════════════════════════════════════════════════
# 18.1  DOCUMENT CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════

async def classify_document(text: str) -> dict:
    """
    Classify a document based on keyword pattern matching.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        score = 0
        matched_patterns = []
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                score += len(matches)
                matched_patterns.append(pattern)
        if score > 0:
            scores[doc_type] = score

    if not scores:
        return {
            "document_type": "NECUNOSCUT",
            "confidence": 0,
            "all_scores": {},
            "text_length": len(text),
        }

    best_type = max(scores, key=scores.get)  # type: ignore
    total = sum(scores.values())
    confidence = round(scores[best_type] / total * 100, 1) if total > 0 else 0

    return {
        "document_type": best_type,
        "confidence": confidence,
        "all_scores": scores,
        "text_length": len(text),
    }


# ═══════════════════════════════════════════════════════════════════════
# 18.2  FINANCIAL STATEMENT PARSER
# ═══════════════════════════════════════════════════════════════════════

async def parse_financial_statement(text: str) -> dict:
    """
    Extract structured financial data from balance sheet text.
    """
    text_lower = text.lower()
    extracted: dict[str, Optional[float]] = {}

    for field, patterns in FINANCIAL_KEYWORDS.items():
        for pattern in patterns:
            # Look for the pattern followed by a number
            regex = pattern + r"[:\s]*[=]?\s*([\d.,]+)"
            match = re.search(regex, text_lower)
            if match:
                try:
                    val_str = match.group(1).replace(".", "").replace(",", ".")
                    extracted[field] = float(val_str)
                except (ValueError, IndexError):
                    pass
                break

    # Try to find the fiscal year
    year_match = re.search(r"(?:anul?|exerci[tț]iu|an\s+fiscal)\s*:?\s*(\d{4})", text_lower)
    fiscal_year = int(year_match.group(1)) if year_match else None

    return {
        "fiscal_year": fiscal_year,
        "extracted_fields": extracted,
        "fields_found": len(extracted),
        "completeness": round(len(extracted) / len(FINANCIAL_KEYWORDS) * 100, 1),
        "parsed_at": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════
# 18.3  CONTRACT ANALYZER
# ═══════════════════════════════════════════════════════════════════════

async def analyze_contract(text: str) -> dict:
    """
    Extract key clauses and terms from contract text.
    """
    text_lower = text.lower()
    clauses: dict[str, dict] = {}

    for clause_name, patterns in CONTRACT_CLAUSES.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                # Extract surrounding context (100 chars before and after)
                start = max(0, match.start() - 100)
                end = min(len(text_lower), match.end() + 100)
                context = text[start:end].strip()

                clauses[clause_name] = {
                    "found": True,
                    "context": context,
                    "position": match.start(),
                }
                break
        if clause_name not in clauses:
            clauses[clause_name] = {"found": False}

    # Extract parties (look for CUI patterns)
    cui_matches = re.findall(r"(?:CUI|CIF|cod\s+fiscal)\s*:?\s*(\d{6,10})", text, re.IGNORECASE)

    # Risk assessment of contract
    risks = []
    if not clauses.get("penalitati", {}).get("found"):
        risks.append({"risk": "FARA_PENALITATI", "detail": "Nu s-au găsit clauze de penalități"})
    if not clauses.get("reziliere", {}).get("found"):
        risks.append({"risk": "FARA_REZILIERE", "detail": "Nu s-au găsit clauze de reziliere"})
    if not clauses.get("forta_majora", {}).get("found"):
        risks.append({"risk": "FARA_FORTA_MAJORA", "detail": "Nu s-a găsit clauza de forță majoră"})

    return {
        "clauses": clauses,
        "clauses_found": sum(1 for c in clauses.values() if c.get("found")),
        "total_clauses_checked": len(CONTRACT_CLAUSES),
        "parties_cui": cui_matches,
        "contract_risks": risks,
        "risk_count": len(risks),
        "text_length": len(text),
    }


# ═══════════════════════════════════════════════════════════════════════
# 18.4  ENTITY EXTRACTION (NER)
# ═══════════════════════════════════════════════════════════════════════

async def extract_entities(text: str) -> dict:
    """
    Named entity recognition for Romanian business documents.
    """
    entities: dict[str, list] = {
        "companies": [],
        "persons": [],
        "fiscal_codes": [],
        "dates": [],
        "amounts": [],
        "addresses": [],
        "caen_codes": [],
    }

    # CUI / CIF
    for m in re.finditer(r"(?:CUI|CIF|cod\s+fiscal)\s*:?\s*(\d{6,10})", text, re.IGNORECASE):
        entities["fiscal_codes"].append(m.group(1))

    # Company names (S.R.L., S.A., etc.)
    for m in re.finditer(r"([A-ZĂÂÎȘȚ][A-ZĂÂÎȘȚ\s&-]{2,})\s+(S\.?R\.?L\.?|S\.?A\.?|S\.?C\.?S\.?|S\.?N\.?C\.?)", text):
        entities["companies"].append(m.group(0).strip())

    # Dates
    for m in re.finditer(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})\b", text):
        entities["dates"].append(m.group(0))

    # Monetary amounts
    for m in re.finditer(r"(\d[\d.,]+)\s*(RON|LEI|EUR|USD|lei|euro|dolari)", text, re.IGNORECASE):
        val = m.group(1).replace(".", "").replace(",", ".")
        entities["amounts"].append({
            "value": val,
            "currency": m.group(2).upper().replace("LEI", "RON").replace("EURO", "EUR").replace("DOLARI", "USD"),
        })

    # CAEN codes
    for m in re.finditer(r"(?:CAEN|cod\s+CAEN)\s*:?\s*(\d{4})", text, re.IGNORECASE):
        entities["caen_codes"].append(m.group(1))

    # Person names (simplified heuristic: Title + Name pattern)
    for m in re.finditer(r"(?:Dl\.|D-na|Dna\.?|Domnul|Doamna)\s+([A-ZĂÂÎȘȚ][a-zăâîșț]+(?:\s+[A-ZĂÂÎȘȚ][a-zăâîșț]+){1,2})", text):
        entities["persons"].append(m.group(1))

    # Addresses (street patterns)
    for m in re.finditer(r"(?:str\.|strada|bd\.|bulevardul)\s+([^,\n]{5,50})", text, re.IGNORECASE):
        entities["addresses"].append(m.group(0).strip())

    # Deduplicate
    for key in entities:
        if isinstance(entities[key], list) and entities[key] and isinstance(entities[key][0], str):
            entities[key] = list(dict.fromkeys(entities[key]))

    total_entities = sum(len(v) for v in entities.values())

    return {
        "entities": entities,
        "total_entities": total_entities,
        "entity_types_found": sum(1 for v in entities.values() if v),
    }


# ═══════════════════════════════════════════════════════════════════════
# 18.5  DOCUMENT COMPARISON
# ═══════════════════════════════════════════════════════════════════════

async def compare_documents(text_a: str, text_b: str) -> dict:
    """
    Compare two document versions and highlight differences.
    """
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    set_a = set(lines_a)
    set_b = set(lines_b)

    added = list(set_b - set_a)
    removed = list(set_a - set_b)
    unchanged = list(set_a & set_b)

    # Word-level stats
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    new_words = words_b - words_a
    removed_words = words_a - words_b

    similarity = len(unchanged) / max(len(set_a | set_b), 1) * 100

    return {
        "lines_a": len(lines_a),
        "lines_b": len(lines_b),
        "added_lines": len(added),
        "removed_lines": len(removed),
        "unchanged_lines": len(unchanged),
        "similarity_pct": round(similarity, 1),
        "added_sample": added[:20],
        "removed_sample": removed[:20],
        "new_words_count": len(new_words),
        "removed_words_count": len(removed_words),
        "chars_a": len(text_a),
        "chars_b": len(text_b),
    }
