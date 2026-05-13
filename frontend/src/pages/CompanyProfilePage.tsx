import { useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, useMemo, useEffect } from "react";
import api from "@/lib/api";
import {
    formatMoney,
    formatNumber,
    formatDate,
    riskCategoryColor,
    riskCategoryLabel,
    cn,
} from "@/lib/utils";
import type { CompanyFull, FinancialData, RiskScore, ESGScore, FraudAlert } from "@/types";
import {
    Building2,
    Shield,
    Leaf,
    Users,
    Gavel,
    FileText,
    AlertTriangle,
    Globe,
    BarChart3,
    Download,
    Clock,
    CheckCircle2,
    Loader2,
    Star,
    Brain,
    Sparkles,
    TrendingUp,
    Award,
    Landmark,
    MapPin,
    Briefcase,
    Contact2,
    Map,
    ChevronDown,
} from "lucide-react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
// Fix leaflet default icon
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    Radar,
} from "recharts";
import { LoadingSpinner, EmptyState, TabNav, type TabItem } from "@/components/common";
import { useCompany, useCompanyFinancials, useRiskScore, useESGScore } from "@/hooks";
import { toast } from "sonner";

export default function CompanyProfilePage() {
    const { cui } = useParams<{ cui: string }>();
    const [activeTab, setActiveTab] = useState("identification");

    const { data: company, isLoading } = useCompany(cui);
    const { data: financials } = useCompanyFinancials(cui, activeTab === "financial" || activeTab === "timeline");
    const { data: risk } = useRiskScore(cui, activeTab === "risk");
    const { data: esg } = useESGScore(cui, activeTab === "esg");

    const TABS: TabItem[] = useMemo(() => [
        { id: "identification", label: "Detalii Identificare", icon: Contact2 },
        { id: "financial", label: "Financiar", icon: BarChart3 },
        { id: "risk", label: "Risc", icon: Shield },
        { id: "esg", label: "ESG", icon: Leaf },
        { id: "timeline", label: "Timeline", icon: Clock },
        { id: "persons", label: "Persoane", icon: Users },
        { id: "legal", label: "Juridic", icon: Gavel },
        { id: "contracts", label: "Contracte", icon: FileText },
        { id: "debts", label: "Datorii", icon: AlertTriangle },
        { id: "eu-projects", label: "Proiecte EU", icon: Globe },
        { id: "fraud", label: "Fraud", icon: Shield },
        { id: "extra", label: "BVB / OSIM / ASF", icon: Award },
    ], []);

    /* Export PDF mutation */
    const exportPdf = useMutation({
        mutationFn: async () => {
            const { data } = await api.post(`/reports/company/${cui}?format=pdf&sections=general,financial,legal,risk,esg,contracts,persons`);
            return data;
        },
        onSuccess: (data) => {
            if (data.download_url) {
                window.open(data.download_url, "_blank");
            }
            toast.success("Raport PDF generat cu succes");
        },
        onError: () => toast.error("Eroare la generarea raportului"),
    });

    /* Watch / Add to portfolio */
    const addToWatch = useMutation({
        mutationFn: async () => {
            // Try to find or create default "Watchlist" portfolio
            const { data: portfolios } = await api.get("/portfolios");
            let watchlist = (portfolios || []).find((p: { name: string }) => p.name === "Watchlist");
            if (!watchlist) {
                const { data: created } = await api.post("/portfolios", { name: "Watchlist", description: "Firme monitorizate" });
                watchlist = created;
            }
            await api.post(`/portfolios/${watchlist.id}/companies?cui=${cui}`);
            return watchlist;
        },
        onSuccess: () => toast.success("Firmă adăugată în Watchlist"),
        onError: () => toast.error("Eroare la adăugare în Watchlist"),
    });

    /* AI Report */
    const [aiReport, setAiReport] = useState<string | null>(null);
    const [showAiReport, setShowAiReport] = useState(false);
    const aiReportMut = useMutation({
        mutationFn: async () => {
            const { data } = await api.post(`/ai/report/${cui}`);
            return data;
        },
        onSuccess: (data) => { setAiReport(data.report); setShowAiReport(true); },
        onError: () => toast.error("AI temporar indisponibil — verifică creditul API"),
    });

    if (isLoading) {
        return <LoadingSpinner size="lg" className="h-64" />;
    }

    if (!company) {
        return <EmptyState message="Companie negăsită" />;
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="card-cosmic relative overflow-hidden">
                <div className="absolute inset-x-0 top-0 h-1.5 bg-nebula-gradient" />
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">{company.denumire}</h1>
                        <p className="mt-1 font-rajdhani text-sm text-slate-400">
                            CUI: {company.cui} · Nr. Reg. Com: {company.j_nr}
                        </p>
                        <p className="mt-1 font-exo text-sm text-slate-400">
                            {company.adresa_completa} · {company.judet}, {company.localitate}
                        </p>
                    </div>
                    <div className="flex flex-wrap items-start gap-2">
                        {/* Action buttons */}
                        <button
                            onClick={() => exportPdf.mutate()}
                            disabled={exportPdf.isPending}
                            className="flex items-center gap-1.5 rounded-xl bg-nebula-gradient px-4 py-2 text-sm font-semibold text-white shadow-nebula transition-all hover:shadow-lg disabled:opacity-60"
                        >
                            {exportPdf.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                            Export PDF
                        </button>
                        <button
                            onClick={() => aiReportMut.mutate()}
                            disabled={aiReportMut.isPending}
                            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white shadow-lg transition-all hover:shadow-xl disabled:opacity-60"
                        >
                            {aiReportMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
                            Raport AI
                        </button>
                        <button
                            onClick={() => addToWatch.mutate()}
                            disabled={addToWatch.isPending}
                            className="flex items-center gap-1.5 rounded-xl border border-stardust-400 bg-stardust-50 dark:bg-stardust-900/20 px-4 py-2 text-sm font-semibold text-stardust-600 dark:text-stardust-400 transition-all hover:bg-stardust-100 dark:hover:bg-stardust-900/30 disabled:opacity-60"
                        >
                            {addToWatch.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Star className="h-4 w-4" />}
                            Watch
                        </button>
                        <span
                            className={cn(
                                "rounded-full px-3 py-1 text-sm font-medium",
                                company.stare === "ACTIVA"
                                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                            )}
                        >
                            {company.stare}
                        </span>
                        {company.has_debts && (
                            <span className="rounded-full bg-orange-100 px-3 py-1 text-sm font-medium text-orange-700">
                                Datorii Buget
                            </span>
                        )}
                        {company.has_insolvency && (
                            <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-700">
                                Insolvență
                            </span>
                        )}
                    </div>
                </div>

                {/* Quick stats */}
                <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <div>
                        <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">CAEN</p>
                        <p className="font-exo text-sm font-medium text-slate-700">{company.caen_principal} — {company.descriere_caen}</p>
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">Formă Juridică</p>
                        <p className="font-exo text-sm font-medium text-slate-700">{company.forma_juridica}</p>
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">Capital Social</p>
                        <p className="font-exo text-sm font-medium text-slate-700">{formatMoney(company.capital_social)}</p>
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">Înființată</p>
                        <p className="font-exo text-sm font-medium text-slate-700">{formatDate(company.data_infiintare)}</p>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <TabNav tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

            {/* Tab Content */}
            {activeTab === "identification" && <IdentificationTab company={company} cui={cui!} />}
            {activeTab === "financial" && <FinancialTab financials={financials} />}
            {activeTab === "risk" && <RiskTab risk={risk} />}
            {activeTab === "esg" && <ESGTab esg={esg} />}
            {activeTab === "timeline" && <TimelineTab cui={cui!} company={company} financials={financials} />}
            {activeTab === "persons" && <PersonsTab cui={cui!} />}
            {activeTab === "legal" && <LegalTab cui={cui!} />}
            {activeTab === "contracts" && <ContractsTab cui={cui!} />}
            {activeTab === "debts" && <DebtsTab cui={cui!} />}
            {activeTab === "eu-projects" && <EUProjectsTab cui={cui!} />}
            {activeTab === "fraud" && <FraudTab cui={cui!} />}
            {activeTab === "extra" && <ExtraDataTab cui={cui!} />}

            {/* AI Report Modal */}
            {showAiReport && aiReport && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="relative max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-violet-200 bg-white dark:bg-slate-900 dark:border-violet-800 p-6 shadow-2xl">
                        <div className="absolute inset-x-0 top-0 h-1.5 rounded-t-2xl bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500" />
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <Sparkles className="h-5 w-5 text-violet-500" />
                                <h2 className="font-orbitron text-lg font-bold text-foreground">Raport AI — {company.denumire}</h2>
                            </div>
                            <button onClick={() => setShowAiReport(false)} className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground transition-colors">✕</button>
                        </div>
                        <div className="prose prose-sm dark:prose-invert max-w-none font-exo text-sm leading-relaxed whitespace-pre-wrap">
                            {aiReport}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Timeline Tab ── */
interface TimelineEvent {
    date: string;
    type: "infiintare" | "financiar" | "juridic" | "contract" | "eu-proiect" | "insolventa" | "datorie" | "altele";
    title: string;
    description: string;
    icon: typeof Building2;
    color: string;
}

function TimelineTab({ cui, company, financials }: { cui: string; company: CompanyFull; financials?: FinancialData[] }) {
    const { data: courtCases } = useQuery({
        queryKey: ["company", cui, "court-cases"],
        queryFn: () => api.get(`/companies/${cui}/court-cases`).then(r => r.data),
    });
    const { data: contracts } = useQuery({
        queryKey: ["company", cui, "contracts"],
        queryFn: () => api.get(`/companies/${cui}/contracts`).then(r => r.data),
    });
    const { data: euProjects } = useQuery({
        queryKey: ["company", cui, "eu-projects"],
        queryFn: () => api.get(`/companies/${cui}/eu-projects`).then(r => r.data),
    });

    const events: TimelineEvent[] = [];

    // Înființare
    if (company.data_infiintare) {
        events.push({
            date: company.data_infiintare,
            type: "infiintare",
            title: "Înființare Companie",
            description: `${company.denumire} — ${company.forma_juridica}, capital social ${formatMoney(company.capital_social)}`,
            icon: Building2,
            color: "bg-nebula-500",
        });
    }

    // Financial years
    if (financials) {
        financials.forEach(f => {
            events.push({
                date: `${f.an_fiscal}-12-31`,
                type: "financiar",
                title: `Bilanț ${f.an_fiscal}`,
                description: `CA: ${formatMoney(f.cifra_afaceri)} · Profit: ${formatMoney(f.profit_net)} · ${formatNumber(f.nr_angajati)} angajați`,
                icon: BarChart3,
                color: parseFloat(f.profit_net) >= 0 ? "bg-green-500" : "bg-dragon-500",
            });
        });
    }

    // Court cases
    if (courtCases) {
        courtCases.forEach((c: { id: number; numar_dosar: string; instanta: string; obiect: string; data_dosar: string }) => {
            events.push({
                date: c.data_dosar,
                type: "juridic",
                title: `Dosar ${c.numar_dosar}`,
                description: `${c.instanta} — ${c.obiect}`,
                icon: Gavel,
                color: "bg-orange-500",
            });
        });
    }

    // Contracts
    if (contracts) {
        contracts.forEach((c: { id: number; numar_contract: string; titlu: string; valoare: string; data_contract: string }) => {
            events.push({
                date: c.data_contract,
                type: "contract",
                title: `Contract SEAP ${c.numar_contract}`,
                description: `${c.titlu} — ${formatMoney(c.valoare)}`,
                icon: FileText,
                color: "bg-cosmos-500",
            });
        });
    }

    // EU Projects
    if (euProjects) {
        euProjects.forEach((p: { id: number; titlu_proiect: string; program: string; valoare_totala: string }) => {
            events.push({
                date: company.data_infiintare, // approximate
                type: "eu-proiect",
                title: `Proiect EU: ${p.program}`,
                description: `${p.titlu_proiect} — ${formatMoney(p.valoare_totala)}`,
                icon: Globe,
                color: "bg-stardust-500",
            });
        });
    }

    // Sort by date descending
    events.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    if (events.length === 0) {
        return <p className="font-rajdhani text-muted-foreground">Nu sunt evenimente disponibile.</p>;
    }

    return (
        <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-border" />

            <div className="space-y-0">
                {events.map((ev, i) => {
                    const Icon = ev.icon;
                    return (
                        <div key={i} className="relative flex gap-4 pb-8">
                            {/* Dot on timeline */}
                            <div className={cn(
                                "relative z-10 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-white shadow-md",
                                ev.color
                            )}>
                                <Icon className="h-4 w-4" />
                            </div>

                            {/* Content card */}
                            <div className="card-cosmic flex-1 py-3 px-4 transition-all hover:shadow-nebula/10">
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <p className="font-exo text-sm font-semibold text-foreground">{ev.title}</p>
                                        <p className="mt-0.5 font-rajdhani text-sm text-muted-foreground">{ev.description}</p>
                                    </div>
                                    <span className="whitespace-nowrap font-rajdhani text-xs font-medium text-muted-foreground">
                                        {formatDate(ev.date)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Identification Tab (merged: identificare + sediu + descriere + activitate) ── */
function IdentificationTab({ company, cui }: { company: CompanyFull; cui: string }) {
    const { data: aiSummary, isLoading: aiLoading } = useQuery({
        queryKey: ["ai-summary", cui],
        queryFn: () => api.get(`/ai/summary/${cui}`).then(r => r.data),
        retry: false,
        staleTime: 86400_000,
    });

    const { data: trademarks, isLoading: loadTm } = useQuery({
        queryKey: ["company", cui, "trademarks"],
        queryFn: async () => (await api.get(`/companies/${cui}/trademarks`)).data,
        staleTime: 86400_000,
    });

    const [showMap, setShowMap] = useState(false);
    const [geocodedCoords, setGeocodedCoords] = useState<[number, number] | null>(null);
    const [geocoding, setGeocoding] = useState(false);

    const precomputedLat = company.lat ? Number(company.lat) : null;
    const precomputedLng = company.lng ? Number(company.lng) : null;
    const hasPrecomputedCoords = precomputedLat !== null && precomputedLng !== null && !isNaN(precomputedLat) && !isNaN(precomputedLng);

    useEffect(() => {
        if (!showMap || hasPrecomputedCoords || geocodedCoords || geocoding) return;
        const query = [company.adresa_completa, company.judet].filter(Boolean).join(", ");
        if (!query) return;
        setGeocoding(true);
        fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&countrycodes=ro`,
            { headers: { "User-Agent": "RomBiz/1.0 (rating.nineinternational.ro)" } }
        )
            .then(r => r.json())
            .then((data: { lat: string; lon: string }[]) => {
                if (data?.[0]) setGeocodedCoords([parseFloat(data[0].lat), parseFloat(data[0].lon)]);
            })
            .catch(() => {})
            .finally(() => setGeocoding(false));
    }, [showMap, hasPrecomputedCoords, geocodedCoords, geocoding, company.adresa_completa, company.judet]);

    const caenCode = company.caen_principal || "—";
    const caenDesc = (company as CompanyFull & { descriere_caen?: string }).descriere_caen || "—";

    return (
        <div className="space-y-6">

            {/* ── 1. Detalii de Identificare ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <Contact2 className="h-4 w-4 text-nebula-500" />
                        Detalii de Identificare
                    </h3>
                    <dl className="space-y-3">
                        {[
                            ["Denumire", company.denumire],
                            ["CUI", company.cui],
                            ["Nr. Reg. Com.", company.j_nr || "—"],
                            ["EUID", company.euid || "—"],
                            ["Data Înființare", formatDate(company.data_infiintare)],
                        ].map(([label, value]) => (
                            <div key={label} className="flex justify-between gap-4">
                                <dt className="font-rajdhani text-sm text-slate-400 shrink-0">{label}</dt>
                                <dd className="font-exo text-sm font-medium text-slate-700 text-right">{value}</dd>
                            </div>
                        ))}
                    </dl>
                </div>

                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-nebula-500" />
                        Statut Juridic
                    </h3>
                    <dl className="space-y-3">
                        {[
                            ["Formă Juridică", company.forma_juridica || "—"],
                            ["Stare", company.stare],
                            ["Capital Social", formatMoney(company.capital_social)],
                            ["TVA", company.platitor_tva ? "Plătitor TVA" : "Neplătitor TVA"],
                        ].map(([label, value]) => (
                            <div key={label} className="flex justify-between gap-4">
                                <dt className="font-rajdhani text-sm text-slate-400 shrink-0">{label}</dt>
                                <dd className="font-exo text-sm font-medium text-slate-700 text-right">{value}</dd>
                            </div>
                        ))}
                        <div className="flex justify-between items-center gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">RO e-Factura</dt>
                            <dd>
                                {company.status_ro_efactura ? (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                                        <CheckCircle2 className="h-3 w-3" /> Înscrisă
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">Nu</span>
                                )}
                            </dd>
                        </div>
                    </dl>
                </div>
            </div>

            {/* ── 2. Sediu & Contact ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-nebula-500" />
                        Sediu Social
                    </h3>
                    <dl className="space-y-3">
                        {[
                            ["Județ", company.judet || "—"],
                            ["Localitate", company.localitate || "—"],
                            ["Adresă", company.adresa_completa || "—"],
                            ["Cod Poștal", (company as CompanyFull & { cod_postal?: string }).cod_postal || "—"],
                        ].map(([label, value]) => (
                            <div key={label} className="flex justify-between gap-4">
                                <dt className="font-rajdhani text-sm text-slate-400 shrink-0">{label}</dt>
                                <dd className="font-exo text-sm font-medium text-slate-700 text-right">{value}</dd>
                            </div>
                        ))}
                    </dl>
                </div>

                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <Globe className="h-4 w-4 text-nebula-500" />
                        Informații de Contact
                    </h3>
                    {!company.telefon && !company.fax && !company.email && !company.website ? (
                        <p className="font-rajdhani text-sm text-slate-400">Date de contact nedisponibile.</p>
                    ) : (
                        <dl className="space-y-3">
                            {company.telefon && (
                                <div className="flex justify-between gap-4">
                                    <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Telefon</dt>
                                    <dd className="font-exo text-sm font-medium text-slate-700 text-right">
                                        <a href={`tel:${company.telefon}`} className="hover:text-nebula-600">{company.telefon}</a>
                                    </dd>
                                </div>
                            )}
                            {company.fax && (
                                <div className="flex justify-between gap-4">
                                    <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Fax</dt>
                                    <dd className="font-exo text-sm font-medium text-slate-700 text-right">{company.fax}</dd>
                                </div>
                            )}
                            {company.email && (
                                <div className="flex justify-between gap-4">
                                    <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Email</dt>
                                    <dd className="font-exo text-sm font-medium text-slate-700 text-right">
                                        <a href={`mailto:${company.email}`} className="text-nebula-500 hover:underline">{company.email}</a>
                                    </dd>
                                </div>
                            )}
                            {company.website && (
                                <div className="flex justify-between gap-4">
                                    <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Adresă Web</dt>
                                    <dd className="font-exo text-sm font-medium text-right">
                                        <a href={company.website.startsWith("http") ? company.website : `https://${company.website}`} target="_blank" rel="noopener noreferrer" className="text-nebula-500 hover:underline">
                                            {company.website}
                                        </a>
                                    </dd>
                                </div>
                            )}
                        </dl>
                    )}
                </div>
            </div>

            {/* ── 3. Descriere Firmă (AI) ── */}
            <div className="card-cosmic relative overflow-hidden border border-violet-200 dark:border-violet-800/50">
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500" />
                <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="h-4 w-4 text-violet-500" />
                    <h3 className="font-orbitron text-sm font-semibold tracking-wide text-violet-600 dark:text-violet-400">
                        Descrierea Firmei — {company.denumire}
                    </h3>
                    {aiLoading && <Loader2 className="ml-auto h-3.5 w-3.5 animate-spin text-violet-400" />}
                </div>
                {aiSummary?.summary ? (
                    <p className="font-exo text-sm leading-relaxed text-slate-600 dark:text-slate-300">{aiSummary.summary}</p>
                ) : aiLoading ? (
                    <div className="space-y-2">
                        <div className="h-3 w-full animate-pulse rounded bg-violet-100 dark:bg-violet-900/30" />
                        <div className="h-3 w-4/5 animate-pulse rounded bg-violet-100 dark:bg-violet-900/30" />
                        <div className="h-3 w-3/5 animate-pulse rounded bg-violet-100 dark:bg-violet-900/30" />
                    </div>
                ) : (
                    <p className="font-rajdhani text-sm text-slate-400">Sumarul AI nu este disponibil momentan.</p>
                )}
            </div>

            {/* ── 4. Domeniu de Activitate ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <Briefcase className="h-4 w-4 text-nebula-500" />
                        Cod CAEN Preponderent
                    </h3>
                    <p className="font-rajdhani text-xs text-slate-400 mb-4">
                        Activitatea care generează cel mai mare venit (conform ultimului bilanț).
                    </p>
                    <dl className="space-y-3">
                        <div className="flex justify-between gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Cod CAEN</dt>
                            <dd className="font-exo text-sm font-bold text-nebula-600">{caenCode}</dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Obiect Activitate</dt>
                            <dd className="font-exo text-sm font-medium text-slate-700 text-right">{caenDesc}</dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Descriere Activitate</dt>
                            <dd className="font-exo text-sm font-medium text-slate-700 text-right">{caenDesc}</dd>
                        </div>
                    </dl>
                </div>

                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <Briefcase className="h-4 w-4 text-cosmos-500" />
                        Cod CAEN Principal
                    </h3>
                    <p className="font-rajdhani text-xs text-slate-400 mb-4">
                        Activitatea înregistrată ca principală la Registrul Comerțului (ONRC).
                    </p>
                    <dl className="space-y-3">
                        <div className="flex justify-between gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Cod CAEN</dt>
                            <dd className="font-exo text-sm font-bold text-cosmos-600">{caenCode}</dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Obiect Activitate</dt>
                            <dd className="font-exo text-sm font-medium text-slate-700 text-right">{caenDesc}</dd>
                        </div>
                        <div className="flex justify-between gap-4">
                            <dt className="font-rajdhani text-sm text-slate-400 shrink-0">Descriere Activitate</dt>
                            <dd className="font-exo text-sm font-medium text-slate-700 text-right">{caenDesc}</dd>
                        </div>
                    </dl>
                </div>
            </div>

            {/* ── 5. Istoric TVA ── */}
            {company.tva_perioade && company.tva_perioade.length > 0 && (
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Istoric TVA</h3>
                    <div className="space-y-2">
                        {company.tva_perioade.map((p, i) => (
                            <div key={i} className="flex items-start justify-between rounded-lg bg-slate-50 dark:bg-slate-800/50 px-4 py-3 text-sm">
                                <div>
                                    <span className="font-exo font-medium text-slate-700">
                                        {p.data_inceput_ScpTVA || "—"} → {p.data_sfarsit_ScpTVA || "prezent"}
                                    </span>
                                    {p.mesaj_ScpTVA && (
                                        <p className="mt-0.5 font-rajdhani text-xs text-slate-500">{p.mesaj_ScpTVA}</p>
                                    )}
                                </div>
                                <span className={`ml-4 shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${!p.data_sfarsit_ScpTVA ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                                    {!p.data_sfarsit_ScpTVA ? "Activ" : "Expirat"}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── 6. Mărci înregistrate la OSIM ── */}
            <div className="card-cosmic">
                <div className="flex items-center gap-2 mb-4">
                    <Award className="h-4 w-4 text-nebula-500" />
                    <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700">Mărci înregistrate la OSIM</h3>
                </div>
                {loadTm ? (
                    <LoadingSpinner />
                ) : trademarks?.length ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-nebula-100 text-left text-xs text-slate-500 uppercase">
                                    <th className="pb-2 pr-4">Tip</th>
                                    <th className="pb-2 pr-4">Denumire</th>
                                    <th className="pb-2 pr-4">Nr. Înregistrare</th>
                                    <th className="pb-2 pr-4">Data Înreg.</th>
                                    <th className="pb-2 pr-4">Expiră</th>
                                    <th className="pb-2">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-nebula-100">
                                {trademarks.map((t: { tip: string; denumire: string; nr_inregistrare: string; data_inregistrare: string; data_expirare: string; status: string }, i: number) => (
                                    <tr key={i} className="hover:bg-nebula-50/50">
                                        <td className="py-2 pr-4 font-rajdhani capitalize">{t.tip}</td>
                                        <td className="py-2 pr-4 font-medium">{t.denumire}</td>
                                        <td className="py-2 pr-4 font-mono text-xs">{t.nr_inregistrare}</td>
                                        <td className="py-2 pr-4 text-slate-500">{t.data_inregistrare?.slice(0, 10)}</td>
                                        <td className="py-2 pr-4 text-slate-500">{t.data_expirare?.slice(0, 10)}</td>
                                        <td className="py-2">
                                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${t.status === "activa" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"}`}>
                                                {t.status ?? "—"}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="font-rajdhani text-sm text-slate-400">Nu există mărci sau brevete înregistrate la OSIM.</p>
                )}
            </div>

            {/* ── 7. Localizare pe hartă ── */}
            <div className="card-cosmic">
                <button
                    onClick={() => setShowMap(v => !v)}
                    className="flex w-full items-center justify-between"
                >
                    <div className="flex items-center gap-2">
                        <Map className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700">Localizare pe Hartă</h3>
                    </div>
                    <ChevronDown className={cn("h-4 w-4 text-slate-400 transition-transform duration-200", showMap && "rotate-180")} />
                </button>

                {showMap && (
                    <div className="mt-4">
                        {(() => {
                            const mapCoords: [number, number] | null =
                                hasPrecomputedCoords ? [precomputedLat!, precomputedLng!] : geocodedCoords;
                            if (geocoding) {
                                return (
                                    <div className="flex items-center justify-center gap-2 py-10 text-slate-400">
                                        <Loader2 className="h-5 w-5 animate-spin" />
                                        <span className="font-rajdhani text-sm">Se determină localizarea pe baza adresei…</span>
                                    </div>
                                );
                            }
                            if (mapCoords) {
                                return (
                                    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700" style={{ height: 380 }}>
                                        <MapContainer
                                            center={mapCoords}
                                            zoom={15}
                                            style={{ height: "100%", width: "100%" }}
                                            scrollWheelZoom={false}
                                        >
                                            <TileLayer
                                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                            />
                                            <Marker position={mapCoords}>
                                                <Popup>
                                                    <div className="text-sm">
                                                        <p className="font-semibold">{company.denumire}</p>
                                                        <p className="text-slate-500 mt-0.5">{company.adresa_completa}</p>
                                                    </div>
                                                </Popup>
                                            </Marker>
                                        </MapContainer>
                                    </div>
                                );
                            }
                            return (
                                <div className="flex flex-col items-center justify-center py-10 text-slate-400">
                                    <MapPin className="h-8 w-8 mb-2 opacity-40" />
                                    <p className="font-rajdhani text-sm">Nu s-a putut determina localizarea pentru această adresă.</p>
                                    <p className="font-rajdhani text-xs mt-1">{company.adresa_completa || "Adresă necunoscută"}</p>
                                </div>
                            );
                        })()}
                    </div>
                )}
            </div>
        </div>
    );
}


function FinancialTab({ financials }: { financials?: FinancialData[] }) {
    if (!financials || financials.length === 0) {
        return <p className="font-rajdhani text-slate-400">Nu sunt date financiare disponibile.</p>;
    }

    const sorted = [...financials].filter(f => f.an_fiscal >= 2015).sort((a, b) => a.an_fiscal - b.an_fiscal);
    const chartData = sorted.map((f) => ({
        an: f.an_fiscal,
        "Cifra Afaceri": parseFloat(f.cifra_afaceri),
        "Profit Net": parseFloat(f.profit_net),
    }));

    return (
        <div className="space-y-6">
            {/* Chart */}
            <div className="card-cosmic">
                <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Evoluție Financiară</h3>
                <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="an" />
                        <YAxis tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                        <Tooltip formatter={(v: number) => formatMoney(v)} />
                        <Line type="monotone" dataKey="Cifra Afaceri" stroke="#7c3aed" strokeWidth={2} />
                        <Line type="monotone" dataKey="Profit Net" stroke="#22c55e" strokeWidth={2} />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Table */}
            <div className="card-cosmic p-0 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b bg-nebula-50/30">
                                <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">An</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Cifra Afaceri</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Profit Net</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Datorii Totale</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Active Imobilizate</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Active Circulante</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Capitaluri Proprii</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Nr. Salariați</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sorted.reverse().map((f) => (
                                <tr key={f.an_fiscal} className="border-b">
                                    <td className="px-4 py-3 font-medium">{f.an_fiscal}</td>
                                    <td className="px-4 py-3 text-right">{formatMoney(f.cifra_afaceri)}</td>
                                    <td className="px-4 py-3 text-right">{formatMoney(f.profit_net)}</td>
                                    <td className="px-4 py-3 text-right">{formatMoney(f.total_datorii)}</td>
                                    <td className="px-4 py-3 text-right">{formatMoney(f.active_imobilizate)}</td>
                                    <td className="px-4 py-3 text-right">{formatMoney(f.active_circulante)}</td>
                                    <td className="px-4 py-3 text-right">{formatMoney(f.capitaluri_prop)}</td>
                                    <td className="px-4 py-3 text-right">{formatNumber(f.nr_angajati)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function RiskTab({ risk }: { risk?: RiskScore }) {
    const [infoOpen, setInfoOpen] = useState(false);

    if (!risk) {
        return <p className="font-rajdhani text-slate-400">Scorul de risc nu a fost calculat.</p>;
    }

    const radarData = [
        { subject: "Financiar", value: parseFloat(risk.scor_financiar) },
        { subject: "Juridic", value: parseFloat(risk.scor_legal) },
        { subject: "Fiscal", value: parseFloat(risk.scor_fiscal) },
        { subject: "Comportamental", value: parseFloat(risk.scor_comportamental) },
    ];

    return (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="card-cosmic">
                <div className="text-center">
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Scor Total Risc</p>
                    <p className="mt-2 font-orbitron text-5xl font-bold text-slate-800">{parseFloat(risk.score).toFixed(1)}</p>
                    <span
                        className={cn(
                            "mt-2 inline-block rounded-full px-4 py-1 text-sm font-semibold",
                            riskCategoryColor(risk.rating)
                        )}
                    >
                        Categoria {risk.rating} — {riskCategoryLabel(risk.rating)}
                    </span>
                    <p className="mt-4 font-rajdhani text-xs text-slate-400">
                        Calculat la: {formatDate(risk.calculat_la)}
                    </p>
                </div>
            </div>

            <div className="card-cosmic">
                <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Componente Risc</h3>
                <ResponsiveContainer width="100%" height={250}>
                    <RadarChart data={radarData}>
                        <PolarGrid />
                        <PolarAngleAxis dataKey="subject" />
                        <Radar
                            name="Score"
                            dataKey="value"
                            stroke="#7c3aed"
                            fill="#7c3aed"
                            fillOpacity={0.3}
                        />
                    </RadarChart>
                </ResponsiveContainer>
            </div>

            {/* Score breakdown */}
            <div className="card-cosmic lg:col-span-2">
                <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Detalii Componente</h3>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    {[
                        { label: "Financiar (30%)", value: risk.scor_financiar },
                        { label: "Juridic (25%)", value: risk.scor_legal },
                        { label: "Fiscal (25%)", value: risk.scor_fiscal },
                        { label: "Comportamental (20%)", value: risk.scor_comportamental },
                    ].map((comp) => (
                        <div key={comp.label} className="text-center">
                            <p className="font-rajdhani text-sm text-slate-400">{comp.label}</p>
                            <p className="font-orbitron text-2xl font-bold text-slate-800">{parseFloat(comp.value).toFixed(1)}</p>
                            <div className="mt-2 h-2 w-full rounded-full bg-nebula-100">
                                <div
                                    className="h-2 rounded-full bg-nebula-gradient"
                                    style={{ width: `${parseFloat(comp.value)}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Metodologie */}
            <div className="card-cosmic lg:col-span-2">
                <button
                    onClick={() => setInfoOpen((v) => !v)}
                    className="flex w-full items-center justify-between text-left"
                >
                    <span className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full border border-nebula-400 text-nebula-600 text-xs font-bold">i</span>
                        Cum este calculat scorul de risc?
                    </span>
                    <span className={cn("text-slate-400 transition-transform", infoOpen && "rotate-180")}>▾</span>
                </button>

                {infoOpen && (
                    <div className="mt-4 space-y-4 font-rajdhani text-sm text-slate-600">
                        <p className="text-slate-500">
                            Scorul total de risc se calculează ca medie ponderată a patru componente independente, fiecare notată de la 1 la 100:
                        </p>
                        <div className="rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-700">
                            Scor Total = 0.30 × Financiar + 0.25 × Juridic + 0.25 × Fiscal + 0.20 × Comportamental
                        </div>

                        <div className="space-y-3">
                            {/* Financiar */}
                            <div className="rounded-lg border border-nebula-100 p-3">
                                <p className="font-semibold text-slate-800 mb-1">📊 Financiar — 30%</p>
                                <p className="text-slate-500 mb-2">Evaluează sănătatea financiară pe baza datelor din bilanțurile MF (ultimul an disponibil).</p>
                                <ul className="space-y-1 list-disc list-inside text-slate-600">
                                    <li><strong>Bază:</strong> 50 puncte (40 dacă nu există date financiare)</li>
                                    <li><strong>Lichiditate curentă</strong> (active circulante / datorii totale): +/−20 pts — lichiditate ≥ 2 este optimă</li>
                                    <li><strong>Marjă de profit</strong> (profit net / cifră afaceri): +10 pts max — margin ≥ 10% este bun</li>
                                    <li><strong>ROA</strong> (profit net / total active × 100): +10 pts max — ROA ≥ 5% este bun</li>
                                    <li><strong>Grad de îndatorare</strong> (datorii / active): −20 pts max — grad ≥ 1 este critic</li>
                                    <li><strong>Istoricul datelor:</strong> +5 pts dacă există ≥ 3 ani de bilanțuri, +2 pts dacă ≥ 1 an</li>
                                </ul>
                            </div>

                            {/* Juridic */}
                            <div className="rounded-lg border border-nebula-100 p-3">
                                <p className="font-semibold text-slate-800 mb-1">⚖️ Juridic — 25%</p>
                                <p className="text-slate-500 mb-2">Evaluează expunerea juridică pe baza dosarelor din Portal Just.</p>
                                <ul className="space-y-1 list-disc list-inside text-slate-600">
                                    <li><strong>Fără dosare:</strong> 80 pts</li>
                                    <li><strong>1–4 dosare:</strong> 65 pts</li>
                                    <li><strong>5–9 dosare:</strong> 50 pts</li>
                                    <li><strong>≥ 10 dosare:</strong> 30 pts</li>
                                    <li><strong>Dosar faliment / insolvență:</strong> 10 pts</li>
                                    <li><strong>Flag insolvență activ (ONRC):</strong> 5 pts</li>
                                </ul>
                            </div>

                            {/* Fiscal */}
                            <div className="rounded-lg border border-nebula-100 p-3">
                                <p className="font-semibold text-slate-800 mb-1">🧾 Fiscal — 25%</p>
                                <p className="text-slate-500 mb-2">Evaluează conformitatea fiscală pe baza datelor ANAF.</p>
                                <ul className="space-y-1 list-disc list-inside text-slate-600">
                                    <li><strong>Fără datorii + plătitor TVA activ:</strong> 80 pts</li>
                                    <li><strong>Fără datorii, non-TVA:</strong> 70 pts</li>
                                    <li><strong>Are datorii bugetare:</strong> 60 pts</li>
                                    <li><strong>Datorii &gt; 10.000 RON:</strong> 55 pts</li>
                                    <li><strong>Datorii &gt; 100.000 RON:</strong> 35 pts</li>
                                    <li><strong>Datorii &gt; 1.000.000 RON:</strong> 15 pts</li>
                                    <li><strong>Inactiv fiscal (ANAF):</strong> 5 pts</li>
                                </ul>
                            </div>

                            {/* Comportamental */}
                            <div className="rounded-lg border border-nebula-100 p-3">
                                <p className="font-semibold text-slate-800 mb-1">🔍 Comportamental — 20%</p>
                                <p className="text-slate-500 mb-2">Evaluează semnalele de risc comportamental și stabilitatea companiei.</p>
                                <ul className="space-y-1 list-disc list-inside text-slate-600">
                                    <li><strong>Bază:</strong> 70 pts</li>
                                    <li><strong>Plătitor TVA activ:</strong> +10 pts</li>
                                    <li><strong>Capital social &gt; 50.000 RON:</strong> +5 pts</li>
                                    <li><strong>Are datorii bugetare:</strong> −10 pts</li>
                                    <li><strong>Split TVA activ:</strong> −10 pts</li>
                                    <li><strong>Inactiv fiscal:</strong> −30 pts</li>
                                    <li><strong>Flag insolvență:</strong> −30 pts</li>
                                </ul>
                            </div>
                        </div>

                        {/* Categorii */}
                        <div>
                            <p className="font-semibold text-slate-700 mb-2">Categorii de risc:</p>
                            <div className="grid grid-cols-5 gap-2 text-center text-xs">
                                {[
                                    { cat: "A", range: "80–100", label: "Risc Minim", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
                                    { cat: "B", range: "60–79", label: "Risc Scăzut", cls: "bg-sky-50 text-sky-700 border-sky-200" },
                                    { cat: "C", range: "40–59", label: "Risc Mediu", cls: "bg-amber-50 text-amber-700 border-amber-200" },
                                    { cat: "D", range: "20–39", label: "Risc Ridicat", cls: "bg-orange-50 text-orange-700 border-orange-200" },
                                    { cat: "E", range: "1–19", label: "Risc Critic", cls: "bg-red-50 text-red-700 border-red-200" },
                                ].map(({ cat, range, label, cls }) => (
                                    <div key={cat} className={cn("rounded border p-2", cls)}>
                                        <div className="font-orbitron font-bold text-base">{cat}</div>
                                        <div className="font-semibold">{range}</div>
                                        <div className="text-xs opacity-80">{label}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <p className="text-xs text-slate-400 italic">
                            Modelul de scoring bulk v2.0 — actualizat automat pe baza datelor ANAF, MF, Portal Just și ONRC.
                            Ponderile pot fi ajustate per industrie (CAEN 2 cifre).
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

function ESGTab({ esg }: { esg?: ESGScore }) {
    if (!esg) {
        return <p className="font-rajdhani text-slate-400">Scorul ESG nu a fost calculat.</p>;
    }

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-nebula-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">ESG Total</p>
                    <p className="mt-2 font-orbitron text-4xl font-bold text-slate-800">{parseFloat(esg.score_total).toFixed(1)}</p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 to-green-500" />
                    <p className="font-rajdhani text-sm font-semibold text-esg-environmental">Environmental</p>
                    <p className="mt-2 font-orbitron text-3xl font-bold text-esg-environmental">
                        {parseFloat(esg.score_e).toFixed(1)}
                    </p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-cosmos-400 to-blue-500" />
                    <p className="font-rajdhani text-sm font-semibold text-esg-social">Social</p>
                    <p className="mt-2 font-orbitron text-3xl font-bold text-esg-social">
                        {parseFloat(esg.score_s).toFixed(1)}
                    </p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-dragon-400 to-amber-500" />
                    <p className="font-rajdhani text-sm font-semibold text-esg-governance">Governance</p>
                    <p className="mt-2 font-orbitron text-3xl font-bold text-esg-governance">
                        {parseFloat(esg.score_g).toFixed(1)}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="card-cosmic">
                    <h3 className="mb-2 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Clasificare</h3>
                    <p className="text-sm">
                        <strong>CSRD:</strong>{" "}
                        {esg.csrd_relevant ? "Aplicabil" : "Nu se aplică"}
                    </p>
                    <p className="mt-1 text-sm">
                        <strong>SFDR:</strong> {esg.sfdr_categoria}
                    </p>
                </div>
                <div className="card-cosmic">
                    <h3 className="mb-2 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Surse Citate</h3>
                    <ul className="list-disc pl-4 text-sm">
                        {(esg.surse_date || []).map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Disclaimer — Hard constraint #12 */}
            <div className="card-cosmic border-l-4 border-dragon-fire py-3 px-4 text-sm text-dragon-600">
                <strong className="font-orbitron text-xs">Disclaimer:</strong> <span className="font-rajdhani">Scorul ESG este generat automat pe baza datelor publice disponibile.</span>
            </div>
        </div>
    );
}

function PersonsTab({ cui }: { cui: string }) {
    const { data: persons, isLoading } = useQuery({
        queryKey: ["company", cui, "persons"],
        queryFn: async () => {
            const { data } = await api.get(`/companies/${cui}/persons`);
            return data;
        },
    });

    if (isLoading) return <LoadingSpinner />;

    if (!persons || persons.length === 0) {
        return <p className="font-rajdhani text-slate-400">Nu sunt date despre persoane disponibile.</p>;
    }

    return (
        <div className="card-cosmic p-0 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b bg-nebula-50/30">
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Nume</th>
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Calitate</th>
                            <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Participare %</th>
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Data Începere</th>
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Data Sfârșit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(persons || []).map((p: { id: number; tip: string; nume_complet: string; procent_parti: number | null; data_start: string; data_sfarsit: string | null }) => (
                            <tr key={p.id} className="border-b border-nebula-100/30 transition-colors hover:bg-nebula-50/20">
                                <td className="px-4 py-3 font-exo font-medium text-slate-700">{p.nume_complet || "—"}</td>
                                <td className="px-4 py-3">
                                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${p.tip === "ADMINISTRATOR" ? "bg-blue-100 text-blue-700" : p.tip === "ASOCIAT" ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-600"}`}>
                                        {p.tip}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-right font-exo text-slate-600">
                                    {p.procent_parti != null ? `${p.procent_parti.toFixed(2)}%` : "—"}
                                </td>
                                <td className="px-4 py-3 font-exo text-slate-600">{formatDate(p.data_start)}</td>
                                <td className="px-4 py-3 font-exo text-slate-600">{p.data_sfarsit ? formatDate(p.data_sfarsit) : "prezent"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function LegalTab({ cui }: { cui: string }) {
    const { data: cases, isLoading } = useQuery({
        queryKey: ["company", cui, "court-cases"],
        queryFn: async () => {
            const { data } = await api.get(`/companies/${cui}/court-cases`);
            return data;
        },
    });

    if (isLoading) return <LoadingSpinner />;

    return (
        <div className="space-y-3">
            {(cases || []).map((c: { id: number; numar_dosar: string; instanta: string; obiect: string; data_dosar: string; calitate: string }) => (
                <div key={c.id} className="card-cosmic py-4 px-5 transition-all hover:shadow-nebula/20">
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="font-exo font-semibold text-slate-700">{c.numar_dosar}</p>
                            <p className="font-rajdhani text-sm text-slate-400">
                                {c.instanta} · {c.obiect}
                            </p>
                        </div>
                        <span className="badge-cosmic">{c.calitate}</span>
                    </div>
                    <p className="mt-1 font-rajdhani text-xs text-slate-400">{formatDate(c.data_dosar)}</p>
                </div>
            ))}
            {(!cases || cases.length === 0) && (
                <p className="font-rajdhani text-slate-400">Nu sunt dosare înregistrate.</p>
            )}
        </div>
    );
}

function ContractsTab({ cui }: { cui: string }) {
    const { data: contracts, isLoading } = useQuery({
        queryKey: ["company", cui, "contracts"],
        queryFn: async () => {
            const { data } = await api.get(`/companies/${cui}/contracts`);
            return data;
        },
    });

    if (isLoading) return <LoadingSpinner />;

    return (
        <div className="card-cosmic p-0 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b bg-nebula-50/30">
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Nr. Contract</th>
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Titlu</th>
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Autoritate</th>
                            <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Valoare</th>
                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Data</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(contracts || []).map((c: { id: number; numar_contract: string; titlu: string; autoritate: string; valoare: string; data_contract: string }) => (
                            <tr key={c.id} className="border-b border-nebula-100/30 transition-colors hover:bg-nebula-50/20">
                                <td className="px-4 py-3 font-exo text-slate-600">{c.numar_contract}</td>
                                <td className="px-4 py-3 max-w-xs truncate font-exo text-slate-700">{c.titlu}</td>
                                <td className="px-4 py-3 font-exo text-slate-600">{c.autoritate}</td>
                                <td className="px-4 py-3 text-right font-exo font-medium text-slate-700">{formatMoney(c.valoare)}</td>
                                <td className="px-4 py-3 font-exo text-slate-600">{formatDate(c.data_contract)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function DebtsTab({ cui }: { cui: string }) {
    const { data, isLoading } = useQuery({
        queryKey: ["redbill", cui],
        queryFn: async () => {
            const { data } = await api.get(`/redbill/${cui}`);
            return data;
        },
    });

    if (isLoading) return <LoadingSpinner />;
    if (!data) return <p className="font-rajdhani text-slate-400">Nu sunt date disponibile.</p>;

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-dragon-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Total Datorii</p>
                    <p className="font-orbitron text-2xl font-bold text-slate-800">{formatMoney(data.total_datorii || "0")}</p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-nebula-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Clasificare</p>
                    <p className="font-orbitron text-2xl font-bold capitalize text-slate-800">{data.risk_classification}</p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-cosmos-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Grad de Prospețime</p>
                    <p className="font-orbitron text-2xl font-bold text-slate-800">{data.freshness_days} zile</p>
                </div>
            </div>
        </div>
    );
}

function EUProjectsTab({ cui }: { cui: string }) {
    const { data: projects, isLoading } = useQuery({
        queryKey: ["company", cui, "eu-projects"],
        queryFn: async () => {
            const { data } = await api.get(`/companies/${cui}/eu-projects`);
            return data;
        },
    });

    if (isLoading) return <LoadingSpinner />;

    return (
        <div className="space-y-3">
            {(projects || []).map((p: { id: number; titlu_proiect: string; program: string; valoare_totala: string; stare: string }) => (
                <div key={p.id} className="card-cosmic py-4 px-5 transition-all hover:shadow-nebula/20">
                    <p className="font-exo font-semibold text-slate-700">{p.titlu_proiect}</p>
                    <p className="font-rajdhani text-sm text-slate-400">
                        {p.program} · {formatMoney(p.valoare_totala)} · {p.stare}
                    </p>
                </div>
            ))}
            {(!projects || projects.length === 0) && (
                <p className="font-rajdhani text-slate-400">Nu sunt proiecte EU înregistrate.</p>
            )}
        </div>
    );
}

// ── Extra Date: BVB + OSIM + ASF ──────────────────────────────────────────────
function ExtraDataTab({ cui }: { cui: string }) {
    const { data: bvb, isLoading: loadBvb } = useQuery({
        queryKey: ["company", cui, "bvb"],
        queryFn: async () => (await api.get(`/companies/${cui}/bvb`)).data,
    });
    const { data: trademarks, isLoading: loadTm } = useQuery({
        queryKey: ["company", cui, "trademarks"],
        queryFn: async () => (await api.get(`/companies/${cui}/trademarks`)).data,
    });
    const { data: asf, isLoading: loadAsf } = useQuery({
        queryKey: ["company", cui, "asf"],
        queryFn: async () => (await api.get(`/companies/${cui}/asf`)).data,
    });

    return (
        <div className="space-y-6">
            {/* ── BVB ── */}
            <div className="card-cosmic p-5">
                <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="h-5 w-5 text-nebula-400" />
                    <h3 className="font-orbitron text-sm font-semibold text-slate-700 uppercase tracking-wide">BVB — Bursa de Valori București</h3>
                </div>
                {loadBvb ? <LoadingSpinner /> : bvb?.listed ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Ticker</p>
                            <p className="font-orbitron text-lg font-bold text-slate-800">{bvb.ticker}</p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Ultimul Preț</p>
                            <p className="font-orbitron text-lg font-bold text-slate-800">{bvb.last_price ?? "—"}</p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Variație %</p>
                            <p className={`font-orbitron text-lg font-bold ${(bvb.change_pct ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                                {bvb.change_pct != null ? `${bvb.change_pct > 0 ? "+" : ""}${bvb.change_pct}%` : "—"}
                            </p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Market Cap</p>
                            <p className="font-orbitron text-lg font-bold text-slate-800">{bvb.market_cap != null ? `${(bvb.market_cap / 1_000_000).toFixed(1)}M` : "—"}</p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">ISIN</p>
                            <p className="font-mono text-sm text-slate-700">{bvb.isin ?? "—"}</p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Piață</p>
                            <p className="font-rajdhani text-sm text-slate-700">{bvb.market ?? "—"}</p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Segment</p>
                            <p className="font-rajdhani text-sm text-slate-700">{bvb.segment ?? "—"}</p>
                        </div>
                        <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                            <p className="font-rajdhani text-xs text-slate-500 uppercase">Volum</p>
                            <p className="font-rajdhani text-sm text-slate-700">{bvb.volume?.toLocaleString("ro-RO") ?? "—"}</p>
                        </div>
                    </div>
                ) : (
                    <p className="font-rajdhani text-sm text-slate-400">Compania nu este listată la BVB.</p>
                )}
            </div>

            {/* ── OSIM ── */}
            <div className="card-cosmic p-5">
                <div className="flex items-center gap-2 mb-4">
                    <Award className="h-5 w-5 text-nebula-400" />
                    <h3 className="font-orbitron text-sm font-semibold text-slate-700 uppercase tracking-wide">OSIM — Mărci & Brevete</h3>
                </div>
                {loadTm ? <LoadingSpinner /> : trademarks?.length ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-nebula-200 text-left text-xs text-slate-500 uppercase">
                                    <th className="pb-2 pr-4">Tip</th>
                                    <th className="pb-2 pr-4">Denumire</th>
                                    <th className="pb-2 pr-4">Nr. Înregistrare</th>
                                    <th className="pb-2 pr-4">Data Înreg.</th>
                                    <th className="pb-2 pr-4">Expiră</th>
                                    <th className="pb-2">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-nebula-100">
                                {trademarks.map((t: { tip: string; denumire: string; nr_inregistrare: string; data_inregistrare: string; data_expirare: string; status: string }, i: number) => (
                                    <tr key={i} className="hover:bg-nebula-50/50">
                                        <td className="py-2 pr-4 font-rajdhani capitalize">{t.tip}</td>
                                        <td className="py-2 pr-4 font-medium">{t.denumire}</td>
                                        <td className="py-2 pr-4 font-mono text-xs">{t.nr_inregistrare}</td>
                                        <td className="py-2 pr-4 text-slate-500">{t.data_inregistrare?.slice(0, 10)}</td>
                                        <td className="py-2 pr-4 text-slate-500">{t.data_expirare?.slice(0, 10)}</td>
                                        <td className="py-2">
                                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${t.status === "activa" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"}`}>
                                                {t.status ?? "—"}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="font-rajdhani text-sm text-slate-400">Nu există mărci sau brevete înregistrate la OSIM.</p>
                )}
            </div>

            {/* ── ASF ── */}
            <div className="card-cosmic p-5">
                <div className="flex items-center gap-2 mb-4">
                    <Landmark className="h-5 w-5 text-nebula-400" />
                    <h3 className="font-orbitron text-sm font-semibold text-slate-700 uppercase tracking-wide">ASF — Autoritatea de Supraveghere Financiară</h3>
                </div>
                {loadAsf ? <LoadingSpinner /> : asf?.supervised ? (
                    <div className="space-y-4">
                        {asf.autorizatie && (
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                                    <p className="font-rajdhani text-xs text-slate-500 uppercase">Tip Entitate</p>
                                    <p className="font-rajdhani font-semibold text-slate-700">{asf.autorizatie.tip_entitate ?? "—"}</p>
                                </div>
                                <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                                    <p className="font-rajdhani text-xs text-slate-500 uppercase">Nr. Autorizație</p>
                                    <p className="font-mono text-sm text-slate-700">{asf.autorizatie.nr_autorizatie ?? "—"}</p>
                                </div>
                                <div className="bg-nebula-50 dark:bg-nebula-900/20 rounded-lg p-3">
                                    <p className="font-rajdhani text-xs text-slate-500 uppercase">Status</p>
                                    <p className={`font-rajdhani font-semibold ${asf.autorizatie.status_autorizatie === "activ" ? "text-green-600" : "text-red-600"}`}>
                                        {asf.autorizatie.status_autorizatie ?? "—"}
                                    </p>
                                </div>
                            </div>
                        )}
                        {asf.sanctiuni?.length > 0 && (
                            <div>
                                <p className="font-rajdhani text-xs text-slate-500 uppercase mb-2">Sancțiuni ASF</p>
                                <div className="space-y-2">
                                    {asf.sanctiuni.map((s: { tip: string; descriere: string; data: string; suma: number }, i: number) => (
                                        <div key={i} className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm">
                                            <p className="font-semibold text-red-700">{s.tip}</p>
                                            <p className="text-red-600">{s.descriere}</p>
                                            {s.data && <p className="text-xs text-red-400 mt-1">{s.data}</p>}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <p className="font-rajdhani text-sm text-slate-400">Compania nu este supravegheată de ASF.</p>
                )}
            </div>
        </div>
    );
}


function FraudTab({ cui }: { cui: string }) {
    const { data, isLoading } = useQuery({
        queryKey: ["fraud", cui],
        queryFn: async () => {
            const { data } = await api.get(`/fraud/${cui}/profile`);
            return data;
        },
    });

    if (isLoading) return <LoadingSpinner />;
    if (!data) return <p className="font-rajdhani text-slate-400">Nu există date fraud.</p>;

    return (
        <div className="space-y-4">
            {/* Disclaimer — Hard constraint #11 */}
            <div className="card-cosmic border-l-4 border-dragon-fire py-3 px-4 text-sm text-dragon-600">
                <strong className="font-orbitron text-xs">Aviz Important:</strong>{" "}
                <span className="font-rajdhani">Datele prezentate reprezintă suspiciuni algoritmice
                    și nu constituie probe sau acuzații. Orice decizie bazată pe aceste informații
                    trebuie verificată independent.</span>
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-dragon-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Scor Anomalie</p>
                    <p className="font-orbitron text-2xl font-bold text-slate-800">{data.anomaly_score}</p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-nebula-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Noduri Graf</p>
                    <p className="font-orbitron text-2xl font-bold text-slate-800">{data.graph_summary?.nodes || 0}</p>
                </div>
                <div className="card-cosmic text-center relative overflow-hidden">
                    <div className="absolute inset-x-0 top-0 h-1 bg-cosmos-gradient" />
                    <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">Alerte Active</p>
                    <p className="font-orbitron text-2xl font-bold text-slate-800">{data.alerts?.length || 0}</p>
                </div>
            </div>

            {data.alerts?.map((alert: FraudAlert) => (
                <div key={alert.id} className="card-cosmic py-4 px-5 transition-all hover:shadow-nebula/20">
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="font-exo font-semibold text-slate-700">{alert.alert_type}</p>
                            <p className="font-rajdhani text-sm text-slate-400">{alert.descriere}</p>
                        </div>
                        <span
                            className={cn(
                                "rounded-full px-2 py-0.5 text-xs font-medium",
                                alert.severity === "CRITICAL" && "bg-red-100 text-red-700",
                                alert.severity === "HIGH" && "bg-orange-100 text-orange-700",
                                alert.severity === "MEDIUM" && "bg-yellow-100 text-yellow-700",
                                alert.severity === "LOW" && "bg-green-100 text-green-700"
                            )}
                        >
                            {alert.severity}
                        </span>
                    </div>
                </div>
            ))}
        </div>
    );
}
