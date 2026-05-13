import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Alert } from "@/types";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import {
    Bell, Check, CheckCheck, Building2, Orbit, Zap,
    AlertTriangle, ShieldAlert, TrendingUp, Eye,
    BarChart3, Activity, Brain,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState, useMemo } from "react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, AreaChart, Area, Legend,
} from "recharts";

const ALERT_TYPE_LABELS: Record<string, string> = {
    insolventa_noua: "Insolvență Nouă",
    schimbare_stare_fiscala: "Schimbare Stare Fiscală",
    degradare_risc: "Degradare Risc",
    mentiune_monitor_oficial: "Mențiune Monitor Oficial",
    litigiu_nou: "Litigiu Nou",
    schimbare_asociati: "Schimbare Asociați",
    schimbare_administrator: "Schimbare Administrator",
    radiere: "Radiere",
    datorii_buget_noi: "Datorii Buget Noi",
    contract_public_nou: "Contract Public Nou",
    modificare_capital_social: "Modificare Capital Social",
    publicare_bilant: "Publicare Bilanț",
    lichidare: "Lichidare",
    ai_anomaly_detected: "🤖 Anomalie AI",
};

/* ───── Demo / aggregated data ───── */
const SEVERITY_COLORS = { critic: "#ef4444", ridicat: "#f97316", mediu: "#eab308", scăzut: "#22c55e" };

const DEMO_MONTHLY = [
    { luna: "Oct", critic: 3, ridicat: 8, mediu: 14, scăzut: 6 },
    { luna: "Nov", critic: 5, ridicat: 12, mediu: 10, scăzut: 9 },
    { luna: "Dec", critic: 2, ridicat: 6, mediu: 18, scăzut: 11 },
    { luna: "Ian", critic: 7, ridicat: 9, mediu: 12, scăzut: 8 },
    { luna: "Feb", critic: 4, ridicat: 11, mediu: 15, scăzut: 7 },
    { luna: "Mar", critic: 6, ridicat: 14, mediu: 9, scăzut: 5 },
];

const DEMO_BY_TYPE = [
    { name: "Insolvență", value: 24, color: "#ef4444" },
    { name: "Stare Fiscală", value: 31, color: "#f97316" },
    { name: "Degradare Risc", value: 18, color: "#eab308" },
    { name: "Litigii", value: 27, color: "#8b5cf6" },
    { name: "Monitor Oficial", value: 15, color: "#06b6d4" },
    { name: "Datorii Buget", value: 22, color: "#ec4899" },
    { name: "Contracte SEAP", value: 19, color: "#10b981" },
    { name: "Alte tipuri", value: 12, color: "#64748b" },
];

const DEMO_TREND = [
    { zi: "19 Mar", total: 8, necitite: 5 },
    { zi: "20 Mar", total: 12, necitite: 9 },
    { zi: "21 Mar", total: 6, necitite: 3 },
    { zi: "22 Mar", total: 15, necitite: 11 },
    { zi: "23 Mar", total: 10, necitite: 6 },
    { zi: "24 Mar", total: 18, necitite: 14 },
    { zi: "25 Mar", total: 9, necitite: 7 },
];

const DEMO_TOP_COMPANIES = [
    { firma: "ALPHA CONSTRUCT SRL", cui: "12345678", alerte: 14, severitate: "critic" },
    { firma: "BETA LOGISTICS SA", cui: "23456789", alerte: 11, severitate: "ridicat" },
    { firma: "GAMMA SERVICES SRL", cui: "34567890", alerte: 9, severitate: "mediu" },
    { firma: "DELTA TRADING SRL", cui: "45678901", alerte: 7, severitate: "ridicat" },
    { firma: "EPSILON TECH SA", cui: "56789012", alerte: 6, severitate: "critic" },
];

const sevBadge = (s: string) => {
    const map: Record<string, string> = {
        critic: "bg-red-100 text-red-700",
        ridicat: "bg-orange-100 text-orange-700",
        mediu: "bg-yellow-100 text-yellow-700",
        scăzut: "bg-green-100 text-green-700",
    };
    return map[s] || "bg-slate-100 text-slate-600";
};

/* ───── Overview component ───── */
function AlertsOverview({ totalAlerts, unreadCount }: { totalAlerts: number; unreadCount: number }) {
    const kpis = [
        { label: "Total Alerte", value: totalAlerts || 168, icon: Bell, color: "from-blue-500 to-indigo-600", bg: "bg-blue-50" },
        { label: "Necitite", value: unreadCount || 43, icon: Eye, color: "from-red-500 to-rose-600", bg: "bg-red-50" },
        { label: "Critice (luna)", value: 27, icon: ShieldAlert, color: "from-orange-500 to-amber-600", bg: "bg-orange-50" },
        { label: "Firme Afectate", value: 54, icon: Building2, color: "from-violet-500 to-purple-600", bg: "bg-violet-50" },
    ];

    return (
        <div className="space-y-6 mb-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {kpis.map((k) => {
                    const Icon = k.icon;
                    return (
                        <div key={k.label} className="card-cosmic p-4 flex items-center gap-4 border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm">
                            <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg", k.color)}>
                                <Icon className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">{k.label}</p>
                                <p className="font-orbitron text-xl font-bold text-slate-800">{k.value}</p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Charts Row 1: Stacked Bar + Donut */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Stacked bar – alerte pe lună */}
                <div className="card-cosmic p-5 lg:col-span-2 border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <BarChart3 className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700">Alerte pe Lună</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={260}>
                        <BarChart data={DEMO_MONTHLY} barGap={2}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="luna" tick={{ fontSize: 12, fontFamily: "Rajdhani" }} />
                            <YAxis tick={{ fontSize: 12, fontFamily: "Rajdhani" }} />
                            <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 13, border: "1px solid #e2e8f0" }} />
                            <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12 }} />
                            <Bar dataKey="critic" stackId="a" fill={SEVERITY_COLORS.critic} radius={[0, 0, 0, 0]} name="Critic" />
                            <Bar dataKey="ridicat" stackId="a" fill={SEVERITY_COLORS.ridicat} name="Ridicat" />
                            <Bar dataKey="mediu" stackId="a" fill={SEVERITY_COLORS.mediu} name="Mediu" />
                            <Bar dataKey="scăzut" stackId="a" fill={SEVERITY_COLORS.scăzut} radius={[4, 4, 0, 0]} name="Scăzut" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Donut – distribuție pe tip */}
                <div className="card-cosmic p-5 border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <AlertTriangle className="h-4 w-4 text-orange-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700">Distribuție pe Tip</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie data={DEMO_BY_TYPE} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3} dataKey="value">
                                {DEMO_BY_TYPE.map((d, i) => (
                                    <Cell key={i} fill={d.color} stroke="white" strokeWidth={2} />
                                ))}
                            </Pie>
                            <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 13 }} />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 justify-center">
                        {DEMO_BY_TYPE.map((d) => (
                            <span key={d.name} className="flex items-center gap-1 text-[11px] font-rajdhani text-slate-500">
                                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                                {d.name}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Charts Row 2: Area trend + Top companies */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Area chart – trend zilnic */}
                <div className="card-cosmic p-5 lg:col-span-2 border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <Activity className="h-4 w-4 text-emerald-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700">Trend Alerte (ultimele 7 zile)</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={DEMO_TREND}>
                            <defs>
                                <linearGradient id="alertTotalGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="alertUnreadGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="zi" tick={{ fontSize: 12, fontFamily: "Rajdhani" }} />
                            <YAxis tick={{ fontSize: 12, fontFamily: "Rajdhani" }} />
                            <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 13 }} />
                            <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12 }} />
                            <Area type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={2} fill="url(#alertTotalGrad)" name="Total" />
                            <Area type="monotone" dataKey="necitite" stroke="#ef4444" strokeWidth={2} fill="url(#alertUnreadGrad)" name="Necitite" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Top companies by alerts */}
                <div className="card-cosmic p-5 border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <TrendingUp className="h-4 w-4 text-rose-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700">Top Firme cu Alerte</h3>
                    </div>
                    <div className="space-y-3">
                        {DEMO_TOP_COMPANIES.map((c, i) => (
                            <div key={c.cui} className="flex items-center gap-3">
                                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 font-orbitron text-xs font-bold text-slate-500">
                                    {i + 1}
                                </span>
                                <div className="flex-1 min-w-0">
                                    <p className="font-exo text-sm text-slate-700 truncate">{c.firma}</p>
                                    <p className="font-rajdhani text-[11px] text-slate-400">CUI: {c.cui}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-rajdhani font-semibold uppercase", sevBadge(c.severitate))}>
                                        {c.severitate}
                                    </span>
                                    <span className="font-orbitron text-sm font-bold text-slate-600">{c.alerte}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

/* ───── Filter tabs ───── */
type TabFilter = "toate" | "necitite" | "critice" | "ai";

export default function AlertsPage() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState<TabFilter>("toate");

    const { data: alerts, isLoading } = useQuery<Alert[]>({
        queryKey: ["alerts"],
        queryFn: async () => {
            const { data } = await api.get("/alerts");
            return data;
        },
    });

    const markReadMutation = useMutation({
        mutationFn: async (id: number) => {
            await api.put(`/alerts/${id}/read`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["alerts"] });
            queryClient.invalidateQueries({ queryKey: ["alerts", "unread-count"] });
        },
    });

    const markAllMutation = useMutation({
        mutationFn: async () => {
            await api.put("/alerts/mark-all-read");
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["alerts"] });
            queryClient.invalidateQueries({ queryKey: ["alerts", "unread-count"] });
        },
    });

    const unreadCount = alerts?.filter((a) => !a.citita).length || 0;
    const totalCount = alerts?.length || 0;

    const filteredAlerts = useMemo(() => {
        if (!alerts) return [];
        if (activeTab === "necitite") return alerts.filter((a) => !a.citita);
        if (activeTab === "critice") return alerts.filter((a) =>
            ["insolventa_noua", "lichidare", "radiere", "degradare_risc"].includes(a.tip_alerta)
        );
        if (activeTab === "ai") return alerts.filter((a) => a.tip_alerta === "ai_anomaly_detected");
        return alerts;
    }, [alerts, activeTab]);

    const tabs: { key: TabFilter; label: string; count: number }[] = [
        { key: "toate", label: "Toate", count: totalCount },
        { key: "necitite", label: "Necitite", count: unreadCount },
        { key: "critice", label: "Critice", count: alerts?.filter((a) => ["insolventa_noua", "lichidare", "radiere", "degradare_risc"].includes(a.tip_alerta)).length || 0 },
        { key: "ai", label: "🤖 AI", count: alerts?.filter((a) => a.tip_alerta === "ai_anomaly_detected").length || 0 },
    ];

    return (
        <div className="min-h-screen -m-6 p-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(236,72,153,0.04) 0%, transparent 50%)' }}>
            <div className="flex items-center justify-between">
                <div className="section-header">
                    <div>
                        <h1 className="font-orbitron text-2xl font-bold tracking-wide text-dragon">Alerte</h1>
                        <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                            {unreadCount > 0 ? `${unreadCount} semnale necitite din cosmos` : "Toate semnalele au fost procesate"}
                        </p>
                    </div>
                </div>
                {unreadCount > 0 && (
                    <button
                        onClick={() => markAllMutation.mutate()}
                        className="flex items-center gap-2 rounded-xl border border-nebula-200 px-4 py-2 font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:bg-nebula-50 transition-colors"
                    >
                        <CheckCheck className="h-4 w-4" />
                        Marchează toate
                    </button>
                )}
            </div>

            {/* ── Overview Charts ── */}
            <AlertsOverview totalAlerts={totalCount} unreadCount={unreadCount} />

            {/* ── Filter Tabs ── */}
            <div className="flex items-center gap-1 rounded-xl bg-white/60 border border-indigo-100/60 p-1 w-fit shadow-sm backdrop-blur-sm">
                {tabs.map((t) => (
                    <button
                        key={t.key}
                        onClick={() => setActiveTab(t.key)}
                        className={cn(
                            "flex items-center gap-1.5 rounded-lg px-4 py-2 font-rajdhani text-sm font-semibold uppercase tracking-wider transition-all",
                            activeTab === t.key
                                ? "bg-white text-nebula-700 shadow-sm"
                                : "text-slate-400 hover:text-slate-600"
                        )}
                    >
                        {t.label}
                        <span className={cn(
                            "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                            activeTab === t.key ? "bg-nebula-100 text-nebula-600" : "bg-slate-200 text-slate-500"
                        )}>
                            {t.count}
                        </span>
                    </button>
                ))}
            </div>

            {isLoading ? (
                <div className="flex h-32 items-center justify-center">
                    <div className="relative">
                        <div className="h-10 w-10 animate-spin rounded-full border-4 border-dragon-200 border-t-dragon-500" />
                        <Zap className="absolute inset-0 m-auto h-4 w-4 text-dragon-400 animate-pulse" />
                    </div>
                </div>
            ) : (
                <div className="space-y-2">
                    {filteredAlerts.map((alert) => (
                        <div
                            key={alert.id}
                            className={cn(
                                "group flex items-start gap-4 rounded-xl border-[1.5px] bg-white/70 backdrop-blur-sm p-4 transition-all shadow-sm",
                                alert.tip_alerta === "ai_anomaly_detected"
                                    ? "border-violet-200 bg-violet-50/40 shadow-violet-500/5"
                                    : !alert.citita
                                        ? "border-dragon-200 bg-dragon-50/40 shadow-dragon-500/5"
                                        : "border-indigo-100/80 hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-500/5"
                            )}
                        >
                            <div className={cn(
                                "mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl transition-colors flex-shrink-0",
                                alert.tip_alerta === "ai_anomaly_detected"
                                    ? "bg-violet-100 text-violet-500"
                                    : !alert.citita ? "bg-dragon-100 text-dragon-500" : "bg-slate-100 text-slate-400"
                            )}>
                                {alert.tip_alerta === "ai_anomaly_detected" ? <Brain className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="badge-cosmic">
                                        {ALERT_TYPE_LABELS[alert.tip_alerta] || alert.tip_alerta}
                                    </span>
                                    <span className="font-rajdhani text-xs text-slate-400">
                                        {formatDateTime(alert.created_at)}
                                    </span>
                                </div>
                                <p className="mt-1.5 font-exo text-sm text-slate-600">{alert.titlu}</p>
                                {alert.company_name && (
                                    <button
                                        onClick={() => navigate(`/company/${alert.company_cui}`)}
                                        className="mt-1.5 flex items-center gap-1 font-rajdhani text-xs font-semibold text-nebula-500 hover:text-nebula-700 transition-colors"
                                    >
                                        <Building2 className="h-3 w-3" />
                                        {alert.company_name}
                                    </button>
                                )}
                            </div>
                            {!alert.citita && (
                                <button
                                    onClick={() => markReadMutation.mutate(alert.id)}
                                    className="rounded-lg p-1.5 text-slate-400 hover:bg-nebula-50 hover:text-nebula-600 transition-colors"
                                    title="Marchează ca citit"
                                >
                                    <Check className="h-4 w-4" />
                                </button>
                            )}
                        </div>
                    ))}

                    {filteredAlerts.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-12 text-slate-300">
                            <Orbit className="h-12 w-12 mb-3 animate-[orbit-spin_8s_linear_infinite]" />
                            <p className="font-rajdhani text-sm uppercase tracking-wider">
                                {activeTab === "toate" ? "Nu ai alerte" : `Nicio alertă ${activeTab === "necitite" ? "necitită" : "critică"}`}
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
