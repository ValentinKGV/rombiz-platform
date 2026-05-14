import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useThemeStore } from "@/store/theme";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import {
    TrendingUp,
    TrendingDown,
    BarChart3,
    Activity,
    PieChart as PieIcon,
    Building2,
    ArrowUpRight,
    ArrowDownRight,
    Minus,
    RefreshCw,
    Search,
    Filter,
} from "lucide-react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend,
    ScatterChart,
    Scatter,
    ZAxis,
    ReferenceLine,
} from "recharts";

/* ─────────────────────────────────────────────
   Types
───────────────────────────────────────────── */
interface BVBCompany {
    id: number;
    cui: string;
    denumire: string;
    judet?: string;
    ticker?: string;
    isin?: string;
    last_price?: number;
    change_pct?: number;
    volume?: number;
    market_cap?: number;
    segment?: string;
    market?: string;
    updated_at?: string;
}

interface BVBStats {
    total: number;
    premium: number;
    standard: number;
    aero: number;
    gainers: number;
    losers: number;
    unchanged: number;
    avg_change_pct: number;
    max_price: number;
    min_price: number;
    top_gainers: BVBCompany[];
    top_losers: BVBCompany[];
    by_segment: { segment: string; count: number }[];
}

interface BVBResponse {
    total: number;
    page: number;
    per_page: number;
    pages: number;
    items: BVBCompany[];
}

/* ─────────────────────────────────────────────
   Constants
───────────────────────────────────────────── */
const WIDGET =
    "card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md shadow-indigo-500/5 backdrop-blur-sm";

const SEGMENT_COLORS: Record<string, string> = {
    Premium: "#6366f1",
    Standard: "#8b5cf6",
    AeRO: "#06b6d4",
    Necunoscut: "#64748b",
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 25;

/* ─────────────────────────────────────────────
   Helpers
───────────────────────────────────────────── */
function formatPrice(v?: number | null) {
    if (v == null) return "—";
    return new Intl.NumberFormat("ro-RO", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 4,
    }).format(v);
}

function formatPct(v?: number | null) {
    if (v == null) return "—";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(2)}%`;
}

function getErrorMessage(error: unknown) {
    if (error instanceof Error) return error.message;
    return "A apărut o eroare la încărcarea datelor.";
}

function PctBadge({ value }: { value?: number | null }) {
    if (value == null) return <span className="text-slate-400">—</span>;
    if (value > 0)
        return (
            <span className="inline-flex items-center gap-0.5 font-semibold text-emerald-500">
                <ArrowUpRight className="h-3.5 w-3.5" />
                {value.toFixed(2)}%
            </span>
        );
    if (value < 0)
        return (
            <span className="inline-flex items-center gap-0.5 font-semibold text-rose-500">
                <ArrowDownRight className="h-3.5 w-3.5" />
                {Math.abs(value).toFixed(2)}%
            </span>
        );
    return (
        <span className="inline-flex items-center gap-0.5 text-slate-400">
            <Minus className="h-3.5 w-3.5" />
            0.00%
        </span>
    );
}

/* ─────────────────────────────────────────────
   Loading / Empty / Error UI
───────────────────────────────────────────── */
function TableSkeleton() {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-700/60">
                        {["Ticker / ISIN", "Denumire", "Segment", "Preț (RON)", "Variație %", "Volum", "Capitalizare"].map(
                            (header) => (
                                <th
                                    key={header}
                                    className="pb-3 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4"
                                >
                                    {header}
                                </th>
                            )
                        )}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-700/40">
                    {Array.from({ length: 8 }).map((_, index) => (
                        <tr key={index}>
                            {Array.from({ length: 7 }).map((__, cellIndex) => (
                                <td key={cellIndex} className="py-3 pr-4">
                                    <div className="h-4 w-full max-w-[140px] animate-pulse rounded bg-slate-200/80 dark:bg-slate-700/70" />
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function ErrorState({
    message,
    onRetry,
}: {
    message: string;
    onRetry: () => void;
}) {
    return (
        <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
            <div className="rounded-full bg-rose-100 px-4 py-2 text-sm font-rajdhani font-semibold text-rose-600 dark:bg-rose-900/30 dark:text-rose-300">
                Nu s-au putut încărca datele BVB.
            </div>
            <p className="max-w-md text-xs text-slate-400">{message}</p>
            <button
                onClick={onRetry}
                className="flex items-center gap-1.5 rounded-lg border border-indigo-200/60 bg-white/70 px-3 py-2 text-xs font-rajdhani font-semibold text-slate-600 transition-colors hover:bg-indigo-50 dark:border-slate-600/60 dark:bg-slate-800/70 dark:text-slate-300 dark:hover:bg-slate-700"
            >
                <RefreshCw className="h-3.5 w-3.5" />
                Reîncearcă
            </button>
        </div>
    );
}

function ChartsSkeleton() {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className={cn(WIDGET, "h-[330px] animate-pulse p-5 lg:col-span-2")} />
                <div className={cn(WIDGET, "h-[330px] animate-pulse p-5")} />
            </div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className={cn(WIDGET, "h-[350px] animate-pulse p-5 lg:col-span-3")} />
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   KPI Cards
───────────────────────────────────────────── */
function KPICards({ stats }: { stats: BVBStats }) {
    const avg = stats.avg_change_pct;
    const kpis = [
        {
            label: "Companii Listate",
            value: stats.total.toString(),
            icon: Building2,
            color: "from-indigo-500 to-violet-600",
            sub: `${stats.premium} Premium • ${stats.standard} Standard`,
        },
        {
            label: "Creșteri Zi",
            value: stats.gainers.toString(),
            icon: TrendingUp,
            color: "from-emerald-500 to-teal-600",
            sub: `${stats.losers} scăderi • ${stats.unchanged} neschimbate`,
        },
        {
            label: "Variație Medie",
            value: formatPct(avg),
            icon: avg >= 0 ? TrendingUp : TrendingDown,
            color: avg >= 0 ? "from-emerald-500 to-teal-600" : "from-rose-500 to-pink-600",
            sub: "față de sesiunea anterioară",
        },
        {
            label: "Segment Premium",
            value: stats.premium.toString(),
            icon: BarChart3,
            color: "from-amber-500 to-orange-600",
            sub: `AeRO: ${stats.aero} companii`,
        },
    ];

    return (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {kpis.map((k) => {
                const Icon = k.icon;
                return (
                    <div key={k.label} className={cn(WIDGET, "flex items-center gap-4 p-4")}>
                        <div
                            className={cn(
                                "flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg",
                                k.color
                            )}
                        >
                            <Icon className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                            <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                {k.label}
                            </p>
                            <p className="truncate font-orbitron text-xl font-bold text-slate-800 dark:text-slate-100">
                                {k.value}
                            </p>
                            <p className="truncate font-rajdhani text-[10px] text-slate-400">{k.sub}</p>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

/* ─────────────────────────────────────────────
   Charts
───────────────────────────────────────────── */
function SegmentPieChart({ stats }: { stats: BVBStats }) {
    const dark = useThemeStore((s) => s.dark);
    const tooltipStyle = {
        borderRadius: 12,
        fontFamily: "Exo 2",
        fontSize: 13,
        border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`,
        backgroundColor: dark ? "#1e293b" : "#ffffff",
        color: dark ? "#e2e8f0" : "#1e293b",
    };

    const data = useMemo(
        () =>
            stats.by_segment.map((s) => ({
                name: s.segment,
                value: Number(s.count),
                color: SEGMENT_COLORS[s.segment] || "#64748b",
            })),
        [stats.by_segment]
    );

    return (
        <div className={cn(WIDGET, "p-5")}>
            <div className="mb-4 flex items-center gap-2">
                <PieIcon className="h-4 w-4 text-violet-500" />
                <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Distribuție Segmente
                </h3>
            </div>
            <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                        label={({ name, value }) => `${name} (${value})`}
                        labelLine={false}
                    >
                        {data.map((d, i) => (
                            <Cell key={i} fill={d.color} stroke={dark ? "#0f172a" : "white"} strokeWidth={2} />
                        ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1">
                {data.map((d) => (
                    <span
                        key={d.name}
                        className="flex items-center gap-1 font-rajdhani text-[11px] text-slate-500 dark:text-slate-400"
                    >
                        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                        {d.name}
                    </span>
                ))}
            </div>
        </div>
    );
}

function GainersLosersChart({ stats }: { stats: BVBStats }) {
    const dark = useThemeStore((s) => s.dark);
    const gridColor = dark ? "#334155" : "#e2e8f0";
    const tickStyle = {
        fontSize: 11,
        fontFamily: "Rajdhani",
        fill: dark ? "#94a3b8" : "#475569",
    };
    const tooltipStyle = {
        borderRadius: 12,
        fontFamily: "Exo 2",
        fontSize: 13,
        border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`,
        backgroundColor: dark ? "#1e293b" : "#ffffff",
        color: dark ? "#e2e8f0" : "#1e293b",
    };

    const allData = useMemo(
        () =>
            [
                ...stats.top_gainers.map((c) => ({
                    ticker: c.ticker || c.cui,
                    change_pct: c.change_pct || 0,
                    last_price: c.last_price,
                    denumire: c.denumire,
                    fill: "#10b981",
                })),
                ...stats.top_losers.map((c) => ({
                    ticker: c.ticker || c.cui,
                    change_pct: c.change_pct || 0,
                    last_price: c.last_price,
                    denumire: c.denumire,
                    fill: "#f43f5e",
                })),
            ].sort((a, b) => b.change_pct - a.change_pct),
        [stats.top_gainers, stats.top_losers]
    );

    return (
        <div className={cn(WIDGET, "p-5 lg:col-span-2")}>
            <div className="mb-4 flex items-center gap-2">
                <Activity className="h-4 w-4 text-indigo-500" />
                <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Top Creșteri & Scăderi Zi
                </h3>
            </div>
            <ResponsiveContainer width="100%" height={260}>
                <BarChart data={allData} layout="vertical" margin={{ left: 80, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} horizontal={false} />
                    <XAxis
                        type="number"
                        tick={tickStyle}
                        tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
                    />
                    <YAxis dataKey="ticker" type="category" tick={{ ...tickStyle, fontSize: 10 }} width={78} />
                    <Tooltip
                        contentStyle={tooltipStyle}
                        formatter={(val: number) => [`${val > 0 ? "+" : ""}${val.toFixed(2)}%`, "Variație"]}
                        labelFormatter={(label) => {
                            const item = allData.find((d) => d.ticker === label);
                            return item?.denumire || label;
                        }}
                    />
                    <ReferenceLine x={0} stroke={dark ? "#475569" : "#94a3b8"} strokeWidth={1} />
                    <Bar dataKey="change_pct" radius={[0, 4, 4, 0]}>
                        {allData.map((entry, index) => (
                            <Cell key={index} fill={entry.fill} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

function PriceDistributionChart({ companies }: { companies: BVBCompany[] }) {
    const dark = useThemeStore((s) => s.dark);
    const gridColor = dark ? "#334155" : "#e2e8f0";
    const tickStyle = {
        fontSize: 11,
        fontFamily: "Rajdhani",
        fill: dark ? "#94a3b8" : "#475569",
    };
    const tooltipStyle = {
        borderRadius: 12,
        fontFamily: "Exo 2",
        fontSize: 13,
        border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`,
        backgroundColor: dark ? "#1e293b" : "#ffffff",
        color: dark ? "#e2e8f0" : "#1e293b",
    };

    const scatterData = useMemo(
        () =>
            companies
                .filter((c) => c.last_price != null && c.change_pct != null)
                .map((c) => ({
                    x: c.last_price as number,
                    y: c.change_pct as number,
                    z: 80,
                    name: c.ticker || c.cui,
                    segment: c.segment || "Necunoscut",
                    denumire: c.denumire,
                })),
        [companies]
    );

    const bySegment = useMemo(() => {
        const grouped: Record<string, typeof scatterData> = {};
        scatterData.forEach((d) => {
            if (!grouped[d.segment]) grouped[d.segment] = [];
            grouped[d.segment].push(d);
        });
        return grouped;
    }, [scatterData]);

    return (
        <div className={cn(WIDGET, "p-5 lg:col-span-3")}>
            <div className="mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-cyan-500" />
                <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Preț vs Variație Zi
                </h3>
                <span className="ml-auto font-rajdhani text-[11px] text-slate-400">
                    {scatterData.length} companii cu date pe pagina curentă
                </span>
            </div>
            <ResponsiveContainer width="100%" height={280}>
                <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                    <XAxis
                        dataKey="x"
                        type="number"
                        name="Preț"
                        tick={tickStyle}
                        label={{
                            value: "Preț (RON)",
                            position: "insideBottom",
                            offset: -5,
                            style: { fontFamily: "Rajdhani", fontSize: 12, fill: dark ? "#94a3b8" : "#475569" },
                        }}
                    />
                    <YAxis
                        dataKey="y"
                        type="number"
                        name="Variație %"
                        tick={tickStyle}
                        label={{
                            value: "Variație %",
                            angle: -90,
                            position: "insideLeft",
                            style: { fontFamily: "Rajdhani", fontSize: 12, fill: dark ? "#94a3b8" : "#475569" },
                        }}
                    />
                    <ZAxis dataKey="z" range={[40, 120]} />
                    <Tooltip
                        contentStyle={tooltipStyle}
                        cursor={{ stroke: dark ? "#334155" : "#cbd5e1", strokeWidth: 1 }}
                        formatter={(value: number, name: string) => {
                            if (name === "Preț") return [`${value.toFixed(4)} RON`, name];
                            if (name === "Variație %") return [`${value > 0 ? "+" : ""}${value.toFixed(2)}%`, name];
                            return [value, name];
                        }}
                    />
                    <ReferenceLine y={0} stroke={dark ? "#475569" : "#94a3b8"} strokeDasharray="4 4" />
                    <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12, color: dark ? "#94a3b8" : "#475569" }} />
                    {Object.entries(bySegment).map(([seg, data]) => (
                        <Scatter
                            key={seg}
                            name={seg}
                            data={data}
                            fill={SEGMENT_COLORS[seg] || "#64748b"}
                            fillOpacity={0.8}
                        />
                    ))}
                </ScatterChart>
            </ResponsiveContainer>
        </div>
    );
}

function ChartsSection({
    stats,
    companies,
}: {
    stats: BVBStats;
    companies: BVBCompany[];
}) {
    return (
        <>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <GainersLosersChart stats={stats} />
                <SegmentPieChart stats={stats} />
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <PriceDistributionChart companies={companies} />
            </div>
        </>
    );
}

const LazyChartsSection = lazy(async () => ({
    default: ChartsSection,
}));

/* ─────────────────────────────────────────────
   Main Page
───────────────────────────────────────────── */
export default function BVBPage() {
    const [search, setSearch] = useState("");
    const [segmentFilter, setSegmentFilter] = useState<string>("");
    const [sortBy, setSortBy] = useState<"last_price" | "change_pct" | "denumire">("last_price");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

    const {
        data: stats,
        isLoading: statsLoading,
        isError: statsIsError,
        error: statsError,
        refetch: refetchStats,
    } = useQuery<BVBStats>({
        queryKey: ["bvb", "stats"],
        queryFn: async () => {
            const { data } = await api.get("/bvb/stats");
            return data;
        },
        staleTime: 5 * 60 * 1000,
    });

    const {
        data: bvbData,
        isLoading: companiesLoading,
        isFetching: companiesFetching,
        isError: companiesIsError,
        error: companiesError,
        refetch: refetchCompanies,
    } = useQuery<BVBResponse>({
        queryKey: ["bvb", "companies", segmentFilter, sortBy, sortDir, page, pageSize],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (segmentFilter) params.set("segment", segmentFilter);
            params.set("sort_by", sortBy);
            params.set("sort_dir", sortDir);
            params.set("page", page.toString());
            params.set("per_page", pageSize.toString());

            const { data } = await api.get(`/bvb/companies?${params}`);
            return data;
        },
        placeholderData: (previousData) => previousData,
        staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        setPage(1);
    }, [search]);

    const filteredCompanies = useMemo(() => {
        const items = bvbData?.items ?? [];
        const q = search.trim().toLowerCase();

        if (!q) return items;

        return items.filter(
            (c) =>
                c.denumire?.toLowerCase().includes(q) ||
                c.ticker?.toLowerCase().includes(q) ||
                c.isin?.toLowerCase().includes(q) ||
                c.cui?.toString().includes(q)
        );
    }, [bvbData?.items, search]);

    const totalPages = Math.max(1, bvbData?.pages ?? 1);
    const canGoPrevious = page > 1;
    const canGoNext = page < totalPages;
    const isInitialLoading = statsLoading || companiesLoading;
    const isRefreshing = companiesFetching && !companiesLoading;

    const handleRefresh = () => {
        refetchStats();
        refetchCompanies();
    };

    return (
        <div
            className="min-h-screen -m-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30 p-6 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950"
            style={{
                backgroundImage:
                    "radial-gradient(circle at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(236,72,153,0.04) 0%, transparent 50%)",
            }}
        >
            {/* Header */}
            <div className="section-header flex items-start justify-between gap-4">
                <div>
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                        BVB — Bursa de Valori București
                    </h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Companii listate la bursă · date de piață în timp real
                    </p>
                </div>

                <button
                    onClick={handleRefresh}
                    disabled={isInitialLoading || isRefreshing}
                    className="flex items-center gap-1.5 rounded-lg border border-indigo-200/60 bg-white/60 px-3 py-2 text-xs font-rajdhani font-semibold text-slate-600 transition-colors hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-600/60 dark:bg-slate-800/60 dark:text-slate-300 dark:hover:bg-slate-700/60"
                >
                    <RefreshCw className={cn("h-3.5 w-3.5", (isInitialLoading || isRefreshing) && "animate-spin")} />
                    Reîmprospătare
                </button>
            </div>

            {statsIsError && (
                <div className={cn(WIDGET, "p-5")}>
                    <ErrorState message={getErrorMessage(statsError)} onRetry={() => refetchStats()} />
                </div>
            )}

            {stats && <KPICards stats={stats} />}

            {stats && (
                <Suspense fallback={<ChartsSkeleton />}>
                    <LazyChartsSection stats={stats} companies={filteredCompanies} />
                </Suspense>
            )}

            {/* Table */}
            <div className={cn(WIDGET, "p-5")}>
                <div className="mb-5 flex flex-wrap items-center gap-3">
                    <div className="mr-auto flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-indigo-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">
                            Companii Listate
                        </h3>
                        {bvbData && (
                            <span className="rounded-full bg-indigo-100 px-2 py-0.5 font-orbitron text-[10px] text-indigo-600 dark:bg-indigo-900/40 dark:text-indigo-300">
                                {filteredCompanies.length} afișate / {bvbData.total} total
                            </span>
                        )}
                        {isRefreshing && (
                            <span className="flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 font-rajdhani text-[10px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                                <RefreshCw className="h-3 w-3 animate-spin" />
                                actualizare
                            </span>
                        )}
                    </div>

                    <div className="relative">
                        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Caută ticker, ISIN, denumire..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-56 rounded-lg border border-slate-200 bg-white/70 py-1.5 pl-8 pr-3 font-rajdhani text-xs text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-slate-600 dark:bg-slate-800/70 dark:text-slate-300"
                        />
                    </div>

                    <div className="flex items-center gap-1.5">
                        <Filter className="h-3.5 w-3.5 text-slate-400" />
                        <select
                            value={segmentFilter}
                            onChange={(e) => {
                                setSegmentFilter(e.target.value);
                                setPage(1);
                            }}
                            className="rounded-lg border border-slate-200 bg-white/70 px-2 py-1.5 font-rajdhani text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-slate-600 dark:bg-slate-800/70 dark:text-slate-300"
                        >
                            <option value="">Toate segmentele</option>
                            <option value="Premium">Premium</option>
                            <option value="Standard">Standard</option>
                            <option value="AeRO">AeRO</option>
                        </select>
                    </div>

                    <select
                        value={`${sortBy}-${sortDir}`}
                        onChange={(e) => {
                            const [sb, sd] = e.target.value.split("-");
                            setSortBy(sb as typeof sortBy);
                            setSortDir(sd as typeof sortDir);
                            setPage(1);
                        }}
                        className="rounded-lg border border-slate-200 bg-white/70 px-2 py-1.5 font-rajdhani text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-slate-600 dark:bg-slate-800/70 dark:text-slate-300"
                    >
                        <option value="last_price-desc">Preț descrescător</option>
                        <option value="last_price-asc">Preț crescător</option>
                        <option value="change_pct-desc">Variație desc</option>
                        <option value="change_pct-asc">Variație asc</option>
                        <option value="denumire-asc">Denumire A→Z</option>
                        <option value="denumire-desc">Denumire Z→A</option>
                    </select>

                    <select
                        value={pageSize}
                        onChange={(e) => {
                            setPageSize(Number(e.target.value));
                            setPage(1);
                        }}
                        className="rounded-lg border border-slate-200 bg-white/70 px-2 py-1.5 font-rajdhani text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-slate-600 dark:bg-slate-800/70 dark:text-slate-300"
                    >
                        {PAGE_SIZE_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                                {option} / pagină
                            </option>
                        ))}
                    </select>
                </div>

                {companiesIsError ? (
                    <ErrorState message={getErrorMessage(companiesError)} onRetry={() => refetchCompanies()} />
                ) : isInitialLoading ? (
                    <TableSkeleton />
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-100 dark:border-slate-700/60">
                                    <th className="pb-3 pr-4 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Ticker / ISIN
                                    </th>
                                    <th className="pb-3 pr-4 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Denumire
                                    </th>
                                    <th className="pb-3 pr-4 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Segment
                                    </th>
                                    <th className="pb-3 pr-4 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Preț (RON)
                                    </th>
                                    <th className="pb-3 pr-4 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Variație %
                                    </th>
                                    <th className="pb-3 pr-4 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Volum
                                    </th>
                                    <th className="pb-3 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Capitalizare
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/40">
                                {filteredCompanies.map((company) => (
                                    <tr
                                        key={company.id}
                                        className="group transition-colors hover:bg-indigo-50/40 dark:hover:bg-indigo-900/10"
                                    >
                                        <td className="py-3 pr-4">
                                            <div className="flex flex-col gap-0.5">
                                                <span className="font-orbitron text-xs font-bold text-indigo-600 dark:text-indigo-400">
                                                    {company.ticker || "—"}
                                                </span>
                                                <span className="max-w-[120px] truncate font-mono text-[9px] text-slate-400">
                                                    {company.isin || "—"}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="py-3 pr-4">
                                            <Link
                                                to={`/company/${company.cui}`}
                                                className="line-clamp-2 max-w-[220px] font-rajdhani text-sm font-semibold text-slate-700 transition-colors hover:text-indigo-600 dark:text-slate-200 dark:hover:text-indigo-400"
                                                title={company.denumire}
                                            >
                                                {company.denumire}
                                            </Link>
                                            {company.judet && (
                                                <span className="font-rajdhani text-[10px] text-slate-400">
                                                    {company.judet}
                                                </span>
                                            )}
                                        </td>
                                        <td className="py-3 pr-4">
                                            {company.segment ? (
                                                <span
                                                    className="inline-block rounded-full px-2 py-0.5 font-rajdhani text-[10px] font-semibold text-white"
                                                    style={{
                                                        backgroundColor: SEGMENT_COLORS[company.segment] || "#64748b",
                                                    }}
                                                >
                                                    {company.segment}
                                                </span>
                                            ) : (
                                                <span className="text-slate-400">—</span>
                                            )}
                                        </td>
                                        <td className="py-3 pr-4 text-right font-mono text-sm font-semibold text-slate-700 dark:text-slate-200">
                                            {formatPrice(company.last_price)}
                                        </td>
                                        <td className="py-3 pr-4 text-right font-mono text-sm">
                                            <PctBadge value={company.change_pct} />
                                        </td>
                                        <td className="py-3 pr-4 text-right font-mono text-xs text-slate-500 dark:text-slate-400">
                                            {company.volume != null ? company.volume.toLocaleString("ro-RO") : "—"}
                                        </td>
                                        <td className="py-3 text-right font-mono text-xs text-slate-500 dark:text-slate-400">
                                            {company.market_cap != null
                                                ? new Intl.NumberFormat("ro-RO", {
                                                      notation: "compact",
                                                      maximumFractionDigits: 1,
                                                  }).format(company.market_cap)
                                                : "—"}
                                        </td>
                                    </tr>
                                ))}

                                {filteredCompanies.length === 0 && (
                                    <tr>
                                        <td colSpan={7} className="py-12 text-center font-rajdhani text-sm text-slate-400">
                                            Nu s-au găsit companii cu criteriile selectate.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}

                {bvbData && !companiesIsError && (
                    <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-slate-700/60">
                        <span className="font-rajdhani text-xs text-slate-400">
                            Pagina {page} din {totalPages} · {bvbData.total} total · {pageSize} pe pagină
                        </span>

                        <div className="flex gap-2">
                            <button
                                disabled={!canGoPrevious || companiesFetching}
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                                className="rounded-lg border border-slate-200 px-3 py-1.5 font-rajdhani text-xs text-slate-600 transition-colors hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                            >
                                Înapoi
                            </button>
                            <button
                                disabled={!canGoNext || companiesFetching}
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                className="rounded-lg border border-slate-200 px-3 py-1.5 font-rajdhani text-xs text-slate-600 transition-colors hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                            >
                                Înainte
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}