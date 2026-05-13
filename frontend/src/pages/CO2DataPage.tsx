import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
    AreaChart, Area, ResponsiveContainer, Tooltip, XAxis,
} from "recharts";
import {
    Loader2,
    Cloud,
    Factory,
    Zap,
    Truck,
    ArrowDownRight,
    Search,
    Calendar,
    ChevronLeft,
    ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

/* ── Types ───────────────────────────────────────────────────── */
interface Co2Summary {
    year: number;
    totalEmisii: number;
    valoareMedieZi: number;
    scope1: number;
    scope2: number;
    scope3Upstream: number;
    scope3Downstream: number;
    scope1MedieZi: number;
    scope2MedieZi: number;
    scope3UpstreamMedieZi: number;
    scope3DownstreamMedieZi: number;
    trends: Record<string, { luna: string; tone: number }[]>;
}

interface SupplyChainItem {
    furnizor: string | null;
    tara: string | null;
    judet: string | null;
    produsServiciu: string | null;
    scope3Direction: string;
    co2Footprint: number;
}

interface SupplyChainResponse {
    year: number;
    items: SupplyChainItem[];
}

const fmt = (v: number) =>
    v.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/* ── Scope card config ─────────────────────────────────────── */
interface ScopeCardConfig {
    key: string;
    label: string;
    scopeField: keyof Co2Summary;
    medieField: keyof Co2Summary;
    trendKey: string;
    color: string;
    gradient: string;
    border: string;
    iconBg: string;
    Icon: React.ElementType;
}

const scopeCards: ScopeCardConfig[] = [
    {
        key: "scope1", label: "SCOPE 1", scopeField: "scope1", medieField: "scope1MedieZi",
        trendKey: "scope1", color: "#3b82f6", gradient: "from-blue-500/10 to-blue-500/5",
        border: "border-t-blue-400", iconBg: "bg-blue-50 text-blue-500",
        Icon: Factory,
    },
    {
        key: "scope2", label: "SCOPE 2", scopeField: "scope2", medieField: "scope2MedieZi",
        trendKey: "scope2", color: "#8b5cf6", gradient: "from-violet-500/10 to-violet-500/5",
        border: "border-t-violet-400", iconBg: "bg-violet-50 text-violet-500",
        Icon: Zap,
    },
    {
        key: "scope3up", label: "SCOPE 3 | UPSTREAM", scopeField: "scope3Upstream", medieField: "scope3UpstreamMedieZi",
        trendKey: "scope3_upstream", color: "#f59e0b", gradient: "from-amber-500/10 to-amber-500/5",
        border: "border-t-amber-400", iconBg: "bg-amber-50 text-amber-500",
        Icon: Truck,
    },
    {
        key: "scope3down", label: "SCOPE 3 | DOWNSTREAM", scopeField: "scope3Downstream", medieField: "scope3DownstreamMedieZi",
        trendKey: "scope3_downstream", color: "#06b6d4", gradient: "from-cyan-500/10 to-cyan-500/5",
        border: "border-t-cyan-400", iconBg: "bg-cyan-50 text-cyan-500",
        Icon: ArrowDownRight,
    },
];

/* ── Scope Mini Chart Card ───────────────────────────────────── */
function ScopeCard({ config, summary }: { config: ScopeCardConfig; summary: Co2Summary }) {
    const value = summary[config.scopeField] as number;
    const medie = summary[config.medieField] as number;
    const trendData = (summary.trends[config.trendKey] || []).map((t, i) => ({
        name: `S${String(i).padStart(2, "0")}`,
        tone: t.tone,
    }));
    const Icon = config.Icon;

    return (
        <div className={cn(
            "rounded-xl border border-slate-200/60 border-t-4 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-slate-700/60 dark:bg-slate-800",
            config.border,
        )}>
            <div className="flex items-start justify-between mb-2">
                <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                        {config.label}
                    </p>
                    <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-sm text-slate-400">Valoare medie/zi</span>
                        <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">{medie} T</span>
                    </div>
                </div>
                <div className={cn("rounded-xl p-2.5", config.iconBg)}>
                    <Icon className="h-5 w-5" />
                </div>
            </div>
            <div className="flex items-center gap-1 mb-1">
                <span className="text-xs text-blue-500">● Anul curent ▾</span>
            </div>
            <p className="text-3xl font-bold text-slate-800 dark:text-slate-100">
                {fmt(value)} <span className="text-base font-medium text-slate-400">Tone</span>
            </p>

            {/* Mini area chart */}
            <div className="mt-3 h-[100px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                        <defs>
                            <linearGradient id={`grad-${config.key}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={config.color} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={config.color} stopOpacity={0.02} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                        <Tooltip
                            formatter={(v: number) => [`${fmt(v)} T`, "CO₂"]}
                            contentStyle={{ borderRadius: 8, fontSize: 12, border: "1px solid #e2e8f0" }}
                        />
                        <Area
                            type="monotone"
                            dataKey="tone"
                            stroke={config.color}
                            strokeWidth={2}
                            fill={`url(#grad-${config.key})`}
                            dot={{ r: 3, fill: config.color, strokeWidth: 0 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

/* ── Total Emissions Card (top-left) ─────────────────────────── */
function TotalEmissionsCard({ summary }: { summary: Co2Summary }) {
    const trendData = useMemo(() => {
        // Merge all scopes into a single monthly total
        const monthMap: Record<string, number> = {};
        for (const [, entries] of Object.entries(summary.trends)) {
            for (const e of entries) {
                monthMap[e.luna] = (monthMap[e.luna] || 0) + e.tone;
            }
        }
        return Object.entries(monthMap)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([, tone], i) => ({ name: `S${String(i).padStart(2, "0")}`, tone }));
    }, [summary.trends]);

    return (
        <div className="rounded-xl border border-slate-200/60 bg-white p-6 shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
            <div className="flex items-start justify-between mb-2">
                <div>
                    <p className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        TOTAL EMISII
                    </p>
                    <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-sm text-slate-400">Valoare medie/zi</span>
                        <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">{summary.valoareMedieZi} T</span>
                    </div>
                </div>
                <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-500">
                    <Cloud className="h-5 w-5" />
                </div>
            </div>
            <div className="flex items-center gap-1 mb-1">
                <span className="text-xs text-blue-500">● Anul curent ▾</span>
            </div>
            <p className="text-4xl font-bold text-slate-800 dark:text-slate-100">
                {fmt(summary.totalEmisii)} <span className="text-lg font-medium text-slate-400">Tone</span>
            </p>

            <div className="mt-4 h-[140px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData} margin={{ top: 5, right: 5, left: 5, bottom: 0 }}>
                        <defs>
                            <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#1e293b" stopOpacity={0.2} />
                                <stop offset="100%" stopColor="#1e293b" stopOpacity={0.02} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                        <Tooltip
                            formatter={(v: number) => [`${fmt(v)} T`, "Total CO₂"]}
                            contentStyle={{ borderRadius: 8, fontSize: 12, border: "1px solid #e2e8f0" }}
                        />
                        <Area
                            type="monotone"
                            dataKey="tone"
                            stroke="#1e293b"
                            strokeWidth={2}
                            fill="url(#totalGrad)"
                            dot={{ r: 3, fill: "#1e293b", strokeWidth: 0 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

/* ── Company Info Card (top-center) ──────────────────────────── */
function CompanyInfoCard() {
    const user = useAuthStore((s) => s.user);
    return (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200/60 bg-white p-6 shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-600 text-white">
                <Cloud className="h-8 w-8" />
            </div>
            <h2 className="text-center text-lg font-bold text-slate-800 dark:text-slate-100">
                {user?.org_name || "—"}
            </h2>
            <p className="mt-2 text-center text-xs text-slate-400 dark:text-slate-500 max-w-[200px]">
                Raportare emisii GHG conform GHG Protocol — Scope 1, 2 & 3
            </p>

            {/* Mini scope diagram */}
            <div className="mt-6 w-full max-w-[220px]">
                <img
                    src="/img/ghg-scopes.png"
                    alt="GHG Scopes"
                    className="w-full opacity-80 dark:opacity-60"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
            </div>
        </div>
    );
}

/* ── Supply Chain Table ──────────────────────────────────────── */
function SupplyChainTable({ cui, year }: { cui: string; year: number }) {
    const [filters, setFilters] = useState({
        furnizor: "", tara: "", judet: "", produs: "",
    });

    const params = useMemo(() => {
        const p: Record<string, string | number> = { cui, year };
        if (filters.furnizor) p.furnizor = filters.furnizor;
        if (filters.tara) p.tara = filters.tara;
        if (filters.judet) p.judet = filters.judet;
        if (filters.produs) p.produs = filters.produs;
        return p;
    }, [cui, year, filters]);

    const { data, isLoading } = useQuery<SupplyChainResponse>({
        queryKey: ["co2-supply-chain", params],
        queryFn: async () => (await api.get("/co2/supply-chain", { params })).data,
        staleTime: 120_000,
    });

    const items = data?.items ?? [];

    const PAGE_SIZE = 4;
    const [page, setPage] = useState(0);
    const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
    const paged = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

    // Reset page when filters/data change
    const itemsLen = items.length;
    useMemo(() => setPage(0), [itemsLen, filters]);

    return (
        <div className="rounded-xl border border-slate-200/60 bg-white p-6 shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
                <h3 className="text-sm font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400">
                    Supply Chain Carbon Intelligence™
                </h3>
                <div className="flex items-center gap-1 text-xs text-slate-400">
                    <Calendar className="h-3.5 w-3.5" />
                    {year}
                </div>
            </div>

            {/* Filter row */}
            <div className="grid grid-cols-2 gap-3 mb-4 md:grid-cols-4">
                {(["furnizor", "tara", "judet", "produs"] as const).map((field) => (
                    <div key={field} className="relative">
                        <input
                            type="text"
                            placeholder={field === "produs" ? "Produs / Serviciu" : field.charAt(0).toUpperCase() + field.slice(1)}
                            value={filters[field === "produs" ? "produs" : field]}
                            onChange={(e) => setFilters((f) => ({ ...f, [field]: e.target.value }))}
                            className="w-full rounded-lg border border-orange-200 bg-orange-50/50 px-2.5 py-1.5 text-xs placeholder-slate-400
                                       focus:border-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-300
                                       dark:border-orange-800 dark:bg-orange-900/20 dark:placeholder-slate-500 dark:text-slate-200"
                        />
                        <Search className="absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                    </div>
                ))}
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700">
                            <th className="py-1.5 pr-2 text-left font-semibold text-orange-600 dark:text-orange-400">Furnizor</th>
                            <th className="py-1.5 pr-2 text-left font-semibold text-orange-600 dark:text-orange-400">Țară</th>
                            <th className="py-1.5 pr-2 text-left font-semibold text-orange-600 dark:text-orange-400">Județ</th>
                            <th className="py-1.5 pr-2 text-left font-semibold text-orange-600 dark:text-orange-400">Produs / Serviciu</th>
                            <th className="py-1.5 pr-2 text-left font-semibold text-orange-600 dark:text-orange-400">Scope3 Up/Downstream</th>
                            <th className="py-1.5 text-right font-semibold text-orange-600 dark:text-orange-400">CO₂ (t)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                            <tr>
                                <td colSpan={6} className="py-8 text-center">
                                    <Loader2 className="inline h-5 w-5 animate-spin text-blue-500" />
                                </td>
                            </tr>
                        ) : items.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="py-8 text-center text-slate-400">
                                    Nicio înregistrare găsită
                                </td>
                            </tr>
                        ) : (
                            paged.map((item, i) => (
                                <tr
                                    key={i}
                                    className="border-b border-slate-100 hover:bg-slate-50 dark:border-slate-700/50 dark:hover:bg-slate-700/30"
                                >
                                    <td className="py-1.5 pr-2 text-slate-600 dark:text-slate-300">{item.furnizor || "—"}</td>
                                    <td className="py-1.5 pr-2 text-slate-600 dark:text-slate-300">{item.tara || "—"}</td>
                                    <td className="py-1.5 pr-2 text-slate-600 dark:text-slate-300">{item.judet || "—"}</td>
                                    <td className="py-1.5 pr-2 text-slate-600 dark:text-slate-300">{item.produsServiciu || "—"}</td>
                                    <td className="py-1.5 pr-2">
                                        <span className={cn(
                                            "rounded-full px-2 py-px text-[10px] font-semibold",
                                            item.scope3Direction === "Upstream"
                                                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                                                : "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300"
                                        )}>
                                            {item.scope3Direction}
                                        </span>
                                    </td>
                                    <td className="py-1.5 text-right font-semibold text-slate-800 dark:text-slate-100">
                                        {fmt(item.co2Footprint)}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {items.length > PAGE_SIZE && (
                <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-700/50">
                    <span className="text-xs text-slate-400">
                        {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, items.length)} din {items.length} înregistrări
                    </span>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => setPage((p) => Math.max(0, p - 1))}
                            disabled={page === 0}
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-orange-50 hover:text-orange-600 disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-orange-900/20"
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </button>
                        {Array.from({ length: totalPages }, (_, i) => (
                            <button
                                key={i}
                                onClick={() => setPage(i)}
                                className={cn(
                                    "h-7 min-w-[1.75rem] rounded-lg text-xs font-medium",
                                    i === page
                                        ? "bg-orange-500 text-white shadow-sm"
                                        : "text-slate-500 hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-orange-900/20"
                                )}
                            >
                                {i + 1}
                            </button>
                        ))}
                        <button
                            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                            disabled={page >= totalPages - 1}
                            className="rounded-lg p-1.5 text-slate-500 hover:bg-orange-50 hover:text-orange-600 disabled:opacity-30 disabled:hover:bg-transparent dark:hover:bg-orange-900/20"
                        >
                            <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Main Page ───────────────────────────────────────────────── */
export default function CO2DataPage() {
    const user = useAuthStore((s) => s.user);
    const cui = user?.org_cui || "";

    const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

    // Get available years
    const { data: yearsData } = useQuery<{ years: number[] }>({
        queryKey: ["co2-years", cui],
        queryFn: async () => (await api.get("/co2/years", { params: { cui } })).data,
        staleTime: 300_000,
        enabled: !!cui,
    });

    const years = yearsData?.years ?? [new Date().getFullYear()];

    // Get CO2 summary
    const { data: summary, isLoading } = useQuery<Co2Summary>({
        queryKey: ["co2-summary", cui, selectedYear],
        queryFn: async () => (await api.get("/co2/summary", { params: { cui, year: selectedYear } })).data,
        staleTime: 120_000,
        enabled: !!cui,
    });

    if (!cui) {
        return (
            <div className="flex flex-col items-center justify-center py-32 text-slate-400">
                <Cloud className="h-12 w-12 mb-3 opacity-40" />
                <p className="text-lg font-medium">Nu există CUI configurat pentru organizația ta.</p>
                <p className="text-sm">Contactează administratorul pentru configurare.</p>
            </div>
        );
    }

    if (isLoading || !summary) {
        return (
            <div className="flex items-center justify-center py-32">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="section-header">
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                        Date CO₂
                    </h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Emisii GHG — Scope 1, 2 & 3 | Supply Chain Carbon Intelligence
                    </p>
                </div>
                {/* Year selector */}
                <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    <select
                        value={selectedYear}
                        onChange={(e) => setSelectedYear(Number(e.target.value))}
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700
                                   focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-300
                                   dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                    >
                        {years.map((y) => (
                            <option key={y} value={y}>{y}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Top row: Total Emissions | Company Info | Supply Chain Table */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_280px_1fr]">
                <TotalEmissionsCard summary={summary} />
                <CompanyInfoCard />
                <SupplyChainTable cui={cui} year={selectedYear} />
            </div>

            {/* Bottom row: 4 scope cards */}
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
                {scopeCards.map((config) => (
                    <ScopeCard key={config.key} config={config} summary={summary} />
                ))}
            </div>
        </div>
    );
}
