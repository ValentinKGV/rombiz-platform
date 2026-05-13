"""
Reports service — PDF, Excel, CSV, JSON, HTML generation.

v2 Improvements:
  7.1: Complete PDF — persons, court cases, public contracts sections
  7.2: Complete Excel — risk, ESG, persons, court, contracts sheets
  7.3: New formats — CSV, JSON, HTML
  7.4: Portfolio reports (multi-company aggregate)
  7.5: Scheduled report support (via Celery beat)
  7.6: ReportExport tracking
  7.7: MinIO / S3 upload support
"""
from __future__ import annotations

import csv
import io
import json
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Company, FinancialData, RiskScore, ESGScore,
    CompanyPerson, CourtCase, PublicContract, ReportExport,
    MonitoredPortfolio, PortfolioCompany,
)
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

ALL_SECTIONS = ["general", "financial", "risk", "esg", "persons", "legal", "contracts"]


def _dec(v) -> float:
    if v is None:
        return 0.0
    return float(v)


class ReportService:
    """Generate PDF, Excel, CSV, JSON, HTML reports (v2)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ================================================================
    # Helper: fetch all company data in one pass
    # ================================================================

    async def _load_company_data(self, company_id: int, sections: list[str]) -> dict:
        """Load all needed data for a company report."""
        data: dict = {}

        result = await self.db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        data["company"] = company

        if "financial" in sections:
            r = await self.db.execute(
                select(FinancialData)
                .where(FinancialData.company_id == company_id)
                .order_by(FinancialData.an_fiscal.desc())
                .limit(10)
            )
            data["financials"] = r.scalars().all()

        if "risk" in sections:
            r = await self.db.execute(
                select(RiskScore)
                .where(RiskScore.company_id == company_id)
                .order_by(RiskScore.calculat_la.desc())
                .limit(5)
            )
            data["risks"] = r.scalars().all()

        if "esg" in sections:
            r = await self.db.execute(
                select(ESGScore)
                .where(ESGScore.company_id == company_id)
                .order_by(ESGScore.calculat_la.desc())
                .limit(5)
            )
            data["esg_scores"] = r.scalars().all()

        if "persons" in sections:
            r = await self.db.execute(
                select(CompanyPerson)
                .where(CompanyPerson.company_id == company_id)
                .order_by(CompanyPerson.tip, CompanyPerson.nume_complet)
            )
            data["persons"] = r.scalars().all()

        if "legal" in sections:
            r = await self.db.execute(
                select(CourtCase)
                .where(CourtCase.company_id == company_id)
                .order_by(CourtCase.ultima_actualizare.desc())
                .limit(20)
            )
            data["court_cases"] = r.scalars().all()

        if "contracts" in sections:
            r = await self.db.execute(
                select(PublicContract)
                .where(PublicContract.company_id == company_id)
                .order_by(PublicContract.data_atribuire.desc())
                .limit(20)
            )
            data["contracts"] = r.scalars().all()

        return data

    # ================================================================
    # 7.1: Complete PDF generation
    # ================================================================

    async def generate_company_pdf(
        self,
        company_id: int,
        sections: list[str],
    ) -> bytes:
        """Generate comprehensive company profile PDF with all sections."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        data = await self._load_company_data(company_id, sections)
        company = data["company"]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        story = []

        # ── Title ──
        story.append(Paragraph(f"Raport Companie: {company.denumire}", styles["Title"]))
        story.append(Paragraph(
            f"CUI: {company.cui} | Generat: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}",
            styles["Normal"],
        ))
        story.append(Spacer(1, 12))

        tbl_style = TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
        header_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.7)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ])

        # ── General Info ──
        if "general" in sections:
            story.append(Paragraph("Informații Generale", styles["Heading1"]))
            info_rows = [
                ["Denumire", company.denumire],
                ["CUI", str(company.cui)],
                ["Nr. Reg. Com.", company.j_nr or "N/A"],
                ["Județul", company.judet or "N/A"],
                ["Localitate", company.localitate or "N/A"],
                ["Adresa", company.adresa_completa or "N/A"],
                ["Cod CAEN", company.caen_principal or "N/A"],
                ["Stare Firmă", company.stare or "N/A"],
                ["Plătitor TVA", "Da" if company.platitor_tva else "Nu"],
                ["Data Înf.", str(company.data_infiintare) if company.data_infiintare else "N/A"],
            ]
            t = Table(info_rows, colWidths=[5 * cm, 11 * cm])
            t.setStyle(tbl_style)
            story.append(t)
            story.append(Spacer(1, 12))

        # ── Financial Data ──
        if "financial" in sections:
            story.append(Paragraph("Date Financiare", styles["Heading1"]))
            financials = data.get("financials", [])
            if financials:
                rows = [["An", "Cifră Afaceri", "Profit Net", "Angajați", "Total Active", "Datorii"]]
                for f in financials:
                    rows.append([
                        str(f.an_fiscal),
                        f"{_dec(f.cifra_afaceri):,.0f} RON",
                        f"{_dec(f.profit_net):,.0f} RON",
                        str(f.nr_angajati or "N/A"),
                        f"{_dec(f.total_active):,.0f} RON",
                        f"{_dec(f.total_datorii):,.0f} RON",
                    ])
                t = Table(rows)
                t.setStyle(header_style)
                story.append(t)
            else:
                story.append(Paragraph("Nu sunt date financiare disponibile.", styles["Normal"]))
            story.append(Spacer(1, 12))

        # ── Risk Score ──
        if "risk" in sections:
            story.append(Paragraph("Scor de Risc", styles["Heading1"]))
            risks = data.get("risks", [])
            if risks:
                risk = risks[0]  # latest
                risk_rows = [
                    ["Scor Total", f"{_dec(risk.score):.1f} / 100"],
                    ["Categorie", risk.rating or "N/A"],
                    ["Financiar", f"{_dec(risk.scor_financiar):.1f}"],
                    ["Legal", f"{_dec(risk.scor_legal):.1f}"],
                    ["Fiscal", f"{_dec(risk.scor_fiscal):.1f}"],
                    ["Comportamental", f"{_dec(risk.scor_comportamental):.1f}"],
                ]
                t = Table(risk_rows, colWidths=[5 * cm, 11 * cm])
                t.setStyle(tbl_style)
                story.append(t)

                if len(risks) > 1:
                    story.append(Spacer(1, 6))
                    story.append(Paragraph("Istoric scor:", styles["Heading3"]))
                    hist = [["Data", "Scor", "Rating"]]
                    for r in risks:
                        hist.append([
                            r.calculat_la.strftime("%d.%m.%Y") if r.calculat_la else "N/A",
                            f"{_dec(r.score):.1f}",
                            r.rating or "N/A",
                        ])
                    t2 = Table(hist)
                    t2.setStyle(header_style)
                    story.append(t2)
            else:
                story.append(Paragraph("Scor de risc nedisponibil.", styles["Normal"]))
            story.append(Spacer(1, 12))

        # ── ESG Score ──
        if "esg" in sections:
            story.append(Paragraph("Scor ESG", styles["Heading1"]))
            esg_list = data.get("esg_scores", [])
            if esg_list:
                esg = esg_list[0]
                esg_rows = [
                    ["Scor Compozit", f"{_dec(esg.score_total):.1f} / 100"],
                    ["Environmental", f"{_dec(esg.score_e):.1f}"],
                    ["Social", f"{_dec(esg.score_s):.1f}"],
                    ["Governance", f"{_dec(esg.score_g):.1f}"],
                    ["SFDR", esg.sfdr_categoria or "N/A"],
                ]
                t = Table(esg_rows, colWidths=[5 * cm, 11 * cm])
                t.setStyle(tbl_style)
                story.append(t)
            else:
                story.append(Paragraph("Scor ESG nedisponibil.", styles["Normal"]))
            story.append(Spacer(1, 12))

        # ── 7.1: Persons / Associates / Administrators ──
        if "persons" in sections:
            story.append(Paragraph("Persoane Asociate", styles["Heading1"]))
            persons = data.get("persons", [])
            if persons:
                rows = [["Nume", "Tip Relație", "Funcție", "Procent"]]
                for p in persons:
                    rows.append([
                        p.nume_complet or "N/A",
                        p.tip or "N/A",
                        p.tip or "N/A",
                        f"{_dec(p.procent_parti)}%" if p.procent_parti else "N/A",
                    ])
                t = Table(rows)
                t.setStyle(header_style)
                story.append(t)
            else:
                story.append(Paragraph("Nicio persoană asociată.", styles["Normal"]))
            story.append(Spacer(1, 12))

        # ── 7.1: Court Cases / Legal ──
        if "legal" in sections:
            story.append(Paragraph("Dosare Judiciare", styles["Heading1"]))
            cases = data.get("court_cases", [])
            if cases:
                rows = [["Nr. Dosar", "Instanță", "Materie", "Stadiu"]]
                for c in cases:
                    rows.append([
                        c.nr_dosar or "N/A",
                        c.instanta or "N/A",
                        c.materie or "N/A",
                        c.stadiu or "N/A",
                    ])
                t = Table(rows)
                t.setStyle(header_style)
                story.append(t)
            else:
                story.append(Paragraph("Niciun dosar judiciar.", styles["Normal"]))
            story.append(Spacer(1, 12))

        # ── 7.1: Public Contracts ──
        if "contracts" in sections:
            story.append(Paragraph("Contracte Publice (SEAP)", styles["Heading1"]))
            contracts = data.get("contracts", [])
            if contracts:
                rows = [["Titlu", "Autoritate", "Valoare", "Data"]]
                for c in contracts:
                    rows.append([
                        (c.titlu_contract or "N/A")[:60],
                        (c.autoritate_contractanta or "N/A")[:40],
                        f"{_dec(c.valoare_ron):,.0f} RON" if c.valoare_ron else "N/A",
                        c.data_atribuire.strftime("%d.%m.%Y") if c.data_atribuire else "N/A",
                    ])
                t = Table(rows)
                t.setStyle(header_style)
                story.append(t)
            else:
                story.append(Paragraph("Niciun contract public.", styles["Normal"]))
            story.append(Spacer(1, 12))

        # ── Footer ──
        story.append(Spacer(1, 24))
        story.append(Paragraph(
            "Generat de RomBiz Intelligence — Toate datele provin din surse publice oficiale.",
            styles["Normal"],
        ))

        doc.build(story)
        return buffer.getvalue()

    # ================================================================
    # 7.2: Complete Excel generation
    # ================================================================

    async def generate_company_excel(
        self,
        company_id: int,
        sections: list[str],
    ) -> bytes:
        """Generate Excel report with dedicated sheets per section."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        data = await self._load_company_data(company_id, sections)
        company = data["company"]

        wb = Workbook()
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="336699", end_color="336699", fill_type="solid")

        def _write_header(ws, headers):
            ws.append(headers)
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

        # ── General ──
        ws = wb.active
        ws.title = "General"
        ws.append(["Câmp", "Valoare"])
        ws.append(["Denumire", company.denumire])
        ws.append(["CUI", company.cui])
        ws.append(["Nr. Reg. Com.", company.j_nr])
        ws.append(["Județ", company.judet])
        ws.append(["Localitate", company.localitate])
        ws.append(["Adresa", company.adresa_completa])
        ws.append(["CAEN", company.caen_principal])
        ws.append(["Stare", company.stare])
        ws.append(["Plătitor TVA", "Da" if company.platitor_tva else "Nu"])
        ws.append(["Data Înființare", str(company.data_infiintare) if company.data_infiintare else "N/A"])
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        # ── Financial ──
        if "financial" in sections:
            ws_fin = wb.create_sheet("Financiar")
            _write_header(ws_fin, [
                "An", "Cifră Afaceri", "Profit Net", "Angajați",
                "Total Active", "Datorii Totale", "Capitaluri Proprii",
            ])
            for f in data.get("financials", []):
                ws_fin.append([
                    f.an_fiscal,
                    _dec(f.cifra_afaceri),
                    _dec(f.profit_net),
                    f.nr_angajati,
                    _dec(f.total_active),
                    _dec(f.total_datorii),
                    _dec(f.capitaluri_prop),
                ])

        # ── 7.2: Risk ──
        if "risk" in sections:
            ws_risk = wb.create_sheet("Risc")
            _write_header(ws_risk, [
                "Data Calcul", "Scor Total", "Rating",
                "Financiar", "Legal", "Fiscal", "Comportamental",
            ])
            for r in data.get("risks", []):
                ws_risk.append([
                    r.calculat_la.strftime("%d.%m.%Y") if r.calculat_la else "N/A",
                    _dec(r.score),
                    r.rating,
                    _dec(r.scor_financiar),
                    _dec(r.scor_legal),
                    _dec(r.scor_fiscal),
                    _dec(r.scor_comportamental),
                ])

        # ── 7.2: ESG ──
        if "esg" in sections:
            ws_esg = wb.create_sheet("ESG")
            _write_header(ws_esg, [
                "Data Calcul", "Scor Total", "E", "S", "G", "SFDR",
            ])
            for e in data.get("esg_scores", []):
                ws_esg.append([
                    e.calculat_la.strftime("%d.%m.%Y") if e.calculat_la else "N/A",
                    _dec(e.score_total),
                    _dec(e.score_e),
                    _dec(e.score_s),
                    _dec(e.score_g),
                    e.sfdr_categoria,
                ])

        # ── 7.2: Persons ──
        if "persons" in sections:
            ws_pers = wb.create_sheet("Persoane")
            _write_header(ws_pers, ["Nume", "Tip", "Procent", "Stare"])
            for p in data.get("persons", []):
                ws_pers.append([
                    p.nume_complet,
                    p.tip,
                    _dec(p.procent_parti) if p.procent_parti else None,
                    "Activ" if p.activ else "Inactiv",
                ])

        # ── 7.2: Court Cases ──
        if "legal" in sections:
            ws_court = wb.create_sheet("Dosare")
            _write_header(ws_court, ["Nr. Dosar", "Instanță", "Materie", "Stadiu", "Ultima Modif."])
            for c in data.get("court_cases", []):
                ws_court.append([
                    c.nr_dosar,
                    c.instanta,
                    c.materie,
                    c.stadiu,
                    c.ultima_actualizare.strftime("%d.%m.%Y") if c.ultima_actualizare else None,
                ])

        # ── 7.2: Contracts ──
        if "contracts" in sections:
            ws_contr = wb.create_sheet("Contracte")
            _write_header(ws_contr, ["Titlu", "Autoritate", "Valoare RON", "Data", "Tip"])
            for c in data.get("contracts", []):
                ws_contr.append([
                    c.titlu_contract,
                    c.autoritate_contractanta,
                    _dec(c.valoare_ron) if c.valoare_ron else None,
                    c.data_atribuire.strftime("%d.%m.%Y") if c.data_atribuire else None,
                    c.tip_procedura,
                ])

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    # ================================================================
    # 7.3: CSV Export
    # ================================================================

    async def generate_company_csv(self, company_id: int, section: str = "financial") -> bytes:
        """Generate CSV for a single section."""
        data = await self._load_company_data(company_id, [section])
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        if section == "financial":
            writer.writerow(["An", "Cifra Afaceri", "Profit Net", "Angajati", "Total Active", "Datorii"])
            for f in data.get("financials", []):
                writer.writerow([
                    f.an_fiscal, _dec(f.cifra_afaceri), _dec(f.profit_net),
                    f.nr_angajati, _dec(f.total_active), _dec(f.total_datorii),
                ])
        elif section == "persons":
            writer.writerow(["Nume", "Tip Relatie", "Functie", "Procent"])
            for p in data.get("persons", []):
                writer.writerow([p.nume_complet, p.tip, p.tip, _dec(p.procent_parti)])
        elif section == "legal":
            writer.writerow(["Nr Dosar", "Instanta", "Materie", "Stadiu"])
            for c in data.get("court_cases", []):
                writer.writerow([c.nr_dosar, c.instanta, c.materie, c.stadiu])
        elif section == "contracts":
            writer.writerow(["Titlu", "Autoritate", "Valoare RON", "Data"])
            for c in data.get("contracts", []):
                writer.writerow([
                    c.titlu_contract, c.autoritate_contractanta,
                    _dec(c.valoare_ron), c.data_atribuire,
                ])

        return buffer.getvalue().encode("utf-8-sig")

    # ================================================================
    # 7.3: JSON Export
    # ================================================================

    async def generate_company_json(self, company_id: int, sections: list[str]) -> bytes:
        """Generate JSON export with all requested sections."""
        data = await self._load_company_data(company_id, sections)
        company = data["company"]

        result: dict = {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "RomBiz Intelligence",
            },
            "company": {
                "cui": company.cui,
                "denumire": company.denumire,
                "j_nr": company.j_nr,
                "judet": company.judet,
                "localitate": company.localitate,
                "adresa": company.adresa_completa,
                "caen": company.caen_principal,
                "stare": company.stare,
                "platitor_tva": company.platitor_tva,
                "data_infiintare": str(company.data_infiintare) if company.data_infiintare else None,
            },
        }

        if "financial" in sections:
            result["financials"] = [
                {
                    "an": f.an_fiscal, "cifra_afaceri": _dec(f.cifra_afaceri),
                    "profit_net": _dec(f.profit_net), "angajati": f.nr_angajati,
                    "total_active": _dec(f.total_active), "datorii": _dec(f.total_datorii),
                }
                for f in data.get("financials", [])
            ]

        if "risk" in sections and data.get("risks"):
            r = data["risks"][0]
            result["risk"] = {
                "score": _dec(r.score), "rating": r.rating,
                "financiar": _dec(r.scor_financiar), "legal": _dec(r.scor_legal),
                "fiscal": _dec(r.scor_fiscal), "comportamental": _dec(r.scor_comportamental),
            }

        if "esg" in sections and data.get("esg_scores"):
            e = data["esg_scores"][0]
            result["esg"] = {
                "score_total": _dec(e.score_total), "e": _dec(e.score_e),
                "s": _dec(e.score_s), "g": _dec(e.score_g),
                "sfdr": e.sfdr_categoria,
            }

        if "persons" in sections:
            result["persons"] = [
                {"nume": p.nume_complet, "tip": p.tip, "procent": _dec(p.procent_parti)}
                for p in data.get("persons", [])
            ]

        if "legal" in sections:
            result["court_cases"] = [
                {"numar": c.nr_dosar, "instanta": c.instanta, "materie": c.materie, "stadiu": c.stadiu}
                for c in data.get("court_cases", [])
            ]

        if "contracts" in sections:
            result["contracts"] = [
                {
                    "titlu": c.titlu_contract, "autoritate": c.autoritate_contractanta,
                    "valoare_ron": _dec(c.valoare_ron), "data": str(c.data_atribuire) if c.data_atribuire else None,
                }
                for c in data.get("contracts", [])
            ]

        return json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")

    # ================================================================
    # 7.3: HTML Export
    # ================================================================

    async def generate_company_html(self, company_id: int, sections: list[str]) -> bytes:
        """Generate a standalone HTML report."""
        data = await self._load_company_data(company_id, sections)
        company = data["company"]

        parts = [
            "<!DOCTYPE html><html lang='ro'><head><meta charset='utf-8'>",
            f"<title>Raport {company.denumire}</title>",
            "<style>body{font-family:Arial,sans-serif;margin:2em}table{border-collapse:collapse;width:100%;margin:1em 0}"
            "th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}th{background:#336699;color:#fff}"
            "h1{color:#336699}h2{color:#555;border-bottom:2px solid #336699;padding-bottom:4px}.footer{margin-top:2em;color:#999;font-size:0.85em}</style>",
            "</head><body>",
            f"<h1>Raport: {company.denumire}</h1>",
            f"<p>CUI: {company.cui} | Generat: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}</p>",
        ]

        if "general" in sections:
            parts.append("<h2>Informații Generale</h2><table>")
            for label, val in [
                ("Denumire", company.denumire), ("CUI", company.cui),
                ("CAEN", company.caen_principal), ("Județ", company.judet),
                ("Stare", company.stare), ("TVA", "Da" if company.platitor_tva else "Nu"),
            ]:
                parts.append(f"<tr><th>{label}</th><td>{val or 'N/A'}</td></tr>")
            parts.append("</table>")

        if "financial" in sections:
            parts.append("<h2>Date Financiare</h2><table>")
            parts.append("<tr><th>An</th><th>Cifră Afaceri</th><th>Profit Net</th><th>Angajați</th></tr>")
            for f in data.get("financials", []):
                parts.append(
                    f"<tr><td>{f.an_fiscal}</td><td>{_dec(f.cifra_afaceri):,.0f} RON</td>"
                    f"<td>{_dec(f.profit_net):,.0f} RON</td><td>{f.nr_angajati or 'N/A'}</td></tr>"
                )
            parts.append("</table>")

        if "persons" in sections:
            parts.append("<h2>Persoane Asociate</h2><table>")
            parts.append("<tr><th>Nume</th><th>Tip</th><th>Funcție</th><th>Procent</th></tr>")
            for p in data.get("persons", []):
                parts.append(
                    f"<tr><td>{p.nume_complet}</td><td>{p.tip}</td>"
                    f"<td>{p.tip or 'N/A'}</td><td>{_dec(p.procent_parti)}%</td></tr>"
                )
            parts.append("</table>")

        if "legal" in sections:
            parts.append("<h2>Dosare Judiciare</h2><table>")
            parts.append("<tr><th>Nr. Dosar</th><th>Instanță</th><th>Materie</th><th>Stadiu</th></tr>")
            for c in data.get("court_cases", []):
                parts.append(
                    f"<tr><td>{c.nr_dosar}</td><td>{c.instanta}</td>"
                    f"<td>{c.materie}</td><td>{c.stadiu}</td></tr>"
                )
            parts.append("</table>")

        if "contracts" in sections:
            parts.append("<h2>Contracte Publice</h2><table>")
            parts.append("<tr><th>Titlu</th><th>Autoritate</th><th>Valoare</th><th>Data</th></tr>")
            for c in data.get("contracts", []):
                parts.append(
                    f"<tr><td>{c.titlu_contract}</td><td>{c.autoritate_contractanta}</td>"
                    f"<td>{_dec(c.valoare_ron):,.0f} RON</td><td>{c.data_atribuire or 'N/A'}</td></tr>"
                )
            parts.append("</table>")

        parts.append("<p class='footer'>Generat de RomBiz Intelligence — Date din surse publice oficiale.</p>")
        parts.append("</body></html>")

        return "\n".join(parts).encode("utf-8")

    # ================================================================
    # 7.4: Portfolio Reports
    # ================================================================

    async def generate_portfolio_pdf(self, portfolio_id: int, user_id: str) -> bytes:
        """Generate aggregate portfolio PDF report."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        # Get portfolio and its companies
        port_result = await self.db.execute(
            select(MonitoredPortfolio).where(MonitoredPortfolio.id == portfolio_id)
        )
        portfolio = port_result.scalar_one_or_none()
        if not portfolio:
            raise ValueError("Portfolio not found")

        pc_result = await self.db.execute(
            select(PortfolioCompany.company_id)
            .where(PortfolioCompany.portfolio_id == portfolio_id)
        )
        company_ids = [r.company_id for r in pc_result.all()]

        # Fetch companies with latest financials and risk
        companies = []
        for cid in company_ids:
            cr = await self.db.execute(select(Company).where(Company.id == cid))
            comp = cr.scalar_one_or_none()
            if not comp:
                continue

            fr = await self.db.execute(
                select(FinancialData).where(FinancialData.company_id == cid)
                .order_by(FinancialData.an_fiscal.desc()).limit(1)
            )
            fin = fr.scalar_one_or_none()

            rr = await self.db.execute(
                select(RiskScore).where(RiskScore.company_id == cid)
                .order_by(RiskScore.calculat_la.desc()).limit(1)
            )
            risk = rr.scalar_one_or_none()

            companies.append({"company": comp, "fin": fin, "risk": risk})

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2 * cm, leftMargin=2 * cm,
                                topMargin=2 * cm, bottomMargin=2 * cm)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Raport Portofoliu: {portfolio.name}", styles["Title"]))
        story.append(Paragraph(
            f"Companii: {len(companies)} | Generat: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}",
            styles["Normal"],
        ))
        story.append(Spacer(1, 12))

        # Summary table
        rows = [["Companie", "CUI", "Județ", "Cifră Afaceri", "Angajați", "Risc"]]
        total_ca = 0.0
        total_emp = 0
        for item in companies:
            c = item["company"]
            f = item["fin"]
            r = item["risk"]
            ca = _dec(f.cifra_afaceri) if f else 0
            emp = f.nr_angajati or 0 if f else 0
            total_ca += ca
            total_emp += emp
            rows.append([
                c.denumire[:40],
                str(c.cui),
                c.judet or "N/A",
                f"{ca:,.0f} RON",
                str(emp),
                r.rating if r else "N/A",
            ])
        rows.append(["TOTAL", "", "", f"{total_ca:,.0f} RON", str(total_emp), ""])

        t = Table(rows)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.7)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ]))
        story.append(t)

        story.append(Spacer(1, 24))
        story.append(Paragraph("Generat de RomBiz Intelligence.", styles["Normal"]))
        doc.build(story)
        return buffer.getvalue()

    async def generate_portfolio_excel(self, portfolio_id: int, user_id: str) -> bytes:
        """Generate portfolio Excel with summary and per-company sheets."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        port_result = await self.db.execute(
            select(MonitoredPortfolio).where(MonitoredPortfolio.id == portfolio_id)
        )
        portfolio = port_result.scalar_one_or_none()
        if not portfolio:
            raise ValueError("Portfolio not found")

        pc_result = await self.db.execute(
            select(PortfolioCompany.company_id)
            .where(PortfolioCompany.portfolio_id == portfolio_id)
        )
        company_ids = [r.company_id for r in pc_result.all()]

        wb = Workbook()
        ws = wb.active
        ws.title = "Sumar"
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="336699", end_color="336699", fill_type="solid")

        headers = ["Companie", "CUI", "Județ", "Cifră Afaceri", "Profit", "Angajați", "Risc", "ESG"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        for cid in company_ids:
            cr = await self.db.execute(select(Company).where(Company.id == cid))
            c = cr.scalar_one_or_none()
            if not c:
                continue
            fr = await self.db.execute(
                select(FinancialData).where(FinancialData.company_id == cid)
                .order_by(FinancialData.an_fiscal.desc()).limit(1)
            )
            fin = fr.scalar_one_or_none()
            rr = await self.db.execute(
                select(RiskScore).where(RiskScore.company_id == cid)
                .order_by(RiskScore.calculat_la.desc()).limit(1)
            )
            risk = rr.scalar_one_or_none()
            er = await self.db.execute(
                select(ESGScore).where(ESGScore.company_id == cid)
                .order_by(ESGScore.calculat_la.desc()).limit(1)
            )
            esg = er.scalar_one_or_none()

            ws.append([
                c.denumire,
                c.cui,
                c.judet,
                _dec(fin.cifra_afaceri) if fin else 0,
                _dec(fin.profit_net) if fin else 0,
                fin.nr_angajati if fin else 0,
                risk.rating if risk else "N/A",
                _dec(esg.score_total) if esg else 0,
            ])

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    # ================================================================
    # 7.6: Track export status
    # ================================================================

    async def update_export_status(
        self, export_id: int, status: str, file_url: str = None
    ):
        """Update a ReportExport record status."""
        result = await self.db.execute(
            select(ReportExport).where(ReportExport.id == export_id)
        )
        export = result.scalar_one_or_none()
        if export:
            export.status = status
            if file_url:
                export.file_url = file_url
            await self.db.flush()

    # ================================================================
    # 7.7: MinIO / S3 upload
    # ================================================================

    async def upload_to_minio(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        bucket: str | None = None,
    ) -> str:
        """Upload file bytes to MinIO and return the presigned URL."""
        try:
            from minio import Minio
        except ImportError:
            logger.warning("minio package not installed, skipping upload")
            return ""

        bucket_name = bucket or settings.MINIO_BUCKET_REPORTS
        object_name = f"{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{uuid.uuid4().hex}_{filename}"

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        # Ensure bucket exists
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # Upload
        data_stream = io.BytesIO(file_data)
        client.put_object(
            bucket_name,
            object_name,
            data_stream,
            length=len(file_data),
            content_type=content_type,
        )

        # Generate presigned URL (valid 7 days)
        from datetime import timedelta
        url = client.presigned_get_object(bucket_name, object_name, expires=timedelta(days=7))
        logger.info("uploaded_to_minio", object_name=object_name, bucket=bucket_name, size=len(file_data))
        return url

    async def generate_and_upload(
        self,
        company_id: int,
        fmt: str = "pdf",
        export_id: int | None = None,
    ) -> dict:
        """Generate a report and upload it to MinIO. Updates export record if provided."""
        content_type_map = {
            "pdf": "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json",
            "html": "text/html",
        }

        # Generate the report
        if fmt == "pdf":
            data = await self.generate_pdf(company_id)
        elif fmt == "xlsx":
            data = await self.generate_excel(company_id)
        elif fmt == "csv":
            data = await self.generate_csv(company_id)
        elif fmt == "json":
            data = await self.generate_json_export(company_id)
            data = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        elif fmt == "html":
            data = await self.generate_html(company_id)
            if isinstance(data, str):
                data = data.encode("utf-8")
        else:
            return {"error": f"Format necunoscut: {fmt}"}

        filename = f"report_{company_id}.{fmt}"
        ct = content_type_map.get(fmt, "application/octet-stream")

        file_url = await self.upload_to_minio(data, filename, content_type=ct)

        if export_id and file_url:
            await self.update_export_status(export_id, "completed", file_url)

        return {
            "company_id": company_id,
            "format": fmt,
            "file_url": file_url,
            "size_bytes": len(data),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
