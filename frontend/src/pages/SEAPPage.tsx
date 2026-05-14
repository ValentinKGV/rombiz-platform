import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useThemeStore } from "@/store/theme";
import api from "@/lib/api";
import type { Tender } from "@/types";
import { formatMoney, formatDate, formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";
import {
    Gavel, Orbit, Search, FileText, TrendingUp,
    Landmark, BarChart3, Activity, PieChart as PieIcon, Euro,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, Legend,
} from "recharts";

interface SeapAuthorityStat {
    autoritate: string;
    nr_contracte: number;
    total_ron: number;
}

interface SeapContract {
    id: number;
    valoare_ron: number | null;
    data_atribuire: string | null;
}

const PROCEDURE_COLORS = [
    "#6366f1",
    "#8b5cf6",
    "#ec4899",
    "#06b6d4",
    "#f97316",
    "#10b981",
    "#f59e0b",
    "#0ea5e9",
];

const MONTH_LABELS = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"];



const WIDGET = "card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md shadow-indigo-500/5 backdrop-blur-sm";

/* ───── Overview component ───── */
function SeapOverview() {
    const dark = useThemeStore((s) => s.dark);
    const gridColor = dark ? "#334155" : "#e2e8f0";
    const tooltipStyle = { borderRadius: 12, fontFamily: "Exo 2", fontSize: 13, border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`, backgroundColor: dark ? "#1e293b" : "#ffffff", color: dark ? "#e2e8f0" : "#1e293b" };
    const tickStyle = { fontSize: 12, fontFamily: "Rajdhani", fill: dark ? "#94a3b8" : "#475569" };
    const today = new Date();
    const startSixMonths = new Date(today.getFullYear(), today.getMonth() - 5, 1);
    const startMonth = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());

    const { data: tendersOverview, isLoading: tendersLoading } = useQuery({
        queryKey: ["seap", "overview", "tenders"],
        queryFn: async () => (await api.get("/seap/tenders", { params: { page_size: 100 } })).data,
    });

    const { data: authorityStats, isLoading: authorityLoading } = useQuery<SeapAuthorityStat[]>({
        queryKey: ["seap", "stats", "authority"],
        queryFn: async () => (await api.get("/seap/stats/by-authority", { params: { top: 200 } })).data,
    });

    const { data: contractsOverview, isLoading: contractsLoading } = useQuery<SeapContract[]>({
        queryKey: ["seap", "overview", "contracts", "6m"],
        queryFn: async () => (await api.get("/seap/contracts", {
            params: {
                per_page: 100,
                data_de_la: startSixMonths.toISOString().slice(0, 10),
            },
        })).data,
    });

    const tenderItems = (tendersOverview?.items || []) as Tender[];
    const totalAuthorities = authorityStats?.length ?? 0;
    const totalValueRon = authorityStats?.reduce((sum, item) => sum + (item.total_ron || 0), 0) ?? 0;

    const awardedThisMonth = useMemo(() => {
        if (!contractsOverview?.length) return 0;
        const start = startMonth.getTime();
        return contractsOverview.filter((c) => {
            if (!c.data_atribuire) return false;
            return new Date(c.data_atribuire).getTime() >= start;
        }).length;
    }, [contractsOverview, startMonth]);

    const monthlyTrend = useMemo(() => {
        if (!contractsOverview?.length) return [] as { luna: string; valoare: number; licitatii: number }[];
        const buckets = new Map<string, { valoare: number; licitatii: number }>();
        for (let i = 5; i >= 0; i -= 1) {
            const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
            buckets.set(`${d.getFullYear()}-${d.getMonth()}`, { valoare: 0, licitatii: 0 });
        }

        contractsOverview.forEach((c) => {
            if (!c.data_atribuire) return;
            const d = new Date(c.data_atribuire);
            const key = `${d.getFullYear()}-${d.getMonth()}`;
            const bucket = buckets.get(key);
            if (!bucket) return;
            bucket.licitatii += 1;
            bucket.valoare += c.valoare_ron || 0;
        });

        return Array.from(buckets.entries()).map(([key, vals]) => {
            const [, month] = key.split("-").map(Number);
            return {
                luna: MONTH_LABELS[month],
                valoare: Math.round(vals.valoare / 1_000_000 * 10) / 10,
                licitatii: vals.licitatii,
            };
        });
    }, [contractsOverview, today]);

    const byProcedure = useMemo(() => {
        if (!tenderItems.length) return [] as { name: string; value: number; color: string }[];
        const counts = new Map<string, number>();
        tenderItems.forEach((t) => {
            const label = t.procedure_type || t.tip_procedura || "N/A";
            counts.set(label, (counts.get(label) || 0) + 1);
        });

        return Array.from(counts.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8)
            .map(([name, value], i) => ({
                name,
                value,
                color: PROCEDURE_COLORS[i % PROCEDURE_COLORS.length],
            }));
    }, [tenderItems]);

    const kpis = [
        {
            label: "Licitații Active",
            value: tendersLoading ? "..." : formatNumber(tenderItems.length),
            icon: FileText,
            color: "from-indigo-500 to-violet-600",
        },
        {
            label: "Valoare Totală",
            value: authorityLoading ? "..." : formatMoney(totalValueRon, "RON"),
            icon: Euro,
            color: "from-emerald-500 to-teal-600",
        },
        {
            label: "Autorități",
            value: authorityLoading ? "..." : formatNumber(totalAuthorities),
            icon: Landmark,
            color: "from-orange-500 to-amber-600",
        },
        {
            label: "Atribuite Luna",
            value: contractsLoading ? "..." : formatNumber(awardedThisMonth),
            icon: TrendingUp,
            color: "from-rose-500 to-pink-600",
        },
    ];

    return (
        <div className="space-y-6 mb-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {kpis.map((k) => {
                    const Icon = k.icon;
                    return (
                        <div key={k.label} className={cn(WIDGET, "p-4 flex items-center gap-4")}>
                            <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg flex-shrink-0", k.color)}>
                                <Icon className="h-5 w-5" />
                            </div>
                            <div className="min-w-0">
                                <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400 dark:text-slate-400">{k.label}</p>
                                <p className="font-orbitron text-xl font-bold text-slate-800 dark:text-slate-100 truncate">{k.value}</p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Charts Row 1: Area trend + Procedure Donut */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className={cn(WIDGET, "p-5 lg:col-span-2")}>
                    <div className="flex items-center gap-2 mb-4">
                        <Activity className="h-4 w-4 text-indigo-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">Evoluție Lunară</h3>
                    </div>
                    {monthlyTrend.length === 0 ? (
                        <div className="flex h-[260px] items-center justify-center text-sm text-slate-400">
                            {contractsLoading ? "Se încarcă..." : "Nu există date"}
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={260}>
                            <AreaChart data={monthlyTrend}>
                                <defs>
                                    <linearGradient id="seapValGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="seapLicGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                                <XAxis dataKey="luna" tick={tickStyle} />
                                <YAxis yAxisId="val" orientation="left" tick={tickStyle} />
                                <YAxis yAxisId="lic" orientation="right" tick={tickStyle} />
                                <Tooltip contentStyle={tooltipStyle} formatter={(v: number, name: string) => (
                                    name === "Valoare (mil RON)" ? [`${v.toLocaleString("ro-RO")} mil RON`, name] : [v, name]
                                )} />
                                <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12, color: dark ? "#94a3b8" : "#475569" }} />
                                <Area yAxisId="val" type="monotone" dataKey="valoare" stroke="#6366f1" strokeWidth={2} fill="url(#seapValGrad)" name="Valoare (mil RON)" />
                                <Area yAxisId="lic" type="monotone" dataKey="licitatii" stroke="#10b981" strokeWidth={2} fill="url(#seapLicGrad)" name="Nr. Licitații" />
                            </AreaChart>
                        </ResponsiveContainer>
                    )}
                </div>

                <div className={cn(WIDGET, "p-5")}>
                    <div className="flex items-center gap-2 mb-4">
                        <PieIcon className="h-4 w-4 text-violet-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">Tip Procedură</h3>
                    </div>
                    {byProcedure.length === 0 ? (
                        <div className="flex h-[200px] items-center justify-center text-sm text-slate-400">
                            {tendersLoading ? "Se încarcă..." : "Nu există date"}
                        </div>
                    ) : (
                        <>
                            <ResponsiveContainer width="100%" height={200}>
                                <PieChart>
                                    <Pie data={byProcedure} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={3} dataKey="value">
                                        {byProcedure.map((d, i) => (
                                            <Cell key={i} fill={d.color} stroke={dark ? "#0f172a" : "white"} strokeWidth={2} />
                                        ))}
                                    </Pie>
                                    <Tooltip contentStyle={tooltipStyle} />
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 justify-center">
                                {byProcedure.map((d) => (
                                    <span key={d.name} className="flex items-center gap-1 text-[11px] font-rajdhani text-slate-500 dark:text-slate-400">
                                        <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                                        {d.name}
                                    </span>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function SEAPPage() {
    const [search, setSearch] = useState("");
    const [cpvFilter, setCpvFilter] = useState("");
    const dark = useThemeStore((s) => s.dark);

    const { data: tenders, isLoading } = useQuery({
        queryKey: ["seap", "tenders", search, cpvFilter],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (search) params.set("q", search);
            if (cpvFilter) params.set("cpv", cpvFilter);
            params.set("page_size", "50");
            const { data } = await api.get(`/seap/tenders?${params}`);
            return data;
        },
    });

    const { data: stats } = useQuery({
        queryKey: ["seap", "stats"],
        queryFn: async () => {
            const { data } = await api.get("/seap/stats/by-cpv");
            return data;
        },
    });

    return (
        <div className="min-h-screen -m-6 p-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(236,72,153,0.04) 0%, transparent 50%)' }}>
            <div className="section-header">
                <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">SEAP — Achiziții Publice</h1>
                <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">Licitații active și contracte publice</p>
            </div>

            {/* ── Overview Charts ── */}
            <SeapOverview />

            {/* Stats Chart — from API */}
            {stats && (
                <div className={cn(WIDGET, "p-5")}>
                    <div className="flex items-center gap-2 mb-4">
                        <BarChart3 className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">Top CPV-uri (date reale)</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={(stats?.items || []).slice(0, 10)}>
                            <CartesianGrid strokeDasharray="3 3" stroke={dark ? "#334155" : "#e2e8f0"} />
                            <XAxis dataKey="cpv" tick={{ fontSize: 11, fontFamily: "Rajdhani", fill: dark ? "#94a3b8" : "#475569" }} />
                            <YAxis tick={{ fontSize: 12, fontFamily: "Rajdhani", fill: dark ? "#94a3b8" : "#475569" }} />
                            <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 13, border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`, backgroundColor: dark ? "#1e293b" : "#ffffff", color: dark ? "#e2e8f0" : "#1e293b" }} />
                            <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} name="Licitații" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Search */}
            <div className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-nebula-400" />
                    <input
                        type="text"
                        placeholder="Caută licitație..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="input-scifi pl-10"
                    />
                </div>
                <input
                    type="text"
                    placeholder="Cod CPV"
                    value={cpvFilter}
                    onChange={(e) => setCpvFilter(e.target.value)}
                    className="input-scifi w-32"
                />
            </div>

            {/* Tenders List */}
            {isLoading ? (
                <div className="flex h-32 items-center justify-center">
                    <div className="relative">
                        <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                    </div>
                </div>
            ) : (
                <div className="space-y-3">
                    {(tenders?.items || []).map((tender: Tender) => (
                        <div key={tender.id} className="group rounded-xl border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 bg-white/70 dark:bg-slate-800/70 backdrop-blur-sm p-4 transition-all hover:border-indigo-200 dark:hover:border-indigo-700/60 hover:shadow-md hover:shadow-indigo-500/5">
                            <div className="flex items-start justify-between gap-4">
                                <div className="min-w-0 flex-1">
                                    <p className="font-exo font-semibold text-slate-700 dark:text-slate-200">{tender.titlu || tender.title}</p>
                                    <p className="mt-1 font-rajdhani text-sm text-slate-400 dark:text-slate-400">
                                        <Gavel className="mr-1 inline h-3 w-3" />
                                        {tender.authority_name} · CPV: {tender.cpv_code}
                                    </p>
                                    <p className="mt-1 font-rajdhani text-xs text-slate-400 dark:text-slate-500">
                                        Nr: {tender.numar_anunt || tender.tender_number} · {tender.tip_procedura || tender.procedure_type}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <p className="font-orbitron font-semibold text-nebula-600">
                                        {formatMoney(tender.estimated_value, tender.moneda || tender.currency)}
                                    </p>
                                    <p className="mt-1 font-rajdhani text-xs text-slate-400">
                                        Limită: {formatDate(tender.submission_deadline)}
                                    </p>
                                    <span className="mt-1 inline-block rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                                        {tender.stare}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
