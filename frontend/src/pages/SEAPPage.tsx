import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useThemeStore } from "@/store/theme";
import api from "@/lib/api";
import type { Tender } from "@/types";
import { formatMoney, formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import {
    Gavel, Orbit, Search, FileText, TrendingUp,
    Landmark, BarChart3, Activity, PieChart as PieIcon, Euro,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, Legend,
} from "recharts";

/* ───── Demo / aggregated data for overview ───── */
const DEMO_MONTHLY = [
    { luna: "Oct", valoare: 48.2, licitatii: 124 },
    { luna: "Nov", valoare: 62.5, licitatii: 156 },
    { luna: "Dec", valoare: 35.8, licitatii: 98 },
    { luna: "Ian", valoare: 71.3, licitatii: 189 },
    { luna: "Feb", valoare: 54.6, licitatii: 142 },
    { luna: "Mar", valoare: 83.1, licitatii: 211 },
];

const DEMO_BY_PROCEDURE = [
    { name: "Licitație Deschisă", value: 42, color: "#6366f1" },
    { name: "Cerere de Ofertă", value: 28, color: "#8b5cf6" },
    { name: "Negociere", value: 12, color: "#ec4899" },
    { name: "Achiziție Directă", value: 35, color: "#06b6d4" },
    { name: "Dialog Competitiv", value: 5, color: "#f97316" },
    { name: "Concurs Soluții", value: 3, color: "#10b981" },
];



const WIDGET = "card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md shadow-indigo-500/5 backdrop-blur-sm";

/* ───── Overview component ───── */
function SeapOverview() {
    const dark = useThemeStore((s) => s.dark);
    const gridColor = dark ? "#334155" : "#e2e8f0";
    const tooltipStyle = { borderRadius: 12, fontFamily: "Exo 2", fontSize: 13, border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`, backgroundColor: dark ? "#1e293b" : "#ffffff", color: dark ? "#e2e8f0" : "#1e293b" };
    const tickStyle = { fontSize: 12, fontFamily: "Rajdhani", fill: dark ? "#94a3b8" : "#475569" };
    const kpis = [
        { label: "Licitații Active", value: "211", icon: FileText, color: "from-indigo-500 to-violet-600" },
        { label: "Valoare Totală", value: "€2.4B", icon: Euro, color: "from-emerald-500 to-teal-600" },
        { label: "Autorități", value: "87", icon: Landmark, color: "from-orange-500 to-amber-600" },
        { label: "Atribuite Luna", value: "45", icon: TrendingUp, color: "from-rose-500 to-pink-600" },
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
                    <ResponsiveContainer width="100%" height={260}>
                        <AreaChart data={DEMO_MONTHLY}>
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
                            <Tooltip contentStyle={tooltipStyle} />
                            <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12, color: dark ? "#94a3b8" : "#475569" }} />
                            <Area yAxisId="val" type="monotone" dataKey="valoare" stroke="#6366f1" strokeWidth={2} fill="url(#seapValGrad)" name="Valoare (M€)" />
                            <Area yAxisId="lic" type="monotone" dataKey="licitatii" stroke="#10b981" strokeWidth={2} fill="url(#seapLicGrad)" name="Nr. Licitații" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                <div className={cn(WIDGET, "p-5")}>
                    <div className="flex items-center gap-2 mb-4">
                        <PieIcon className="h-4 w-4 text-violet-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700 dark:text-slate-200">Tip Procedură</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                            <Pie data={DEMO_BY_PROCEDURE} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={3} dataKey="value">
                                {DEMO_BY_PROCEDURE.map((d, i) => (
                                    <Cell key={i} fill={d.color} stroke={dark ? "#0f172a" : "white"} strokeWidth={2} />
                                ))}
                            </Pie>
                            <Tooltip contentStyle={tooltipStyle} />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 justify-center">
                        {DEMO_BY_PROCEDURE.map((d) => (
                            <span key={d.name} className="flex items-center gap-1 text-[11px] font-rajdhani text-slate-500 dark:text-slate-400">
                                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                                {d.name}
                            </span>
                        ))}
                    </div>
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
