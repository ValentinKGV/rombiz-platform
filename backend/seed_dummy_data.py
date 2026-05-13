"""
Seed realistic dummy data for manual testing of the RomBiz platform.
Run with: python seed_dummy_data.py
"""
import asyncio
import uuid
import random
import secrets
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal


async def main():
    from app.core.database import engine, Base, AsyncSessionLocal
    from app.models import models  # noqa: F401
    from app.core.security import hash_password
    from sqlalchemy import select, text

    print("=" * 60)
    print("  RomBiz — Seed Dummy Data for Testing")
    print("=" * 60)

    # Create all tables
    print("\n[1/10] Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓ Tables created")

    async with AsyncSessionLocal() as session:
        # ── Check if data already exists ──
        result = await session.execute(select(models.Company).limit(1))
        if result.scalar_one_or_none():
            print("\n  ⚠ Dummy data already exists. Delete rombiz_dev.db to re-seed.")
            return

        # ══════════════════════════════════════════════════════════
        # ORGANIZATION & USERS
        # ══════════════════════════════════════════════════════════
        print("\n[2/10] Creating organizations & users...")

        # Deterministic UUIDs so re-seeding doesn't invalidate existing JWT sessions
        org_id = uuid.UUID("00000000-0000-4000-a000-000000000001")

        # Check if org already exists
        existing_org = await session.execute(
            select(models.Organization).where(models.Organization.id == str(org_id))
        )
        if not existing_org.scalar_one_or_none():
            org = models.Organization(
                id=org_id,
                name="Nine International Group",
                cui="12345678",
                email="demo@rombiz.ro",
                subscription_plan="ENTERPRISE",
                subscription_status="ACTIVE",
                monthly_api_calls=0,
                api_calls_limit=10000,
            )
            session.add(org)
            await session.flush()
            print(f"  ✓ Organization created: Nine International Group")
        else:
            print(f"  ⏩ Organization already exists, skipping")

        admin_id = uuid.UUID("00000000-0000-4000-a000-000000000010")
        analyst_id = uuid.UUID("00000000-0000-4000-a000-000000000020")
        viewer_id = uuid.UUID("00000000-0000-4000-a000-000000000030")

        users_data = [
            (admin_id, "admin@rombiz.ro", "Admin123!", "Alexandru", "Popescu", "admin"),
            (analyst_id, "analyst@rombiz.ro", "Analyst123!", "Maria", "Ionescu", "analyst"),
            (viewer_id, "viewer@rombiz.ro", "Viewer123!", "George", "Dumitrescu", "viewer"),
        ]
        actual_user_ids = {}
        for uid, email, pwd, fn, ln, role in users_data:
            existing_user_result = await session.execute(
                select(models.User).where(models.User.email == email)
            )
            existing_user = existing_user_result.scalar_one_or_none()
            if not existing_user:
                new_user = models.User(
                    id=uid, org_id=org_id, email=email,
                    password_hash=hash_password(pwd),
                    first_name=fn, last_name=ln,
                    role=role, is_active=True, email_verified=True,
                )
                session.add(new_user)
                actual_user_ids[email] = uid
                print(f"  ✓ User created: {email} / {pwd}")
            else:
                actual_user_ids[email] = uuid.UUID(str(existing_user.id))
                existing_user.org_id = str(org_id)
                print(f"  ⏩ User {email} exists (id={existing_user.id}), reusing & linking to org")
        await session.flush()

        # Use real IDs for FK references throughout seed
        admin_id = actual_user_ids.get("admin@rombiz.ro", admin_id)
        analyst_id = actual_user_ids.get("analyst@rombiz.ro", analyst_id)
        viewer_id = actual_user_ids.get("viewer@rombiz.ro", viewer_id)
        print(f"  ✓ Users ready: admin@rombiz.ro / Admin123!")
        print(f"           analyst@rombiz.ro / Analyst123!")
        print(f"           viewer@rombiz.ro / Viewer123!")

        # ══════════════════════════════════════════════════════════
        # COMPANIES — 20 realistic Romanian companies
        # ══════════════════════════════════════════════════════════
        print("\n[3/10] Creating companies...")

        companies_data = [
            # (cui, denumire, forma_juridica, caen, judet, localitate, capital, stare, data_inf, platitor_tva)
            (14399840, "DEDEMAN SRL", "SRL", "4752", "Bacău", "Bacău", Decimal("50000000.00"), "ACTIVA", date(1992, 7, 15), True),
            (6563869, "EMAG TECHNOLOGY SRL", "SRL", "4791", "București", "Sector 1", Decimal("200000.00"), "ACTIVA", date(1992, 2, 10), True),
            (18189442, "ALTEX ROMANIA SRL", "SRL", "4743", "București", "Sector 3", Decimal("2000000.00"), "ACTIVA", date(2005, 10, 1), True),
            (1590082, "PETROM SA", "SA", "0610", "București", "Sector 1", Decimal("5664410834.00"), "ACTIVA", date(1991, 3, 20), True),
            (1553483, "AUTOMOBILE DACIA SA", "SA", "2910", "Argeș", "Mioveni", Decimal("2542664460.00"), "ACTIVA", date(1990, 12, 5), True),
            (30834857, "KAUFLAND ROMANIA SCS", "SRL", "4711", "București", "Sector 2", Decimal("500000000.00"), "ACTIVA", date(2004, 6, 15), True),
            (18505009, "LIDL DISCOUNT SRL", "SRL", "4711", "București", "Sector 1", Decimal("100000000.00"), "ACTIVA", date(2002, 9, 20), True),
            (6328953, "CARREFOUR ROMANIA SA", "SA", "4711", "București", "Sector 6", Decimal("43952980.00"), "ACTIVA", date(1994, 5, 12), True),
            (15622207, "TRANSGAZ SA", "SA", "4950", "Sibiu", "Mediaș", Decimal("117738440.00"), "ACTIVA", date(2000, 11, 1), True),
            (13549838, "ELECTRICA SA", "SA", "3514", "București", "Sector 1", Decimal("3464435970.00"), "ACTIVA", date(2000, 7, 10), True),
            (30302207, "TECH SOLUTIONS ROMANIA SRL", "SRL", "6201", "Cluj", "Cluj-Napoca", Decimal("10000.00"), "ACTIVA", date(2012, 3, 15), True),
            (41234567, "CONSTRUCTII MODERNE SRL", "SRL", "4120", "Timiș", "Timișoara", Decimal("500000.00"), "ACTIVA", date(2018, 6, 1), True),
            (32456789, "AGRO INVEST SRL", "SRL", "0111", "Iași", "Iași", Decimal("200000.00"), "ACTIVA", date(2014, 4, 20), False),
            (27891234, "PHARMA CARE SRL", "SRL", "4773", "Brașov", "Brașov", Decimal("50000.00"), "ACTIVA", date(2010, 8, 10), True),
            (38765432, "TRANSPORT EXPRESS SRL", "SRL", "4941", "Constanța", "Constanța", Decimal("100000.00"), "ACTIVA", date(2016, 1, 25), True),
            (19876543, "HOTEL REGAL SA", "SA", "5510", "Cluj", "Cluj-Napoca", Decimal("5000000.00"), "ACTIVA", date(2006, 11, 15), True),
            (25432198, "FINTECH INNOVATORS SRL", "SRL", "6419", "București", "Sector 1", Decimal("1000000.00"), "ACTIVA", date(2019, 5, 8), True),
            (11223344, "PRODUCTIE ALIMENTARA SA", "SA", "1071", "Mureș", "Târgu Mureș", Decimal("3000000.00"), "ACTIVA", date(1995, 3, 1), True),
            (44556677, "ENERGIE VERDE SRL", "SRL", "3511", "Sibiu", "Sibiu", Decimal("2000000.00"), "ACTIVA", date(2020, 2, 14), True),
            (99887766, "STAR IMPEX SRL", "SRL", "4690", "Galați", "Galați", Decimal("50000.00"), "RADIATA", date(2008, 6, 1), False),
        ]

        company_objs = []
        for i, (cui, den, fj, caen, jud, loc, cap, stare, di, ptva) in enumerate(companies_data):
            c = models.Company(
                cui=cui,
                denumire=den,
                forma_juridica=fj,
                j_nr=f"J{random.randint(1,40)}/{random.randint(100,9999)}/{di.year}",
                caen_principal=caen,
                judet=jud,
                localitate=loc,
                capital_social=cap,
                stare=stare,
                data_infiintare=di,
                platitor_tva=ptva,
                tva_la_incasare=(i % 5 == 0),
                split_tva=(i == 3),
                inactiv_fiscal=(stare == "RADIATA"),
                adresa_completa=f"Str. Exemplu nr. {random.randint(1,200)}, {loc}, {jud}",
                cod_postal=f"{random.randint(10,99)}{random.randint(1000,9999)}",
                lat=Decimal(f"{random.uniform(44.0, 47.5):.7f}"),
                lng=Decimal(f"{random.uniform(22.0, 28.5):.7f}"),
                has_insolvency=(i == 19),  # STAR IMPEX
                has_litigation=(i in [2, 5, 11, 14]),
                has_debts=(i in [11, 12, 19]),
                has_seap_contracts=(i in [0, 3, 4, 8, 9, 11]),
                has_eu_projects=(i in [10, 12, 18]),
                has_trademarks=(i in [0, 1, 4, 6]),
                data_quality_score=random.randint(40, 95),
                data_sources={"anaf": True, "onrc": True, "bpi": (i == 19)},
            )
            company_objs.append(c)

        session.add_all(company_objs)
        await session.flush()
        print(f"  ✓ {len(company_objs)} companies created")

        # ══════════════════════════════════════════════════════════
        # FINANCIAL DATA — 3 years per company
        # ══════════════════════════════════════════════════════════
        print("\n[4/10] Creating financial data (3 years × 20 companies)...")

        financials = []
        for comp in company_objs:
            base_ca = random.randint(500_000, 500_000_000)
            for year in [2022, 2023, 2024]:
                growth = Decimal(str(random.uniform(0.85, 1.25)))
                ca = int(base_ca * growth)
                profit = int(ca * Decimal(str(random.uniform(-0.05, 0.20))))
                total_active = int(ca * Decimal(str(random.uniform(0.5, 2.0))))
                total_datorii = int(total_active * Decimal(str(random.uniform(0.1, 0.7))))
                capitaluri = total_active - total_datorii

                f = models.FinancialData(
                    company_id=comp.id,
                    an_fiscal=year,
                    cifra_afaceri=ca,
                    profit_net=profit,
                    total_active=total_active,
                    total_datorii=total_datorii,
                    capitaluri_prop=capitaluri,
                    nr_angajati=random.randint(5, 15000),
                    rata_lichiditate=Decimal(str(round(random.uniform(0.5, 3.0), 4))),
                    grad_indatorare=Decimal(str(round(random.uniform(0.1, 0.8), 4))),
                    roa=Decimal(str(round(random.uniform(-0.05, 0.25), 4))),
                    roe=Decimal(str(round(random.uniform(-0.10, 0.35), 4))),
                    profit_margin=Decimal(str(round(random.uniform(-0.05, 0.20), 4))),
                    sursa="ANAF",
                )
                financials.append(f)
                base_ca = ca

        session.add_all(financials)
        await session.flush()
        print(f"  ✓ {len(financials)} financial records")

        # ══════════════════════════════════════════════════════════
        # COMPANY PERSONS — associates & administrators
        # ══════════════════════════════════════════════════════════
        print("\n[5/10] Creating company persons...")

        names = [
            "Andrei Popescu", "Maria Elena Ionescu", "Cristian Georgescu",
            "Ana Maria Radu", "Ion Vasilescu", "Elena Dumitrescu",
            "Mihai Constantinescu", "Daniela Stan", "Alexandru Marin",
            "Ioana Popa", "Stefan Dinu", "Gabriela Neagu",
            "Adrian Vlad", "Raluca Florea", "Bogdan Matei",
            "Simona Ciobanu", "Dragoș Cojocaru", "Laura Toma",
            "Cristina Preda", "Florin Badea",
        ]
        persons = []
        for comp in company_objs:
            # 1-3 associates
            n_assoc = random.randint(1, 3)
            remaining = Decimal("100.000")
            for j in range(n_assoc):
                if j == n_assoc - 1:
                    share = remaining
                else:
                    share = Decimal(str(round(random.uniform(10, float(remaining - 10)), 3)))
                    remaining -= share

                p = models.CompanyPerson(
                    company_id=comp.id,
                    tip="ASOCIAT",
                    nume_complet=random.choice(names),
                    procent_parti=share,
                    data_start=comp.data_infiintare,
                    activ=True,
                )
                persons.append(p)

            # 1 administrator
            admin_p = models.CompanyPerson(
                company_id=comp.id,
                tip="ADMINISTRATOR",
                nume_complet=random.choice(names),
                data_start=comp.data_infiintare,
                activ=True,
            )
            persons.append(admin_p)

        session.add_all(persons)
        await session.flush()
        print(f"  ✓ {len(persons)} company persons")

        # ══════════════════════════════════════════════════════════
        # RISK SCORES
        # ══════════════════════════════════════════════════════════
        print("\n[6/10] Creating risk scores...")

        risk_scores = []
        ratings_map = {range(1, 20): "E", range(20, 40): "D", range(40, 60): "C",
                       range(60, 80): "B", range(80, 101): "A"}
        for comp in company_objs:
            score = random.randint(10, 95) if comp.stare == "ACTIVA" else random.randint(1, 25)
            rating = "C"
            for rng, r in ratings_map.items():
                if score in rng:
                    rating = r
                    break

            rs = models.RiskScore(
                company_id=comp.id,
                score=score,
                rating=rating,
                scor_financiar=Decimal(str(round(random.uniform(10, 100), 2))),
                scor_legal=Decimal(str(round(random.uniform(10, 100), 2))),
                scor_fiscal=Decimal(str(round(random.uniform(10, 100), 2))),
                scor_comportamental=Decimal(str(round(random.uniform(10, 100), 2))),
                limita_credit=random.randint(10000, 5000000),
                probabilitate_insolventa=Decimal(str(round(random.uniform(0.01, 0.50), 4))),
                factori_risc={
                    "vechime_firma": f"{(date.today() - comp.data_infiintare).days // 365} ani",
                    "litigii_active": comp.has_litigation,
                    "datorii_restante": comp.has_debts,
                    "sector_risc": "mediu" if random.random() > 0.3 else "ridicat",
                },
                model_versiune="v2.1",
            )
            risk_scores.append(rs)

        session.add_all(risk_scores)
        await session.flush()
        print(f"  ✓ {len(risk_scores)} risk scores")

        # ══════════════════════════════════════════════════════════
        # ESG SCORES
        # ══════════════════════════════════════════════════════════
        print("\n[7/10] Creating ESG scores...")

        esg_scores = []
        esg_ratings = {range(0, 20): "E", range(20, 40): "D", range(40, 60): "C",
                       range(60, 80): "B", range(80, 101): "A"}
        for comp in company_objs:
            se = Decimal(str(round(random.uniform(15, 90), 2)))
            ss = Decimal(str(round(random.uniform(15, 90), 2)))
            sg = Decimal(str(round(random.uniform(15, 90), 2)))
            st = round((se + ss + sg) / 3, 2)
            esg_r = "C"
            for rng, r in esg_ratings.items():
                if int(st) in rng:
                    esg_r = r
                    break

            esg = models.ESGScore(
                company_id=comp.id,
                score_e=se,
                score_s=ss,
                score_g=sg,
                score_total=st,
                e_emisii_co2=Decimal(str(round(random.uniform(100, 50000), 2))),
                e_amenzi_mediu=Decimal(str(round(random.uniform(0, 100000), 2))) if random.random() > 0.7 else Decimal("0"),
                e_certificari_iso=random.random() > 0.5,
                s_stabilitate_angajati=Decimal(str(round(random.uniform(40, 95), 2))),
                s_salariu_vs_sector=Decimal(str(round(random.uniform(70, 130), 2))),
                s_litigii_munca=Decimal(str(round(random.uniform(0, 5), 2))),
                s_certificari_sociale=random.random() > 0.6,
                g_stabilitate_management=Decimal(str(round(random.uniform(30, 95), 2))),
                g_transparenta_actionariat=Decimal(str(round(random.uniform(20, 100), 2))),
                g_conformitate_fiscala=Decimal(str(round(random.uniform(50, 100), 2))),
                g_dosare_penale=Decimal(str(round(random.uniform(0, 3), 2))),
                esg_rating=esg_r,
                csrd_relevant=random.random() > 0.6,
                sfdr_categoria=random.choice(["Art.6", "Art.8", "Art.9", None]),
                surse_date={"anaf": True, "onrc": True, "auto_calc": True},
                metodologie_versiune="v1.3",
            )
            esg_scores.append(esg)

        session.add_all(esg_scores)
        await session.flush()
        print(f"  ✓ {len(esg_scores)} ESG scores")

        # ══════════════════════════════════════════════════════════
        # COURT CASES & HEARINGS
        # ══════════════════════════════════════════════════════════
        print("\n[8/10] Creating court cases, debts, contracts, alerts...")

        court_cases = []
        hearings = []
        litigation_companies = [c for c in company_objs if c.has_litigation]
        objects_litigiu = [
            "Pretenții comerciale", "Contestație executare silită",
            "Anulare act administrativ", "Litigiu muncă",
            "Insolvență", "Despăgubiri civile", "Reziliere contract",
            "Obligația de a face", "Acțiune în anulare",
        ]
        instante = [
            "Tribunalul București", "Tribunalul Cluj",
            "Tribunalul Timiș", "Judecătoria Sectorului 1",
            "Curtea de Apel București", "Tribunalul Constanța",
        ]

        dosar_counter = 1
        for comp in litigation_companies:
            n_cases = random.randint(1, 4)
            for _ in range(n_cases):
                dd = date(random.randint(2021, 2025), random.randint(1, 12), random.randint(1, 28))
                inst = random.choice(instante)
                nr_dosar = f"{dosar_counter}/{random.randint(100,999)}/{dd.year}"
                dosar_counter += 1

                cc = models.CourtCase(
                    company_id=comp.id,
                    nr_dosar=nr_dosar,
                    instanta=inst,
                    instanta_oras=inst.replace("Tribunalul ", "").replace("Judecătoria ", "").replace("Curtea de Apel ", ""),
                    obiect=random.choice(objects_litigiu),
                    materie=random.choice(["civil", "comercial", "contencios", "penal"]),
                    rol_firma=random.choice(["RECLAMANT", "PARAT"]),
                    parti={"reclamant": "SC Exemplu SRL", "parat": comp.denumire},
                    stadiu=random.choice(["Fond", "Apel", "Recurs", "Finalizat"]),
                    data_dosar=dd,
                    urmatorul_termen=dd + timedelta(days=random.randint(30, 180)) if random.random() > 0.3 else None,
                    source="PORTAL_JUST",
                )
                court_cases.append(cc)

        session.add_all(court_cases)
        await session.flush()

        # Add hearings
        for cc in court_cases:
            n_hearings = random.randint(1, 5)
            for h in range(n_hearings):
                hd = (cc.data_dosar or date(2023, 1, 1)) + timedelta(days=30 * (h + 1))
                hearing = models.LitigationHearing(
                    case_id=cc.id,
                    hearing_date=hd,
                    sala=f"Sala {random.randint(1, 20)}",
                    status=random.choice(["Programat", "Amânat", "Dezbatere", "Pronunțare"]),
                    outcome="Amânat pentru lipsă părți" if random.random() > 0.5 else None,
                )
                hearings.append(hearing)

        session.add_all(hearings)
        await session.flush()
        print(f"  ✓ {len(court_cases)} court cases, {len(hearings)} hearings")

        # ── COMPANY DEBTS ──
        debts = []
        for comp in company_objs:
            if comp.has_debts:
                for _ in range(random.randint(1, 3)):
                    d = models.CompanyDebt(
                        company_id=comp.id,
                        suma_restanta=Decimal(str(round(random.uniform(5000, 500000), 2))),
                        tip_datorie=random.choice([
                            "Impozit pe profit", "TVA", "Contribuții sociale",
                            "Impozit pe venit", "Amenzi fiscale",
                        ]),
                        data_raportare=date(2025, random.randint(1, 12), 1),
                        sursa="ANAF",
                    )
                    debts.append(d)

        session.add_all(debts)
        await session.flush()
        print(f"  ✓ {len(debts)} company debts")

        # ── PUBLIC CONTRACTS (SEAP) ──
        contracts = []
        seap_companies = [c for c in company_objs if c.has_seap_contracts]
        autoritati = [
            ("4267117", "Primăria Municipiului București"),
            ("4283045", "Ministerul Transporturilor"),
            ("4407795", "Ministerul Sănătății"),
            ("11983913", "Compania Națională de Autostrăzi"),
            ("13633330", "Ministerul Educației"),
        ]
        for comp in seap_companies:
            n_contracts = random.randint(1, 5)
            for _ in range(n_contracts):
                auto_cui, auto_name = random.choice(autoritati)
                val = Decimal(str(round(random.uniform(50000, 10000000), 2)))
                da = date(random.randint(2020, 2025), random.randint(1, 12), random.randint(1, 28))
                pc = models.PublicContract(
                    company_id=comp.id,
                    autoritate_contractanta_cui=auto_cui,
                    autoritate_contractanta=auto_name,
                    nr_contract=f"CN-{random.randint(10000, 99999)}",
                    titlu_contract=random.choice([
                        "Furnizare echipamente IT și servicii mentenanță",
                        "Lucrări de modernizare infrastructură rutieră",
                        "Servicii de consultanță tehnică",
                        "Achiziție materiale de construcții",
                        "Servicii de pază și protecție",
                        "Furnizare combustibili",
                        "Servicii de curățenie",
                    ]),
                    cod_cpv=random.choice(["30200000", "45233000", "71300000", "44100000", "79710000"]),
                    tip_procedura=random.choice(["Licitație deschisă", "Cerere de ofertă", "Negociere"]),
                    valoare=val,
                    moneda="RON",
                    valoare_ron=val,
                    data_atribuire=da,
                    data_inceput=da + timedelta(days=30),
                    data_finalizare=da + timedelta(days=365),
                    durata_luni=12,
                    seap_url=f"https://sicap-prod.e-licitatie.ro/contract/{random.randint(100000, 999999)}",
                )
                contracts.append(pc)

        session.add_all(contracts)
        await session.flush()
        print(f"  ✓ {len(contracts)} public contracts (SEAP)")

        # ── INSOLVENCY CASE ──
        insolvency = models.InsolvencyCase(
            company_id=company_objs[19].id,  # STAR IMPEX - radiata
            nr_dosar_bpi=f"BPI-{random.randint(10000,99999)}/2023",
            nr_dosar_tribunal=f"1234/118/2023",
            tip_procedura="Faliment",
            tribunal="Tribunalul Galați",
            practician="CITR Filiala București SPRL",
            data_publicare=date(2023, 3, 15),
            data_deschidere=date(2023, 1, 10),
            status="ACTIV",
            raw_data={"stadiu": "lichidare", "masa_credala": 1500000},
        )
        session.add(insolvency)
        await session.flush()
        print(f"  ✓ 1 insolvency case")

        # ── EU PROJECTS ──
        eu_projects = []
        for comp in company_objs:
            if comp.has_eu_projects:
                val_total = random.randint(500000, 5000000)
                eu_pct = Decimal(str(round(random.uniform(50, 85), 2)))
                eu_val = int(val_total * eu_pct / 100)
                ep = models.EUProject(
                    company_id=comp.id,
                    titlu=random.choice([
                        "Digitalizarea proceselor operaționale — PNRR C7",
                        "Creșterea competitivității prin inovare — POCIDIF",
                        "Tranziție energetică verde — PNRR C6",
                        "Dezvoltare capacități de producție — POC 2021-2027",
                    ]),
                    program_operational=random.choice(["PNRR", "POCIDIF", "POC", "POIM"]),
                    valoare_totala_ron=val_total,
                    finantare_ue_ron=eu_val,
                    finantare_ue_pct=eu_pct,
                    cofinantare_ron=val_total - eu_val,
                    data_aprobare=date(random.randint(2022, 2024), random.randint(1, 12), 1),
                    data_finalizare=date(2026, 12, 31),
                    status=random.choice(["IMPLEMENTARE", "FINALIZAT", "APROBARE"]),
                )
                eu_projects.append(ep)

        session.add_all(eu_projects)
        await session.flush()
        print(f"  ✓ {len(eu_projects)} EU projects")

        # ══════════════════════════════════════════════════════════
        # ALERTS
        # ══════════════════════════════════════════════════════════
        print("\n[9/10] Creating alerts, exchange rates, fraud alerts...")

        alerts = []
        alert_types = [
            ("RISK_CHANGE", "Scor de risc modificat", "Scorul de risc pentru {den} a scăzut de la 72 la 45 puncte."),
            ("INSOLVENCY", "Dosar insolvență deschis", "A fost publicat un nou dosar de insolvență pentru {den} în BPI."),
            ("DEBT_NEW", "Datorii noi la ANAF", "{den} a fost publicat pe lista contribuabililor cu datorii restante la ANAF."),
            ("LITIGATION", "Dosar nou pe portal.just.ro", "Un nou dosar a fost înregistrat pentru {den} la Tribunalul București."),
            ("SEAP_CONTRACT", "Contract SEAP nou", "{den} a câștigat un contract de achiziție publică în valoare de 1.5M RON."),
            ("ESG_UPDATE", "Scor ESG actualizat", "Scorul ESG pentru {den} a fost recalculat: E=72, S=68, G=80."),
            ("FISCAL_STATUS", "Modificare status fiscal", "{den} a fost declarat inactiv fiscal de către ANAF."),
            ("ASSOCIATES_CHANGE", "Schimbare asociați", "Structura de acționariat pentru {den} a fost modificată la ONRC."),
            ("ADMIN_CHANGE", "Schimbare administrator", "Administratorul companiei {den} a fost schimbat conform ORC."),
            ("CAPITAL_CHANGE", "Modificare capital social", "Capitalul social al {den} a fost majorat cu 500.000 RON."),
            ("ADDRESS_CHANGE", "Schimbare sediu social", "{den} și-a mutat sediul social la o nouă adresă."),
            ("CAEN_CHANGE", "Modificare cod CAEN", "Codul CAEN principal al {den} a fost schimbat."),
            ("MO_MENTION", "Publicare în Monitorul Oficial", "{den} a fost menționat într-un act publicat în Monitorul Oficial."),
            ("BILANT_PUBLISHED", "Bilanț publicat", "Bilanțul financiar pentru anul 2024 al {den} a fost depus la ANAF."),
        ]
        # Generate 25 alerts covering all types for richer data
        for i in range(25):
            comp = company_objs[i % len(company_objs)]
            atype, title_tpl, content_tpl = alert_types[i % len(alert_types)]
            alert = models.Alert(
                org_id=org_id,
                company_id=comp.id,
                user_id=admin_id,
                tip_alerta=atype,
                titlu=title_tpl,
                continut=content_tpl.format(den=comp.denumire),
                data_eveniment=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
                citita=(i > 15),
                trimisa_email=(i < 10),
            )
            alerts.append(alert)

        session.add_all(alerts)
        await session.flush()
        print(f"  ✓ {len(alerts)} alerts")

        # ── EXCHANGE RATES (BNR) — last 30 days ──
        rates = []
        # Realistic BNR rates as of July 2025
        currencies = {"EUR": 4.9770, "USD": 4.4680, "GBP": 5.9350, "CHF": 5.3120, "HUF": 0.01238}
        for day_offset in range(30):
            d = date.today() - timedelta(days=day_offset)
            if d.weekday() >= 5:  # skip weekends
                continue
            for curr, base_rate in currencies.items():
                # Very small daily variation (±0.003 for major, ±0.00003 for HUF)
                max_fluct = 0.00003 if curr == "HUF" else 0.003
                fluctuation = random.uniform(-max_fluct, max_fluct)
                rate = models.ExchangeRate(
                    date=d,
                    currency=curr,
                    rate_ron=Decimal(str(round(base_rate + fluctuation, 6))),
                    source="BNR",
                )
                rates.append(rate)

        session.add_all(rates)
        await session.flush()
        print(f"  ✓ {len(rates)} exchange rates (BNR)")

        # ── FRAUD ALERTS ──
        fraud_alerts = []
        fraud_types = [
            ("CIRCULAR_OWNERSHIP", "HIGH", "Structură circulară de acționariat detectată"),
            ("SHELL_COMPANY", "MEDIUM", "Companie cu indicatori de firmă fantomă"),
            ("RAPID_CHANGES", "LOW", "Schimbări rapide în structura de conducere"),
            ("SHARED_ADDRESS", "MEDIUM", "Multiple companii înregistrate la aceeași adresă"),
            ("UNUSUAL_TRANSACTIONS", "CRITICAL", "Tranzacții neobișnuite detectate în bilanțuri"),
            ("CAROUSEL", "HIGH", "Suspiciune de tranzacții circulare tip carusel TVA"),
            ("PHOENIX", "HIGH", "Tipare de firmă phoenix — închidere și redeschidere sub alt CUI"),
            ("REVENUE_MANIPULATION", "MEDIUM", "Discrepanțe între cifra de afaceri și activele declarate"),
            ("ADDRESS_FRAUD", "LOW", "Sediu social la adresă folosită de 15+ companii"),
            ("CLUSTERING", "MEDIUM", "Cluster neobișnuit de companii cu aceleași persoane cheie"),
        ]
        # Assign fraud alerts to specific well-known companies for a realistic demo
        fraud_assignments = [
            (0, 0),  # DEDEMAN - CIRCULAR_OWNERSHIP
            (1, 1),  # EMAG - SHELL_COMPANY
            (2, 2),  # ALTEX - RAPID_CHANGES
            (5, 3),  # KAUFLAND - SHARED_ADDRESS
            (3, 4),  # PETROM - UNUSUAL_TRANSACTIONS
            (10, 5), # TECH SOLUTIONS - CAROUSEL
            (11, 6), # CONSTRUCTII MODERNE - PHOENIX
            (12, 7), # AGRO INVEST - REVENUE_MANIPULATION
            (13, 8), # PHARMA CARE - ADDRESS_FRAUD
            (14, 9), # TRANSPORT EXPRESS - CLUSTERING
            (0, 4),  # DEDEMAN - UNUSUAL_TRANSACTIONS (2nd alert)
            (1, 5),  # EMAG - CAROUSEL
            (2, 3),  # ALTEX - SHARED_ADDRESS
            (3, 7),  # PETROM - REVENUE_MANIPULATION
            (4, 2),  # DACIA - RAPID_CHANGES
            (15, 0), # HOTEL REGAL - CIRCULAR_OWNERSHIP
            (16, 1), # FINTECH INNOVATORS - SHELL_COMPANY
            (17, 8), # PRODUCTIE ALIMENTARA - ADDRESS_FRAUD
            (18, 9), # ENERGIE VERDE - CLUSTERING
            (19, 4), # STAR IMPEX - UNUSUAL_TRANSACTIONS
        ]
        for comp_idx, ftype_idx in fraud_assignments:
            if comp_idx >= len(company_objs):
                continue
            comp = company_objs[comp_idx]
            ftype, sev, desc = fraud_types[ftype_idx]
            fa = models.FraudAlert(
                company_id=comp.id,
                alert_type=ftype,
                severity=sev,
                descriere=f"{desc} — {comp.denumire} (CUI: {comp.cui})",
                confidence=Decimal(str(round(random.uniform(0.3, 0.95), 4))),
                status=random.choice(["OPEN", "REVIEWED", "DISMISSED"]),
                dovezi={"indicator": ftype, "sursa": "graph_analysis", "detalii": "Verificare manuală recomandată"},
            )
            fraud_alerts.append(fa)

        session.add_all(fraud_alerts)
        await session.flush()
        print(f"  ✓ {len(fraud_alerts)} fraud alerts")

        # ── COMPANY MENTIONS (Monitor Oficial) ──
        mentions = []
        tip_acte = [
            "Hotărâre AGA", "Rezoluție ORC", "Act constitutiv modificat",
            "Fuziune/Absorbție", "Majorare capital social",
        ]
        for comp in company_objs[:10]:
            m = models.CompanyMention(
                company_id=comp.id,
                tip_sectiune=random.choice(["MO4", "MO7"]),
                tip_act=random.choice(tip_acte),
                nr_monitor=f"MOF Partea IV nr. {random.randint(1000,5000)}/{random.randint(2023,2025)}",
                data_publicare=date(random.randint(2023, 2025), random.randint(1, 12), random.randint(1, 28)),
                continut_rezumat=f"Publicare act constitutiv actualizat pentru {comp.denumire}",
                pdf_url=f"https://monitoruloficial.ro/pdf/{random.randint(100000,999999)}.pdf",
                pdf_parsed=random.random() > 0.5,
            )
            mentions.append(m)

        session.add_all(mentions)
        await session.flush()
        print(f"  ✓ {len(mentions)} Monitor Oficial mentions")

        # ══════════════════════════════════════════════════════════
        # PORTFOLIO
        # ══════════════════════════════════════════════════════════
        print("\n[10/10] Creating portfolio & RedBill cases...")

        portfolio = models.MonitoredPortfolio(
            id=uuid.uuid4(),
            org_id=org_id,
            user_id=admin_id,
            name="Portofoliu Principal",
            description="Companii monitorizate — clienți și furnizori cheie",
            alert_email=True,
            alert_sms=False,
        )
        session.add(portfolio)
        await session.flush()

        # Add 8 companies to portfolio
        portfolio_entries = []
        for comp in company_objs[:8]:
            pe = models.PortfolioCompany(
                portfolio_id=portfolio.id,
                company_id=comp.id,
                notes=f"Monitorizare activă — {comp.denumire}",
            )
            portfolio_entries.append(pe)
        session.add_all(portfolio_entries)
        await session.flush()

        # ── Portfolio 2: Sector Retail ──
        portfolio2 = models.MonitoredPortfolio(
            id=uuid.uuid4(),
            org_id=org_id,
            user_id=admin_id,
            name="Sector Retail",
            description="Monitorizare competitori și parteneri din retail",
            alert_email=True,
            alert_sms=False,
        )
        session.add(portfolio2)
        await session.flush()
        retail_indices = [5, 6, 7]  # KAUFLAND, LIDL, CARREFOUR
        for idx in retail_indices:
            if idx < len(company_objs):
                pe = models.PortfolioCompany(
                    portfolio_id=portfolio2.id,
                    company_id=company_objs[idx].id,
                    notes=f"Competitor retail — {company_objs[idx].denumire}",
                )
                portfolio_entries.append(pe)
        session.add_all(portfolio_entries[-len(retail_indices):])
        await session.flush()

        # ── Portfolio 3: Risc Ridicat ──
        portfolio3 = models.MonitoredPortfolio(
            id=uuid.uuid4(),
            org_id=org_id,
            user_id=admin_id,
            name="Companiile cu Risc Ridicat",
            description="Firme cu datorii, insolvență sau procese active — monitorizare intensivă",
            alert_email=True,
            alert_sms=True,
        )
        session.add(portfolio3)
        await session.flush()
        risk_indices = [11, 12, 19]  # CONSTRUCTII MODERNE, AGRO INVEST, STAR IMPEX
        for idx in risk_indices:
            if idx < len(company_objs):
                pe2 = models.PortfolioCompany(
                    portfolio_id=portfolio3.id,
                    company_id=company_objs[idx].id,
                    notes=f"Atenție risc — {company_objs[idx].denumire}",
                )
                session.add(pe2)
        await session.flush()

        total_portfolios = 3
        total_pe = len(portfolio_entries) + len(retail_indices) + len(risk_indices)
        print(f"  ✓ {total_portfolios} portfolios with {total_pe} total company links")

        # ── REDBILL CASES ──
        redbill_cases = []
        for _ in range(5):
            creditor = random.choice(company_objs[:10])
            debtor = random.choice(company_objs[10:18])
            rb = models.RedBillCase(
                creditor_cui=creditor.cui,
                debtor_cui=debtor.cui,
                invoice_number=f"FA-{random.randint(1000,9999)}/{2025}",
                invoice_amount=Decimal(str(round(random.uniform(5000, 200000), 2))),
                invoice_date=date(2025, random.randint(1, 6), random.randint(1, 28)),
                due_date=date(2025, random.randint(7, 12), random.randint(1, 28)),
                visibility=random.choice(["PUBLIC", "PRIVATE"]),
                status=random.choice(["OPEN", "PAID", "DISPUTE"]),
                collection_started=random.random() > 0.7,
                org_id=org_id,
            )
            redbill_cases.append(rb)

        session.add_all(redbill_cases)
        await session.flush()
        print(f"  ✓ {len(redbill_cases)} RedBill cases")

        # ── NEW COMPANIES FEED ──
        new_feed = []
        for i, comp in enumerate(company_objs[10:15]):
            nf = models.NewCompanyFeed(
                company_id=comp.id,
                registration_date=date.today() - timedelta(days=i),
                feed_date=date.today() - timedelta(days=i),
                sursa="ONRC",
                is_notified=False,
            )
            new_feed.append(nf)
        # Also add a few more recent entries from other companies
        for i, comp in enumerate(company_objs[15:19]):
            nf = models.NewCompanyFeed(
                company_id=comp.id,
                registration_date=date.today() - timedelta(days=i + 1),
                feed_date=date.today() - timedelta(days=i + 1),
                sursa="ONRC",
                is_notified=False,
            )
            new_feed.append(nf)
        session.add_all(new_feed)
        await session.flush()
        print(f"  ✓ {len(new_feed)} new companies feed entries")

        # ── ACTIVE TENDERS  ──
        tenders = []
        for _ in range(6):
            auto_cui, auto_name = random.choice(autoritati)
            t = models.PublicTenderActive(
                authority_cui=auto_cui,
                authority_name=auto_name,
                tender_number=f"SCN-{random.randint(100000,999999)}",
                title=random.choice([
                    "Achiziție sisteme informatice pentru administrație publică",
                    "Lucrări de reabilitare drumuri naționale", 
                    "Servicii de proiectare și consultanță tehnică",
                    "Furnizare echipamente medicale",
                    "Servicii de întreținere spații verzi",
                    "Lucrări de construcții clădiri publice",
                ]),
                cpv_code=random.choice(["30200000", "45233000", "71300000", "33100000", "77310000"]),
                estimated_value=Decimal(str(round(random.uniform(100000, 5000000), 2))),
                currency="RON",
                procedure_type=random.choice(["Licitație deschisă", "Cerere de ofertă", "Procedură simplificată"]),
                deadline=date.today() + timedelta(days=random.randint(10, 60)),
                seap_url=f"https://sicap-prod.e-licitatie.ro/tender/{random.randint(100000, 999999)}",
            )
            tenders.append(t)

        session.add_all(tenders)
        await session.flush()
        print(f"  ✓ {len(tenders)} active tenders (SEAP)")

        # ── ENTITY RELATIONS (Supply Chain, Ownership, Partnerships) ──
        print("\n[11/14] Creating entity relations...")

        entity_relations = []
        relation_types = ["FURNIZOR", "SUPPLIER", "PARTENER", "SUBCONTRACTOR", "OWNERSHIP", "CLIENT"]
        for i, comp in enumerate(company_objs[:15]):
            # Each company has 2-4 relationships with other companies
            n_rels = random.randint(2, 4)
            targets = random.sample([c for c in company_objs if c.id != comp.id], min(n_rels, len(company_objs) - 1))
            for target in targets:
                rel = models.EntityRelation(
                    source_type="COMPANY",
                    source_id=comp.id,
                    target_type="COMPANY",
                    target_id=target.id,
                    relation_type=random.choice(relation_types),
                    weight=Decimal(str(round(random.uniform(0.1, 1.0), 3))),
                    sursa=random.choice(["ONRC", "ANAF", "MANUAL"]),
                    valid_from=comp.data_infiintare,
                )
                entity_relations.append(rel)

        # Add person-to-company ownership relations
        for person in persons[:20]:
            if person.tip == "ASOCIAT" and person.procent_parti and person.procent_parti > 10:
                rel = models.EntityRelation(
                    source_type="PERSON",
                    source_id=person.id,
                    target_type="COMPANY",
                    target_id=person.company_id,
                    relation_type="OWNERSHIP",
                    weight=person.procent_parti / 100 if person.procent_parti else Decimal("0.5"),
                    sursa="ONRC",
                    valid_from=person.data_start,
                )
                entity_relations.append(rel)

        session.add_all(entity_relations)
        await session.flush()
        print(f"  ✓ {len(entity_relations)} entity relations")

        # ── GRAPH METRICS ──
        print("\n[12/14] Creating graph metrics...")

        graph_metrics = []
        for comp in company_objs:
            gm = models.GraphMetric(
                company_id=comp.id,
                entity_type="company",
                entity_id=comp.id,
                pagerank_score=Decimal(str(round(random.uniform(0.001, 0.15), 8))),
                betweenness=Decimal(str(round(random.uniform(0.0, 0.5), 8))),
                degree_in=random.randint(0, 10),
                degree_out=random.randint(0, 8),
                community_id=random.randint(1, 5),
                suspicion_score=Decimal(str(round(random.uniform(0.0, 0.8), 4))),
            )
            graph_metrics.append(gm)

        session.add_all(graph_metrics)
        await session.flush()
        print(f"  ✓ {len(graph_metrics)} graph metrics")

        # ── ENVIRONMENTAL FINES ──
        print("\n[13/14] Creating environmental fines & ESG raw data...")

        env_fines = []
        autoritati_mediu = [
            "Garda Națională de Mediu", "Agenția de Protecție a Mediului",
            "Administrația Fondului pentru Mediu", "Inspectoratul de Stat în Construcții",
        ]
        for comp in random.sample(company_objs[:15], 6):
            ef = models.EnvironmentalFine(
                company_id=comp.id,
                autoritate=random.choice(autoritati_mediu),
                suma_ron=Decimal(str(round(random.uniform(5000, 200000), 2))),
                motiv=random.choice([
                    "Depășire limite emisii CO2",
                    "Deversare neconformă ape uzate",
                    "Depozitare ilegală deșeuri industriale",
                    "Lipsa autorizație de mediu",
                    "Poluare fonică peste limitele legale",
                ]),
                data_amenda=date(random.randint(2022, 2025), random.randint(1, 12), random.randint(1, 28)),
                status=random.choice(["ACTIVA", "PLATITA", "CONTESTATA"]),
            )
            env_fines.append(ef)

        session.add_all(env_fines)
        await session.flush()

        # ── ESG RAW DATA ──
        esg_raw = []
        esg_indicators = [
            ("E", "emisii_co2", "tone CO2e", "100-50000"),
            ("E", "consum_energie", "MWh", "500-100000"),
            ("E", "deseuri_reciclate", "%", "10-90"),
            ("S", "rata_retentie_angajati", "%", "40-95"),
            ("S", "ore_training_angajat", "ore/an", "5-100"),
            ("S", "diferenta_salariala_gen", "%", "0-25"),
            ("G", "independenta_ca", "%", "20-100"),
            ("G", "diversitate_ca", "%", "10-60"),
            ("G", "transparenta_financiara", "scor", "30-100"),
        ]
        for comp in company_objs[:12]:
            for cat, ind, unit, val_range in esg_indicators:
                lo, hi = [float(x) for x in val_range.split("-")]
                val = round(random.uniform(lo, hi), 2)
                esg_d = models.ESGRawData(
                    company_id=comp.id,
                    sursa=random.choice(["ANAF", "ONRC", "AUTO_CALC", "ESG_PROVIDER"]),
                    categorie=cat,
                    indicator=ind,
                    valoare=str(val),
                    unitate=unit,
                    an_referinta=random.choice([2023, 2024]),
                    data_colectare=date.today() - timedelta(days=random.randint(1, 180)),
                )
                esg_raw.append(esg_d)

        session.add_all(esg_raw)
        await session.flush()
        print(f"  ✓ {len(env_fines)} environmental fines, {len(esg_raw)} ESG raw data points")

        # ── API KEYS for Marketplace ──
        print("\n[14/14] Creating API keys & audit log entries...")

        api_key_1 = models.ApiKey(
            org_id=org_id,
            name="Production Key",
            key_hash=secrets.token_hex(32),
            key_prefix="rombiz_p",
            permissions={"read": True, "write": False, "admin": False},
            rate_limit_rpm=60,
            is_active=True,
        )
        api_key_2 = models.ApiKey(
            org_id=org_id,
            name="Development Key",
            key_hash=secrets.token_hex(32),
            key_prefix="rombiz_d",
            permissions={"read": True, "write": True, "admin": False},
            rate_limit_rpm=120,
            is_active=True,
        )
        session.add_all([api_key_1, api_key_2])
        await session.flush()

        # ── AUDIT LOG entries ──
        audit_entries = []
        audit_actions = [
            ("company.view", "Vizualizare profil companie"),
            ("search.execute", "Căutare companii"),
            ("report.generate", "Generare raport"),
            ("portfolio.update", "Actualizare portofoliu"),
            ("alert.read", "Citire alerte"),
            ("risk.recalculate", "Recalculare scor risc"),
        ]
        for i in range(20):
            uid = random.choice([admin_id, analyst_id, viewer_id])
            action, desc = random.choice(audit_actions)
            ae = models.AuditLog(
                org_id=org_id,
                user_id=uid,
                action=action,
                entity_type="company" if "company" in action else "system",
                entity_id=str(random.choice(company_objs[:10]).id) if "company" in action else None,
                ip_address=f"192.168.1.{random.randint(1, 254)}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) RomBiz/1.0",
                payload_json={"descriere": desc},
            )
            audit_entries.append(ae)

        session.add_all(audit_entries)
        await session.flush()
        print(f"  ✓ 2 API keys, {len(audit_entries)} audit log entries")

        # ── REPORT EXPORTS ──
        report_exports = []
        export_types = [
            ("company_report", "pdf", "completed"),
            ("portfolio_report", "xlsx", "completed"),
            ("risk_analysis", "pdf", "completed"),
            ("financial_export", "csv", "completed"),
            ("esg_report", "pdf", "processing"),
        ]
        for i, (etype, fmt, status) in enumerate(export_types):
            re = models.ReportExport(
                org_id=org_id,
                user_id=admin_id,
                company_id=company_objs[i].id if i < len(company_objs) else None,
                export_type=etype,
                format=fmt,
                status=status,
                file_url=f"/exports/report_{i+1}.{fmt}" if status == "completed" else None,
            )
            report_exports.append(re)
        session.add_all(report_exports)
        await session.flush()
        print(f"  ✓ {len(report_exports)} report exports")

        # ── COMMIT ALL ──
        await session.commit()

    print("\n" + "=" * 60)
    print("  ✅ ALL DUMMY DATA SEEDED SUCCESSFULLY!")
    print("=" * 60)
    print(f"""
  Login credentials:
    admin@rombiz.ro    / Admin123!    (role: admin)
    analyst@rombiz.ro  / Analyst123!  (role: analyst)
    viewer@rombiz.ro   / Viewer123!   (role: viewer)

  Data summary:
    • 20 companies (Romanian firms with realistic data)
    • 60 financial records (3 years per company)
    • ~60 company persons (associates & administrators)
    • 20 risk scores + 20 ESG scores
    • ~15 court cases with hearings
    • ~15 SEAP public contracts
    • ~6 active tenders
    • 12 alerts (various types)
    • ~100 BNR exchange rates (last 30 days)
    • 8 fraud alerts
    • 10 Monitor Oficial mentions
    • 1 portfolio with 8 monitored companies
    • 5 RedBill cases
    • 5 new companies feed entries
    • 1 insolvency case
    • 3 EU projects
    • ~50 entity relations (supply chain, ownership)
    • 20 graph metrics
    • ~6 environmental fines
    • ~108 ESG raw data points
    • 2 API keys
    • 20 audit log entries
""")


if __name__ == "__main__":
    asyncio.run(main())
