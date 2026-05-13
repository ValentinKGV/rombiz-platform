import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import {
    DollarSign,
    Users,
    FileText,
    CheckCircle2,
    Gift,
    UserPlus,
    XCircle,
    UserMinus,
    Clock,
    Timer,
    TrendingUp,
    Percent,
    Loader2,
    Send,
    MessageSquare,
    Handshake,
    ShieldX,
    BadgeCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Types ───────────────────────────────────────────────────── */
interface CrmStats {
    totalVanzari: number;
    totalClienti: number;
    totalFacturat: number;
    totalIncasat: number;
    valoareOferte: number;
    potentialiClienti: number;
    totalOfertepierdute: number;
    totalClientiPierduti: number;
    restDeIncasat: number;
    durataMedieIncasare: number;
    durataMedieVanzare: number;
    rataConversie: number;
    valoareContracte: number;
    nrContracte: number;
}

interface ContractItem {
    id: number;
    client: string;
    valoareOferta: number;
    valoareContract: number;
    dataInchidere: string | null;
    serviciu: string | null;
    numarContract: string | null;
}

interface ContracteResponse {
    valoareContracte: number;
    nrContracte: number;
    items: ContractItem[];
}

interface PipelineItem {
    status: string;
    count: number;
    valoare: number;
}

interface StatCard {
    label: string;
    value: string;
    icon: React.ElementType;
    accent: "green" | "blue" | "orange" | "pink" | "purple" | "red";
    valueColor?: string;
}

const fmt = (v: number) =>
    v.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function buildCards(s: CrmStats) {
    const row1: StatCard[] = [
        { label: "Total Vânzări", value: fmt(s.totalVanzari), icon: DollarSign, accent: "green" },
        { label: "Total Clienți", value: String(Math.round(s.totalClienti)), icon: Users, accent: "blue" },
        { label: "Total Facturat", value: fmt(s.totalFacturat), icon: FileText, accent: "green" },
        { label: "Total Încasat", value: fmt(s.totalIncasat), icon: CheckCircle2, accent: "blue" },
    ];
    const row2: StatCard[] = [
        { label: "Valoare Oferte", value: fmt(s.valoareOferte), icon: Gift, accent: "orange" },
        { label: "Potențiali Clienți", value: String(Math.round(s.potentialiClienti)), icon: UserPlus, accent: "orange" },
        { label: "Total Oferte Pierdute", value: fmt(s.totalOfertepierdute), icon: XCircle, accent: "pink", valueColor: "text-red-500" },
        { label: "Total Clienți Pierduți", value: String(Math.round(s.totalClientiPierduti)), icon: UserMinus, accent: "pink", valueColor: "text-red-500" },
    ];
    const row3: StatCard[] = [
        { label: "Rest de Încasat", value: fmt(s.restDeIncasat), icon: Clock, accent: "purple" },
        { label: "Durată Medie Încasare", value: `${s.durataMedieIncasare.toFixed(1)} zile`, icon: Timer, accent: "purple" },
        { label: "Durată Medie Vânzare", value: `${s.durataMedieVanzare.toFixed(1)} zile`, icon: TrendingUp, accent: "purple" },
        { label: "Rată Conversie", value: `${s.rataConversie}%`, icon: Percent, accent: "purple" },
    ];
    return { row1, row2, row3 };
}

/* ── Accent maps ─────────────────────────────────────────────── */
const borderMap: Record<string, string> = {
    green: "border-t-emerald-400",
    blue: "border-t-blue-400",
    orange: "border-t-amber-400",
    pink: "border-t-rose-400",
    purple: "border-t-violet-400",
    red: "border-t-red-400",
};

const iconBgMap: Record<string, string> = {
    green: "bg-emerald-50 text-emerald-500",
    blue: "bg-blue-50 text-blue-500",
    orange: "bg-amber-50 text-amber-500",
    pink: "bg-rose-50 text-rose-500",
    purple: "bg-violet-50 text-violet-500",
    red: "bg-red-50 text-red-500",
};

/* ── StatCard Component ──────────────────────────────────────── */
function CrmStatCard({ card }: { card: StatCard }) {
    const Icon = card.icon;
    return (
        <div
            className={cn(
                "relative rounded-xl border border-slate-200/60 border-t-4 bg-white p-3 sm:p-4 shadow-sm transition-shadow hover:shadow-md dark:border-slate-700/60 dark:bg-slate-800",
                borderMap[card.accent]
            )}
        >
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 space-y-1.5">
                    <p className="text-xs font-medium leading-tight text-slate-500 dark:text-slate-400">{card.label}</p>
                    <p className={cn("truncate text-base font-bold sm:text-lg xl:text-xl text-slate-800 dark:text-slate-100", card.valueColor)}>
                        {card.value}
                    </p>
                </div>
                <div className={cn("flex-shrink-0 rounded-xl p-2", iconBgMap[card.accent])}>
                    <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
                </div>
            </div>
        </div>
    );
}

/* ── Contracte Widget ────────────────────────────────────────── */
const periodMap = {
    "Zi": "zi",
    "Săptămână": "saptamana",
    "Lună": "luna",
    "An": "an",
} as const;
const periods = Object.keys(periodMap) as (keyof typeof periodMap)[];

function ContracteWidget() {
    const [period, setPeriod] = useState<keyof typeof periodMap>("Lună");

    const { data } = useQuery<ContracteResponse>({
        queryKey: ["crm-contracte", period],
        queryFn: async () => (await api.get("/crm/contracte", { params: { period: periodMap[period] } })).data,
        staleTime: 120_000,
    });

    // Build chart data from contract items (aggregate by date)
    const chartData = useMemo(() => {
        if (!data?.items?.length) return [];
        const byDate: Record<string, number> = {};
        for (const c of data.items) {
            const key = c.dataInchidere ?? "N/A";
            byDate[key] = (byDate[key] || 0) + c.valoareContract;
        }
        return Object.entries(byDate)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([date, val]) => ({ date: date.slice(5), valoare: val }));
    }, [data?.items]);

    return (
        <div className="flex h-full flex-col rounded-xl border border-slate-200/60 bg-white shadow-sm dark:border-slate-700/60 dark:bg-slate-800 overflow-hidden">
            <div className="p-6 pb-3 text-center">
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Valoare Contracte</h3>
                <p className="mt-2 text-4xl font-bold text-cyan-500">{fmt(data?.valoareContracte ?? 0)}</p>
                <p className="mt-1 text-sm text-slate-400">{data?.nrContracte ?? 0} contracte</p>

                {/* Period selector */}
                <div className="mt-4 flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-700">
                    {periods.map((p) => (
                        <button
                            key={p}
                            onClick={() => setPeriod(p)}
                            className={cn(
                                "flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                                period === p
                                    ? "bg-blue-500 text-white shadow-sm"
                                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400"
                            )}
                        >
                            {p}
                        </button>
                    ))}
                </div>
            </div>

            {/* Area chart at bottom */}
            <div className="mt-auto flex-1 min-h-[120px]">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="contractGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.35} />
                                <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.02} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="date" hide />
                        <Tooltip
                            formatter={(v: number) => [fmt(v) + " RON", "Valoare"]}
                            contentStyle={{ borderRadius: 8, fontSize: 12, border: "1px solid #e2e8f0" }}
                        />
                        <Area
                            type="monotone"
                            dataKey="valoare"
                            stroke="#06b6d4"
                            strokeWidth={2}
                            fill="url(#contractGrad)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

/* ── Pipeline Widget ─────────────────────────────────────────── */
const pipelineConfig: Record<string, { label: string; icon: React.ElementType; gradient: string; border: string; iconBg: string; badge: string }> = {
    oferta_serviciu: { label: "Ofertă Serviciu", icon: Send, gradient: "from-amber-500/10 to-amber-500/5", border: "border-l-amber-400", iconBg: "bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400", badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" },
    in_discutie: { label: "În Discuție", icon: MessageSquare, gradient: "from-sky-500/10 to-sky-500/5", border: "border-l-sky-400", iconBg: "bg-sky-100 text-sky-600 dark:bg-sky-900/40 dark:text-sky-400", badge: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300" },
    in_negociere: { label: "În Negociere", icon: Handshake, gradient: "from-blue-500/10 to-blue-500/5", border: "border-l-blue-400", iconBg: "bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400", badge: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
    contract: { label: "Contract", icon: BadgeCheck, gradient: "from-emerald-500/10 to-emerald-500/5", border: "border-l-emerald-400", iconBg: "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/40 dark:text-emerald-400", badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" },
    client_pierdut: { label: "Client Pierdut", icon: ShieldX, gradient: "from-red-500/10 to-red-500/5", border: "border-l-red-400", iconBg: "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400", badge: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
};

function PipelineWidget() {
    const { data } = useQuery<{ pipeline: PipelineItem[] }>({
        queryKey: ["crm-pipeline"],
        queryFn: async () => (await api.get("/crm/pipeline")).data,
        staleTime: 120_000,
    });

    const items = data?.pipeline ?? [];
    const totalCount = items.reduce((s, i) => s + i.count, 0) || 1;
    // Sort: funnel order
    const order = ["oferta_serviciu", "in_discutie", "in_negociere", "contract", "client_pierdut"];
    const sorted = [...items].sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status));

    return (
        <div className="rounded-xl border border-slate-200/60 bg-white p-6 shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
            <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Pipeline Vânzări</h3>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {totalCount} lead-uri
                </span>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
                {sorted.map((item) => {
                    const cfg = pipelineConfig[item.status];
                    if (!cfg) return null;
                    const Icon = cfg.icon;
                    const pct = Math.round((item.count / totalCount) * 100);
                    return (
                        <div
                            key={item.status}
                            className={cn(
                                "relative rounded-xl border-l-4 bg-gradient-to-br p-4 transition-shadow hover:shadow-md dark:border-slate-700/60",
                                cfg.border,
                                cfg.gradient
                            )}
                        >
                            <div className="flex items-center gap-2 mb-3">
                                <div className={cn("rounded-lg p-1.5", cfg.iconBg)}>
                                    <Icon className="h-4 w-4" />
                                </div>
                                <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold", cfg.badge)}>
                                    {pct}%
                                </span>
                            </div>
                            <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{item.count}</p>
                            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mt-0.5">{cfg.label}</p>
                            <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">{fmt(item.valoare)} RON</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Main Page ───────────────────────────────────────────────── */
export default function CRMDataPage() {
    const { data: stats, isLoading } = useQuery<CrmStats>({
        queryKey: ["crm-stats"],
        queryFn: async () => (await api.get("/crm/stats")).data,
        staleTime: 120_000,
    });

    if (isLoading || !stats) {
        return (
            <div className="flex items-center justify-center py-32">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    const { row1, row2, row3 } = buildCards(stats);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="section-header">
                <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                    Date CRM
                </h1>
                <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                    Date live din ATH | CRM — vânzări, clienți, pipeline
                </p>
            </div>

            {/* Grid: 3 rows of cards + side widget */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_320px] xl:items-stretch">
                {/* Left: stat cards */}
                <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-4">
                        {row1.map((c) => <CrmStatCard key={c.label} card={c} />)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-4">
                        {row2.map((c) => <CrmStatCard key={c.label} card={c} />)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-4">
                        {row3.map((c) => <CrmStatCard key={c.label} card={c} />)}
                    </div>
                </div>

                {/* Right: Contracte widget — matches card rows height */}
                <ContracteWidget />
            </div>

            {/* Pipeline widget */}
            <PipelineWidget />
        </div>
    );
}
