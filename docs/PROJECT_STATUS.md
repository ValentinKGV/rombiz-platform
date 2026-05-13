# RomBiz Platform — Documentație Completă & Status Proiect

> **Data generării:** 2 Martie 2026  
> **Total linii cod:** ~26,000+ (Backend ~15,000 Python + 808 SQL | Frontend ~10,200 TSX/TS)  
> **Fișiere:** ~130+

---

## Cuprins

1. [Sumar Executiv](#1-sumar-executiv)
2. [Backend — Core Infrastructure](#2-backend--core-infrastructure)
3. [Backend — Modele & Baza de Date](#3-backend--modele--baza-de-date)
4. [Backend — API Endpoints](#4-backend--api-endpoints)
5. [Backend — Servicii (Business Logic)](#5-backend--servicii-business-logic)
6. [Backend — Colectori de Date](#6-backend--colectori-de-date)
7. [Backend — Celery Tasks](#7-backend--celery-tasks)
8. [Backend — Middleware & Utilități](#8-backend--middleware--utilități)
9. [Frontend — Infrastructură](#9-frontend--infrastructură)
10. [Frontend — Pagini](#10-frontend--pagini)
11. [Frontend — Componente & Hooks](#11-frontend--componente--hooks)
12. [Infrastructură & DevOps](#12-infrastructură--devops)
13. [Documentație Existentă](#13-documentație-existentă)
14. [Teste](#14-teste)
15. [Buguri Cunoscute](#15-buguri-cunoscute)
16. [Tabel Rezumativ per Modul](#16-tabel-rezumativ-per-modul)
17. [Lista Completă TODO — Ce Rămâne de Făcut](#17-lista-completă-todo--ce-rămâne-de-făcut)

---

## 1. Sumar Executiv

### Arhitectură generală
| Layer | Tehnologie |
|---|---|
| Backend | FastAPI 0.115, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2 |
| Frontend | React 18.3 + TypeScript 5.4, Vite, Tailwind CSS |
| State Management | Zustand + TanStack React Query 5 |
| Baza de Date | PostgreSQL 16 + Elasticsearch 8.12 + Neo4j 5 + Redis 7 |
| Task Queue | Celery 5.4 cu Redis broker |
| Stocare fișiere | MinIO (S3-compatible) |
| AI | Anthropic Claude (function calling) |
| Proxy | Nginx |
| Container | Docker Compose v3.9 (10 servicii) |

### Progres Global

| Ramură | Progres | Note |
|--------|---------|------|
| **Backend Core** | 🟢 95% | Complet funcțional |
| **Modele BD** | 🟢 100% | 25+ modele, migrare SQL completă |
| **API Endpoints** | 🟢 95% | 28 routere, ~70 endpoints |
| **Servicii** | 🟡 85% | Toate implementate, 2 cu stocaj in-memory |
| **Colectori** | 🟡 80% | 11 conectori, 2 minimali |
| **Celery Tasks** | 🟢 90% | 12 task-uri periodice, SMS stub |
| **Frontend Pagini** | 🟡 80% | 27 pagini, buguri API path + TabNav |
| **Frontend Componente** | 🟢 90% | 14 componente reutilizabile |
| **Infrastructură** | 🟡 75% | Docker complet, SSL/HTTPS lipsă |
| **Teste** | 🔴 5% | Doar 5 teste triviale |
| **Documentație** | 🟡 70% | API.md incomplet, README cu erori |
| **TOTAL PROIECT** | **~82%** | |

---

## 2. Backend — Core Infrastructure

**Locație:** `backend/app/core/`  
**Status:** 🟢 95% complet

| Fișier | Funcționalitate | Status | Ce lipsește |
|--------|-----------------|--------|-------------|
| `config.py` (~110 linii) | Pydantic Settings — DB, Redis, Celery, ES, Neo4j, MinIO, JWT RS256, GDPR, API-uri externe (ANAF/BNR/BPI/SEAP/ONRC), AI (Anthropic), SMTP/SMS, Rate Limiting, Sentry | ✅ Complet | — |
| `database.py` (~65 linii) | SQLAlchemy async engine + session factory, `get_db()` dependency, `get_db_context()` pt Celery, SQLite auto-detect | ✅ Complet | — |
| `security.py` (~115 linii) | JWT RS256 (HS256 fallback dev), `TokenPayload`, `create_access_token()`, `create_refresh_token()`, `get_current_user()`, `require_role()` RBAC, bcrypt | ✅ Complet | Cheile RSA trebuie generate pt producție |
| `redis.py` (20 linii) | Singleton redis_client, decode_responses, 50 conexiuni max | ✅ Complet | — |
| `logging.py` (40 linii) | structlog + stdlib, JSON output, ISO timestamps | ✅ Complet | — |
| `compat_types.py` (~75 linii) | TypeDecorator wrappers (UUID, JSON, ARRAY, INET) pt PostgreSQL/SQLite dual-dialect | ✅ Complet | — |

**Ce mai trebuie făcut:**
- [ ] Genera chei RSA reale (`keys/private.pem`, `keys/public.pem`) pt producție
- [ ] Restricționa CORS (acum este `allow_origin_regex=r".*"` — orice domeniu)

---

## 3. Backend — Modele & Baza de Date

**Locație:** `backend/app/models/models.py` (841 linii) + `migrations/versions/001_initial_schema.sql` (808 linii)  
**Status:** 🟢 100% complet

### Modele ORM (25+)

| Model | Descriere | Coloane Cheie |
|-------|-----------|---------------|
| `Organization` | Multi-tenancy root | subscription, api_calls_limit |
| `User` | Utilizatori cu roluri | admin/analyst/viewer, api_key, alert_preferences |
| `ApiKey` | Chei API hashed | permissions JSONB, rate_limit |
| `Company` | Entitate core | ~35 coloane, 10 relații, CUI unic, tsvector search, lat/lng |
| `FinancialData` | Bilanțuri anuale | CA, profit, capitaluri, ROA/ROE/marjă/lichiditate |
| `CompanyPerson` | Asociați/Administratori | CNP hashed GDPR, procent acțiuni |
| `InsolvencyCase` | Date BPI | dosare, proceduri, practicieni |
| `CourtCase` + `LitigationHearing` | Dosare instanță | ROLII integration, termene |
| `PublicContract` + `PublicTenderActive` | SEAP contracte + licitații | CPV codes, valori |
| `RiskScore` | Scor risc 1-100 | 4 sub-scoruri (financiar/legal/fiscal/comportamental) |
| `ESGScore` | Scor ESG | E/S/G sub-scoruri, CSRD/SFDR |
| `CompanyDebt` | Datorii ANAF | tip, sumă, data |
| `ExchangeRate` | Cursuri BNR | dată + monedă unice |
| `EUProject` | Proiecte MySMIS | program, axă, valori |
| `CompanyMention` | Monitor Oficial | MO4/MO7 |
| `Alert` | 13 tipuri alerte | multi-channel dispatch |
| `MonitoredPortfolio` + `PortfolioCompany` | Portofolii M2M | — |
| `SavedSearch` | Căutări salvate | filtru, notify_new |
| `EntityRelation` | Graf relații (fraud) | source/target, weight |
| `FraudAlert` + `GraphMetric` | Rezultate detecție fraudă | PageRank, betweenness |
| `RedBillCase` | Recuperare creanțe | — |
| `NewCompanyFeed` | Feed ONRC | — |
| `ReportExport` | Export PDF/Excel | credite consumate |
| `AuditLog` | GDPR audit trail | IP, user agent |
| `DataSourceSyncLog` | Istoric sincronizare | — |

### Migrare SQL
- 22 tabele cu FK + cascade
- Extensii: `pg_trgm`, `unaccent`, `btree_gin`, `uuid-ossp`
- Trigger auto-update `tsvector` + `updated_at`
- Funcție PL/pgSQL `validate_cui()`
- 3 materialized views: `mv_company_summary`, `mv_sector_stats`, `mv_top_companies_by_county`
- Indexări: GIN, BRIN, parțiale, compozite
- Rollback DDL inclus

**Ce mai trebuie făcut:**
- [ ] Migra de la SQL raw la Alembic (revision chain, `alembic.ini`, `env.py`)
- [ ] Creat script de creare index Elasticsearch
- [ ] Creat schema Neo4j (constraints, indexes)

---

## 4. Backend — API Endpoints

**Locație:** `backend/app/api/v1/endpoints/`  
**Status:** 🟢 95% complet — 28 routere, ~70 endpoints, toate funcționale

| Modul | Endpoints | Linii | Implementare | Descriere |
|-------|-----------|-------|--------------|-----------|
| `auth.py` | register, login, refresh, me | 130 | ✅ Real | DB queries, JWT, bcrypt |
| `companies.py` | GET /{cui}, financial, persons, insolvency, court-cases, contracts, eu-projects, mentions, batch | 270 | ✅ Real | Batch 500 CUI, relații complete |
| `search.py` | POST search, autocomplete, facets, did-you-mean, geo, saved-searches | 370 | ✅ Real | 50+ filtre, subquery joins, sortare |
| `risk.py` | score, recalculate (Celery), history, distribution, predict, benchmark | 170 | ✅ Real | Delegare la `RiskScoringEngine` |
| `esg.py` | score, recalculate, raw-data, env-fines, ranking, factsheet, compare, portfolio, timeline | 302 | ✅ Real | Full DB queries + service |
| `fraud.py` | profile, alerts, graph, composite-score, scan/batch, detection/algorithms | 306 | ✅ Real | `FraudGraphEngine` |
| `alerts.py` | **WebSocket** /ws/{token}, list, unread-count, mark-read, types, analytics | 273 | ✅ Real | `ConnectionManager` real-time |
| `portfolios.py` | CRUD, add/remove companies, saved searches | 290 | ✅ Real | DB persistat |
| `redbill.py` | debtor profile, report (Celery PDF), stats | 175 | ✅ Real | `RedBillService` |
| `seap.py` | tenders, contracts, stats by authority/CPV | 200 | ✅ Real | Agregări DB |
| `reports.py` | company/portfolio report (PDF/XLSX Celery, CSV/JSON/HTML inline), exports, download | 202 | ✅ Real | Multi-format async |
| `admin.py` | dashboard, data-sources, audit-log, users CRUD/invite/role/deactivate, org, GDPR, feature flags | 608 | ✅ Real | `require_role("admin")` |
| `ai_agent.py` | Claude AI agent cu 10 tool-uri, streaming SSE, Redis memorie, token tracking | 707 | ✅ Real | Anthropic function calling |
| `dashboard.py` | stats (period-filter), ESG/fraud/BNR/contracts widgets | 243 | ✅ Real | DB aggregations |
| `predictive.py` | forecast, bankruptcy, degradation, sector trends, Monte Carlo | 100 | ✅ Real | Delegare service |
| `new_companies.py` | feed filtrat, stats, heatmap | 190 | ✅ Real | DB queries |
| `relationships.py` | UBO, contagion, directors, group, timeline | 70 | ✅ Real | Delegare service |
| `due_diligence.py` | checklist, red flags, peers, report, compliance | 65 | ✅ Real | Delegare service |
| `market_intelligence.py` | competitors, benchmarks, market-size, M&A targets, price intel | 70 | ✅ Real | Delegare service |
| `supply_chain.py` | network, dependencies, disruptions, alternatives, score | 65 | ✅ Real | Delegare service |
| `document_intelligence.py` | classify, parse-financial, analyze-contract, extract-entities, compare | 65 | ✅ Real | Delegare service |
| `regulatory_compliance.py` | GDPR, fiscal, environmental, labor, AML | 55 | ✅ Real | Delegare service |
| `geospatial.py` | heatmap, zones, proximity, geodemographic, counties | 60 | ✅ Real | Delegare service |
| `api_marketplace.py` | keys CRUD, usage, rate-limits, SDK docs, webhooks | 90 | ✅ Real | Delegare service |
| `portfolio_optimization.py` | optimize, rebalance, benchmark, attribution, scenarios | 70 | ✅ Real | Delegare service |
| `international_expansion.py` | cross-border, FX risk, market entry, regulatory, translate | 70 | ✅ Real | Delegare service |
| `blockchain_audit.py` | audit-trail, hash-document, verify, smart-contract, custody, timestamp | 100 | ✅ Real | Delegare service |

**Ce mai trebuie făcut:**
- [ ] Nimic major — toate endpoint-urile sunt funcționale

---

## 5. Backend — Servicii (Business Logic)

**Locație:** `backend/app/services/`  
**Status:** 🟡 85% complet

| Serviciu | Linii | Status | Algoritmi Cheie | Ce Lipsește |
|----------|-------|--------|-----------------|-------------|
| `risk_scoring.py` | 904 | ✅ Complet | Altman Z-Score adaptat pt 60+ CAEN; 4 componente ponderate (financiar 30%, legal 25%, fiscal 25%, comportamental 20%); probabilitate insolvență logistică; estimare credit limit | — |
| `esg_scoring.py` | 1101 | ✅ Complet | EU Taxonomy mapping; intensitate carbon per CAEN; CSRD 12-item checklist; GRI Standards; SFDR clasificare; conversie BNR EUR | — |
| `fraud_graph.py` | 935 | ✅ Complet | 7 algoritmi: Carousel (Neo4j Cypher + PG recursive CTE), Phoenix company, Beneficial owner clustering, Anomaly scoring. Dual Neo4j/PostgreSQL fallback | — |
| `search_service.py` | 531 | ✅ Complet | ES Romanian analyzer (stemmer, stop words, asciifolding); 42 coordinate județe; bulk indexing; pg_trgm fuzzy fallback | Script creare index ES |
| `predictive_analytics.py` | 868 | ✅ Complet | Regresie liniară (pure Python); predicție faliment (model logistic Z-Score + datorii + vârstă + sector); Monte Carlo; degradare risc; tendințe sector | — |
| `reports_service.py` | 845 | ✅ Complet | PDF (ReportLab A4), Excel (openpyxl), CSV, JSON, HTML; rapoarte multi-secțiune companie + portofoliu | Upload MinIO lipsă |
| `alerts_service.py` | 575 | ✅ Complet | 13 tipuri alerte cu rate limiting per tip; dedup smart (1h window); dispatch multi-canal (WS, email, SMS, webhook) | SMS = stub |
| `relationship_intelligence.py` | 675 | ✅ Complet | UBO recursiv (max depth 10); procent multiplicat; rețea directori partajați; mapare contagion | — |
| `due_diligence.py` | 728 | ✅ Complet | DD checklist automat cu 9 verificări ponderate (scor 100); verdicte: FAVORABIL/CONDIȚIONAT/NEFAVORABIL; red flags; comparare peers | — |
| `market_intelligence.py` | 417 | ✅ Complet | Analiză competitivă CAEN+județ; benchmarks sector (5 ani agregate); sizing piață; screening M&A | — |
| `supply_chain.py` | 440 | ✅ Complet | Rețea furnizori via EntityRelation; dependențe single-source; alerte disrupție (insolvență/datorii/risc); furnizori alternativi | — |
| `document_intelligence.py` | 288 | ⚠️ Minimal | Clasificare regex (8 tipuri); parsare bilanțuri; extracție clauze contract (7 tipuri); NER românesc (CUI, date, sume) | Fără ML/NLP — doar regex |
| `regulatory_compliance.py` | 534 | ✅ Complet | 5 module: GDPR (DPO, CAEN risc), fiscal (datorii, TVA), mediu (amenzi, CAEN risc), muncă, AML (PEP, sancțiuni) | — |
| `geospatial_bi.py` | 331 | ✅ Complet | Heatmap pe județe; 8 regiuni dezvoltare; Haversine proximity; agregate geodemografice | — |
| `api_marketplace.py` | 481 | ⚠️ Parțial | Chei API cu SHA-256; analytics; rate limiting; webhooks; generare SDK docs | **In-memory dicts** — nu DB! |
| `redbill_service.py` | ~100 | ✅ Complet | Profilare datornici; clasificare risc (verde/galben/portocaliu/roșu); freshness 90 zile | — |
| `blockchain_audit.py` | 475 | ⚠️ Simulat | SHA-256 hash chain **in-memory**; hashing documente; chain-of-custody; verificare integritate | **State pierdut la restart** |
| `portfolio_optimization.py` | 515 | ✅ Complet | Markowitz simplificat (Sharpe); rebalansare (risk_parity/equal_weight/momentum); benchmark; atribuție; scenarii | Unele valori random.uniform() |
| `international_expansion.py` | 452 | ✅ Complet | 12 profiluri țări UE (taxe, TVA, PIB, populație); scoring cross-border; FX VaR 95%; dificultate intrare piață | Unele valori simulate |

**Ce mai trebuie făcut:**
- [ ] `api_marketplace.py` — Migra stocajul din dict-uri in-memory în tabele DB
- [ ] `blockchain_audit.py` — Migra chain-ul SHA-256 din memorie în DB (tabel persistent)
- [ ] `document_intelligence.py` — Adăuga ML/NLP pt clasificare inteligentă (opțional, funcționează cu regex)
- [ ] Upload efectiv în MinIO pt rapoartele generate (`reports_service.py`)
- [ ] Integrare Twilio/Vonage pt SMS în `alerts_service.py`

---

## 6. Backend — Colectori de Date

**Locație:** `backend/app/collectors/`  
**Status:** 🟡 80% complet

| Colector | Linii | Status | Sursă Date | Funcționalități |
|----------|-------|--------|------------|-----------------|
| `base_connector.py` | ~155 | ✅ Complet | — | Circuit breaker (5 fail → open, 60s reset), httpx async, rate limiting, retry cu backoff, handling 429 |
| `anaf.py` | 214 | ✅ Complet | ANAF v8 Bulk API | Batch 500 CUI, `_parse_company()`, `fetch_debts()` Decimal, `fetch_balance_sheet()`. Freshness 90 zile |
| `onrc.py` | ~115 | ✅ Complet | ONRC/RECOM | Asociați, administratori, capital social, 30-day cache TTL, `fetch_new_companies()` |
| `bpi.py` | ~85 | ✅ Complet | BPI (Buletinul Procedurilor de Insolvență) | Parsare cazuri (nr_dosar, tip_procedura, practician, tribunal) |
| `bnr.py` | ~130 | ✅ Complet | BNR (Banca Națională) | XML parser cu namespace, URL-uri zilnice/10-zile/anuale, Decimal pt cursuri |
| `seap.py` | ~95 | ✅ Complet | SEAP (e-licitatie.ro) | Licitații active + contracte atribuite, coduri CPV, Decimal pt valori |
| `portal_just.py` | ~105 | ✅ Complet | Portal Just / ROLII | Căutare dosare după număr/firmă, parsare termene |
| `monitor_oficial.py` | ~80 | ✅ Complet | Monitorul Oficial | Secțiuni MO4/MO7, căutare mențiuni CUI |
| `mysmis.py` | ~85 | ✅ Complet | MySMIS2021 | Proiecte UE finanțate, program, axă, Decimal |
| `aegrm.py` | ~50 | ⚠️ Minimal | AEGRM (Garanții Mobiliare) | Sync = stub ("requires manual/scheduled sync"); `fetch_single()` funcționează |
| `osim.py` | ~55 | ⚠️ Minimal | OSIM (Mărci & Brevete) | Sync neautomatizat; `fetch_single()` face keyword search |

**Ce mai trebuie făcut:**
- [ ] `aegrm.py` — Implementa sync automat complet
- [ ] `osim.py` — Implementa sync automat complet
- [ ] Adăuga colector **BVB** (Bursa de Valori București) — specificat în prompt, neimplementat
- [ ] Adăuga colector **ASF** (Autoritatea de Supraveghere Financiară) — specificat în prompt
- [ ] Adăuga colector **INS** (Institutul Național de Statistică) — specificat în prompt
- [ ] CIP (Centrala Incidentelor de Plăți) — tabel existent dar necesită contract BNR

---

## 7. Backend — Celery Tasks

**Locație:** `backend/app/tasks/`  
**Status:** 🟢 90% complet

| Modul | Linii | Status | Schedule |
|-------|-------|--------|----------|
| `celery_app.py` | 152 | ✅ Complet | Config: 6 cozi (sync, compute, reports, notifications), UTC, beat cu 12 task-uri periodice |
| `sync_tasks.py` | 549 | ✅ Complet | ANAF/6h, BNR/zilnic 14:00, BPI/4h, SEAP/2h, MO/12h, PortalJust/6h, MySMIS/săptămânal, NewCompanies/zilnic 08:00 |
| `risk_tasks.py` | ~70 | ✅ Complet | Recalculare individuală + batch zilnic 02:00 |
| `esg_tasks.py` | ~70 | ✅ Complet | Recalculare individuală + batch săptămânal duminca 03:00 |
| `fraud_tasks.py` | ~85 | ✅ Complet | Detecție completă (carousel + phoenix + cluster) zilnic 04:00 |
| `report_tasks.py` | 152 | ✅ Complet | Generare rapoarte companie/portofoliu/redbill (PDF/XLSX), update `ReportExport` |
| `notification_tasks.py` | ~145 | ⚠️ Parțial | Email SMTP ✅, Webhook httpx ✅, Slack webhook ✅, **SMS = STUB** |
| `maintenance_tasks.py` | ~75 | ✅ Complet | Refresh materialized views/4h, cleanup date expirate zilnic 01:00 |

**Ce mai trebuie făcut:**
- [ ] Implementa `send_alert_sms` cu Twilio/Vonage (acum only stub)
- [ ] Adăuga retry policy mai robust pt task-urile de sync (acum basic)

---

## 8. Backend — Middleware & Utilități

**Locație:** `backend/app/middleware/` + `backend/app/utils/`  
**Status:** 🟢 95% complet

| Fișier | Linii | Status | Funcționalitate |
|--------|-------|--------|-----------------|
| `gdpr.py` | 190 | ✅ Complet | Soft delete cascade, GDPR data export (portabilitate), audit logging |
| `multi_tenancy.py` | ~70 | ✅ Complet | Middleware injectare `org_id`, `enforce_org_id()`, `org_id_filter()` generic |
| `validators.py` | ~90 | ✅ Complet | `validate_cui()` mod-11, `hash_cnp()` SHA-256 cu pepper, `mask_cnp()`, `safe_decimal()`, `utc_now()` |

**Ce mai trebuie făcut:**
- [ ] Nimic — complet funcțional

---

## 9. Frontend — Infrastructură

**Locație:** `frontend/src/`  
**Status:** 🟢 90% complet

| Fișier | Linii | Funcționalitate | Status |
|--------|-------|-----------------|--------|
| `main.tsx` | 32 | Entry point, QueryClient (5min stale, 30min GC, retry:1), BrowserRouter | ✅ |
| `App.tsx` | ~155 | 27 lazy-loaded routes, ProtectedRoute, WebSocket la auth, Ctrl+K, Sonner | ✅ |
| `index.css` | ~450 | Temă sci-fi "cosmic/nebula", CSS variables, animații custom | ✅ |
| `lib/api.ts` | ~90 | Axios, JWT interceptor, refresh token queue, redirect 401 | ✅ |
| `lib/utils.ts` | ~95 | `cn()`, `formatMoney`, `formatDate`, `validateCUI` mod-11 | ✅ |
| `lib/websocket.ts` | ~80 | WebSocket client, auto-reconnect, exponential backoff (max 5) | ✅ |
| `store/auth.ts` | ~80 | Zustand: user, login, register, logout, fetchUser | ✅ |
| `types/index.ts` | ~330 | 30+ tipuri TypeScript complete | ✅ |

**Ce mai trebuie făcut:**
- [ ] Directoarele `src/services/` și `src/utils/` sunt goale (logica e în `lib/`) — de curățat sau populat

---

## 10. Frontend — Pagini

**Locație:** `frontend/src/pages/`  
**Status:** 🟡 80% complet — 27 pagini, dar cu buguri sistematice

### Pagini 100% funcționale (API paths corecte, fără buguri):

| Pagină | Linii | Funcționalități |
|--------|-------|-----------------|
| `LoginPage.tsx` | ~110 | Form email/password, animație orbit, error handling |
| `RegisterPage.tsx` | ~185 | 6 câmpuri, validare client-side |
| `DashboardPage.tsx` | 552 | Period filter, 4 KPI, ESG/Fraud/BNR/Contracts widgets, Risk pie, CAEN bar, SFDR, WS alerts live |
| `SearchPage.tsx` | ~235 | Căutare full-text, filtre avansate (județ, stare, CA, angajați, CAEN, datorii), 6 sortări, 42 județe |
| `CompanyProfilePage.tsx` | 658 | **10 tab-uri**: General, Financiar (LineChart + tabel), Risc (RadarChart), ESG (CSRD/SFDR), Persoane, Juridic, Contracte, Datorii, Proiecte UE, Fraud |
| `PortfoliosPage.tsx` | ~160 | CRUD: list cards, create, delete, navigate |
| `AlertsPage.tsx` | ~145 | List cu read/unread, mark individual/all, 13 tipuri, navigare companie |
| `SEAPPage.tsx` | ~130 | Căutare licitații, filtrare CPV, statistici chart, carduri |
| `NewCompaniesPage.tsx` | ~155 | Stats (azi/săptămîna/luna), bar chart per județ, tabel sortabil |
| `ESGDashboardPage.tsx` | ~120 | ESG legend cards, Top 20 ranking |
| `RedBillPage.tsx` | ~165 | Căutare CUI, summary cards, tabel datorii, generare raport, warning freshness |
| `ReportsPage.tsx` | ~110 | Lista exporturi, status icons, download links, polling 5s |
| `AdminPage.tsx` | 555 | 5 tab-uri: Overview (KPI + data sources + sync), Users (invite/search/role/toggle/credits), Organizations, GDPR (export/anonymize, audit log), Feature Flags |
| `AIAgentPage.tsx` | ~365 | Chat interface, non-streaming (POST) + streaming (SSE), suggested queries, proactive insights, token count |

### Pagini cu bug API path dublu (12 pagini — `/api/v1/api/v1/...`):

> ⚠️ Aceste pagini folosesc `api.get('/api/v1/...')` dar Axios baseURL este deja `/api/v1`, rezultând path dublu.

| Pagină | Linii | Funcționalități | Bug TabNav? |
|--------|-------|-----------------|-------------|
| `PredictivePage.tsx` | ~555 | 4 tabs: Forecast (area chart + table + confidence), Bankruptcy (gauge + risk factors), Degradation, Sector Trends | ✅ Da |
| `RelationshipsPage.tsx` | 345 | 5 tabs: UBO (%), Contagion, Directors, Group, Timeline | ✅ Da |
| `DueDiligencePage.tsx` | 384 | 5 tabs: Checklist (DD score + verdict), Red Flags, Peers, Compliance, Full Report | ✅ Da |
| `MarketIntelligencePage.tsx` | 313 | 5 tabs: Competitors, Benchmarks, Market Sizing, M&A Targets, Price Intelligence | ✅ Da |
| `SupplyChainPage.tsx` | ~290 | 5 tabs: Network, Dependencies, Disruptions, Alternatives, Score | ✅ Da |
| `DocumentIntelligencePage.tsx` | ~260 | 5 tabs: Classify, Financial Parser, Contract Analysis, Entity Extraction, Compare | ✅ Da |
| `RegulatoryCompliancePage.tsx` | ~280 | 5 tabs: GDPR, Fiscal, Environmental, Labor, AML | ✅ Da |
| `GeospatialPage.tsx` | ~280 | 5 tabs: Heatmap (fără hartă reală!), Zones, Proximity, County Detail, All Counties | ✅ Da |
| `APIMarketplacePage.tsx` | 432 | 5 tabs: API Keys (create/revoke), Usage (charts), Rate Limits, SDK & Docs, Webhooks | ✅ Da |
| `PortfolioOptimizationPage.tsx` | 383 | 5 tabs: Optimize (Markowitz), Rebalance, Benchmark, Attribution, Scenarios | ✅ Da |
| `InternationalExpansionPage.tsx` | 366 | 5 tabs: Cross-border, FX Risk, Market Entry, Regulatory Comparison, Translations | ✅ Da |
| `BlockchainAuditPage.tsx` | 338 | 5 tabs: Audit Trail, Hash Document, Smart Contract, Chain of Custody, Timestamp | ✅ Da |

### Pagină cu placeholder:

| Pagină | Linii | Problema |
|--------|-------|---------|
| `FraudGraphPage.tsx` | ~165 | Vizualizarea grafului = placeholder div ("React Flow se va integra aici"), RestFlow instalat dar neintegrat |

**Ce mai trebuie făcut:**
- [ ] **CRITIC** — Corectare API path dublu în 12 pagini (eliminare `/api/v1/` prefix, folosire path relativ)
- [ ] **CRITIC** — Corectare props TabNav în 12 pagini (`key`→`id`, `active`→`activeTab`, `onChange`→`onTabChange`)
- [ ] Integrare ReactFlow în `FraudGraphPage.tsx` pt vizualizare graf
- [ ] Integrare Leaflet hartă reală în `GeospatialPage.tsx` (doar bar/pie charts acum)
- [ ] Fix type mismatches: `SEAPPage` (câmpuri românești vs englezești), `ReportsPage` (`tip` → `export_type`)
- [ ] `CompanyProfilePage` — câmpuri inexistente în tip (`nr_reg_com`, `adresa`)

---

## 11. Frontend — Componente & Hooks

**Locație:** `frontend/src/components/` + `frontend/src/hooks/`  
**Status:** 🟢 90% complet

### Componente (14)

| Component | Linii | Status |
|-----------|-------|--------|
| `DashboardLayout.tsx` | ~195 | ✅ Sidebar colapsabil, 11 nav items, mobile responsive, badge alerte, avatar |
| `ErrorBoundary.tsx` | ~60 | ✅ Catch errori render, retry button |
| `LoadingSpinner.tsx` | ~40 | ✅ 3 mărimi, Orbit icon |
| `EmptyState.tsx` | ~35 | ✅ Icon configurabil, mesaj, subtitle, action slot |
| `Pagination.tsx` | ~45 | ✅ Prev/next cu page info |
| `DisclaimerBanner.tsx` | ~30 | ✅ Warning/info variants |
| `Badge.tsx` | ~30 | ✅ 5 variants, 2 mărimi |
| `SectionHeader.tsx` | ~25 | ✅ Titlu, subtitle, actions slot |
| `TabNav.tsx` | ~95 | ✅ Pills + underline variants, icons, badge counts |
| `StatCard.tsx` | ~60 | ✅ KPI card cu gradient accent |
| `Skeleton.tsx` | ~75 | ✅ Skeleton, SkeletonCard, SkeletonTable |
| `CompanyRow.tsx` | ~55 | ✅ Row clickabil cu risk badge |
| `index.ts` (common) | 11 | ✅ Barrel export |
| `index.ts` (company) | 1 | ✅ Barrel export |

### Hooks (7)

| Hook | Linii | Status |
|------|-------|--------|
| `useDebounce.ts` | 17 | ✅ Generic, 300ms default |
| `useWebSocket.ts` | 35 | ✅ Wraps wsClient, max 50 alerts |
| `usePagination.ts` | 55 | ✅ Page/pageSize state, nav helpers |
| `useCompany.ts` | 50 | ✅ `useCompany`, `useCompanyFinancials`, `useRiskScore`, `useESGScore` |
| `useAlerts.ts` | 45 | ✅ Polling 30s/15s |
| `useLocalStorage.ts` | 30 | ✅ Generic, SSR-safe |
| `index.ts` | 6 | ✅ Barrel export |

**Ce mai trebuie făcut:**
- [ ] AdminPage folosește propriul `StatCard` local (props diferite) — de unificat cu `components/common/StatCard`

---

## 12. Infrastructură & DevOps

**Status:** 🟡 75% complet

### Docker Compose (187 linii) — 10 servicii

| Serviciu | Imagine | Port | Status |
|----------|---------|------|--------|
| `postgres` | 16-alpine | 5432 | ✅ Healthcheck, volum, tuning |
| `redis` | 7-alpine | 6379 | ✅ Healthcheck, volum |
| `elasticsearch` | 8.12.0 | 9200 | ✅ Single-node, memorie 2GB |
| `neo4j` | 5-community | 7474/7687 | ✅ APOC plugin |
| `minio` | latest | 9000/9001 | ✅ Console + API |
| `backend` | Custom | 8000 | ⚠️ `--reload` + `--workers 4` conflict |
| `celery-worker` | Custom | — | ✅ 5 cozi subscrise |
| `celery-beat` | Custom | — | ✅ Scheduler periodic |
| `frontend` | Node 20 Alpine | 3000 | ✅ Vite dev server |
| `nginx` | Alpine | 80/443 | ⚠️ Port 443 expus dar SSL neconfigurat |

### Nginx (105 linii)
- Rate limiting: API 30r/s, Auth 5r/s
- Security headers configurate
- WebSocket support (alerts + Vite HMR)
- **Lipsă HTTPS/SSL block**

**Ce mai trebuie făcut:**
- [ ] **CRITIC** — Crea fișier `.env.example` (referit în README, nu există)
- [ ] Fix `docker-compose.yml` — elimina `--workers 4` cu `--reload` (incompatibil)
- [ ] Configura SSL/HTTPS în nginx (certificat Let's Encrypt/auto-signed)
- [ ] Fix `VITE_API_URL=http://backend:8000` — nu funcționează din browser (trebuie URL nginx)
- [ ] Adăuga `worker_processes auto;` în nginx.conf
- [ ] Adăuga caching headers pt assets statice frontend
- [ ] Configurare `proxy_buffering off` pt SSE streaming
- [ ] Separare rețele Docker (frontend/backend/data)
- [ ] Adăuga monitoring (Prometheus + Grafana sau similar)

---

## 13. Documentație Existentă

| Fișier | Linii | Completitudine | Probleme |
|--------|-------|----------------|----------|
| `README.md` | 146 | 70% | `.env.example` lipsă, comandă migrare incorectă, lipsă instrucțiuni teste |
| `docs/API.md` | 110 | 50% | Doar 42 din ~70 endpoints documentate, zero exemple request/response |
| `docs/AUDIT_REPORT.md` | 699 | 90% | Constrângerile #5/#6 lipsă, data veche (2025) |
| `prompt...md` | 3587 | 100% (spec) | Specificație master, multe features neimplementate (SSR, mobile, TimescaleDB) |

**Ce mai trebuie făcut:**
- [ ] Actualiza `docs/API.md` — documenta toate ~70 endpoints cu exemple
- [ ] Actualiza `README.md` — corecta comenzi, adăuga prerequisites, instrucțiuni dev local, teste
- [ ] Crea `.env.example` cu toate variabilele necesare
- [ ] Actualiza `AUDIT_REPORT.md` cu data curentă

---

## 14. Teste

**Status:** 🔴 5% complet

| Fișier | Teste | Ce testează |
|--------|-------|-------------|
| `test_api.py` | 2 | `test_health`, `test_login_invalid` |
| `test_validators.py` | 3 | CUI valid, CUI invalid, CUI cu prefix RO |
| **Total** | **5** | — |

**Ce mai trebuie făcut:**
- [ ] Teste unitare pt fiecare serviciu (risk_scoring, esg_scoring, fraud_graph, etc.)
- [ ] Teste integrare pt endpoints API (auth flow, CRUD companies, search)
- [ ] Teste pt colectori (mock external APIs)
- [ ] Teste pt Celery tasks
- [ ] Teste pt middleware (GDPR, multi-tenancy)
- [ ] Teste pt WebSocket alerts
- [ ] Teste pt AI agent
- [ ] Teste frontend (React Testing Library / Vitest)
- [ ] Setup CI/CD pipeline pt rulare teste automat

---

## 15. Buguri Cunoscute

### 🔴 CRITICE (blochează funcționalitatea)

1. **API Path Dublu** — 12 pagini frontend fac `api.get('/api/v1/...')` dar Axios baseURL e deja `/api/v1` → path devine `/api/v1/api/v1/...` → HTTP 404. Pagini afectate: PredictivePage, RelationshipsPage, DueDiligencePage, MarketIntelligencePage, SupplyChainPage, DocumentIntelligencePage, RegulatoryCompliancePage, GeospatialPage, APIMarketplacePage, PortfolioOptimizationPage, InternationalExpansionPage, BlockchainAuditPage.

2. **TabNav Props Greșite** — Aceleași 12 pagini pasează `key`/`active`/`onChange` în loc de `id`/`activeTab`/`onTabChange` → tab-urile nu se evidențiază și nu răspund la click.

### 🟡 MEDII (funcționalitate degradată)

3. **Type Mismatches** — `SEAPPage` folosește câmpuri românești (`autoritate_contractanta`) dar tipul TypeScript definește câmpuri englezești (`authority_name`). Similar `ReportsPage` (`tip` vs `export_type`).

4. **Blockchain Audit In-Memory** — Hash chain-ul se pierde la restart server.

5. **API Marketplace In-Memory** — Cheile API, usage, webhooks nu sunt persistate.

### 🟢 MINORE (cosmetice/îmbunătățiri)

6. **FraudGraphPage** — Vizualizare graf placeholder (ReactFlow instalat dar neintegrat)
7. **GeospatialPage** — Fără hartă Leaflet (instalat dar nefolosit)
8. **AdminPage** — StatCard local duplicat vs componenta comună
9. **Parola superadmin hardcoded** — `Admin123!` în `seed_admin.py`
10. **`npm run dev` eșuează** — Posibil dependințe neinstalate (ultimul exit code = 1)

---

## 16. Tabel Rezumativ per Modul

| # | Modul | Fișiere | Linii | % Gata | Prioritate Acțiune |
|---|-------|---------|-------|--------|---------------------|
| 1 | Backend Core | 6 | ~425 | 95% | 🟢 Minor — chei RSA, CORS |
| 2 | Modele BD | 2 | ~1650 | 100% | 🟢 OK — migrare Alembic opțional |
| 3 | Schemas | 1 | ~700 | 100% | 🟢 OK |
| 4 | API Endpoints | 28 | ~5000 | 95% | 🟢 OK |
| 5 | Servicii Backend | 19 | ~10,500 | 85% | 🟡 api_marketplace + blockchain → DB |
| 6 | Colectori Date | 11 | ~1170 | 80% | 🟡 AEGRM, OSIM, + surse noi |
| 7 | Celery Tasks | 8 | ~1400 | 90% | 🟢 Minor — SMS |
| 8 | Middleware/Utils | 3 | ~350 | 95% | 🟢 OK |
| 9 | Frontend Infra | 8 | ~760 | 90% | 🟢 OK |
| 10 | Frontend Pagini | 27 | ~7470 | 80% | 🔴 Fix API paths + TabNav (12 pagini) |
| 11 | Frontend Componente | 14 | ~830 | 90% | 🟢 OK |
| 12 | Frontend Hooks | 7 | ~240 | 100% | 🟢 OK |
| 13 | Docker/Nginx | 2 | ~290 | 75% | 🟡 SSL, .env, fix conflicte |
| 14 | Documentație | 4 | ~955 | 70% | 🟡 API.md, README, .env.example |
| 15 | Teste | 2 | ~40 | 5% | 🔴 Aproape inexistente |

---

## 17. Lista Completă TODO — Ce Rămâne de Făcut

### 🔴 Prioritate CRITICĂ (trebuie făcute primele)

- [ ] **Fix API path dublu în 12 pagini** — elimina `/api/v1/` din apelurile `api.get()`/`api.post()` (toate trebuie să fie path-uri relative, ex: `/predictive/forecast` nu `/api/v1/predictive/forecast`)
- [ ] **Fix TabNav props în 12 pagini** — `key`→`id`, `active`→`activeTab`, `onChange`→`onTabChange`
- [ ] **Crea `.env.example`** cu toate variabilele necesare
- [ ] **Fix `docker-compose.yml`** — elimina `--workers 4` de la backend (incompatibil cu `--reload`)

### 🟡 Prioritate MEDIE (funcționalitate completă)

- [ ] Fix type mismatches: SEAPPage, ReportsPage, CompanyProfilePage
- [ ] Migra `api_marketplace.py` din in-memory în tabele DB
- [ ] Migra `blockchain_audit.py` din hash chain in-memory în DB
- [ ] Implementa upload MinIO pt rapoarte generate
- [ ] Implementa SMS notifications (Twilio/Vonage) în `notification_tasks.py`
- [ ] Implementa sync automat `aegrm.py` (garanții mobiliare)
- [ ] Implementa sync automat `osim.py` (mărci/brevete)
- [ ] Integra ReactFlow pt vizualizare graf fraud în `FraudGraphPage.tsx`
- [ ] Integra Leaflet hartă reală în `GeospatialPage.tsx`
- [ ] Configura SSL/HTTPS nginx + certificat
- [ ] Fix `VITE_API_URL` în docker-compose (trebuie URL accesibil din browser)
- [ ] Crea script setup index Elasticsearch (analyzer + mapping)
- [ ] Crea schema/constraints Neo4j

### 🟢 Prioritate SCĂZUTĂ (polish & extras)

- [ ] Scrie teste unitare pt servicii (minim risk, esg, fraud)
- [ ] Scrie teste integrare pt API endpoints
- [ ] Scrie teste frontend (React Testing Library)
- [ ] Actualiza `docs/API.md` — toate ~70 endpoints + exemple
- [ ] Actualiza `README.md` — corecta comenzi, prerequisites, dev workflow
- [ ] Adăuga Alembic pt migrări incrementale
- [ ] Restricționa CORS pt producție (nu `r".*"`)
- [ ] Genera chei RSA pt producție
- [ ] Schimba parola superadmin din hardcoded
- [ ] Adăuga colector BVB (Bursa de Valori București)
- [ ] Adăuga colector ASF (Autoritatea de Supraveghere Financiară)
- [ ] Adăuga colector INS (Institutul Național de Statistică)
- [ ] Unifica StatCard component (AdminPage local vs common)
- [ ] Separa rețele Docker
- [ ] Adăuga monitoring (Prometheus/Grafana)
- [ ] Document Intelligence — ML/NLP upgrade (opțional, regex funcționează)
- [ ] Configurare CI/CD pipeline
- [ ] Curăța directoarele goale (`src/services/`, `src/utils/`)

### 📋 Features din Specificație Neimplementate Încă

| Feature din Prompt | Status | Efort Estimat |
|--------------------|--------|---------------|
| Next.js SSR | ❌ Neimplementat (React SPA) | Mare — restructurare completă |
| React Native Mobile | ❌ Neimplementat | Mare — proiect separat |
| TimescaleDB time-series | ❌ Neimplementat | Mediu |
| Kong API Gateway | ❌ Neimplementat (Nginx) | Mediu |
| Sigma.js/D3.js fraud viz | ❌ Neimplementat (placeholder) | Mediu |
| BVB data source | ❌ Neimplementat | Mic |
| ASF data source | ❌ Neimplementat | Mic |
| INS data source | ❌ Neimplementat | Mic |
| `data_quality_score` | ❌ Neimplementat | Mic |

---

> **Concluzie:** Proiectul este **~82% complet** cu o bază solidă. Cele mai urgente acțiuni sunt fix-urile de buguri frontend (API paths + TabNav) care afectează 12 pagini, urmate de persistarea datelor in-memory și configurarea infrastructurii pt producție.
