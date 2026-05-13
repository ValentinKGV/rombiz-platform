import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useThemeStore } from "@/store/theme";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import {
    TrendingUp, TrendingDown, BarChart3, Activity,
    PieChart as PieIcon, Building2, ArrowUpRight, ArrowDownRight,
    Minus, RefreshCw, Search, Filter,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area,
    Legend, ScatterChart, Scatter, ZAxis, ReferenceLine,
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
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {kpis.map((k) => {
                const Icon = k.icon;
                return (
                    <div key={k.label} className={cn(WIDGET, "p-4 flex items-center gap-4")}>
                        <div
                            className={cn(
                                "flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg flex-shrink-0",
                                k.color
                            )}
                        >
                            <Icon className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                            <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                {k.label}
                            </p>
                            <p className="font-orbitron text-xl font-bold text-slate-800 dark:text-slate-100 truncate">
                                {k.value}
                            </p>
                            <p className="font-rajdhani text-[10px] text-slate-400 truncate">{k.sub}</p>
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

    const data = stats.by_segment.map((s) => ({
        name: s.segment,
        value: Number(s.count),
        color: SEGMENT_COLORS[s.segment] || "#64748b",
    }));

    return (
        <div className={cn(WIDGET, "p-5")}>
            <div className="flex items-center gap-2 mb-4">
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
                            <Cell
                                key={i}
                                fill={d.color}
                                stroke={dark ? "#0f172a" : "white"}
                                strokeWidth={2}
                            />
                        ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 justify-center">
                {data.map((d) => (
                    <span
                        key={d.name}
                        className="flex items-center gap-1 text-[11px] font-rajdhani text-slate-500 dark:text-slate-400"
                    >
                        <span
                            className="inline-block h-2 w-2 rounded-full"
                            style={{ backgroundColor: d.color }}
                        />
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

    // Combine top gainers + losers for bar chart
    const allData = [
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
    ].sort((a, b) => b.change_pct - a.change_pct);

    return (
        <div className={cn(WIDGET, "p-5 lg:col-span-2")}>
            <div className="flex items-center gap-2 mb-4">
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
                    <YAxis
                        dataKey="ticker"
                        type="category"
                        tick={{ ...tickStyle, fontSize: 10 }}
                        width={78}
                    />
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

    // Scatter: last_price vs change_pct with segment color
    const scatterData = companies
        .filter((c) => c.last_price != null && c.change_pct != null)
        .map((c) => ({
            x: c.last_price as number,
            y: c.change_pct as number,
            z: 80,
            name: c.ticker || c.cui,
            segment: c.segment || "Necunoscut",
            denumire: c.denumire,
        }));

    // Group by segment for scatter series
    const bySegment: Record<string, typeof scatterData> = {};
    scatterData.forEach((d) => {
        if (!bySegment[d.segment]) bySegment[d.segment] = [];
        bySegment[d.segment].push(d);
    });

    return (
        <div className={cn(WIDGET, "p-5 lg:col-span-3")}>
            <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-4 w-4 text-cyan-500" />
                <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Preț vs Variație Zi (toate companiile)
                </h3>
                <span className="ml-auto text-[11px] font-rajdhani text-slate-400">
                    {scatterData.length} companii cu date
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
                    <Legend
                        wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12, color: dark ? "#94a3b8" : "#475569" }}
                    />
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

/* ─────────────────────────────────────────────
   Main Page
───────────────────────────────────────────── */
export default function BVBPage() {
    const dark = useThemeStore((s) => s.dark);
    const [search, setSearch] = useState("");
    const [segmentFilter, setSegmentFilter] = useState<string>("");
    const [sortBy, setSortBy] = useState<"last_price" | "change_pct" | "denumire">("last_price");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
    const [page, setPage] = useState(1);

    const { data: stats, isLoading: statsLoading } = useQuery<BVBStats>({
        queryKey: ["bvb", "stats"],
        queryFn: async () => {
            const { data } = await api.get("/bvb/stats");
            return data;
        },
        staleTime: 5 * 60 * 1000,
    });

    const { data: bvbData, isLoading: companiesLoading, refetch } = useQuery<BVBResponse>({
        queryKey: ["bvb", "companies", segmentFilter, sortBy, sortDir, page],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (segmentFilter) params.set("segment", segmentFilter);
            params.set("sort_by", sortBy);
            params.set("sort_dir", sortDir);
            params.set("page", page.toString());
            params.set("per_page", "100");
            const { data } = await api.get(`/bvb/companies?${params}`);
            return data;
        },
        staleTime: 5 * 60 * 1000,
    });

    // Client-side search filter
    const filtered = useMemo(() => {
        if (!bvbData?.items) return [];
        if (!search.trim()) return bvbData.items;
        const q = search.toLowerCase();
        return bvbData.items.filter(
            (c) =>
                c.denumire?.toLowerCase().includes(q) ||
                c.ticker?.toLowerCase().includes(q) ||
                c.isin?.toLowerCase().includes(q) ||
                c.cui?.toString().includes(q)
        );
    }, [bvbData, search]);

    const isLoading = statsLoading || companiesLoading;

    return (
        <div
            className="min-h-screen -m-6 p-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950"
            style={{
                backgroundImage:
                    "radial-gradient(circle at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(236,72,153,0.04) 0%, transparent 50%)",
            }}
        >
            {/* ── Header ── */}
            <div className="section-header flex items-start justify-between">
                <div>
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                        BVB — Bursa de Valori București
                    </h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Companii listate la bursă · date de piață în timp real
                    </p>
                </div>
                <button
                    onClick={() => refetch()}
                    className="flex items-center gap-1.5 rounded-lg border border-indigo-200/60 dark:border-slate-600/60 bg-white/60 dark:bg-slate-800/60 px-3 py-2 text-xs font-rajdhani font-semibold text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-slate-700/60 transition-colors"
                >
                    <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
                    Reîmprospătare
                </button>
            </div>

            {/* ── KPI Cards ── */}
            {stats && <KPICards stats={stats} />}

            {/* ── Charts Row 1 ── */}
            {stats && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <GainersLosersChart stats={stats} />
                    <SegmentPieChart stats={stats} />
                </div>
            )}

            {/* ── Scatter Chart ── */}
            {bvbData && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <PriceDistributionChart companies={bvbData.items} />
                </div>
            )}

            {/* ── Table ── */}
            <div className={cn(WIDGET, "p-5")}>
                <div className="flex flex-wrap items-center gap-3 mb-5">
                    <div className="flex items-center gap-2 mr-auto">
                        <Building2 className="h-4 w-4 text-indigo-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">
                            Companii Listate
                        </h3>
                        {bvbData && (
                            <span className="rounded-full bg-indigo-100 dark:bg-indigo-900/40 px-2 py-0.5 text-[10px] font-orbitron text-indigo-600 dark:text-indigo-300">
                                {filtered.length} / {bvbData.total}
                            </span>
                        )}
                    </div>

                    {/* Search */}
                    <div className="relative">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Caută ticker, ISIN, denumire..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-56 rounded-lg border border-slate-200 dark:border-slate-600 bg-white/70 dark:bg-slate-800/70 pl-8 pr-3 py-1.5 text-xs font-rajdhani text-slate-700 dark:text-slate-300 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        />
                    </div>

                    {/* Segment filter */}
                    <div className="flex items-center gap-1.5">
                        <Filter className="h-3.5 w-3.5 text-slate-400" />
                        <select
                            value={segmentFilter}
                            onChange={(e) => { setSegmentFilter(e.target.value); setPage(1); }}
                            className="rounded-lg border border-slate-200 dark:border-slate-600 bg-white/70 dark:bg-slate-800/70 px-2 py-1.5 text-xs font-rajdhani text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                        >
                            <option value="">Toate segmentele</option>
                            <option value="Premium">Premium</option>
                            <option value="Standard">Standard</option>
                            <option value="AeRO">AeRO</option>
                        </select>
                    </div>

                    {/* Sort */}
                    <select
                        value={`${sortBy}-${sortDir}`}
                        onChange={(e) => {
                            const [sb, sd] = e.target.value.split("-");
                            setSortBy(sb as typeof sortBy);
                            setSortDir(sd as typeof sortDir);
                            setPage(1);
                        }}
                        className="rounded-lg border border-slate-200 dark:border-slate-600 bg-white/70 dark:bg-slate-800/70 px-2 py-1.5 text-xs font-rajdhani text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    >
                        <option value="last_price-desc">Preț descrescător</option>
                        <option value="last_price-asc">Preț crescător</option>
                        <option value="change_pct-desc">Variație desc</option>
                        <option value="change_pct-asc">Variație asc</option>
                        <option value="denumire-asc">Denumire A→Z</option>
                        <option value="denumire-desc">Denumire Z→A</option>
                    </select>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <RefreshCw className="h-6 w-6 animate-spin text-indigo-400" />
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-100 dark:border-slate-700/60">
                                    <th className="pb-3 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4">
                                        Ticker / ISIN
                                    </th>
                                    <th className="pb-3 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4">
                                        Denumire
                                    </th>
                                    <th className="pb-3 text-left font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4">
                                        Segment
                                    </th>
                                    <th className="pb-3 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4">
                                        Preț (RON)
                                    </th>
                                    <th className="pb-3 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4">
                                        Variație %
                                    </th>
                                    <th className="pb-3 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400 pr-4">
                                        Volum
                                    </th>
                                    <th className="pb-3 text-right font-rajdhani text-xs uppercase tracking-wider text-slate-400">
                                        Capitalizare
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/40">
                                {filtered.map((company) => (
                                    <tr
                                        key={company.id}
                                        className="group hover:bg-indigo-50/40 dark:hover:bg-indigo-900/10 transition-colors"
                                    >
                                        <td className="py-3 pr-4">
                                            <div className="flex flex-col gap-0.5">
                                                <span className="font-orbitron text-xs font-bold text-indigo-600 dark:text-indigo-400">
                                                    {company.ticker || "—"}
                                                </span>
                                                <span className="font-mono text-[9px] text-slate-400 truncate max-w-[120px]">
                                                    {company.isin || "—"}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="py-3 pr-4">
                                            <Link
                                                to={`/company/${company.cui}`}
                                                className="font-rajdhani text-sm font-semibold text-slate-700 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors line-clamp-2 max-w-[220px]"
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
                                                    className="inline-block rounded-full px-2 py-0.5 text-[10px] font-rajdhani font-semibold text-white"
                                                    style={{
                                                        backgroundColor:
                                                            SEGMENT_COLORS[company.segment] || "#64748b",
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
                                            {company.volume != null
                                                ? company.volume.toLocaleString("ro-RO")
                                                : "—"}
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
                                {filtered.length === 0 && (
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

                {/* Pagination */}
                {bvbData && bvbData.pages > 1 && (
                    <div className="flex items-center justify-between mt-5 pt-4 border-t border-slate-100 dark:border-slate-700/60">
                        <span className="font-rajdhani text-xs text-slate-400">
                            Pagina {page} din {bvbData.pages} ({bvbData.total} total)
                        </span>
                        <div className="flex gap-2">
                            <button
                                disabled={page === 1}
                                onClick={() => setPage((p) => p - 1)}
                                className="rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-1.5 text-xs font-rajdhani text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-indigo-50 dark:hover:bg-slate-700 transition-colors"
                            >
                                Înapoi
                            </button>
                            <button
                                disabled={page === bvbData.pages}
                                onClick={() => setPage((p) => p + 1)}
                                className="rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-1.5 text-xs font-rajdhani text-slate-600 dark:text-slate-300 disabled:opacity-40 hover:bg-indigo-50 dark:hover:bg-slate-700 transition-colors"
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
