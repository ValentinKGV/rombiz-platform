import { useState, useEffect, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { Link, useNavigate } from "react-router-dom";
import {
    Building2,
    AlertTriangle,
    TrendingUp,
    Bell,
    Activity,
    Orbit,
    Flame,
    Sparkles,
    Leaf,
    Shield,
    Banknote,
    FileText,
    Wifi,
    WifiOff,
    Search,
    Bot,
    ReceiptText,
    Briefcase,
    ChevronRight,
    Clock,
    Eye,
    EyeOff,
    Star,
    Plus,
} from "lucide-react";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
    LineChart,
    Line,
} from "recharts";
import { wsClient } from "@/lib/websocket";
import { cn } from "@/lib/utils";
import { useThemeStore } from "@/store/theme";



interface WatchedCompany {
    id: number;
    cui: number;
    denumire: string;
    judet: string;
    localitate: string;
    stare: string;
    caen_principal: string;
    has_debts: boolean;
    has_insolvency: boolean;
    added_at: string | null;
}


interface FraudWidget {
    companies_with_debts: number;
    companies_with_insolvency: number;
    companies_with_litigation: number;
}

interface ExchangeRatesWidget {
    date: string | null;
    rates: { currency: string; rate_ron: number }[];
}

interface ContractsWidget {
    total_contracts: number;
    total_value: number;
    recent_contracts: number;
    recent_value: number;
    period: string;
}


const ACTIVITY_TREND = [
    { zi: "Lun", companii: 12, alerte: 5, facturi: 3 },
    { zi: "Mar", companii: 18, alerte: 8, facturi: 6 },
    { zi: "Mie", companii: 15, alerte: 3, facturi: 4 },
    { zi: "Joi", companii: 22, alerte: 11, facturi: 8 },
    { zi: "Vin", companii: 19, alerte: 7, facturi: 5 },
    { zi: "Sâm", companii: 8, alerte: 2, facturi: 1 },
    { zi: "Dum", companii: 5, alerte: 1, facturi: 0 },
];

const MONTHLY_REVENUE = [
    { luna: "Oct", valoare: 145000 },
    { luna: "Nov", valoare: 162000 },
    { luna: "Dec", valoare: 138000 },
    { luna: "Ian", valoare: 178000 },
    { luna: "Feb", valoare: 195000 },
    { luna: "Mar", valoare: 212000 },
];

const QUICK_MODULES = [
    { path: "/search", label: "Căutare Firme", icon: Search, color: "from-blue-500 to-indigo-600", desc: "Caută după CUI, denumire" },
    { path: "/alerts", label: "Alerte", icon: Bell, color: "from-red-500 to-rose-600", desc: "43 necitite" },
    { path: "/fraud", label: "Fraud Graph", icon: Shield, color: "from-orange-500 to-amber-600", desc: "Rețele suspecte" },
    { path: "/portfolios", label: "Portofolii", icon: Briefcase, color: "from-violet-500 to-purple-600", desc: "Monitorizare firme" },
    { path: "/facturi-furnizori", label: "Facturi Furnizori", icon: ReceiptText, color: "from-emerald-500 to-teal-600", desc: "42 facturi active" },
    { path: "/ai", label: "AI Agent", icon: Bot, color: "from-cyan-500 to-blue-600", desc: "Asistent inteligent" },
    { path: "/crm", label: "Date CRM", icon: Sparkles, color: "from-pink-500 to-rose-600", desc: "Vânzări & clienți" },
    { path: "/my-esg", label: "Datele mele ESG", icon: Leaf, color: "from-green-500 to-emerald-600", desc: "Scor ESG 72%" },
];

const FACTURI_SCADENTE = [
    { furnizor: "MEGA DISTRIBUTION SRL", numar: "FRN-20260035", suma: 8420.50, zile: 3 },
    { furnizor: "TECH SUPPLIES SA", numar: "FRN-20260033", suma: 15200.00, zile: 5 },
    { furnizor: "GLOBAL LOGISTICS SA", numar: "FRN-20260036", suma: 4890.75, zile: 7 },
    { furnizor: "ENERGY PRO SA", numar: "FRN-20260037", suma: 22100.00, zile: 12 },
];

export default function DashboardPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const dark = useThemeStore((s) => s.dark);
    const [wsConnected, setWsConnected] = useState(false);
    const chartGrid = dark ? "#334155" : "#e2e8f0";
    const chartTick = { fontSize: 12, fontFamily: "Rajdhani", fill: dark ? "#94a3b8" : "#475569" };
    const chartTooltip = { borderRadius: 12, fontFamily: "Exo 2", fontSize: 13, border: `1px solid ${dark ? "#334155" : "#e2e8f0"}`, backgroundColor: dark ? "#1e293b" : "#ffffff", color: dark ? "#e2e8f0" : "#1e293b" };
    const [liveAlerts, setLiveAlerts] = useState<{ id: number; tip_alerta: string; titlu: string; created_at: string }[]>([]);

    // Watchlist
    const { data: watchlist, isLoading: watchlistLoading } = useQuery({
        queryKey: ["watchlist"],
        queryFn: async () => (await api.get("/watch")).data,
    });

    // Recent alerts (for sidebar)
    const { data: stats } = useQuery({
        queryKey: ["dashboard-alerts"],
        queryFn: async () => (await api.get("/dashboard/stats", { params: { period: "7d" } })).data,
    });

    // Global widgets
    const { data: fraudWidget } = useQuery<FraudWidget>({
        queryKey: ["dashboard-fraud"],
        queryFn: async () => (await api.get("/dashboard/widgets/fraud")).data,
    });

    const { data: ratesWidget } = useQuery<ExchangeRatesWidget>({
        queryKey: ["dashboard-rates"],
        queryFn: async () => (await api.get("/dashboard/widgets/exchange-rates")).data,
    });

    const { data: contractsWidget } = useQuery<ContractsWidget>({
        queryKey: ["dashboard-contracts"],
        queryFn: async () => (await api.get("/dashboard/widgets/contracts", { params: { period: "30d" } })).data,
    });

    // WebSocket real-time alerts
    useEffect(() => {
        wsClient.connect();
        setWsConnected(true);

        const unsubscribe = wsClient.onAlert((alert) => {
            setLiveAlerts((prev) => [
                { id: Date.now(), tip_alerta: alert.tip_alerta, titlu: alert.titlu, created_at: new Date().toISOString() },
                ...prev.slice(0, 4),
            ]);
        });

        return () => unsubscribe();
    }, []);

    // Unwatch mutation
    const unwatchMutation = useMutation({
        mutationFn: async (cui: number) => api.delete(`/watch/${cui}`),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
    });

    const companies: WatchedCompany[] = watchlist?.companies || [];
    const kpiTotal = companies.length;
    const kpiActive = companies.filter((c) => c.stare === "ACTIVA").length;
    const kpiDebts = companies.filter((c) => c.has_debts).length;
    const kpiInsolvent = companies.filter((c) => c.has_insolvency).length;

    const statusData = useMemo(() => {
        const map: Record<string, number> = {};
        companies.forEach((c) => { map[c.stare] = (map[c.stare] || 0) + 1; });
        return Object.entries(map).map(([name, value]) => ({ name, value }));
    }, [companies]);
    const STATUS_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#64748b"];

    const allAlerts = [
        ...liveAlerts,
        ...((stats?.recent_alerts || []) as { id: number; tip_alerta: string; titlu: string; created_at: string }[]).filter(
            (a) => !liveAlerts.some((la) => la.id === a.id)
        ),
    ].slice(0, 6);

    if (watchlistLoading) {
        return (
            <div className="flex h-64 items-center justify-center">
                <div className="relative">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                    <Orbit className="absolute inset-0 m-auto h-5 w-5 text-nebula-400 animate-pulse" />
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Page header */}
            <div className="section-header flex items-center justify-between">
                <div>
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                        Command Center
                    </h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Watchlist personal — companiile tale monitorizate
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5" title={wsConnected ? "Live" : "Offline"}>
                        {wsConnected ? (
                            <Wifi className="h-4 w-4 text-emerald-500" />
                        ) : (
                            <WifiOff className="h-4 w-4 text-slate-400" />
                        )}
                        <span className="text-xs text-slate-400">
                            {wsConnected ? "Live" : "Offline"}
                        </span>
                    </div>
                    <button
                        onClick={() => navigate("/search")}
                        className="btn-cosmic flex items-center gap-2 px-4 py-2 text-sm"
                    >
                        <Plus className="h-4 w-4" /> Adaugă Companie
                    </button>
                </div>
            </div>

            {/* KPI Cards — watchlist stats + empty state */}
            {companies.length === 0 ? (
                <div className="card-cosmic flex flex-col items-center justify-center py-16 text-center">
                    <Star className="h-14 w-14 text-slate-200 dark:text-slate-700 mb-4" />
                    <h3 className="font-orbitron text-lg font-bold text-slate-400 mb-2">Nicio companie urmărită</h3>
                    <p className="font-exo text-sm text-slate-400 max-w-sm mb-5">
                        Adaugă companii la watchlist din pagina de Căutare apăsând iconița{" "}
                        <Eye className="inline h-4 w-4 text-nebula-400" /> de lângă fiecare firmă.
                    </p>
                    <button onClick={() => navigate("/search")} className="btn-cosmic flex items-center gap-2 px-6 py-2.5">
                        <Search className="h-4 w-4" /> Caută Companii
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <KPICard
                        title="Companii Urmărite"
                        value={String(kpiTotal)}
                        icon={<Eye className="h-5 w-5" />}
                        gradient="from-nebula-500 to-cosmos-500"
                        iconBg="bg-nebula-100"
                        iconColor="text-nebula-600"
                        borderColor="border-nebula-100"
                    />
                    <KPICard
                        title="Active"
                        value={String(kpiActive)}
                        icon={<Activity className="h-5 w-5" />}
                        gradient="from-emerald-400 to-cosmos-400"
                        iconBg="bg-emerald-100"
                        iconColor="text-emerald-600"
                        borderColor="border-emerald-100"
                    />
                    <KPICard
                        title="Cu Datorii"
                        value={String(kpiDebts)}
                        icon={<AlertTriangle className="h-5 w-5" />}
                        gradient="from-dragon-fire to-stardust-500"
                        iconBg="bg-dragon-100"
                        iconColor="text-dragon-600"
                        borderColor="border-dragon-100"
                    />
                    <KPICard
                        title="Insolvente"
                        value={String(kpiInsolvent)}
                        icon={<Flame className="h-5 w-5" />}
                        gradient="from-dragon-blood to-dragon-500"
                        iconBg="bg-red-100"
                        iconColor="text-red-600"
                        borderColor="border-red-100"
                    />
                </div>
            )}

            {/* ─── Quick Access Modules ─── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
                {QUICK_MODULES.map((m) => {
                    const Icon = m.icon;
                    return (
                        <Link
                            key={m.path}
                            to={m.path}
                            className="group card-cosmic flex flex-col items-center gap-2 py-4 px-2 text-center hover:shadow-lg transition-all hover:-translate-y-0.5"
                        >
                            <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-md transition-transform group-hover:scale-110", m.color)}>
                                <Icon className="h-4 w-4" />
                            </div>
                            <span className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">{m.label}</span>
                            <span className="font-exo text-[10px] text-slate-400">{m.desc}</span>
                        </Link>
                    );
                })}
            </div>

            {/* 10.2: New Widgets Row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* Watchlist status distribution */}
                <div className="card-cosmic">
                    <div className="flex items-center gap-2 mb-3">
                        <Eye className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Status Watchlist
                        </h3>
                    </div>
                    {companies.length > 0 ? (
                        <div className="space-y-1.5 text-sm">
                            {statusData.map((s, i) => (
                                <div key={s.name} className="flex justify-between items-center">
                                    <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: STATUS_COLORS[i % STATUS_COLORS.length] }} />
                                        {s.name}
                                    </span>
                                    <span className="font-semibold" style={{ color: STATUS_COLORS[i % STATUS_COLORS.length] }}>{s.value}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">Nicio companie urmărită</p>
                    )}
                </div>

                {/* Fraud/Risk Summary */}
                <div className="card-cosmic">
                    <div className="flex items-center gap-2 mb-3">
                        <Shield className="h-4 w-4 text-red-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Riscuri Active
                        </h3>
                    </div>
                    {fraudWidget ? (
                        <div className="space-y-1.5 text-sm">
                            <div className="flex justify-between">
                                <span className="text-slate-500 dark:text-slate-400">Datorii</span>
                                <span className="font-semibold text-amber-500">{fraudWidget.companies_with_debts}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500 dark:text-slate-400">Insolvențe</span>
                                <span className="font-semibold text-red-500">{fraudWidget.companies_with_insolvency}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500 dark:text-slate-400">Litigii</span>
                                <span className="font-semibold text-orange-500">{fraudWidget.companies_with_litigation}</span>
                            </div>
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">Se încarcă...</p>
                    )}
                </div>

                {/* Exchange Rates */}
                <div className="card-cosmic">
                    <div className="flex items-center gap-2 mb-3">
                        <Banknote className="h-4 w-4 text-cosmos-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Curs BNR
                        </h3>
                    </div>
                    {ratesWidget?.rates?.length ? (
                        <div className="space-y-1.5 text-sm">
                            {ratesWidget.rates
                                .filter((r) => ["EUR", "USD", "GBP", "CHF"].includes(r.currency))
                                .map((r) => (
                                    <div key={r.currency} className="flex justify-between">
                                        <span className="text-slate-500 dark:text-slate-400">{r.currency}</span>
                                        <span className="font-mono font-semibold text-slate-700 dark:text-slate-200">
                                            {r.rate_ron.toFixed(4)}
                                        </span>
                                    </div>
                                ))}
                            {ratesWidget.date && (
                                <p className="mt-1 text-[10px] text-slate-400">Data: {ratesWidget.date}</p>
                            )}
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">Indisponibil</p>
                    )}
                </div>

                {/* Contracts Summary */}
                <div className="card-cosmic">
                    <div className="flex items-center gap-2 mb-3">
                        <FileText className="h-4 w-4 text-blue-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Contracte Publice
                        </h3>
                    </div>
                    {contractsWidget ? (
                        <div className="space-y-1.5 text-sm">
                            <div className="flex justify-between">
                                <span className="text-slate-500 dark:text-slate-400">Total</span>
                                <span className="font-semibold text-slate-700 dark:text-slate-200">{formatNumber(contractsWidget.total_contracts)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500 dark:text-slate-400">Recente</span>
                                <span className="font-semibold text-blue-500">{formatNumber(contractsWidget.recent_contracts)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500 dark:text-slate-400">Valoare recentă</span>
                                <span className="font-mono text-xs font-semibold text-emerald-500">
                                    {formatNumber(Math.round(contractsWidget.recent_value))} RON
                                </span>
                            </div>
                        </div>
                    ) : (
                        <p className="text-xs text-slate-400">Se încarcă...</p>
                    )}
                </div>
            </div>

            {/* ─── Activity Trend + Revenue ─── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Activity trend (area) */}
                <div className="card-cosmic lg:col-span-2">
                    <div className="flex items-center gap-2 mb-5">
                        <Activity className="h-5 w-5 text-blue-500" />
                        <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
                            Activitate Săptămânală
                        </h3>
                    </div>
                    <ResponsiveContainer width="100%" height={240}>
                        <AreaChart data={ACTIVITY_TREND}>
                            <defs>
                                <linearGradient id="gradComp" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="gradAlert" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="gradFact" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                            <XAxis dataKey="zi" tick={chartTick} />
                            <YAxis tick={chartTick} />
                            <Tooltip contentStyle={chartTooltip} />
                            <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12, color: dark ? "#94a3b8" : "#475569" }} />
                            <Area type="monotone" dataKey="companii" stroke="#6366f1" strokeWidth={2} fill="url(#gradComp)" name="Companii vizitate" />
                            <Area type="monotone" dataKey="alerte" stroke="#ef4444" strokeWidth={2} fill="url(#gradAlert)" name="Alerte" />
                            <Area type="monotone" dataKey="facturi" stroke="#10b981" strokeWidth={2} fill="url(#gradFact)" name="Facturi" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Monthly revenue line */}
                <div className="card-cosmic">
                    <div className="flex items-center gap-2 mb-5">
                        <TrendingUp className="h-5 w-5 text-emerald-500" />
                        <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
                            Valoare Facturi
                        </h3>
                    </div>
                    <ResponsiveContainer width="100%" height={240}>
                        <LineChart data={MONTHLY_REVENUE}>
                            <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
                            <XAxis dataKey="luna" tick={chartTick} />
                            <YAxis tick={{ ...chartTick, fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                            <Tooltip contentStyle={chartTooltip} formatter={(v: number) => `${v.toLocaleString("ro-RO")} RON`} />
                            <Line type="monotone" dataKey="valoare" stroke="#10b981" strokeWidth={2.5} dot={{ fill: "#10b981", r: 4 }} name="Valoare (RON)" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* ─── Watchlist Companies ─── */}
            {companies.length > 0 && (
                <div className="card-cosmic">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Eye className="h-5 w-5 text-nebula-500" />
                            <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
                                Companii urmărite ({companies.length})
                            </h3>
                        </div>
                        <Link
                            to="/search"
                            className="flex items-center gap-1 font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:text-nebula-700 transition-colors"
                        >
                            Adaugă <ChevronRight className="h-3 w-3" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {companies.map((c) => (
                            <div
                                key={c.cui}
                                className="group flex items-center gap-3 rounded-xl border border-slate-100 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/50 p-3 transition-all hover:border-nebula-200 dark:hover:border-nebula-700/50 hover:shadow-sm cursor-pointer"
                                onClick={() => navigate(`/company/${c.cui}`)}
                            >
                                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-nebula-50 dark:bg-nebula-900/30 text-nebula-400">
                                    <Building2 className="h-5 w-5" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="font-exo font-semibold text-slate-700 dark:text-slate-200 truncate text-sm">{c.denumire}</p>
                                    <p className="font-rajdhani text-xs text-slate-400">CUI: {c.cui} · {c.judet}</p>
                                </div>
                                <div className="flex shrink-0 items-center gap-1.5">
                                    <span className={cn(
                                        "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                                        c.stare === "ACTIVA" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-600"
                                    )}>
                                        {c.stare}
                                    </span>
                                    {c.has_debts && (
                                        <span title="Datorii" className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-100 text-amber-600">
                                            <AlertTriangle className="h-2.5 w-2.5" />
                                        </span>
                                    )}
                                    <button
                                        onClick={(e) => { e.stopPropagation(); unwatchMutation.mutate(c.cui); }}
                                        title="Scoate din watchlist"
                                        className="flex h-6 w-6 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-600 text-slate-300 opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 transition-all"
                                    >
                                        <EyeOff className="h-3 w-3" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ─── Facturi Scadente + Alerts side by side ─── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Facturi scadente */}
                <div className="card-cosmic">
                    <div className="mb-5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <ReceiptText className="h-5 w-5 text-amber-500" />
                            <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
                                Facturi Scadente
                            </h3>
                            <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-amber-100 px-1.5 text-[10px] font-bold text-amber-700">
                                {FACTURI_SCADENTE.length}
                            </span>
                        </div>
                        <Link
                            to="/facturi-furnizori"
                            className="flex items-center gap-1 font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:text-nebula-700 transition-colors"
                        >
                            Toate <ChevronRight className="h-3 w-3" />
                        </Link>
                    </div>
                    <div className="space-y-3">
                        {FACTURI_SCADENTE.map((f) => (
                            <div key={f.numar} className="flex items-center gap-3 rounded-xl border border-slate-100 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/50 p-3 transition-all hover:border-amber-200 dark:hover:border-amber-700/50 hover:shadow-sm">
                                <div className={cn(
                                    "flex h-9 w-9 items-center justify-center rounded-lg flex-shrink-0",
                                    f.zile <= 3 ? "bg-red-50 text-red-500" : f.zile <= 7 ? "bg-amber-50 text-amber-500" : "bg-slate-50 text-slate-400"
                                )}>
                                    <Clock className="h-4 w-4" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-exo text-sm font-medium text-slate-700 dark:text-slate-200 truncate">{f.furnizor}</p>
                                    <p className="font-rajdhani text-[11px] text-slate-400">{f.numar} · scadent în {f.zile} zile</p>
                                </div>
                                <span className={cn(
                                    "font-orbitron text-sm font-bold",
                                    f.zile <= 3 ? "text-red-600" : f.zile <= 7 ? "text-amber-600" : "text-slate-600"
                                )}>
                                    {f.suma.toLocaleString("ro-RO", { minimumFractionDigits: 2 })}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Recent Alerts */}
                <div className="card-cosmic">
                    <div className="mb-5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Bell className="h-5 w-5 text-dragon-500" />
                            <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
                                Alerte Recente
                            </h3>
                            {liveAlerts.length > 0 && (
                                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white animate-pulse">
                                    {liveAlerts.length}
                                </span>
                            )}
                        </div>
                        <Link
                            to="/alerts"
                            className="flex items-center gap-1 font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:text-nebula-700 transition-colors"
                        >
                            Toate <ChevronRight className="h-3 w-3" />
                        </Link>
                    </div>
                    <div className="space-y-3">
                        {allAlerts.slice(0, 5).map((alert) => (
                            <div
                                key={alert.id}
                                className="group flex items-start gap-3 rounded-xl border border-slate-100 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/50 p-3 transition-all hover:border-dragon-200 dark:hover:border-red-700/50 hover:shadow-sm"
                            >
                                <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-dragon-50 text-dragon-500 transition-colors group-hover:bg-dragon-100">
                                    <Bell className="h-4 w-4" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="font-exo text-sm font-semibold text-slate-700 dark:text-slate-200">{alert.tip_alerta}</p>
                                    <p className="truncate font-exo text-sm text-slate-400">{alert.titlu}</p>
                                </div>
                            </div>
                        ))}
                        {allAlerts.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-8 text-slate-300">
                                <Orbit className="h-10 w-10 mb-2 animate-[orbit-spin_8s_linear_infinite]" />
                                <p className="font-rajdhani text-sm">Nicio alertă recentă</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

function KPICard({
    title,
    value,
    icon,
    gradient,
    iconBg,
    iconColor,
    borderColor,
}: {
    title: string;
    value: string;
    icon: React.ReactNode;
    gradient: string;
    iconBg: string;
    iconColor: string;
    borderColor: string;
}) {
    return (
        <div className={`card-cosmic group relative overflow-hidden border ${borderColor}`}>
            {/* Subtle gradient top line */}
            <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${gradient} opacity-60`} />
            <div className="flex items-center justify-between">
                <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">{title}</p>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg} ${iconColor} transition-transform group-hover:scale-110`}>
                    {icon}
                </div>
            </div>
            <p className="mt-3 font-orbitron text-3xl font-bold text-slate-800 dark:text-white">{value}</p>
        </div>
    );
}
