# RomBiz Intelligence Platform

> **Platformă completă de Business Intelligence pentru firmele din România.**  
> Colectare date din 12+ surse publice · Scoring risc (Altman Z-Score) · ESG/CSRD · Fraud Graph (Neo4j) · AI Agent · Rapoarte PDF/Excel

---

## Cuprins

1. [Prezentare generală](#1-prezentare-generală)
2. [Stack tehnologic](#2-stack-tehnologic)
3. [Arhitectură](#3-arhitectură)
4. [Instalare rapidă (Docker)](#4-instalare-rapidă-docker)
5. [Configurare variabile de mediu](#5-configurare-variabile-de-mediu)
6. [Baza de date & migrări](#6-baza-de-date--migrări)
7. [Chei RSA (JWT RS256)](#7-chei-rsa-jwt-rs256)
8. [Surse de date (Colectori)](#8-surse-de-date-colectori)
9. [API Reference](#9-api-reference)
10. [Module principale (Backend)](#10-module-principale-backend)
11. [Frontend](#11-frontend)
12. [Celery — Task Queue](#12-celery--task-queue)
13. [Infrastructură & servicii auxiliare](#13-infrastructură--servicii-auxiliare)
14. [Securitate](#14-securitate)
15. [Testare](#15-testare)
16. [Deployment producție](#16-deployment-producție)
17. [Structura proiectului](#17-structura-proiectului)
18. [Constrângeri hard](#18-constrângeri-hard)
19. [Contribuții](#19-contribuții)

---

## 1. Prezentare generală

RomBiz Intelligence agregă date din surse publice oficiale și le transformă în intelligence acționabil:

| Capacitate | Descriere |
|---|---|
| **Profil 360° companie** | Date ONRC, ANAF, bilanțuri, persoane, adrese |
| **Scoring risc A–E** | Altman Z-Score adaptat + componente juridic/fiscal/comportamental |
| **ESG / CSRD** | Scoring Environmental-Social-Governance, aliniere EU Taxonomy, SFDR |
| **Fraud Graph** | Detecție proprietate circulară, rețele phoenix, clustering persoane (Neo4j) |
| **Alerte timp real** | WebSocket push + Email/SMS la modificări importante |
| **Due Diligence** | Rapoarte complete pentru parteneriate și investiții |
| **AI Agent** | Interogare în limbaj natural (Anthropic Claude) |
| **Piață publică** | Licitații SEAP, contracte câștigate, firme noi ONRC |
| **Rapoarte** | Export PDF, XLSX, CSV, JSON, HTML stocate în MinIO |
| **API Marketplace** | Expunere date ca API comercial cu chei per-tenant |

---

## 2. Stack Tehnologic

| Layer | Tehnologie | Versiune |
|---|---|---|
| **Backend** | Python + FastAPI (async/await) | 3.12 / 0.115 |
| **ORM** | SQLAlchemy async | 2.0 |
| **Baza de date** | PostgreSQL | 16 |
| **Search** | Elasticsearch (analyzer ro) | 8.12 |
| **Cache / Broker** | Redis | 7 |
| **Task Queue** | Celery + Beat Scheduler | 5.4 |
| **Graph DB** | Neo4j Community | 5 |
| **Object Storage** | MinIO (S3-compatible) | latest |
| **Auth** | JWT RS256 (HS256 fallback dev) | jose / pyjwt |
| **AI** | Anthropic Claude (function calling) | claude-3-5 |
| **Frontend** | React + TypeScript + Vite | 18.3 / 5.4 |
| **Styling** | Tailwind CSS (cosmic/space theme) | 3.4 |
| **State** | Zustand (auth) + TanStack Query | 5.0 |
| **Proxy** | Nginx (SSL, rate-limit, gzip, WS) | alpine |
| **Container** | Docker Compose | v3.9 |
| **Monitoring** | Sentry (errors + traces) | SDK |

---

## 3. Arhitectură

```
                          ┌─────────────────────────────┐
                          │         Nginx (80/443)       │
                          │  Rate-limit · SSL · gzip      │
                          └────────┬──────────┬──────────┘
                                   │          │
                         ┌─────────▼──┐  ┌────▼────────┐
                         │  Frontend  │  │  Backend API │
                         │ React/Vite │  │  FastAPI     │
                         │  :3000     │  │  :8000       │
                         └────────────┘  └──┬───────────┘
                                            │
              ┌─────────────────────────────┼──────────────────────┐
              │                             │                      │
    ┌─────────▼──────┐          ┌──────────▼──────┐     ┌────────▼──────┐
    │  PostgreSQL 16 │          │   Redis 7        │     │ Elasticsearch │
    │  Primary DB    │          │  Cache · Broker  │     │  Full-text    │
    └────────────────┘          └─────────┬────────┘     └───────────────┘
                                          │
                              ┌──────────▼──────┐
                              │  Celery Workers  │
                              │  + Beat Scheduler│
                              └──────────────────┘
              ┌───────────────────────────────────────┐
              │  Supporting Services                    │
              │  Neo4j (Fraud Graph) · MinIO (Files)   │
              │  Sentry (APM) · Twilio (SMS)           │
              └───────────────────────────────────────┘
```

---

## 4. Instalare rapidă (Docker)

### Cerințe pre-instalare
- Docker ≥ 24.x și Docker Compose v2
- 4 GB RAM disponibil (8 GB recomandat pentru toate serviciile)
- 20 GB spațiu pe disc

### Pași

```bash
# 1. Clonează proiectul
git clone https://github.com/yourorg/rombiz-platform.git
cd rombiz-platform

# 2. Copiază și editează variabilele de mediu
cp .env.example .env
nano .env   # Setează parolele, cheile API, etc.

# 3. Generează chei RSA pentru JWT (obligatoriu)
mkdir -p backend/keys
openssl genrsa -out backend/keys/private.pem 4096
openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem

# 4. Pornește toate serviciile
docker compose up -d

# 5. Inițializează baza de date
docker compose exec backend python seed_admin.py

# 6. (Opțional) Încarcă date de test
docker compose exec backend python seed_dummy_data.py
```

### Servicii disponibile după pornire

| Serviciu | URL |
|---|---|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **API Docs (ReDoc)** | http://localhost:8000/redoc |
| **Nginx Proxy** | http://localhost |
| **MinIO Console** | http://localhost:9001 |
| **Neo4j Browser** | http://localhost:7474 |
| **Elasticsearch** | http://localhost:9200 |
| **PostgreSQL** | localhost:5432 |
| **Redis** | localhost:6379 |

---

## 5. Configurare variabile de mediu

Copiați `.env.example` în `.env` și completați valorile:

```env
# ── Aplicație ─────────────────────────────────────────────
APP_NAME=RomBiz Intelligence
APP_VERSION=1.0.0
ENVIRONMENT=development          # development | production
DEBUG=true

# ── Baza de date ──────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://rombiz:changeme@postgres:5432/rombiz
POSTGRES_PASSWORD=changeme       # Schimbați obligatoriu!

# ── Redis & Celery ────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# ── Elasticsearch ─────────────────────────────────────────
ELASTICSEARCH_URL=http://elasticsearch:9200

# ── Neo4j ─────────────────────────────────────────────────
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme          # Schimbați obligatoriu!

# ── MinIO / S3 ────────────────────────────────────────────
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=changeme        # Schimbați obligatoriu!
MINIO_SECURE=false               # true în producție

# ── JWT ───────────────────────────────────────────────────
JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Administrator implicit ────────────────────────────────
ADMIN_EMAIL=admin@rombiz.ro
ADMIN_PASSWORD=                  # Generat automat dacă e gol

# ── Anthropic AI ──────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...

# ── Sentry ────────────────────────────────────────────────
SENTRY_DSN=https://xxx@sentry.io/yyy

# ── SMTP (Email) ──────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@rombiz.ro
SMTP_PASSWORD=...
SMTP_FROM=noreply@rombiz.ro

# ── SMS (Twilio) ──────────────────────────────────────────
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+40...

# ── CORS ──────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:3000","https://rombiz.ro"]
```

> **Notă:** în producție, schimbați **obligatoriu** toate parolele din `.env` și setați `ENVIRONMENT=production`.

---

## 6. Baza de date & migrări

### Inițializare cu Alembic (recomandat)

```bash
# Din directorul backend/
cd backend

# Prima migrare (autogenerate bazat pe modele)
alembic revision --autogenerate -m "initial_schema"

# Aplică migrarea
alembic upgrade head

# Verificare stare
alembic current
alembic history
```

### Inițializare directă cu SQL (alternativă)

```bash
docker compose exec postgres psql -U rombiz -d rombiz -f \
  /docker-entrypoint-initdb.d/001_initial_schema.sql
```

### Seed admin

```bash
# Crează superadmin-ul din .env (ADMIN_EMAIL + ADMIN_PASSWORD)
docker compose exec backend python seed_admin.py
```

Dacă `ADMIN_PASSWORD` nu e setat în `.env`, parola este generată automat și afișată o singură dată în consolă — **salvați-o imediat!**

### Seed date de test

```bash
docker compose exec backend python seed_dummy_data.py
```

---

## 7. Chei RSA (JWT RS256)

JWT-urile sunt semnate cu RS256 în producție. Generați cheile înainte de prima pornire:

```bash
mkdir -p backend/keys

# Generare cheie privată 4096-bit
openssl genrsa -out backend/keys/private.pem 4096

# Extragere cheie publică
openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem
```

> **Atenție:** Fișierele `keys/private.pem` și `keys/public.pem` sunt în `.gitignore`. **Nu le commitați niciodată în repository!**

În development (fără chei), sistemul folosește automat HS256 cu un secret hardcodat și afișează un warning. Această stare **nu este permisă în producție**.

---

## 8. Surse de date (Colectori)

Platforma sincronizează date din 11 surse publice:

| Colector | Sursă | Date colectate | Frecvență |
|---|---|---|---|
| `anaf.py` | ANAF | TVA, Split TVA, inactivi fiscali, bilanțuri | Zilnic |
| `onrc.py` | ONRC | Date registru comerț, asociați, administratori | La cerere (cache 30 zile) |
| `bpi.py` | BPI.ro | Proceduri insolvență, dosare tribunal | Zilnic (RSS) |
| `portal_just.py` | PortalJust | Dosare judecătorești, termene | Zilnic |
| `aegrm.py` | AEGRM/RNPM | Gajuri, ipoteci, datorii AEGRM | Săptămânal |
| `osim.py` | OSIM | Mărci înregistrate, brevete | Săptămânal |
| `seap.py` | SEAP/SICAP | Licitații publice, contracte atribuite | Zilnic |
| `bnr.py` | BNR | Cursuri valutare EUR/RON | Zilnic (unica sursă valutară) |
| `ins.py` | INS | Statistici macroeconomice, indicatori sector | Lunar |
| `monitor_oficial.py` | MOF | Publicații Monitor Oficial | Zilnic |
| `mysmis.py` | MySMIS | Proiecte fonduri europene | Săptămânal |
| `bvb.py` | BVB | Date companii listate (BET) | Zilnic |
| `asf.py` | ASF | Companii reglementate ASF | Lunar |

### Declanșarea manuală a unui sync

```bash
# Via API (rol admin):
curl -X POST http://localhost:8000/api/v1/admin/sync/anaf \
  -H "Authorization: Bearer <TOKEN>"

# Via Celery direct:
docker compose exec backend celery -A app.tasks.celery_app:celery_app \
  call app.tasks.sync_tasks.sync_anaf
```

---

## 9. API Reference

### Base URL

```
# Development
http://localhost:8000/api/v1

# Producție
https://api.rombiz.ro/api/v1
```

### Autentificare

Toate endpoint-urile (excepție: `/auth/*`) necesită header:

```
Authorization: Bearer <access_token>
```

Token-urile sunt RS256 JWT cu exp. 30 minute. Refresh automat cu `/auth/refresh`.

### Endpoint-uri principale

#### Auth
| Metodă | Path | Descriere |
|---|---|---|
| POST | `/auth/register` | Înregistrare cont + organizație |
| POST | `/auth/login` | Login → access + refresh token |
| POST | `/auth/refresh` | Rotație refresh token |
| GET | `/auth/me` | Profil utilizator curent |

#### Companii
| Metodă | Path | Descriere |
|---|---|---|
| GET | `/companies/{cui}` | Profil complet companie |
| GET | `/companies/{cui}/financial` | Date financiare (all years, DESC) |
| GET | `/companies/{cui}/persons` | Asociați + administratori |
| GET | `/companies/{cui}/insolvency` | Cazuri insolvență (BPI) |
| GET | `/companies/{cui}/court-cases` | Dosare judecătorești |
| GET | `/companies/{cui}/contracts` | Contracte publice (SEAP) |
| GET | `/companies/{cui}/eu-projects` | Proiecte fonduri UE |
| GET | `/companies/{cui}/mentions` | Mențiuni Monitor Oficial |
| POST | `/companies/batch` | Batch fetch (max 500 CUIs) |

#### Căutare
| Metodă | Path | Descriere |
|---|---|---|
| POST | `/search/` | Căutare avansată (50+ filtre) |
| GET | `/search/autocomplete?q=` | Autocompletare prefix |
| GET | `/search/facets` | Agregări (județe, CAEN, etc.) |

#### Risk Scoring
| Metodă | Path | Descriere |
|---|---|---|
| GET | `/risk/{cui}` | Scor risc curent (A–E) |
| GET | `/risk/{cui}/history` | Istoric scoruri |
| POST | `/risk/{cui}/recalculate` | Recalculare forțată |

#### ESG
| Metodă | Path | Descriere |
|---|---|---|
| GET | `/esg/{cui}` | Scor ESG + disclaimer |
| GET | `/esg/ranking` | Top companii ESG pe sector |

#### Fraud Graph
| Metodă | Path | Descriere |
|---|---|---|
| GET | `/fraud/{cui}` | Profil fraud (anomaly score, alerte) |
| GET | `/fraud/{cui}/graph` | Subgraf relații (noduri + muchii) |

#### Alerte
| Metodă | Path | Descriere |
|---|---|---|
| WS | `/alerts/ws/{token}` | WebSocket notificări real-time |
| GET | `/alerts/` | Lista alerte (paginat) |
| GET | `/alerts/unread-count` | Nr. necitite |
| PUT | `/alerts/{id}/read` | Marchează citit |
| PUT | `/alerts/mark-all-read` | Marchează toate citite |

#### Portofolii
| Metodă | Path | Descriere |
|---|---|---|
| GET | `/portfolios/` | Lista portofolii |
| POST | `/portfolios/` | Creare portofoliu |
| POST | `/portfolios/{id}/companies` | Adaugă companie |
| GET | `/portfolios/{id}/risk-summary` | Sumar risc portofoliu |

#### Rapoarte
| Metodă | Path | Descriere |
|---|---|---|
| POST | `/reports/company/{cui}` | Generare raport (PDF/XLSX/CSV/JSON/HTML) |
| POST | `/reports/portfolio/{id}` | Raport portofoliu |
| GET | `/reports/exports` | Lista exporturi |
| GET | `/reports/exports/{id}/download` | Stream fișier din MinIO |

#### Admin (rol: admin)
| Metodă | Path | Descriere |
|---|---|---|
| GET | `/admin/dashboard` | Dashboard statistici |
| GET | `/admin/data-sources` | Health surse date |
| POST | `/admin/sync/{source}` | Trigger sync manual |
| GET | `/admin/audit-log` | Jurnal audit |

#### AI Agent
| Metodă | Path | Descriere |
|---|---|---|
| POST | `/ai-agent/query` | Întrebare în limbaj natural |
| GET | `/ai-agent/history` | Istoricul conversațiilor |

### Coduri de eroare

| Cod | Semnificație |
|---|---|
| 400 | Request invalid |
| 401 | Token expirat / invalid |
| 403 | Rol insuficient |
| 404 | Resursă negăsită |
| 422 | Validare eșuată (CUI invalid, etc.) |
| 429 | Rate limit depășit |
| 500 | Eroare internă server |

### Rate Limiting

- **General:** 30 req/s per IP (configurat Nginx)
- **Auth:** 5 req/s (protecție brute-force)
- **AI Agent:** 10 req/minut per user

---

## 10. Module principale (Backend)

### `app/core/`
| Modul | Rol |
|---|---|
| `config.py` | Pydantic Settings — toate variabilele de config din `.env` |
| `database.py` | SQLAlchemy async engine, `get_db()` FastAPI dependency |
| `security.py` | JWT RS256, bcrypt, `get_current_user()`, `require_role()` RBAC |
| `redis.py` | Redis singleton client |
| `logging.py` | structlog JSON, ISO timestamps |
| `compat_types.py` | TypeDecorators SQLite/PostgreSQL dual-dialect |
| `rate_limit.py` | Rate limiting decoratori per-endpoint |

### `app/models/models.py`
35+ modele SQLAlchemy ORM:

| Model | Tabel | Descriere |
|---|---|---|
| `Organization` | organizations | Tenant (multi-tenancy root) |
| `User` | users | Utilizatori cu rol (admin/analyst/viewer) |
| `Company` | companies | Entitate centrală — date ONRC |
| `FinancialData` | financial_data | Bilanțuri anuale |
| `CompanyPerson` | company_persons | Asociați, administratori, directori |
| `InsolvencyCase` | insolvency_cases | Dosare BPI |
| `CourtCase` | court_cases | Dosare Portal Just |
| `CompanyDebt` | company_debts | Datorii AEGRM |
| `PublicContract` | public_contracts | Contracte SEAP |
| `RiskScore` | risk_scores | Scoruri risc calculate |
| `ESGScore` | esg_scores | Scoruri ESG calculate |
| `FraudAlert` | fraud_alerts | Alerte fraud detectate |
| `Trademark` | trademarks | Mărci OSIM |
| `StatisticSnapshot` | statistic_snapshots | Date statistice INS |
| `Alert` | alerts | Alerte utilizatori |
| `Portfolio` | portfolios | Portofolii de monitorizare |
| `ReportExport` | report_exports | Rapoarte generate |
| `DataSourceSyncLog` | data_source_sync_logs | Jurnal sync colectori |

### `app/services/`

| Serviciu | Descriere |
|---|---|
| `risk_scoring.py` | Altman Z-Score + 4 componente, profil risc, credit limit, benchmark sector |
| `esg_scoring.py` | E/S/G scoring, CSRD readiness, EU Taxonomy, SFDR, GRI mapping |
| `fraud_graph.py` | Ownership circular, phoenix, clustering, anomaly scoring (Neo4j + PG fallback) |
| `search_service.py` | Elasticsearch full-text + PostgreSQL fallback, autocomplete, facete |
| `reports_service.py` | Generare PDF/XLSX/CSV/JSON/HTML, upload MinIO |
| `alerts_service.py` | Creare, routing și notificare alerte |
| `due_diligence.py` | Raport complet due diligence |
| `redbill_service.py` | Evaluare comportament de plată |
| `predictive.py` | Predicție insolvență (logistic regression) |
| `document_intelligence.py` | Extragere structurată din documente |
| `esg_portfolio.py` | Agregare ESG pe portofoliu |
| `supply_chain.py` | Analiză lanț de aprovizionare |
| `market_intel.py` | Intelligence de piață |
| `blockchain_audit.py` | Audit trail imutabil |
| `api_marketplace.py` | Gestionare chei API comerciale |

---

## 11. Frontend

### Tehnologii
- React 18.3 + TypeScript 5.4
- Vite 5 (build tool)
- Tailwind CSS (tema cosmic/space)
- Zustand (auth store)
- TanStack Query v5 (server state)
- ReactFlow (graf fraud vizual)
- Recharts (grafice)
- shadcn/ui (componente UI)

### Pagini (Rute)
| Rută | Pagină | Descriere |
|---|---|---|
| `/` | Dashboard | KPI-uri, distribuție risc, alerte recente |
| `/login` | Login | Autentificare |
| `/register` | Register | Înregistrare cont |
| `/search` | Search | Căutare full-text companii |
| `/company/:cui` | Company Profile | 11 tab-uri (General, Financiar, Persoane, etc.) |
| `/portfolios` | Portfolios | Gestiune portofolii |
| `/alerts` | Alerts | Lista alerte + notificări |
| `/fraud` | Fraud Graph | Vizualizare graf relații |
| `/esg` | ESG Dashboard | Scoruri ESG și ranking |
| `/redbill` | RedBill | Datorii restante |
| `/seap` | SEAP | Licitații publice |
| `/new-companies` | New Companies | Firme noi ONRC |
| `/reports` | Reports | Generare și descărcare rapoarte |
| `/ai-agent` | AI Agent | Chat AI pentru date companii |
| `/admin` | Admin | Dashboard administrare (rol admin) |

### Build pentru producție

```bash
cd frontend
npm install
npm run build
# Artefactele sunt în frontend/dist/
```

---

## 12. Celery — Task Queue

Celery folosește Redis ca broker și result backend. Există **5 cozi** specializate:

| Coadă | Scop |
|---|---|
| `default` | Task-uri generale |
| `sync` | Sincronizare surse de date |
| `compute` | Risk / ESG scoring (CPU-intensive) |
| `reports` | Generare rapoarte |
| `notifications` | Email, SMS, push notifications |

### Task-uri periodice (Beat Scheduler)

| Task | Frecvență |
|---|---|
| Sync ANAF (TVA, inactivi) | Zilnic 02:00 |
| Sync BPI (insolvențe) | Zilnic 06:00 |
| Sync Portal Just | Zilnic 07:00 |
| Sync SEAP | Zilnic 08:00 |
| Sync BNR (curs valutar) | Zilnic 09:00 |
| Sync AEGRM | Săptămânal luni 03:00 |
| Recalculare risc companii | Zilnic 10:00 |
| Verificare alerte | La fiecare 15 minute |
| Cleanup exporturi vechi | Săptămânal |

### Monitorizare Celery

```bash
# Status worker-e
docker compose exec celery-worker celery -A app.tasks.celery_app:celery_app status

# Monitor în timp real (CLI)
docker compose exec celery-worker celery -A app.tasks.celery_app:celery_app events

# Flower (UI monitoring) — dacă este instalat
docker compose exec celery-worker celery -A app.tasks.celery_app:celery_app flower
```

---

## 13. Infrastructură & servicii auxiliare

### Nginx
- Reverse proxy pentru Backend (:8000) și Frontend (:3000)
- SSL/TLS termination (TLS 1.2 + 1.3, HSTS)
- Rate limiting: 30 req/s general, 5 req/s auth
- Gzip compression
- WebSocket support (`Upgrade: websocket`)
- SSE streaming (proxy buffering off)

### MinIO
- Bucket `reports` — rapoarte generate (PDF, XLSX, etc.)
- Bucket `pdfs` — documente procesate
- URL-uri presemnate valabile 7 zile
- Download via endpoint `/reports/exports/{id}/download` (streaming)

### Neo4j
- Grafuri de relații (companie ↔ persoană)
- Detecție ownership circular, carousele, clustere
- Fallback PostgreSQL dacă Neo4j nu e disponibil

### Elasticsearch
- Index `companies` cu Romanian analyzer
- Suport fuzzy matching, diacritice
- Fallback SQL ILIKE dacă ES nu e disponibil

### Sentry
- Integrat în FastAPI + SQLAlchemy
- `traces_sample_rate`: 20% producție, 100% development
- PII disabled (`send_default_pii=False`)

---

## 14. Securitate

| Măsură | Implementare |
|---|---|
| **Auth** | JWT RS256 (HS256 interzis în producție) |
| **Parole** | bcrypt fără limită de lungime |
| **CORS** | Restricționat la origini explicite (nu `*`) |
| **SSL** | TLS 1.2+, HSTS (nginx) |
| **Admin password** | Din `ADMIN_PASSWORD` env var, nu hardcodat |
| **RBAC** | 3 roluri: admin, analyst, viewer |
| **Rate limiting** | Nginx (30 req/s general, 5 req/s auth) |
| **GDPR** | Middleware anonimizare CNP, logging consimțământ |
| **Multi-tenancy** | Izolare date per organizație |
| **SQL injection** | Parametrizat prin SQLAlchemy ORM |
| **XSS** | Sanitizare input, Content-Security-Policy |

---

## 15. Testare

```bash
cd backend

# Toate testele
pytest -v

# Doar unitare
pytest tests/test_security.py tests/test_risk_scoring.py tests/test_esg_scoring.py -v

# Integrare API
pytest tests/test_api_integration.py -v

# Cu coverage
pytest --cov=app --cov-report=html
```

### Acoperire teste (77 teste)

| Modul | Teste | Acoperire |
|---|---|---|
| `core/security.py` | 11 | JWT, bcrypt, roluri |
| `services/risk_scoring.py` | 27 | Weights, categorii A-E, credit limit, Z-Score |
| `services/esg_scoring.py` | 22 | SFDR, GRI, taxonomy, carbon |
| `API integration` | 12 | Health, auth, companies, reports |
| `utils/validators.py` | 5 | CUI mod-11 |

---

## 16. Deployment producție

### Checklist obligatoriu înainte de lansare

- [ ] Setați `ENVIRONMENT=production` în `.env`
- [ ] Generați chei RSA și puneți-le în `backend/keys/`
- [ ] Schimbați TOATE parolele din `.env` (Postgres, Neo4j, MinIO, etc.)
- [ ] Configurați un domeniu real și certificate SSL (Let's Encrypt)
- [ ] Setați `ADMIN_PASSWORD` în `.env` (sau salvați parola generată)
- [ ] Configurați `SENTRY_DSN` pentru monitoring erori
- [ ] Configurați `SMTP_*` pentru notificări email
- [ ] Setați `CORS_ORIGINS` doar cu domeniile voastre
- [ ] Activați HTTPS în `nginx.conf` (certificatele SSL)
- [ ] Configurați backup automat pentru volumul `pgdata`
- [ ] Setați `MINIO_SECURE=true`

### Generare certificat SSL (Let's Encrypt)

```bash
# Cu Certbot
certbot certonly --standalone -d rombiz.ro -d www.rombiz.ro

# Copiați certificatele în nginx/ssl/
cp /etc/letsencrypt/live/rombiz.ro/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/rombiz.ro/privkey.pem nginx/ssl/key.pem
```

### Comenzi utile

```bash
# Restart serviciu specific
docker compose restart backend

# Urmărire logs
docker compose logs -f backend
docker compose logs -f celery-worker

# Actualizare cod (zero-downtime)
git pull
docker compose build backend frontend
docker compose up -d --no-deps backend frontend

# Backup baza de date
docker compose exec postgres pg_dump -U rombiz rombiz > backup_$(date +%Y%m%d).sql

# Restaurare backup
docker compose exec -T postgres psql -U rombiz rombiz < backup_20260101.sql
```

---

## 17. Structura proiectului

```
rombiz-platform/
├── .env.example                    # Template variabile de mediu
├── docker-compose.yml              # 10 servicii Docker
├── README.md                       # Această documentație
│
├── backend/
│   ├── alembic.ini                 # Configurare Alembic
│   ├── pytest.ini                  # Configurare pytest (asyncio_mode=auto)
│   ├── requirements.txt            # Dependențe Python (~40 pachete)
│   ├── seed_admin.py               # Script creare superadmin
│   ├── seed_dummy_data.py          # Date de test
│   │
│   ├── keys/                       # Chei RSA (gitignore!)
│   │   ├── private.pem
│   │   └── public.pem
│   │
│   ├── migrations/
│   │   ├── env.py                  # Alembic env (async support)
│   │   ├── script.py.mako          # Template migrare
│   │   └── versions/
│   │       └── 001_initial_schema.sql   # Schema SQL inițială
│   │
│   ├── app/
│   │   ├── main.py                 # FastAPI app, Sentry init, lifespan
│   │   │
│   │   ├── api/v1/
│   │   │   ├── router.py           # Mounting 14 routere
│   │   │   └── endpoints/          # auth, companies, search, risk, esg,
│   │   │                           # fraud, alerts, portfolios, redbill,
│   │   │                           # seap, reports, admin, ai_agent, new_companies
│   │   │
│   │   ├── collectors/             # 11 conectori surse externe
│   │   │   ├── base_connector.py   # BaseConnector (httpx async, rate-limit, retry)
│   │   │   ├── anaf.py / bpi.py / onrc.py / portal_just.py
│   │   │   ├── aegrm.py / osim.py / seap.py / bnr.py
│   │   │   ├── ins.py / monitor_oficial.py / mysmis.py
│   │   │   └── bvb.py / asf.py
│   │   │
│   │   ├── core/                   # config, database, security, redis, logging
│   │   ├── middleware/             # multi_tenancy.py, gdpr.py
│   │   ├── models/models.py        # 35+ SQLAlchemy modele
│   │   ├── schemas/schemas.py      # Pydantic v2 schemas
│   │   ├── services/               # 15 servicii business logic
│   │   ├── tasks/                  # Celery tasks (sync, compute, reports, notif)
│   │   └── utils/                  # validators.py (CUI mod-11, CNP)
│   │
│   └── tests/
│       ├── test_api.py             # Teste health + auth
│       ├── test_api_integration.py # Teste integrare API (mock DB)
│       ├── test_security.py        # JWT, bcrypt
│       ├── test_risk_scoring.py    # RiskScoringEngine unit tests
│       ├── test_esg_scoring.py     # ESGScoringEngine unit tests
│       └── test_validators.py      # CUI validator
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Router + layout
│   │   ├── pages/                  # 15 pagini React
│   │   ├── components/             # Componente reutilizabile
│   │   ├── services/               # API client (axios/fetch)
│   │   ├── store/                  # Zustand auth store
│   │   ├── hooks/                  # Custom hooks
│   │   ├── types/                  # TypeScript types
│   │   └── utils/                  # Utilități frontend
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
│
├── nginx/
│   └── nginx.conf                  # Proxy, SSL, rate-limit, WebSocket
│
└── docs/
    ├── API.md                      # Documentație API detaliată
    ├── GHID_UTILIZARE.md           # Ghid utilizator (română)
    ├── PROJECT_STATUS.md           # Status complet proiect
    └── AUDIT_REPORT.md             # Raport audit tehnic
```

---

## 18. Constrângeri hard

Reguli de business care nu pot fi modificate:

| # | Constrângere |
|---|---|
| 1 | JWT-urile sunt **RS256 în producție** — HS256 este interzis |
| 2 | Parolele admin nu sunt niciodată hardcodate — citite din env |
| 3 | CNP-urile sunt **hashed** înainte de stocare (SHA-256 + salt) |
| 4 | Cursul EUR/RON vine **exclusiv de la BNR** — fără alte surse |
| 5 | Toate scorurile includ **disclaimer** că sunt algoritmice, nu legale |
| 6 | Datele personale sunt anonimizate în logs (middleware GDPR) |
| 7 | Rate limiting activ pe toate endpoint-urile publice |
| 8 | Multi-tenancy: niciun tenant nu vede datele altui tenant |

---

## 19. Contribuții

1. Fork repository
2. Creează branch: `git checkout -b feature/numele-feature`
3. Rulează testele: `pytest -v`
4. Commit: `git commit -m "feat: descriere"`
5. Push și deschide Pull Request

### Convenții

- **Python:** Black formatter, isort, type hints obligatorii
- **TypeScript:** ESLint + Prettier
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`)
- **Teste:** Orice funcționalitate nouă necesită teste

---

*RomBiz Intelligence Platform — © 2026. Toate datele sunt colectate din surse publice oficiale. Scorurile și analizele au caracter informativ și nu constituie consultanță juridică sau financiară.*

## Stack Tehnologic

| Layer | Tehnologie |
|-------|-----------|
| Backend | Python 3.12, FastAPI (async), SQLAlchemy 2.0 |
| Database | PostgreSQL 16 (pg_trgm, unaccent, btree_gin) |
| Search | Elasticsearch 8.x (Romanian analyzer) |
| Cache/Broker | Redis 7.x |
| Task Queue | Celery 5 (5 queues, beat scheduler) |
| Graph DB | Neo4j 5 (Fraud Graph) |
| Object Storage | MinIO (S3-compatible) |
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS |
| Auth | JWT RS256 |
| Proxy | Nginx (rate limiting, gzip, WebSocket) |
| Container | Docker Compose |

## Structura Proiectului

```
rombiz-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # 14 endpoint modules
│   │   ├── collectors/          # 11 data collectors (ANAF, ONRC, BPI, etc.)
│   │   ├── core/                # config, database, redis, security, logging
│   │   ├── middleware/          # multi-tenancy, GDPR
│   │   ├── models/              # 35+ SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic v2 schemas
│   │   ├── services/            # risk, ESG, fraud, search, reports, alerts, redbill
│   │   ├── tasks/               # Celery tasks (sync, risk, esg, fraud, reports, etc.)
│   │   └── utils/               # validators (CUI mod-11, CNP hashing)
│   ├── migrations/              # SQL migration scripts
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/layout/   # DashboardLayout
│   │   ├── lib/                 # API client, WebSocket, utils
│   │   ├── pages/               # 15 page components
│   │   ├── store/               # Zustand auth store
│   │   └── types/               # TypeScript type definitions
│   ├── Dockerfile
│   └── package.json
├── nginx/nginx.conf
├── docker-compose.yml
└── .env.example
```

## Module Principale

### Surse de Date (Colectori)
- **ANAF** — TVA, Split TVA, bilanțuri, liste contribuabili
- **ONRC** — date registru comerț (cache 30 zile)
- **BPI** — Buletinul Procedurilor de Insolvență
- **Monitor Oficial** — publicații MOF
- **Portal Just** — dosare instanțe
- **AEGRM (RNPM)** — gajuri și ipoteci
- **OSIM** — mărci și brevete
- **SEAP** — licitații publice
- **BNR** — cursuri valutare (unicul sursă — constrângere #8)
- **MySMIS** — fonduri europene

### Analiză & Scoring
- **Risk Score** — Altman Z-Score + 4 componente (financiar, juridic, fiscal, comportamental)
- **ESG Score** — Environmental, Social, Governance (CSRD/SFDR compliant)
- **Fraud Graph** — Neo4j graph analysis, community detection, anomaly scoring
- **RedBill** — evaluare datorii restante

### API Endpoints (14 module)
`auth`, `companies`, `search`, `risk`, `esg`, `fraud`, `alerts` (WebSocket), `portfolios`, `redbill`, `seap`, `reports`, `admin`, `ai_agent`, `new_companies`

### Frontend (15 pagini)
Dashboard, Search, Company Profile (10 taburi), Portfolios, Alerts, SEAP, New Companies, Fraud Graph, ESG Dashboard, RedBill, Reports, Admin, AI Agent, Login, Register

## Setup Rapid

### 1. Configurare
```bash
cp .env.example .env
# Editează .env cu credențialele tale
```

### 2. Docker Compose
```bash
docker-compose up -d
```

Serviciile pornesc:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Nginx Proxy**: http://localhost (port 80)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Elasticsearch**: localhost:9200
- **Neo4j Browser**: http://localhost:7474
- **MinIO Console**: http://localhost:9001

### 3. Migrare Bază de Date
```bash
docker-compose exec backend python -c "
from app.core.database import engine
from app.models.models import Base
import asyncio
asyncio.run(Base.metadata.create_all(engine))
"
```

Sau rulează scriptul SQL direct:
```bash
docker-compose exec postgres psql -U rombiz -d rombiz_db -f /migrations/001_initial_schema.sql
```

### 4. Creare Cont Admin
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@rombiz.ro",
    "password": "SecurePassword123!",
    "prenume": "Admin",
    "nume": "RomBiz",
    "organizatie": "RomBiz SRL"
  }'
```

## Constrângeri Hard (15)

| # | Regulă |
|---|--------|
| 1 | `Decimal` pentru sume — NICIODATĂ `float` |
| 2 | CUI validat cu checksum mod-11 |
| 3 | `org_id` pe fiecare query (multi-tenancy) |
| 4 | Datorii ANAF max 90 zile vechime |
| 5 | Bilanțuri anuale disponibile din iulie |
| 6 | Fără CIP fără contract BNR |
| 7 | CNP: SHA-256 + pepper, afișat mascat |
| 8 | Cursuri BNR — singura sursă |
| 9 | Cache ONRC 30 zile |
| 10 | UTC în baza de date, Europe/Bucharest la afișare |
| 11 | Fraud alerts = "suspiciune algoritmică" |
| 12 | ESG score cu surse citate + disclaimer |
| 13 | GDPR soft delete cascade |
| 14 | JWT RS256 — NICIODATĂ HS256 |
| 15 | `Decimal` pentru bani în Python și TypeScript |

## Celery Tasks & Beat Schedule

| Task | Queue | Frecvență |
|------|-------|-----------|
| ANAF TVA batch sync | sync | Zilnic 02:00 |
| ANAF bilanțuri | sync | Zilnic 03:00 |
| BPI insolvențe | sync | La 6 ore |
| Portal Just dosare | sync | La 12 ore |
| SEAP licitații | sync | La 4 ore |
| BNR cursuri | sync | Zilnic 13:00 |
| Risk scoring | compute | La 2 ore |
| ESG scoring | compute | Săptămânal (Luni) |
| Fraud graph | compute | Zilnic 04:00 |
| Materialized views | default | La 30 min |
| Elasticsearch reindex | default | Zilnic 05:00 |
| GDPR cleanup | default | Săptămânal |

## Licență

Proprietar — © RomBiz Intelligence
