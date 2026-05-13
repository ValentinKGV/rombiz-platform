-- ============================================================
-- RomBiz Intelligence Platform — Complete PostgreSQL Schema
-- Version: 1.0.0
-- Date: 2026-02-25
-- ============================================================

-- ============================================================
-- EXTENSIONS (run once)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- fuzzy search with trigrams
CREATE EXTENSION IF NOT EXISTS unaccent;    -- diacritics normalization
CREATE EXTENSION IF NOT EXISTS btree_gin;   -- GIN on scalar types
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUID generation

-- ============================================================
-- ORGANIZATIONS (Multi-tenancy root)
-- ============================================================
CREATE TABLE organizations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(200) NOT NULL,
    cui                     VARCHAR(20),
    email                   VARCHAR(200) UNIQUE NOT NULL,
    subscription_plan       VARCHAR(20) DEFAULT 'FREE',
    subscription_status     VARCHAR(20) DEFAULT 'ACTIVE',
    subscription_expires_at TIMESTAMPTZ,
    monthly_api_calls       INTEGER DEFAULT 0,
    api_calls_limit         INTEGER DEFAULT 100,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email           VARCHAR(200) UNIQUE NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    role            VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('admin','analyst','viewer')),
    is_active       BOOLEAN DEFAULT TRUE,
    email_verified  BOOLEAN DEFAULT FALSE,
    last_login      TIMESTAMPTZ,
    api_key         VARCHAR(64) UNIQUE,
    credits_left    INTEGER DEFAULT 0,
    alert_preferences JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_org   ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- API KEYS
-- ============================================================
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    key_hash        VARCHAR(64) UNIQUE NOT NULL,
    key_prefix      VARCHAR(8),
    permissions     JSONB DEFAULT '["read"]'::jsonb,
    rate_limit_rpm  INTEGER DEFAULT 60,
    total_calls     BIGINT DEFAULT 0,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COMPANIES (Core entity)
-- ============================================================
CREATE TABLE companies (
    id                  BIGSERIAL PRIMARY KEY,
    cui                 INTEGER UNIQUE NOT NULL,
    j_nr                VARCHAR(20),
    denumire            VARCHAR(500) NOT NULL,
    denumire_search     TSVECTOR,
    forma_juridica      VARCHAR(10) CHECK (forma_juridica IN ('SRL','SA','PFA','RA','SNC','SCS','ALT')),
    stare               VARCHAR(20) DEFAULT 'ACTIVA',
    data_infiintare     DATE,
    data_radiere        DATE,
    caen_principal      VARCHAR(4),
    capital_social      NUMERIC(18,2),
    adresa_completa     TEXT,
    judet               VARCHAR(50),
    localitate          VARCHAR(100),
    cod_postal          VARCHAR(10),
    lat                 NUMERIC(10,7),
    lng                 NUMERIC(10,7),
    -- Status fiscal ANAF
    platitor_tva        BOOLEAN DEFAULT FALSE,
    tva_la_incasare     BOOLEAN DEFAULT FALSE,
    split_tva           BOOLEAN DEFAULT FALSE,
    inactiv_fiscal      BOOLEAN DEFAULT FALSE,
    -- Denormalized flags
    has_insolvency      BOOLEAN DEFAULT FALSE,
    has_litigation      BOOLEAN DEFAULT FALSE,
    has_debts           BOOLEAN DEFAULT FALSE,
    has_seap_contracts  BOOLEAN DEFAULT FALSE,
    has_eu_projects     BOOLEAN DEFAULT FALSE,
    has_trademarks      BOOLEAN DEFAULT FALSE,
    -- Data quality
    data_quality_score  SMALLINT DEFAULT 0 CHECK (data_quality_score BETWEEN 0 AND 100),
    data_sources        JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_companies_search       ON companies USING GIN(denumire_search);
CREATE INDEX idx_companies_trgm         ON companies USING GIN(denumire gin_trgm_ops);
CREATE INDEX idx_companies_cui          ON companies(cui);
CREATE INDEX idx_companies_caen         ON companies(caen_principal);
CREATE INDEX idx_companies_judet_stare  ON companies(judet, stare);
CREATE INDEX idx_companies_active       ON companies(stare) WHERE stare = 'ACTIVA';
CREATE INDEX idx_companies_insolvency   ON companies(id) WHERE has_insolvency = TRUE;
CREATE INDEX idx_companies_debts        ON companies(id) WHERE has_debts = TRUE;

-- Trigger: auto-update tsvector + updated_at
CREATE OR REPLACE FUNCTION companies_update_trigger()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.denumire_search = to_tsvector('romanian',
        COALESCE(NEW.denumire, '') || ' ' ||
        COALESCE(NEW.adresa_completa, '') || ' ' ||
        COALESCE(NEW.cui::text, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_companies_update
    BEFORE INSERT OR UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION companies_update_trigger();

-- CUI validation function (official Romanian algorithm)
CREATE OR REPLACE FUNCTION validate_cui(cui_input INTEGER) RETURNS BOOLEAN AS $$
DECLARE
    digits  INTEGER[];
    weights INTEGER[] := ARRAY[7, 5, 3, 2, 1, 7, 5, 3, 2];
    suma    INTEGER := 0;
    rest    INTEGER;
    cui_str TEXT;
    i       INTEGER;
BEGIN
    cui_str := LPAD(cui_input::TEXT, 10, '0');
    IF LENGTH(cui_str) < 2 OR LENGTH(cui_str) > 10 THEN RETURN FALSE; END IF;
    FOR i IN 1..LENGTH(cui_str)-1 LOOP
        suma := suma + SUBSTRING(cui_str, LENGTH(cui_str)-i, 1)::INTEGER
                     * weights[i];
    END LOOP;
    rest := (suma * 10) % 11;
    IF rest = 10 THEN rest := 0; END IF;
    RETURN rest = SUBSTRING(cui_str, LENGTH(cui_str), 1)::INTEGER;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================
-- FINANCIAL DATA (annual balance sheets)
-- ============================================================
CREATE TABLE financial_data (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    an_fiscal       SMALLINT NOT NULL,
    cifra_afaceri   BIGINT,
    profit_net      BIGINT,
    total_active    BIGINT,
    total_datorii   BIGINT,
    capitaluri_prop BIGINT,
    nr_angajati     INTEGER,
    rata_lichiditate  NUMERIC(8,4),
    grad_indatorare   NUMERIC(8,4),
    roa               NUMERIC(8,4),
    roe               NUMERIC(8,4),
    profit_margin     NUMERIC(8,4),
    sursa           VARCHAR(20) DEFAULT 'ANAF',
    UNIQUE(company_id, an_fiscal)
);

-- ============================================================
-- COMPANY PERSONS (associates, administrators)
-- ============================================================
CREATE TABLE company_persons (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    tip             VARCHAR(20) CHECK (tip IN ('ASOCIAT','ADMINISTRATOR','CENZOR','AUDITOR')),
    nume_complet    VARCHAR(200),
    cnp_partial     VARCHAR(64),  -- SHA-256 hashed for GDPR
    procent_parti   NUMERIC(6,3),
    data_start      DATE,
    data_sfarsit    DATE,
    activ           BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_persons_hash ON company_persons(md5(LOWER(TRIM(nume_complet))));

-- ============================================================
-- INSOLVENCY CASES (BPI)
-- ============================================================
CREATE TABLE insolvency_cases (
    id                  BIGSERIAL PRIMARY KEY,
    company_id          BIGINT REFERENCES companies(id),
    nr_dosar_bpi        VARCHAR(50),
    nr_dosar_tribunal   VARCHAR(50),
    tip_procedura       VARCHAR(50),
    tribunal            VARCHAR(100),
    practician          VARCHAR(200),
    data_publicare      DATE,
    data_deschidere     DATE,
    status              VARCHAR(30) DEFAULT 'ACTIV',
    continut_pdf_url    VARCHAR(500),
    raw_data            JSONB
);

-- ============================================================
-- COURT CASES (ROLII)
-- ============================================================
CREATE TABLE court_cases (
    id                  BIGSERIAL PRIMARY KEY,
    company_id          BIGINT REFERENCES companies(id),
    nr_dosar            VARCHAR(50) UNIQUE,
    instanta            VARCHAR(200),
    instanta_oras       VARCHAR(100),
    obiect              VARCHAR(500),
    materie             VARCHAR(50),
    rol_firma           VARCHAR(20),
    parti               JSONB,
    stadiu              VARCHAR(100),
    solutie             TEXT,
    data_solutie        DATE,
    data_dosar          DATE,
    ultima_actualizare  DATE,
    urmatorul_termen    DATE,
    source              VARCHAR(20) DEFAULT 'PORTAL_JUST',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_court_cases_company ON court_cases(company_id);
CREATE INDEX idx_court_cases_termen  ON court_cases(urmatorul_termen) WHERE urmatorul_termen >= CURRENT_DATE;
CREATE INDEX idx_court_cases_created ON court_cases USING BRIN(created_at);

-- ============================================================
-- LITIGATION HEARINGS
-- ============================================================
CREATE TABLE litigation_hearings (
    id              BIGSERIAL PRIMARY KEY,
    case_id         BIGINT REFERENCES court_cases(id) ON DELETE CASCADE,
    hearing_date    DATE NOT NULL,
    hearing_time    TIME,
    sala            VARCHAR(30),
    status          VARCHAR(50),
    outcome         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_hearings_case     ON litigation_hearings(case_id);
CREATE INDEX idx_hearings_date     ON litigation_hearings(hearing_date) WHERE hearing_date >= CURRENT_DATE;
CREATE INDEX idx_hearings_tomorrow ON litigation_hearings(hearing_date)
    WHERE hearing_date = CURRENT_DATE + 1 AND status = 'programat';

-- ============================================================
-- PUBLIC CONTRACTS (SEAP) — Awarded
-- ============================================================
CREATE TABLE public_contracts (
    id                          BIGSERIAL PRIMARY KEY,
    company_id                  BIGINT REFERENCES companies(id),
    autoritate_contractanta_cui VARCHAR(20),
    autoritate_contractanta     VARCHAR(500),
    nr_contract                 VARCHAR(100),
    titlu_contract              TEXT,
    cod_cpv                     VARCHAR(20),
    denumire_cpv                VARCHAR(200),
    tip_procedura               VARCHAR(50),
    valoare                     NUMERIC(18,2),
    moneda                      VARCHAR(5) DEFAULT 'RON',
    valoare_ron                 NUMERIC(18,2),
    data_atribuire              DATE,
    data_inceput                DATE,
    data_finalizare             DATE,
    durata_luni                 SMALLINT,
    seap_url                    TEXT,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_contracts_company ON public_contracts(company_id);
CREATE INDEX idx_contracts_cpv     ON public_contracts(cod_cpv);
CREATE INDEX idx_contracts_data    ON public_contracts(data_atribuire DESC);
CREATE INDEX idx_contracts_created ON public_contracts USING BRIN(created_at);

-- ============================================================
-- PUBLIC TENDERS ACTIVE (SEAP) — Open tenders
-- ============================================================
CREATE TABLE public_tenders_active (
    id                      BIGSERIAL PRIMARY KEY,
    authority_cui           VARCHAR(20),
    authority_name          VARCHAR(500),
    tender_number           VARCHAR(100) UNIQUE,
    title                   TEXT,
    cpv_code                VARCHAR(20),
    cpv_name                VARCHAR(200),
    estimated_value         NUMERIC(18,2),
    currency                VARCHAR(5) DEFAULT 'RON',
    procedure_type          VARCHAR(50),
    deadline                DATE,
    submission_deadline     TIMESTAMPTZ,
    seap_url                TEXT,
    caen_relevante          VARCHAR(4)[],
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_tenders_deadline ON public_tenders_active(deadline) WHERE deadline >= CURRENT_DATE;
CREATE INDEX idx_tenders_cpv     ON public_tenders_active(cpv_code);
CREATE INDEX idx_tenders_caen    ON public_tenders_active USING GIN(caen_relevante);
CREATE INDEX idx_tenders_active  ON public_tenders_active(submission_deadline) WHERE submission_deadline > NOW();

-- ============================================================
-- RISK SCORES
-- ============================================================
CREATE TABLE risk_scores (
    id                          BIGSERIAL PRIMARY KEY,
    company_id                  BIGINT REFERENCES companies(id) UNIQUE,
    score                       INTEGER CHECK (score BETWEEN 1 AND 100),
    rating                      VARCHAR(5),
    scor_financiar              NUMERIC(5,2),
    scor_legal                  NUMERIC(5,2),
    scor_fiscal                 NUMERIC(5,2),
    scor_comportamental         NUMERIC(5,2),
    limita_credit               BIGINT,
    probabilitate_insolventa    NUMERIC(6,4),
    factori_risc                JSONB,
    calculat_la                 TIMESTAMPTZ DEFAULT NOW(),
    model_versiune              VARCHAR(10)
);
CREATE INDEX idx_risk_scores_company ON risk_scores(company_id);
CREATE INDEX idx_risk_scores_score   ON risk_scores(score DESC);

-- ============================================================
-- ESG SCORES
-- ============================================================
CREATE TABLE esg_scores (
    id                          BIGSERIAL PRIMARY KEY,
    company_id                  BIGINT REFERENCES companies(id) UNIQUE,
    score_e                     NUMERIC(5,2),
    score_s                     NUMERIC(5,2),
    score_g                     NUMERIC(5,2),
    score_total                 NUMERIC(5,2),
    e_emisii_co2                NUMERIC(12,2),
    e_amenzi_mediu              NUMERIC(12,2),
    e_certificari_iso           BOOLEAN,
    s_stabilitate_angajati      NUMERIC(5,2),
    s_salariu_vs_sector         NUMERIC(5,2),
    s_litigii_munca             NUMERIC(5,2),
    s_certificari_sociale       BOOLEAN,
    g_stabilitate_management    NUMERIC(5,2),
    g_transparenta_actionariat  NUMERIC(5,2),
    g_conformitate_fiscala      NUMERIC(5,2),
    g_dosare_penale             NUMERIC(5,2),
    esg_rating                  VARCHAR(5),
    csrd_relevant               BOOLEAN,
    sfdr_categoria              VARCHAR(15),
    surse_date                  JSONB,
    metodologie_versiune        VARCHAR(10),
    calculat_la                 TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ESG RAW DATA
-- ============================================================
CREATE TABLE esg_raw_data (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    sursa           VARCHAR(50),
    categorie       VARCHAR(10),
    indicator       VARCHAR(100),
    valoare         TEXT,
    unitate         VARCHAR(30),
    an_referinta    SMALLINT,
    data_colectare  DATE,
    raw_json        JSONB
);

-- ============================================================
-- ENVIRONMENTAL FINES
-- ============================================================
CREATE TABLE environmental_fines (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    autoritate      VARCHAR(100),
    suma_ron        NUMERIC(14,2),
    motiv           TEXT,
    data_amenda     DATE,
    status          VARCHAR(20)
);

-- ============================================================
-- COMPANY DEBTS (ANAF)
-- ============================================================
CREATE TABLE company_debts (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    suma_restanta   NUMERIC(18,2),
    tip_datorie     VARCHAR(100),
    data_raportare  DATE,
    sursa           VARCHAR(30) DEFAULT 'ANAF',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- EXCHANGE RATES (BNR)
-- ============================================================
CREATE TABLE exchange_rates (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    currency    VARCHAR(5) NOT NULL,
    rate_ron    NUMERIC(12,6) NOT NULL,
    source      VARCHAR(10) DEFAULT 'BNR',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, currency)
);
CREATE INDEX idx_exchange_rates_lookup ON exchange_rates(date, currency);

-- ============================================================
-- EU PROJECTS
-- ============================================================
CREATE TABLE eu_projects (
    id                  BIGSERIAL PRIMARY KEY,
    company_id          BIGINT REFERENCES companies(id),
    titlu               TEXT,
    program_operational VARCHAR(50),
    valoare_totala_ron  BIGINT,
    finantare_ue_ron    BIGINT,
    finantare_ue_pct    NUMERIC(5,2),
    cofinantare_ron     BIGINT,
    data_aprobare       DATE,
    data_finalizare     DATE,
    status              VARCHAR(20),
    sursa_url           TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_eu_projects_company ON eu_projects(company_id);

-- ============================================================
-- COMPANY MENTIONS (Monitor Oficial)
-- ============================================================
CREATE TABLE company_mentions (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    tip_sectiune    VARCHAR(5) CHECK (tip_sectiune IN ('MO4','MO7')),
    tip_act         VARCHAR(100),
    nr_monitor      VARCHAR(50),
    data_publicare  DATE,
    continut_rezumat TEXT,
    pdf_url         TEXT,
    pdf_parsed      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_mentions_company ON company_mentions(company_id, data_publicare DESC);

-- ============================================================
-- MONITORED PORTFOLIOS
-- ============================================================
CREATE TABLE monitored_portfolios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE NOT NULL,
    user_id         UUID REFERENCES users(id),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    alert_email     BOOLEAN DEFAULT TRUE,
    alert_sms       BOOLEAN DEFAULT FALSE,
    alert_webhook   BOOLEAN DEFAULT FALSE,
    webhook_url     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_portfolios_org ON monitored_portfolios(org_id);

CREATE TABLE portfolio_companies (
    id              BIGSERIAL PRIMARY KEY,
    portfolio_id    UUID REFERENCES monitored_portfolios(id) ON DELETE CASCADE,
    company_id      BIGINT REFERENCES companies(id),
    added_at        TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT,
    UNIQUE(portfolio_id, company_id)
);
CREATE INDEX idx_portfolio_companies_pid ON portfolio_companies(portfolio_id);
CREATE INDEX idx_portfolio_companies_cid ON portfolio_companies(company_id);

-- ============================================================
-- SAVED SEARCHES
-- ============================================================
CREATE TABLE saved_searches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id          UUID REFERENCES organizations(id),
    name            VARCHAR(200) NOT NULL,
    filters_json    JSONB NOT NULL,
    result_count    INTEGER DEFAULT 0,
    notify_new      BOOLEAN DEFAULT FALSE,
    last_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_saved_searches_user   ON saved_searches(user_id);
CREATE INDEX idx_saved_searches_notify ON saved_searches(notify_new) WHERE notify_new = TRUE;

-- ============================================================
-- ALERTS
-- ============================================================
CREATE TABLE alerts (
    id              BIGSERIAL PRIMARY KEY,
    org_id          UUID REFERENCES organizations(id),
    portfolio_id    UUID REFERENCES monitored_portfolios(id),
    company_id      BIGINT REFERENCES companies(id),
    user_id         UUID REFERENCES users(id),
    tip_alerta      VARCHAR(50),
    titlu           VARCHAR(500),
    continut        TEXT,
    alert_payload   JSONB,
    data_eveniment  TIMESTAMPTZ,
    citita          BOOLEAN DEFAULT FALSE,
    trimisa_email   BOOLEAN DEFAULT FALSE,
    trimisa_sms     BOOLEAN DEFAULT FALSE,
    trimis_webhook  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_alerts_org_unread ON alerts(org_id, created_at DESC) WHERE citita = FALSE;
CREATE INDEX idx_alerts_company    ON alerts(company_id, created_at DESC);
CREATE INDEX idx_alerts_created    ON alerts USING BRIN(created_at);

-- ============================================================
-- FRAUD GRAPH
-- ============================================================
CREATE TABLE entity_relations (
    id              BIGSERIAL PRIMARY KEY,
    source_type     VARCHAR(20) CHECK (source_type IN ('COMPANY','PERSON')),
    source_id       BIGINT NOT NULL,
    target_type     VARCHAR(20) CHECK (target_type IN ('COMPANY','PERSON')),
    target_id       BIGINT NOT NULL,
    relation_type   VARCHAR(30) NOT NULL,
    weight          NUMERIC(6,3),
    sursa           VARCHAR(20),
    valid_from      DATE,
    valid_to        DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_relations_source ON entity_relations(source_type, source_id);
CREATE INDEX idx_relations_target ON entity_relations(target_type, target_id);

CREATE TABLE fraud_alerts (
    id              BIGSERIAL PRIMARY KEY,
    alert_type      VARCHAR(50) NOT NULL,
    severity        VARCHAR(10) CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    company_ids     INTEGER[],
    person_hashes   VARCHAR[],
    descriere       TEXT,
    dovezi          JSONB,
    confidence      NUMERIC(5,4),
    status          VARCHAR(20) DEFAULT 'OPEN',
    detectat_la     TIMESTAMPTZ DEFAULT NOW(),
    rezolvat_la     TIMESTAMPTZ
);
CREATE INDEX idx_fraud_alerts_type      ON fraud_alerts(alert_type, severity);
CREATE INDEX idx_fraud_alerts_companies ON fraud_alerts USING GIN(company_ids);
CREATE INDEX idx_fraud_alerts_created   ON fraud_alerts USING BRIN(detectat_la);

CREATE TABLE graph_metrics (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(20),
    entity_id       BIGINT,
    pagerank_score  NUMERIC(10,8),
    betweenness     NUMERIC(10,8),
    degree_in       INTEGER,
    degree_out      INTEGER,
    community_id    INTEGER,
    suspicion_score NUMERIC(6,4),
    calculat_la     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- REDBILL (Invoice Collection)
-- ============================================================
CREATE TABLE redbill_cases (
    id                  BIGSERIAL PRIMARY KEY,
    creditor_cui        INTEGER NOT NULL,
    debtor_cui          INTEGER NOT NULL,
    invoice_number      VARCHAR(100) NOT NULL,
    invoice_amount      NUMERIC(18,2) NOT NULL,
    invoice_date        DATE NOT NULL,
    due_date            DATE NOT NULL,
    visibility          VARCHAR(10) DEFAULT 'PUBLIC',
    status              VARCHAR(20) DEFAULT 'OPEN',
    collection_started  BOOLEAN DEFAULT FALSE,
    org_id              UUID REFERENCES organizations(id),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- NEW COMPANIES FEED
-- ============================================================
CREATE TABLE new_companies_feed (
    id                  BIGSERIAL PRIMARY KEY,
    company_id          BIGINT REFERENCES companies(id),
    registration_date   DATE,
    feed_date           DATE DEFAULT CURRENT_DATE,
    sursa               VARCHAR(30),
    is_notified         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_new_companies_feed_date ON new_companies_feed(feed_date DESC);
CREATE INDEX idx_new_companies_notified  ON new_companies_feed(is_notified) WHERE is_notified = FALSE;

-- ============================================================
-- CIP INCIDENTS (placeholder — requires BNR contract)
-- ============================================================
CREATE TABLE cip_incidents (
    id              BIGSERIAL PRIMARY KEY,
    company_id      BIGINT REFERENCES companies(id),
    incident_type   VARCHAR(30),
    incident_date   DATE,
    amount          NUMERIC(18,2),
    currency        VARCHAR(5) DEFAULT 'RON',
    bank_name       VARCHAR(200),
    status          VARCHAR(20),
    source          VARCHAR(30),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT cip_access_note CHECK (TRUE)
);

-- ============================================================
-- REPORT EXPORTS
-- ============================================================
CREATE TABLE report_exports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    company_id      BIGINT REFERENCES companies(id),
    export_type     VARCHAR(30),
    format          VARCHAR(10),
    task_id         VARCHAR(100),
    filters_json    JSONB,
    row_count       INTEGER,
    file_url        TEXT,
    status          VARCHAR(20) DEFAULT 'pending',
    credits_consumed INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ
);
CREATE INDEX idx_exports_org ON report_exports(org_id, created_at DESC);

-- ============================================================
-- AUDIT LOG (GDPR)
-- ============================================================
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       TEXT,
    payload_json    JSONB,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_log_created ON audit_log USING BRIN(created_at);
CREATE INDEX idx_audit_log_org     ON audit_log(org_id, created_at DESC);

-- ============================================================
-- DATA SOURCE SYNC LOG
-- ============================================================
CREATE TABLE data_source_sync_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name         VARCHAR(50) NOT NULL,
    sync_type           VARCHAR(20),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    records_processed   INTEGER DEFAULT 0,
    records_inserted    INTEGER DEFAULT 0,
    records_updated     INTEGER DEFAULT 0,
    records_failed      INTEGER DEFAULT 0,
    error_message       TEXT,
    status              VARCHAR(20),
    metadata_json    JSONB
);
CREATE INDEX idx_sync_log_source_status ON data_source_sync_log(source_name, status);
CREATE INDEX idx_sync_log_started_at    ON data_source_sync_log(started_at DESC);

-- View: latest sync per source
CREATE VIEW data_source_health AS
SELECT DISTINCT ON (source_name)
    source_name, sync_type, started_at, completed_at,
    records_processed, status, error_message
FROM data_source_sync_log
ORDER BY source_name, started_at DESC;

-- ============================================================
-- MATERIALIZED VIEWS
-- ============================================================

-- Company summary (denormalized card view)
CREATE MATERIALIZED VIEW mv_company_summary AS
SELECT
    c.id, c.cui, c.denumire, c.forma_juridica, c.stare,
    c.judet, c.localitate, c.caen_principal,
    c.has_insolvency, c.has_debts, c.has_litigation,
    c.data_quality_score,
    rs.score AS risk_score, rs.rating AS risk_rating,
    fd.cifra_afaceri AS ca_ultimul_an,
    fd.profit_net AS profit_ultimul_an,
    fd.nr_angajati,
    fd.an_fiscal AS an_bilant
FROM companies c
LEFT JOIN risk_scores rs ON rs.company_id = c.id
LEFT JOIN LATERAL (
    SELECT * FROM financial_data
    WHERE company_id = c.id
    ORDER BY an_fiscal DESC LIMIT 1
) fd ON TRUE
WHERE c.stare = 'ACTIVA';

CREATE UNIQUE INDEX ON mv_company_summary(id);
CREATE INDEX ON mv_company_summary(judet, caen_principal);
CREATE INDEX ON mv_company_summary(risk_score DESC);

-- Sector stats
CREATE MATERIALIZED VIEW mv_sector_stats AS
SELECT
    c.caen_principal,
    COUNT(*) AS nr_firme,
    COUNT(*) FILTER (WHERE c.stare = 'ACTIVA') AS nr_active,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fd.cifra_afaceri) AS median_ca,
    AVG(fd.cifra_afaceri) AS avg_ca,
    AVG(fd.nr_angajati)   AS avg_angajati,
    AVG(rs.score)         AS avg_risk_score,
    COUNT(*) FILTER (WHERE c.has_insolvency) AS nr_insolvente
FROM companies c
LEFT JOIN financial_data fd ON fd.company_id = c.id
    AND fd.an_fiscal = (SELECT MAX(an_fiscal) FROM financial_data WHERE company_id = c.id)
LEFT JOIN risk_scores rs ON rs.company_id = c.id
GROUP BY c.caen_principal;

CREATE UNIQUE INDEX ON mv_sector_stats(caen_principal);

-- Top companies per county
CREATE MATERIALIZED VIEW mv_top_companies_by_county AS
SELECT
    c.judet,
    c.id AS company_id,
    c.denumire,
    c.cui,
    c.caen_principal,
    fd.cifra_afaceri,
    fd.nr_angajati,
    rs.score AS risk_score,
    ROW_NUMBER() OVER (PARTITION BY c.judet ORDER BY fd.cifra_afaceri DESC NULLS LAST) AS rank_in_county
FROM companies c
LEFT JOIN financial_data fd ON fd.company_id = c.id
    AND fd.an_fiscal = (SELECT MAX(an_fiscal) FROM financial_data WHERE company_id = c.id)
LEFT JOIN risk_scores rs ON rs.company_id = c.id
WHERE c.stare = 'ACTIVA'
  AND fd.cifra_afaceri > 0;

CREATE UNIQUE INDEX ON mv_top_companies_by_county(judet, company_id);
CREATE INDEX ON mv_top_companies_by_county(judet, rank_in_county);

-- ============================================================
-- DOWN MIGRATION (rollback)
-- ============================================================
-- DROP MATERIALIZED VIEW IF EXISTS mv_top_companies_by_county;
-- DROP MATERIALIZED VIEW IF EXISTS mv_sector_stats;
-- DROP MATERIALIZED VIEW IF EXISTS mv_company_summary;
-- DROP VIEW IF EXISTS data_source_health;
-- DROP TABLE IF EXISTS audit_log CASCADE;
-- DROP TABLE IF EXISTS report_exports CASCADE;
-- DROP TABLE IF EXISTS cip_incidents CASCADE;
-- DROP TABLE IF EXISTS new_companies_feed CASCADE;
-- DROP TABLE IF EXISTS redbill_cases CASCADE;
-- DROP TABLE IF EXISTS graph_metrics CASCADE;
-- DROP TABLE IF EXISTS fraud_alerts CASCADE;
-- DROP TABLE IF EXISTS entity_relations CASCADE;
-- DROP TABLE IF EXISTS alerts CASCADE;
-- DROP TABLE IF EXISTS saved_searches CASCADE;
-- DROP TABLE IF EXISTS portfolio_companies CASCADE;
-- DROP TABLE IF EXISTS monitored_portfolios CASCADE;
-- DROP TABLE IF EXISTS company_mentions CASCADE;
-- DROP TABLE IF EXISTS eu_projects CASCADE;
-- DROP TABLE IF EXISTS exchange_rates CASCADE;
-- DROP TABLE IF EXISTS company_debts CASCADE;
-- DROP TABLE IF EXISTS environmental_fines CASCADE;
-- DROP TABLE IF EXISTS esg_raw_data CASCADE;
-- DROP TABLE IF EXISTS esg_scores CASCADE;
-- DROP TABLE IF EXISTS risk_scores CASCADE;
-- DROP TABLE IF EXISTS public_tenders_active CASCADE;
-- DROP TABLE IF EXISTS public_contracts CASCADE;
-- DROP TABLE IF EXISTS litigation_hearings CASCADE;
-- DROP TABLE IF EXISTS court_cases CASCADE;
-- DROP TABLE IF EXISTS insolvency_cases CASCADE;
-- DROP TABLE IF EXISTS company_persons CASCADE;
-- DROP TABLE IF EXISTS financial_data CASCADE;
-- DROP TABLE IF EXISTS data_source_sync_log CASCADE;
-- DROP TABLE IF EXISTS companies CASCADE;
-- DROP TABLE IF EXISTS api_keys CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS organizations CASCADE;
-- DROP FUNCTION IF EXISTS companies_update_trigger();
-- DROP FUNCTION IF EXISTS validate_cui(INTEGER);
