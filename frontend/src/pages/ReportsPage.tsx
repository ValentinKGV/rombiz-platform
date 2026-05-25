import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { ReportExport } from "@/types";
import { formatDateTime } from "@/lib/utils";
import {
    CheckCircle, Clock, Download, FileText, Orbit, XCircle,
    BarChart3, TrendingUp, FileSpreadsheet, Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import {
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";

/* ───── Demo Data ───── */
const DEMO_EXPORTS: ReportExport[] = [
    { id: "1", export_type: "Due Diligence", format: "PDF", status: "completed", created_at: "2026-03-27T10:15:00Z", file_url: "#" },
    { id: "2", export_type: "Raport Financiar", format: "Excel", status: "completed", created_at: "2026-03-26T14:30:00Z", file_url: "#" },
    { id: "3", export_type: "Analiză ESG", format: "PDF", status: "processing", created_at: "2026-03-27T11:45:00Z", file_url: null },
    { id: "5", export_type: "Portofoliu Export", format: "Excel", status: "completed", created_at: "2026-03-24T16:00:00Z", file_url: "#" },
    { id: "6", export_type: "Monitorizare SEAP", format: "PDF", status: "failed", created_at: "2026-03-23T08:10:00Z", file_url: null },
    { id: "7", export_type: "Raport Companie", format: "PDF", status: "completed", created_at: "2026-03-22T12:30:00Z", file_url: "#" },
    { id: "8", export_type: "Supply Chain", format: "Excel", status: "completed", created_at: "2026-03-21T15:45:00Z", file_url: "#" },
] as any;

const DEMO_MONTHLY = [
    { month: "Oct", count: 12 }, { month: "Nov", count: 18 },
    { month: "Dec", count: 15 }, { month: "Ian", count: 22 },
    { month: "Feb", count: 28 }, { month: "Mar", count: 34 },
];

const DEMO_BY_TYPE = [
    { name: "Due Diligence", value: 28, color: "#6366f1" },
    { name: "Raport Financiar", value: 22, color: "#10b981" },
    { name: "Analiză ESG", value: 15, color: "#f59e0b" },
    { name: "Altele", value: 35, color: "#8b5cf6" },
];

const DEMO_BY_FORMAT = [
    { name: "PDF", value: 65, color: "#ef4444" },
    { name: "Excel", value: 35, color: "#10b981" },
];

const W = "border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm";

const fadeUp = {
    hidden: { opacity: 0, y: 16 },
    visible: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.4, ease: "easeOut" as const } }),
};

export default function ReportsPage() {
    const { data: rawExports, isLoading } = useQuery<ReportExport[]>({
        queryKey: ["reports", "exports"],
        queryFn: async () => {
            const { data } = await api.get("/reports/exports");
            return data.items || data;
        },
        refetchInterval: 5000,
    });

    const exports = rawExports && rawExports.length > 0 ? rawExports : DEMO_EXPORTS;

    const completedCount = exports.filter((r) => r.status === "completed").length;
    const processingCount = exports.filter((r) => r.status === "processing").length;
    const failedCount = exports.filter((r) => r.status === "failed").length;

    const statusIcon = (status: string) => {
        switch (status) {
            case "processing":
                return <Clock className="h-4 w-4 animate-spin text-yellow-500" />;
            case "completed":
                return <CheckCircle className="h-4 w-4 text-green-500" />;
            case "failed":
                return <XCircle className="h-4 w-4 text-red-500" />;
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen -m-6 p-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(236,72,153,0.04) 0%, transparent 50%)' }}>

            {/* ── Hero Banner ── */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950 to-violet-950 p-6 shadow-2xl lg:p-8"
            >
                <div className="pointer-events-none absolute inset-0 opacity-30"
                    style={{ backgroundImage: "radial-gradient(circle at 15% 50%, rgba(99,102,241,0.35) 0%, transparent 50%), radial-gradient(circle at 85% 20%, rgba(139,92,246,0.3) 0%, transparent 50%), radial-gradient(circle at 50% 80%, rgba(16,185,129,0.2) 0%, transparent 50%)" }}
                />
                <div className="pointer-events-none absolute inset-0 opacity-[0.04]"
                    style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)", backgroundSize: "40px 40px" }}
                />
                <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-sm">
                            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                            <span className="font-rajdhani text-[11px] font-semibold uppercase tracking-[0.15em] text-white/70">Export Center</span>
                        </div>
                        <h1 className="mt-3 font-orbitron text-2xl font-bold tracking-wide text-white lg:text-3xl">Rapoarte</h1>
                        <p className="mt-2 max-w-lg font-rajdhani text-sm leading-relaxed text-white/50">
                            Rapoarte generate (PDF/Excel) și exporturi. Descarcă rapoartele finalizate sau monitorizează statusul celor în lucru.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-green-400 text-white shadow-lg shadow-emerald-500/25">
                                <FileText className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Total Rapoarte</p>
                                <p className="font-orbitron text-lg font-bold text-white">{exports.length}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-purple-400 text-white shadow-lg shadow-violet-500/25">
                                <CheckCircle className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Finalizate</p>
                                <p className="font-orbitron text-lg font-bold text-white">{completedCount}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* ── KPI Row ── */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                    { icon: <FileText className="h-5 w-5" />, iconBg: "from-indigo-500 to-violet-400", label: "Total Rapoarte", value: exports.length, sub: "rapoarte generate" },
                    { icon: <CheckCircle className="h-5 w-5" />, iconBg: "from-emerald-500 to-green-400", label: "Finalizate", value: completedCount, sub: "descărcabile" },
                    { icon: <Clock className="h-5 w-5" />, iconBg: "from-amber-500 to-orange-400", label: "În Procesare", value: processingCount, sub: "în curs de generare" },
                    { icon: <XCircle className="h-5 w-5" />, iconBg: "from-red-500 to-pink-400", label: "Eșuate", value: failedCount, sub: "necesită regenerare" },
                ].map((kpi, i) => (
                    <motion.div
                        key={kpi.label}
                        initial={{ opacity: 0, y: 14 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: i * 0.08 }}
                        className={cn("group relative overflow-hidden rounded-2xl bg-white/70 p-5 hover:shadow-xl hover:border-indigo-200 transition-all duration-300 hover:-translate-y-0.5", W)}
                    >
                        <div className="flex items-center gap-4">
                            <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-md transition-transform group-hover:scale-110", kpi.iconBg)}>
                                {kpi.icon}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">{kpi.label}</p>
                                <p className="font-orbitron text-2xl font-black text-slate-800">{kpi.value}</p>
                            </div>
                        </div>
                        <div className="mt-3"><span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">{kpi.sub}</span></div>
                    </motion.div>
                ))}
            </div>

            {/* ── Charts Row ── */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                {/* Monthly trend */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70 lg:col-span-1", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-400 text-white shadow-md">
                            <TrendingUp className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Rapoarte / Lună</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={240}>
                            <AreaChart data={DEMO_MONTHLY}>
                                <defs>
                                    <linearGradient id="reportTrendFill" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }} formatter={(v: number) => [v, "Rapoarte"]} />
                                <Area type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2.5} fill="url(#reportTrendFill)" dot={{ r: 3, fill: "#6366f1", strokeWidth: 2, stroke: "#fff" }} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* By type donut */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.25 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-500 to-teal-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-400 text-white shadow-md">
                            <BarChart3 className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Tip Raport</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={240}>
                            <PieChart>
                                <defs>
                                    {DEMO_BY_TYPE.map((d, i) => (
                                        <linearGradient key={i} id={`reportTypeGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                                            <stop offset="0%" stopColor={d.color} stopOpacity={1} />
                                            <stop offset="100%" stopColor={d.color} stopOpacity={0.6} />
                                        </linearGradient>
                                    ))}
                                </defs>
                                <Pie data={DEMO_BY_TYPE} cx="50%" cy="45%" innerRadius={45} outerRadius={75} paddingAngle={3} dataKey="value" strokeWidth={0}>
                                    {DEMO_BY_TYPE.map((_, i) => <Cell key={i} fill={`url(#reportTypeGrad${i})`} />)}
                                </Pie>
                                <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10, paddingTop: 12 }} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }} formatter={(v: number) => [v, "Rapoarte"]} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* By format donut */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-amber-500 to-orange-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-400 text-white shadow-md">
                            <FileSpreadsheet className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Format Export</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={240}>
                            <PieChart>
                                <defs>
                                    {DEMO_BY_FORMAT.map((d, i) => (
                                        <linearGradient key={i} id={`reportFmtGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                                            <stop offset="0%" stopColor={d.color} stopOpacity={1} />
                                            <stop offset="100%" stopColor={d.color} stopOpacity={0.6} />
                                        </linearGradient>
                                    ))}
                                </defs>
                                <Pie data={DEMO_BY_FORMAT} cx="50%" cy="45%" innerRadius={45} outerRadius={75} paddingAngle={3} dataKey="value" strokeWidth={0}>
                                    {DEMO_BY_FORMAT.map((_, i) => <Cell key={i} fill={`url(#reportFmtGrad${i})`} />)}
                                </Pie>
                                <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10, paddingTop: 12 }} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }} formatter={(v: number) => [`${v}%`, "Procent"]} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>
            </div>

            {/* ── Reports Table ── */}
            {isLoading ? (
                <div className="flex h-32 items-center justify-center">
                    <div className="relative">
                        <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                    </div>
                </div>
            ) : (
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.35 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-500" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-md">
                            <FileText className="h-4 w-4" />
                        </div>
                        <div>
                            <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Rapoarte Generate</h3>
                            <p className="font-rajdhani text-[10px] text-slate-400">{exports.length} rapoarte</p>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b bg-slate-50/50">
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Tip</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Format</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Status</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Creat la</th>
                                    <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Acțiuni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {exports.map((report, idx) => (
                                    <motion.tr
                                        key={report.id}
                                        custom={idx}
                                        variants={fadeUp}
                                        initial="hidden"
                                        animate="visible"
                                        className="border-b border-slate-50 transition-colors hover:bg-indigo-50/40"
                                    >
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2">
                                                <FileText className="h-3.5 w-3.5 text-indigo-400" />
                                                <span className="font-medium text-slate-700">{report.export_type}</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={cn(
                                                "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold",
                                                report.format?.toLowerCase() === "pdf" ? "bg-red-100/60 text-red-700" : "bg-emerald-100/60 text-emerald-700"
                                            )}>
                                                {report.format}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-1.5">
                                                {statusIcon(report.status)}
                                                <span className={cn(
                                                    "text-xs capitalize",
                                                    report.status === "completed" && "text-green-600",
                                                    report.status === "failed" && "text-red-600",
                                                    report.status === "processing" && "text-yellow-600"
                                                )}>
                                                    {report.status === "completed" ? "Finalizat" : report.status === "processing" ? "În procesare" : report.status === "failed" ? "Eșuat" : report.status}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 font-rajdhani text-slate-400">
                                            {formatDateTime(report.created_at)}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            {report.status === "completed" && report.file_url && (
                                                <a
                                                    href={report.file_url}
                                                    download
                                                    className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-3 py-1.5 text-[10px] font-semibold text-white shadow-md shadow-indigo-500/20 transition-all hover:shadow-lg hover:-translate-y-0.5"
                                                >
                                                    <Download className="h-3 w-3" />
                                                    Descarcă
                                                </a>
                                            )}
                                        </td>
                                    </motion.tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {exports.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-16 text-slate-300">
                            <Orbit className="mb-3 h-10 w-10 animate-[orbit-spin_8s_linear_infinite]" />
                            <p className="font-rajdhani text-sm uppercase tracking-wider">Nu ai rapoarte generate. Generează rapoarte din pagina unei companii.</p>
                        </div>
                    )}
                </motion.div>
            )}
        </div>
    );
}
