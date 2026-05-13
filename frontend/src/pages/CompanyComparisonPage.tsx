import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatMoney, formatNumber, cn } from "@/lib/utils";
import type { CompanyFull, FinancialData, RiskScore, ESGScore } from "@/types";
import {
    Search, X, Plus, TrendingUp, Shield, Leaf, Building2,
    BarChart3, Users, Brain, Loader2, Sparkles,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend,
} from "recharts";

const COLORS = ["#818cf8", "#34d399", "#f59e0b", "#ef4444"];
const MAX_COMPANIES = 4;

function useAutocomplete(q: string) {
    return useQuery({
        queryKey: ["autocomplete", q],
        queryFn: () => api.get<{ cui: string; denumire: string; judet: string; stare: string }[]>(
            `/search/autocomplete?q=${encodeURIComponent(q)}&limit=8`
        ).then(r => r.data),
        enabled: q.length >= 2,
        staleTime: 30_000,
    });
}

function useCompanyComparison(cuis: string[]) {
    const companies = useQuery({
        queryKey: ["compare-companies", cuis],
        queryFn: () => Promise.all(
            cuis.map(cui => api.get<CompanyFull>(`/companies/${cui}`).then(r => r.data))
        ),
        enabled: cuis.length >= 2,
    });

    const financials = useQuery({
        queryKey: ["compare-financials", cuis],
        queryFn: () => Promise.all(
            cuis.map(cui => api.get<FinancialData[]>(`/companies/${cui}/financial`).then(r => r.data))
        ),
        enabled: cuis.length >= 2,
    });

    const risks = useQuery({
        queryKey: ["compare-risk", cuis],
        queryFn: () => Promise.all(
            cuis.map(cui => api.get<RiskScore>(`/risk/${cui}`).then(r => r.data).catch(() => null))
        ),
        enabled: cuis.length >= 2,
    });

    const esgs = useQuery({
        queryKey: ["compare-esg", cuis],
        queryFn: () => Promise.all(
            cuis.map(cui => api.get<ESGScore>(`/esg/${cui}`).then(r => r.data).catch(() => null))
        ),
        enabled: cuis.length >= 2,
    });

    return { companies, financials, risks, esgs };
}

/* ── Company Selector ── */
function CompanySelector({ index, onSelect, onRemove, selected }: {
    index: number;
    onSelect: (cui: string) => void;
    onRemove: () => void;
    selected?: CompanyFull;
}) {
    const [q, setQ] = useState("");
    const { data: suggestions } = useAutocomplete(q);

    if (selected) {
        return (
            <div className="card-cosmic relative flex items-center gap-3 p-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl text-white"
                    style={{ background: COLORS[index % COLORS.length] }}>
                    <Building2 className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                    <p className="truncate font-exo text-sm font-semibold text-foreground">{selected.denumire}</p>
                    <p className="font-rajdhani text-xs text-muted-foreground">CUI: {selected.cui} · {selected.judet}</p>
                </div>
                <button onClick={onRemove} className="rounded-lg p-1.5 text-muted-foreground hover:text-dragon-500 transition-colors">
                    <X className="h-4 w-4" />
                </button>
            </div>
        );
    }

    return (
        <div className="card-cosmic relative p-3">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                    type="text"
                    value={q}
                    onChange={e => setQ(e.target.value)}
                    placeholder={`Caută compania ${index + 1}...`}
                    className="input-scifi w-full pl-10 text-sm"
                />
            </div>
            {suggestions && suggestions.length > 0 && (
                <ul className="absolute left-0 right-0 top-full z-20 mt-1 max-h-48 overflow-y-auto rounded-xl border border-border bg-card shadow-cosmic-lg">
                    {suggestions.map(s => (
                        <li key={s.cui}>
                            <button
                                onClick={() => { onSelect(s.cui); setQ(""); }}
                                className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-nebula-50/50 dark:hover:bg-nebula-900/30 transition-colors"
                            >
                                <span className="font-exo font-medium text-foreground">{s.denumire}</span>
                                <span className="font-rajdhani text-xs text-muted-foreground">CUI: {s.cui}</span>
                                <span className={cn(
                                    "ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold",
                                    s.stare === "ACTIVA" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                                )}>{s.stare}</span>
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

/* ── Main Page ── */
export default function CompanyComparisonPage() {
    const [cuis, setCuis] = useState<string[]>([]);
    const { companies, financials, risks, esgs } = useCompanyComparison(cuis);
    const isReady = cuis.length >= 2 && companies.data;

    const addCompany = (cui: string) => {
        if (cuis.length < MAX_COMPANIES && !cuis.includes(cui)) {
            setCuis([...cuis, cui]);
        }
    };

    const removeCompany = (idx: number) => {
        setCuis(cuis.filter((_, i) => i !== idx));
    };

    /* AI Comparison */
    const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
    const aiCompare = useMutation({
        mutationFn: async () => {
            const { data } = await api.post("/ai/compare", null, {
                params: { cuis: cuis.map(Number) },
                paramsSerializer: { indexes: null },
            });
            return data;
        },
        onSuccess: (data) => setAiAnalysis(data.analysis),
        onError: () => setAiAnalysis("Eroare: AI temporar indisponibil. Verifică creditul API."),
    });

    /* Build comparison chart data for financials */
    const revenueChartData = useMemo(() => {
        if (!financials.data) return [];
        const yearsSet = new Set<number>();
        financials.data.forEach(fList => fList.forEach(f => yearsSet.add(f.an_fiscal)));
        const years = [...yearsSet].sort();
        return years.map(year => {
            const entry: Record<string, unknown> = { year };
            financials.data!.forEach((fList, i) => {
                const rec = fList.find(f => f.an_fiscal === year);
                entry[`ca_${i}`] = rec ? parseFloat(rec.cifra_afaceri) : 0;
            });
            return entry;
        });
    }, [financials.data]);

    const profitChartData = useMemo(() => {
        if (!financials.data) return [];
        const yearsSet = new Set<number>();
        financials.data.forEach(fList => fList.forEach(f => yearsSet.add(f.an_fiscal)));
        const years = [...yearsSet].sort();
        return years.map(year => {
            const entry: Record<string, unknown> = { year };
            financials.data!.forEach((fList, i) => {
                const rec = fList.find(f => f.an_fiscal === year);
                entry[`profit_${i}`] = rec ? parseFloat(rec.profit_net) : 0;
            });
            return entry;
        });
    }, [financials.data]);

    const riskRadarData = useMemo(() => {
        if (!risks.data) return [];
        const axes = [
            { key: "scor_financiar", label: "Financiar" },
            { key: "scor_legal", label: "Legal" },
            { key: "scor_fiscal", label: "Fiscal" },
            { key: "scor_comportamental", label: "Comportamental" },
        ];
        return axes.map(ax => {
            const entry: Record<string, unknown> = { axis: ax.label };
            risks.data!.forEach((r, i) => {
                entry[`risk_${i}`] = r ? parseFloat(r[ax.key as keyof RiskScore] as string) : 0;
            });
            return entry;
        });
    }, [risks.data]);

    const names = companies.data?.map(c => c.denumire.length > 20 ? c.denumire.slice(0, 20) + "…" : c.denumire) ?? [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">Comparare Firme</h1>
                    <p className="mt-1 font-exo text-sm text-muted-foreground">
                        Selectează 2-4 companii pentru analiză comparativă side-by-side
                    </p>
                </div>
                {isReady && (
                    <button
                        onClick={() => aiCompare.mutate()}
                        disabled={aiCompare.isPending}
                        className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg transition-all hover:shadow-xl hover:from-violet-500 hover:to-purple-500 disabled:opacity-60"
                    >
                        {aiCompare.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
                        Compară cu AI
                    </button>
                )}
            </div>

            {/* Selectors */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: Math.max(cuis.length + 1, 2) }).slice(0, MAX_COMPANIES).map((_, i) => (
                    <CompanySelector
                        key={i}
                        index={i}
                        selected={companies.data?.[i]}
                        onSelect={addCompany}
                        onRemove={() => removeCompany(i)}
                    />
                ))}
                {cuis.length < MAX_COMPANIES && cuis.length >= 2 && (
                    <button
                        onClick={() => { }}
                        className="card-cosmic flex items-center justify-center gap-2 p-3 text-sm text-muted-foreground hover:text-nebula-500 transition-colors border-2 border-dashed border-border"
                    >
                        <Plus className="h-4 w-4" /> Adaugă firmă
                    </button>
                )}
            </div>

            {!isReady && cuis.length < 2 && (
                <div className="card-cosmic flex flex-col items-center justify-center py-16 text-center">
                    <BarChart3 className="mb-4 h-16 w-16 text-nebula-300" />
                    <p className="font-exo text-lg font-semibold text-foreground">Selectează minim 2 companii</p>
                    <p className="mt-1 font-rajdhani text-sm text-muted-foreground">
                        Folosește câmpurile de căutare de mai sus pentru a adăuga companiile de comparat
                    </p>
                </div>
            )}

            {companies.isLoading && (
                <div className="flex items-center justify-center py-16">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                </div>
            )}

            {isReady && (
                <div className="space-y-6">
                    {/* ── AI Analysis Panel ── */}
                    {(aiAnalysis || aiCompare.isPending) && (
                        <div className="card-cosmic relative overflow-hidden border-2 border-violet-200 dark:border-violet-800">
                            <div className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500" />
                            <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="h-5 w-5 text-violet-500" />
                                <h2 className="font-orbitron text-lg font-semibold text-foreground">Analiză AI</h2>
                                {aiCompare.isPending && (
                                    <span className="ml-auto flex items-center gap-1.5 text-xs font-rajdhani text-violet-500">
                                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Se generează analiza...
                                    </span>
                                )}
                            </div>
                            {aiAnalysis && (
                                <div className="prose prose-sm dark:prose-invert max-w-none font-exo text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                                    {aiAnalysis}
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── General Info Table ── */}
                    <div className="card-cosmic overflow-x-auto">
                        <h2 className="mb-4 font-orbitron text-lg font-semibold text-foreground flex items-center gap-2">
                            <Building2 className="h-5 w-5 text-nebula-500" /> Informații Generale
                        </h2>
                        <table className="table-cosmic w-full text-sm">
                            <thead>
                                <tr>
                                    <th className="text-left">Indicator</th>
                                    {companies.data!.map((c, i) => (
                                        <th key={c.cui} className="text-left">
                                            <span className="inline-block h-2 w-2 rounded-full mr-1.5" style={{ background: COLORS[i] }} />
                                            {c.denumire}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {[
                                    { label: "CUI", get: (c: CompanyFull) => c.cui },
                                    { label: "Stare", get: (c: CompanyFull) => c.stare },
                                    { label: "Județ", get: (c: CompanyFull) => `${c.judet}, ${c.localitate}` },
                                    { label: "CAEN", get: (c: CompanyFull) => `${c.caen_principal} — ${c.descriere_caen}` },
                                    { label: "Formă Juridică", get: (c: CompanyFull) => c.forma_juridica },
                                    { label: "Capital Social", get: (c: CompanyFull) => formatMoney(c.capital_social) },
                                    { label: "Data Înființare", get: (c: CompanyFull) => c.data_infiintare },
                                    { label: "Plătitor TVA", get: (c: CompanyFull) => c.platitor_tva ? "Da" : "Nu" },
                                    { label: "Datorii Buget", get: (c: CompanyFull) => c.has_debts ? "⚠️ Da" : "✅ Nu" },
                                    { label: "Insolvență", get: (c: CompanyFull) => c.has_insolvency ? "⚠️ Da" : "✅ Nu" },
                                ].map(row => (
                                    <tr key={row.label}>
                                        <td className="font-medium text-muted-foreground">{row.label}</td>
                                        {companies.data!.map(c => (
                                            <td key={c.cui} className="text-foreground">{row.get(c)}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* ── Financials Charts ── */}
                    {financials.data && revenueChartData.length > 0 && (
                        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                            <div className="card-cosmic">
                                <h3 className="mb-3 font-orbitron text-sm font-semibold text-foreground flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-nebula-500" /> Cifra de Afaceri
                                </h3>
                                <ResponsiveContainer width="100%" height={280}>
                                    <BarChart data={revenueChartData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                        <XAxis dataKey="year" fontSize={12} />
                                        <YAxis fontSize={11} tickFormatter={v => `${(v / 1e6).toFixed(0)}M`} />
                                        <Tooltip
                                            formatter={(v: number) => formatMoney(v)}
                                            contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }}
                                        />
                                        <Legend />
                                        {cuis.map((_, i) => (
                                            <Bar key={i} dataKey={`ca_${i}`} name={names[i]} fill={COLORS[i]} radius={[4, 4, 0, 0]} />
                                        ))}
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="card-cosmic">
                                <h3 className="mb-3 font-orbitron text-sm font-semibold text-foreground flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 text-stardust-500" /> Profit Net
                                </h3>
                                <ResponsiveContainer width="100%" height={280}>
                                    <BarChart data={profitChartData}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                        <XAxis dataKey="year" fontSize={12} />
                                        <YAxis fontSize={11} tickFormatter={v => `${(v / 1e6).toFixed(0)}M`} />
                                        <Tooltip
                                            formatter={(v: number) => formatMoney(v)}
                                            contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }}
                                        />
                                        <Legend />
                                        {cuis.map((_, i) => (
                                            <Bar key={i} dataKey={`profit_${i}`} name={names[i]} fill={COLORS[i]} radius={[4, 4, 0, 0]} />
                                        ))}
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                    {/* ── Latest Financial Metrics Table ── */}
                    {financials.data && (
                        <div className="card-cosmic overflow-x-auto">
                            <h2 className="mb-4 font-orbitron text-lg font-semibold text-foreground flex items-center gap-2">
                                <BarChart3 className="h-5 w-5 text-nebula-500" /> Indicatori Financiari (Ultimul An)
                            </h2>
                            <table className="table-cosmic w-full text-sm">
                                <thead>
                                    <tr>
                                        <th className="text-left">Indicator</th>
                                        {companies.data!.map((c, i) => (
                                            <th key={c.cui} className="text-right">
                                                <span className="inline-block h-2 w-2 rounded-full mr-1.5" style={{ background: COLORS[i] }} />
                                                {names[i]}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {(() => {
                                        const latest = financials.data!.map(fList =>
                                            fList.length > 0 ? fList.reduce((a, b) => a.an_fiscal > b.an_fiscal ? a : b) : null
                                        );
                                        const rows = [
                                            { label: "An Fiscal", get: (f: FinancialData | null) => f?.an_fiscal ?? "—" },
                                            { label: "Cifra Afaceri", get: (f: FinancialData | null) => f ? formatMoney(f.cifra_afaceri) : "—" },
                                            { label: "Profit Net", get: (f: FinancialData | null) => f ? formatMoney(f.profit_net) : "—" },
                                            { label: "Nr. Angajați", get: (f: FinancialData | null) => f ? formatNumber(f.nr_angajati) : "—" },
                                            { label: "Total Active", get: (f: FinancialData | null) => f ? formatMoney(f.total_active) : "—" },
                                            { label: "Total Datorii", get: (f: FinancialData | null) => f ? formatMoney(f.total_datorii) : "—" },
                                            { label: "Lichiditate", get: (f: FinancialData | null) => f ? `${parseFloat(f.rata_lichiditate).toFixed(2)}` : "—" },
                                            { label: "Grad Îndatorare", get: (f: FinancialData | null) => f ? `${(parseFloat(f.grad_indatorare) * 100).toFixed(1)}%` : "—" },
                                            { label: "ROA", get: (f: FinancialData | null) => f ? `${(parseFloat(f.roa) * 100).toFixed(1)}%` : "—" },
                                            { label: "ROE", get: (f: FinancialData | null) => f ? `${(parseFloat(f.roe) * 100).toFixed(1)}%` : "—" },
                                        ];
                                        return rows.map(row => (
                                            <tr key={row.label}>
                                                <td className="font-medium text-muted-foreground">{row.label}</td>
                                                {latest.map((f, i) => (
                                                    <td key={i} className="text-right text-foreground">{row.get(f)}</td>
                                                ))}
                                            </tr>
                                        ));
                                    })()}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* ── Risk Radar ── */}
                    {risks.data && riskRadarData.length > 0 && (
                        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                            <div className="card-cosmic">
                                <h3 className="mb-3 font-orbitron text-sm font-semibold text-foreground flex items-center gap-2">
                                    <Shield className="h-4 w-4 text-nebula-500" /> Profil Risc
                                </h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <RadarChart data={riskRadarData}>
                                        <PolarGrid stroke="hsl(var(--border))" />
                                        <PolarAngleAxis dataKey="axis" fontSize={12} />
                                        {cuis.map((_, i) => (
                                            <Radar
                                                key={i}
                                                name={names[i]}
                                                dataKey={`risk_${i}`}
                                                stroke={COLORS[i]}
                                                fill={COLORS[i]}
                                                fillOpacity={0.15}
                                            />
                                        ))}
                                        <Legend />
                                        <Tooltip
                                            contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }}
                                        />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Risk scores summary */}
                            <div className="card-cosmic">
                                <h3 className="mb-3 font-orbitron text-sm font-semibold text-foreground flex items-center gap-2">
                                    <Shield className="h-4 w-4 text-dragon-500" /> Scoruri Risc
                                </h3>
                                <div className="space-y-4">
                                    {risks.data!.map((r, i) => (
                                        <div key={i} className="rounded-xl border border-border p-3">
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="inline-block h-3 w-3 rounded-full" style={{ background: COLORS[i] }} />
                                                <span className="font-exo text-sm font-semibold text-foreground">{names[i]}</span>
                                                {r && (
                                                    <span className={cn(
                                                        "ml-auto rounded-full px-2.5 py-0.5 text-xs font-bold",
                                                        r.rating === "A" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                                                            r.rating === "B" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
                                                                r.rating === "C" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                                                                    r.rating === "D" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" :
                                                                        "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                                                    )}>
                                                        {r.rating} — {parseFloat(r.score).toFixed(0)}/100
                                                    </span>
                                                )}
                                            </div>
                                            {r ? (
                                                <div className="grid grid-cols-4 gap-2 text-xs">
                                                    {["scor_financiar", "scor_legal", "scor_fiscal", "scor_comportamental"].map(k => (
                                                        <div key={k} className="text-center">
                                                            <div className="mb-1 h-1.5 rounded-full bg-muted overflow-hidden">
                                                                <div className="h-full rounded-full" style={{
                                                                    width: `${parseFloat(r[k as keyof RiskScore] as string)}%`,
                                                                    background: COLORS[i]
                                                                }} />
                                                            </div>
                                                            <span className="text-muted-foreground capitalize">{k.replace("scor_", "")}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-xs text-muted-foreground">Scor risc indisponibil</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ── ESG Comparison ── */}
                    {esgs.data && esgs.data.some(Boolean) && (
                        <div className="card-cosmic">
                            <h2 className="mb-4 font-orbitron text-lg font-semibold text-foreground flex items-center gap-2">
                                <Leaf className="h-5 w-5 text-green-500" /> ESG Comparativ
                            </h2>
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                                {esgs.data!.map((e, i) => (
                                    <div key={i} className="rounded-xl border border-border p-4 text-center">
                                        <div className="flex items-center justify-center gap-2 mb-3">
                                            <span className="inline-block h-3 w-3 rounded-full" style={{ background: COLORS[i] }} />
                                            <span className="font-exo text-sm font-semibold text-foreground">{names[i]}</span>
                                        </div>
                                        {e ? (
                                            <div className="space-y-2">
                                                <div className="font-orbitron text-3xl font-bold text-nebula">
                                                    {parseFloat(e.score_total).toFixed(0)}
                                                </div>
                                                <div className="flex justify-center gap-3 text-xs">
                                                    <span className="text-green-500">E: {parseFloat(e.score_e).toFixed(0)}</span>
                                                    <span className="text-blue-500">S: {parseFloat(e.score_s).toFixed(0)}</span>
                                                    <span className="text-purple-500">G: {parseFloat(e.score_g).toFixed(0)}</span>
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    {e.csrd_relevant ? "CSRD Relevant" : ""} {e.sfdr_categoria}
                                                </div>
                                            </div>
                                        ) : (
                                            <p className="text-sm text-muted-foreground">Indisponibil</p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ── Employees Comparison ── */}
                    {financials.data && (
                        <div className="card-cosmic">
                            <h3 className="mb-3 font-orbitron text-sm font-semibold text-foreground flex items-center gap-2">
                                <Users className="h-4 w-4 text-nebula-500" /> Evoluție Angajați
                            </h3>
                            <ResponsiveContainer width="100%" height={250}>
                                <BarChart data={(() => {
                                    const yearsSet = new Set<number>();
                                    financials.data!.forEach(fList => fList.forEach(f => yearsSet.add(f.an_fiscal)));
                                    return [...yearsSet].sort().map(year => {
                                        const entry: Record<string, unknown> = { year };
                                        financials.data!.forEach((fList, i) => {
                                            const rec = fList.find(f => f.an_fiscal === year);
                                            entry[`emp_${i}`] = rec?.nr_angajati ?? 0;
                                        });
                                        return entry;
                                    });
                                })()}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                                    <XAxis dataKey="year" fontSize={12} />
                                    <YAxis fontSize={11} />
                                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} />
                                    <Legend />
                                    {cuis.map((_, i) => (
                                        <Bar key={i} dataKey={`emp_${i}`} name={names[i]} fill={COLORS[i]} radius={[4, 4, 0, 0]} />
                                    ))}
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
