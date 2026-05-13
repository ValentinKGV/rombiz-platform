/**
 * RomBiz Intelligence — TypeScript type definitions.
 * Hard constraint #15: Decimal for money (string in TS).
 */

// ── Auth ──
export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: "admin" | "analist" | "viewer";
    org_id: string;
    org_name: string;
    org_cui?: string;
    is_active: boolean;
    email_verified?: boolean;
    created_at?: string;
    last_login?: string;
    credits_left?: number;
    avatar_url?: string | null;
}

export interface AuthTokens {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

// ── Company ──
export interface CompanyBrief {
    id: number;
    cui: string;
    denumire: string;
    judet: string;
    localitate: string;
    caen_principal: string;
    descriere_caen: string;
    stare: string;
    risk_score?: string; // Decimal as string
    risk_rating?: string;
}

export interface CompanyFull extends CompanyBrief {
    j_nr: string;
    euid?: string;
    lat?: string | null;
    lng?: string | null;
    adresa_completa: string;
    forma_juridica: string;
    capital_social: string; // Decimal
    data_infiintare: string;
    has_debts: boolean;
    has_insolvency: boolean;
    are_litigii_active: boolean;
    platitor_tva: boolean;
    telefon?: string;
    fax?: string;
    email?: string;
    website?: string;
    status_ro_efactura?: boolean;
    tva_perioade?: Array<{
        data_inceput_ScpTVA: string;
        data_sfarsit_ScpTVA?: string;
        data_anul_imp_ScpTVA?: string;
        mesaj_ScpTVA?: string;
    }>;
    updated_at: string;
}

export interface FinancialData {
    id: number;
    an_fiscal: number;
    cifra_afaceri: string; // Decimal
    profit_net: string;
    total_active: string;
    active_imobilizate: string;
    active_circulante: string;
    capitaluri_prop: string;
    nr_angajati: number;
    total_datorii: string;
    rata_lichiditate: string;
    grad_indatorare: string;
    roa: string;
    roe: string;
    profit_margin: string;
}

// ── Risk Score ──
export interface RiskScore {
    score: string; // Decimal
    rating: "A" | "B" | "C" | "D" | "E";
    scor_financiar: string;
    scor_legal: string;
    scor_fiscal: string;
    scor_comportamental: string;
    calculat_la: string;
}

// ── ESG Score ──
export interface ESGScore {
    score_total: string;
    score_e: string;
    score_s: string;
    score_g: string;
    csrd_relevant: boolean;
    sfdr_categoria: string;
    surse_date: string[]; // Hard constraint #12
    calculat_la: string;
}

// ── Fraud ──
export interface FraudAlert {
    id: number;
    alert_type: string;
    severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    descriere: string;
    dovezi: Record<string, unknown>;
    confidence: string;
    created_at: string;
}

export interface FraudProfile {
    company: CompanyBrief;
    alerts: FraudAlert[];
    graph_summary: {
        nodes: number;
        edges: number;
        clusters: number;
    };
    anomaly_score: string;
}

// ── Alerts ──
export type AlertType =
    | "fiscal_status_change"
    | "insolvency_opened"
    | "new_court_case"
    | "financial_data_published"
    | "administrator_change"
    | "associates_change"
    | "new_public_contract"
    | "risk_score_degraded"
    | "address_change"
    | "caen_change"
    | "new_mo_mention"
    | "debt_status_change"
    | "esg_score_change"
    | "ai_anomaly_detected";

export interface Alert {
    id: number;
    tip_alerta: AlertType;
    titlu: string;
    continut?: string;
    company_id: number;
    company_cui: string;
    company_name: string;
    citita: boolean;
    alert_payload: Record<string, unknown>;
    created_at: string;
}

// ── Portfolio ──
export interface Portfolio {
    id: number;
    name: string;
    description?: string;
    companies: CompanyBrief[];
    company_count: number;
    created_at: string;
}

// ── Search ──
export interface SearchFilters {
    query?: string;
    judet?: string;
    localitate?: string;
    caen_principal?: string;
    forma_juridica?: string;
    stare?: string;
    cifra_afaceri_min?: string;
    cifra_afaceri_max?: string;
    profit_net_min?: string;
    profit_net_max?: string;
    angajati_min?: number;
    angajati_max?: number;
    risk_category?: string[];
    data_infiintare_min?: string;
    data_infiintare_max?: string;
    has_debts?: boolean;
    has_insolvency?: boolean;
    tara?: string;
    administrator?: string;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
}

export interface SearchResult {
    items: CompanyBrief[];
    total: number;
    page: number;
    page_size: number;
    facets?: Record<string, { key: string; count: number }[]>;
}

// ── SEAP ──
export interface Tender {
    id: number;
    numar_anunt?: string;
    tender_number?: string;
    titlu?: string;
    title?: string;
    authority_name: string;
    cui_autoritate?: string;
    cpv_code: string;
    estimated_value: string;
    moneda?: string;
    currency?: string;
    data_publicare?: string;
    submission_deadline: string;
    tip_procedura?: string;
    procedure_type?: string;
    stare?: string;
    seap_url?: string;
}

export interface PublicContract {
    id: number;
    numar_contract: string;
    titlu: string;
    castigator_cui: string;
    castigator_denumire: string;
    autoritate: string;
    valoare: string;
    moneda: string;
    data_contract: string;
    cpv_code: string;
}

// ── RedBill ──
export interface DebtProfile {
    company: CompanyBrief;
    total_outstanding_ron: string;
    risk_level: "green" | "yellow" | "orange" | "red";
    fiscal_debts_count: number;
    other_debts_count: number;
    fresh_data_count: number;
    stale_data_count: number;
    has_debts: boolean;
}

// ── New Companies Feed ──
export interface NewCompany {
    id: number;
    cui: string;
    denumire: string;
    judet: string;
    localitate: string;
    caen_principal: string;
    registration_date: string;
}

// ── Admin ──
export interface DataSourceHealth {
    source_name: string;
    status: "healthy" | "degraded" | "down";
    last_sync_at: string;
    records_processed: number;
    records_failed?: number;
    error_rate: number;
}

export interface AdminDashboard {
    total_companies: number;
    total_users: number;
    total_organizations: number;
    active_alerts: number;
    data_sources: DataSourceHealth[];
    sync_stats: {
        today: number;
        week: number;
        failed: number;
    };
}

// ── Reports ──
export interface ReportExport {
    id: number;
    export_type: string;
    format: "pdf" | "xlsx";
    status: "processing" | "completed" | "failed";
    file_url?: string;
    created_at: string;
}

// ── Pagination ──
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
}

// ── AI Agent ──
export interface AIQueryRequest {
    query: string;
    context?: Record<string, unknown>;
}

export interface AIQueryResponse {
    answer: string;
    sources?: {
        type: string;
        data: Record<string, unknown>;
    }[];
    tokens_used: number;
    input_tokens?: number;
    output_tokens?: number;
    model?: string;
}

export interface AIInsight {
    type: "positive" | "warning" | "danger" | "info";
    title: string;
    text: string;
}

export interface AIConversationHistory {
    messages: { role: string; content: string }[];
    count: number;
}

// ── Predictive Analytics (Branch 13) ──
export interface ForecastPrediction {
    an: number;
    cifra_afaceri: number | null;
    cifra_afaceri_confidence: number | null;
    profit_net: number | null;
    profit_net_confidence: number | null;
    nr_angajati: number | null;
    nr_angajati_confidence: number | null;
    total_active: number | null;
    total_datorii: number | null;
    profit_margin_projected: number | null;
    grad_indatorare_projected: number | null;
}

export interface ForecastResponse {
    company_id: number;
    years_ahead: number;
    data_points: number;
    trend: string | null;
    historical: Record<string, unknown>[];
    predictions: ForecastPrediction[];
    methodology: string | null;
    disclaimer: string;
    error: string | null;
}

export interface BankruptcyRiskFactor {
    factor: string;
    impact: string;
    detail: string;
}

export interface BankruptcyPrediction {
    company_id: number;
    probability: number;
    category: string;
    features: Record<string, number>;
    risk_factors: BankruptcyRiskFactor[];
    risk_factors_count: number;
    risk_score_actual: number | null;
    model_version: string;
    disclaimer: string;
    error: string | null;
}

export interface DegradationWarning {
    signal: string;
    severity: string;
    detail: string;
}

export interface RiskDegradationResponse {
    company_id: number;
    current_score: number;
    current_rating: string | null;
    projected_score_6m: number;
    projected_rating_6m: string | null;
    degradation_probability: number;
    prediction: string;
    signals_detected: number;
    total_signals_checked: number;
    warnings: DegradationWarning[];
    disclaimer: string;
}

export interface SectorYearlyData {
    an: number;
    companies_reporting: number;
    total_ca: number;
    avg_ca: number;
    total_profit: number;
    avg_profit: number;
    total_employees: number;
    avg_employees: number;
}

export interface SectorTrendResponse {
    caen_code: string;
    total_companies: number;
    active_companies: number;
    sector_trend: string;
    insolvency_rate: number;
    yearly_data: SectorYearlyData[];
    births: { an: number; count: number }[];
    deaths: { an: number; count: number }[];
    analysis_period: string | null;
}

export interface MonteCarloCompanyRisk {
    company_id: number;
    ca: number;
    default_prob: number;
    volatility: number;
}

export interface MonteCarloDistBucket {
    range_low: number;
    range_high: number;
    count: number;
    frequency: number;
}

export interface MonteCarloResponse {
    portfolio_id: string;
    simulations: number;
    companies_count: number;
    baseline_ca: number;
    baseline_profit: number;
    expected_ca: number;
    expected_profit: number;
    var_95_ca: number;
    var_99_ca: number;
    worst_case_ca: number;
    best_case_ca: number;
    avg_defaults: number;
    max_defaults: number;
    distribution: MonteCarloDistBucket[];
    company_risks: MonteCarloCompanyRisk[];
    disclaimer: string;
    error: string | null;
}
