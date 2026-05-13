import { useQuery } from "@tanstack/react-query";
import { Orbit, Leaf, Users, Building2, TrendingUp, Award, BarChart3, Target, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    AreaChart, Area, PieChart, Pie, Cell, Legend,
} from "recharts";

/* ───── Demo Data ───── */
const DEMO_RANKING = [
    { cui: 12345678, denumire: "MEGA DISTRIBUTION SRL", caen_principal: "4711", score_total: 87.5, score_e: 82.3, score_s: 89.1, score_g: 91.2 },
    { cui: 23456789, denumire: "TECH GLOBAL SA", caen_principal: "6201", score_total: 84.2, score_e: 79.8, score_s: 86.4, score_g: 86.5 },
    { cui: 34567890, denumire: "VERDE CONSTRUCT SRL", caen_principal: "4120", score_total: 81.9, score_e: 91.5, score_s: 74.2, score_g: 80.0 },
    { cui: 45678901, denumire: "ECO SOLUTIONS SA", caen_principal: "3811", score_total: 80.1, score_e: 93.7, score_s: 70.5, score_g: 76.2 },
    { cui: 56789012, denumire: "SMART ENERGY SRL", caen_principal: "3514", score_total: 78.6, score_e: 88.3, score_s: 72.8, score_g: 74.7 },
    { cui: 67890123, denumire: "AGRO PREMIUM SA", caen_principal: "0111", score_total: 76.4, score_e: 85.1, score_s: 68.9, score_g: 75.2 },
    { cui: 78901234, denumire: "DIGITAL FINANCE SRL", caen_principal: "6419", score_total: 75.8, score_e: 62.4, score_s: 81.2, score_g: 83.8 },
    { cui: 89012345, denumire: "BIO FARM SA", caen_principal: "0147", score_total: 74.5, score_e: 90.2, score_s: 65.1, score_g: 68.2 },
    { cui: 90123456, denumire: "AUTONOM TRANSPORT SRL", caen_principal: "4941", score_total: 73.2, score_e: 67.8, score_s: 78.5, score_g: 73.3 },
    { cui: 10234567, denumire: "PHARMA HEALTH SA", caen_principal: "2120", score_total: 72.8, score_e: 71.5, score_s: 82.4, score_g: 64.5 },
    { cui: 11234568, denumire: "SOLAR POWER SA", caen_principal: "3511", score_total: 71.6, score_e: 94.2, score_s: 58.4, score_g: 62.2 },
    { cui: 12345679, denumire: "RETAIL MAX SRL", caen_principal: "4711", score_total: 70.3, score_e: 65.8, score_s: 74.1, score_g: 71.0 },
    { cui: 13456780, denumire: "INDUSTRIA NORD SA", caen_principal: "2511", score_total: 69.5, score_e: 58.7, score_s: 75.6, score_g: 74.2 },
    { cui: 14567891, denumire: "LOGISTICS PLUS SRL", caen_principal: "5210", score_total: 68.9, score_e: 63.2, score_s: 72.8, score_g: 70.7 },
    { cui: 15678902, denumire: "FOOD QUALITY SA", caen_principal: "1071", score_total: 67.4, score_e: 72.1, score_s: 64.5, score_g: 65.6 },
];

const DEMO_SECTOR_ESG = [
    { sector: "IT & Tech", e: 68, s: 82, g: 85 },
    { sector: "Construcții", e: 52, s: 71, g: 74 },
    { sector: "Energie", e: 78, s: 65, g: 70 },
    { sector: "Agricultură", e: 82, s: 60, g: 62 },
    { sector: "Retail", e: 58, s: 75, g: 72 },
    { sector: "Transport", e: 45, s: 68, g: 66 },
];

const DEMO_TREND = [
    { month: "Oct", avg_e: 68, avg_s: 72, avg_g: 71 },
    { month: "Nov", avg_e: 70, avg_s: 73, avg_g: 72 },
    { month: "Dec", avg_e: 69, avg_s: 74, avg_g: 73 },
    { month: "Ian", avg_e: 72, avg_s: 75, avg_g: 74 },
    { month: "Feb", avg_e: 74, avg_s: 76, avg_g: 75 },
    { month: "Mar", avg_e: 76, avg_s: 77, avg_g: 76 },
];

const DEMO_DISTRIBUTION = [
    { name: "Excelent (80+)", value: 28, color: "#10b981" },
    { name: "Bun (60-79)", value: 45, color: "#6366f1" },
    { name: "Mediu (40-59)", value: 18, color: "#eab308" },
    { name: "Slab (<40)", value: 9, color: "#ef4444" },
];

const DEMO_RADAR = [
    { subject: "Emisii CO₂", A: 78 },
    { subject: "Deșeuri", A: 65 },
    { subject: "Angajați", A: 82 },
    { subject: "Diversitate", A: 71 },
    { subject: "Transparență", A: 88 },
    { subject: "Audit", A: 76 },
];

const ESG_COLORS = { e: "#10b981", s: "#6366f1", g: "#f59e0b" };

const fadeUp = {
    hidden: { opacity: 0, y: 16 },
    visible: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07, duration: 0.45, ease: "easeOut" as const } }),
};

const W = "border-[1.5px] border-indigo-100/80 shadow-md shadow-indigo-500/5 backdrop-blur-sm";

function scoreColor(s: number) {
    if (s >= 80) return "text-emerald-600";
    if (s >= 60) return "text-indigo-600";
    if (s >= 40) return "text-amber-600";
    return "text-red-600";
}

function scoreBadge(s: number) {
    if (s >= 80) return "bg-emerald-100 text-emerald-700";
    if (s >= 60) return "bg-indigo-100 text-indigo-700";
    if (s >= 40) return "bg-amber-100 text-amber-700";
    return "bg-red-100 text-red-700";
}

export default function ESGDashboardPage() {
    const { data: rawRanking, isLoading } = useQuery({
        queryKey: ["esg", "ranking"],
        queryFn: async () => {
            const { data } = await api.get("/esg/ranking/top?limit=20");
            return data?.ranking ?? data ?? [];
        },
    });

    const ranking = rawRanking && rawRanking.length > 0 ? rawRanking : DEMO_RANKING;

    // Compute KPIs from ranking
    const avgTotal = ranking.length > 0 ? (ranking.reduce((acc: number, r: any) => acc + (r.score_total || 0), 0) / ranking.length).toFixed(1) : "0";
    const avgE = ranking.length > 0 ? (ranking.reduce((acc: number, r: any) => acc + (r.score_e || 0), 0) / ranking.length).toFixed(1) : "0";
    const avgS = ranking.length > 0 ? (ranking.reduce((acc: number, r: any) => acc + (r.score_s || 0), 0) / ranking.length).toFixed(1) : "0";
    const avgG = ranking.length > 0 ? (ranking.reduce((acc: number, r: any) => acc + (r.score_g || 0), 0) / ranking.length).toFixed(1) : "0";

    return (
        <div className="min-h-screen -m-6 p-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(16,185,129,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(99,102,241,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(245,158,11,0.04) 0%, transparent 50%)' }}>

            {/* ── Hero Banner ── */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-emerald-950 to-teal-950 p-6 shadow-2xl lg:p-8"
            >
                <div className="pointer-events-none absolute inset-0 opacity-30"
                    style={{ backgroundImage: "radial-gradient(circle at 15% 50%, rgba(16,185,129,0.35) 0%, transparent 50%), radial-gradient(circle at 85% 20%, rgba(99,102,241,0.3) 0%, transparent 50%), radial-gradient(circle at 50% 80%, rgba(245,158,11,0.2) 0%, transparent 50%)" }}
                />
                <div className="pointer-events-none absolute inset-0 opacity-[0.04]"
                    style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)", backgroundSize: "40px 40px" }}
                />
                <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-sm">
                            <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                            <span className="font-rajdhani text-[11px] font-semibold uppercase tracking-[0.15em] text-white/70">Scoring ESG</span>
                        </div>
                        <h1 className="mt-3 font-orbitron text-2xl font-bold tracking-wide text-white lg:text-3xl">ESG Dashboard</h1>
                        <p className="mt-2 max-w-lg font-rajdhani text-sm leading-relaxed text-white/50">
                            Scoruri Environmental, Social și Governance calculate pe baza datelor publice disponibile. Analiza completă a sustenabilității companiilor.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-green-400 text-white shadow-lg shadow-emerald-500/25">
                                <Award className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Scor Mediu</p>
                                <p className="font-orbitron text-lg font-bold text-white">{avgTotal}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-400 text-white shadow-lg shadow-indigo-500/25">
                                <Building2 className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Companii Evaluate</p>
                                <p className="font-orbitron text-lg font-bold text-white">{ranking.length}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* ── KPI Row ── */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                    { icon: <TrendingUp className="h-5 w-5" />, iconBg: "from-emerald-500 to-green-400", label: "Scor Mediu Total", value: avgTotal, sub: "din toate companiile" },
                    { icon: <Leaf className="h-5 w-5" />, iconBg: "from-emerald-500 to-teal-400", label: "Environmental (E)", value: avgE, sub: "media scorurilor E" },
                    { icon: <Users className="h-5 w-5" />, iconBg: "from-indigo-500 to-violet-400", label: "Social (S)", value: avgS, sub: "media scorurilor S" },
                    { icon: <Building2 className="h-5 w-5" />, iconBg: "from-amber-500 to-orange-400", label: "Governance (G)", value: avgG, sub: "media scorurilor G" },
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
                        <div className="mt-3 flex items-center gap-1.5">
                            <span className="inline-flex items-center gap-0.5 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">{kpi.sub}</span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* ── ESG Legend Cards ── */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {[
                    { color: ESG_COLORS.e, gradient: "from-emerald-500 to-teal-400", title: "Environmental", desc: "Emisii, amenzi de mediu, sector CAEN cu impact", icon: <Leaf className="h-4 w-4" /> },
                    { color: ESG_COLORS.s, gradient: "from-indigo-500 to-violet-400", title: "Social", desc: "Angajați, litigii de muncă, contracte publice", icon: <Users className="h-4 w-4" /> },
                    { color: ESG_COLORS.g, gradient: "from-amber-500 to-orange-400", title: "Governance", desc: "Transparență acționariat, stabilitate admin, raportare", icon: <Building2 className="h-4 w-4" /> },
                ].map((item, i) => (
                    <motion.div
                        key={item.title}
                        initial={{ opacity: 0, y: 14 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.15 + i * 0.08 }}
                        className={cn("relative overflow-hidden rounded-2xl bg-white/70 p-5", W)}
                    >
                        <div className={cn("absolute inset-x-0 top-0 h-1 bg-gradient-to-r", item.gradient)} />
                        <div className="flex items-center gap-2.5">
                            <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-md", item.gradient)}>
                                {item.icon}
                            </div>
                            <h3 className="font-orbitron text-xs font-semibold tracking-wide" style={{ color: item.color }}>{item.title}</h3>
                        </div>
                        <p className="mt-3 font-rajdhani text-sm text-slate-400">{item.desc}</p>
                    </motion.div>
                ))}
            </div>

            {/* ── Charts Row 1: Trend + Radar ── */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-500 to-teal-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-400 text-white shadow-md">
                            <TrendingUp className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Evoluție Scoruri ESG (6 luni)</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={280}>
                            <AreaChart data={DEMO_TREND}>
                                <defs>
                                    <linearGradient id="esgFillE" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={ESG_COLORS.e} stopOpacity={0.2} /><stop offset="100%" stopColor={ESG_COLORS.e} stopOpacity={0} /></linearGradient>
                                    <linearGradient id="esgFillS" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={ESG_COLORS.s} stopOpacity={0.2} /><stop offset="100%" stopColor={ESG_COLORS.s} stopOpacity={0} /></linearGradient>
                                    <linearGradient id="esgFillG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={ESG_COLORS.g} stopOpacity={0.2} /><stop offset="100%" stopColor={ESG_COLORS.g} stopOpacity={0} /></linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <YAxis domain={[40, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12, padding: "8px 14px" }} />
                                <Area type="monotone" dataKey="avg_e" name="Environmental" stroke={ESG_COLORS.e} strokeWidth={2.5} fill="url(#esgFillE)" dot={{ r: 3, fill: ESG_COLORS.e, strokeWidth: 2, stroke: "#fff" }} />
                                <Area type="monotone" dataKey="avg_s" name="Social" stroke={ESG_COLORS.s} strokeWidth={2.5} fill="url(#esgFillS)" dot={{ r: 3, fill: ESG_COLORS.s, strokeWidth: 2, stroke: "#fff" }} />
                                <Area type="monotone" dataKey="avg_g" name="Governance" stroke={ESG_COLORS.g} strokeWidth={2.5} fill="url(#esgFillG)" dot={{ r: 3, fill: ESG_COLORS.g, strokeWidth: 2, stroke: "#fff" }} />
                                <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.25 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-400 text-white shadow-md">
                            <Target className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Profil ESG Mediu</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={280}>
                            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={DEMO_RADAR}>
                                <PolarGrid stroke="#e2e8f0" />
                                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: "#64748b" }} />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9, fill: "#94a3b8" }} />
                                <Radar name="Scor" dataKey="A" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>
            </div>

            {/* ── Charts Row 2: Distribution + Sector Comparison ── */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-pink-500 to-rose-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-pink-500 to-rose-400 text-white shadow-md">
                            <BarChart3 className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Distribuție Scoruri ESG</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={260}>
                            <PieChart>
                                <defs>
                                    {DEMO_DISTRIBUTION.map((d, i) => (
                                        <linearGradient key={i} id={`esgDistGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                                            <stop offset="0%" stopColor={d.color} stopOpacity={1} />
                                            <stop offset="100%" stopColor={d.color} stopOpacity={0.6} />
                                        </linearGradient>
                                    ))}
                                </defs>
                                <Pie data={DEMO_DISTRIBUTION} cx="50%" cy="45%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value" strokeWidth={0}>
                                    {DEMO_DISTRIBUTION.map((_, i) => <Cell key={i} fill={`url(#esgDistGrad${i})`} />)}
                                </Pie>
                                <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10, paddingTop: 12 }} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }} formatter={(v: number) => [v, "Companii"]} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.35 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70 lg:col-span-2", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-amber-500 to-orange-400" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-400 text-white shadow-md">
                            <BarChart3 className="h-4 w-4" />
                        </div>
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">ESG pe Sector Economic</h3>
                    </div>
                    <div className="p-5">
                        <ResponsiveContainer width="100%" height={260}>
                            <BarChart data={DEMO_SECTOR_ESG}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="sector" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }} />
                                <Bar dataKey="e" name="Environmental" fill={ESG_COLORS.e} radius={[4, 4, 0, 0]} barSize={16} />
                                <Bar dataKey="s" name="Social" fill={ESG_COLORS.s} radius={[4, 4, 0, 0]} barSize={16} />
                                <Bar dataKey="g" name="Governance" fill={ESG_COLORS.g} radius={[4, 4, 0, 0]} barSize={16} />
                                <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>
            </div>

            {/* ── Disclaimer ── */}
            <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }}
                className={cn("rounded-2xl bg-amber-50/80 p-4", W, "border-amber-200/60")}
            >
                <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-400 text-white shadow-md">
                        <Target className="h-4 w-4" />
                    </div>
                    <div>
                        <p className="font-orbitron text-xs font-semibold text-amber-800">Disclaimer</p>
                        <p className="mt-1 font-rajdhani text-sm text-amber-700/80">
                            Scorurile ESG sunt calculate pe baza datelor publice disponibile și nu constituie un rating oficial. Sursele sunt citate și verificabile. Scorurile nu trebuie utilizate ca singur criteriu de investiție.
                        </p>
                    </div>
                </div>
            </motion.div>

            {/* ── Ranking Table ── */}
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
                    transition={{ duration: 0.5, delay: 0.4 }}
                    className={cn("relative overflow-hidden rounded-2xl bg-white/70", W)}
                >
                    <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-500 to-indigo-500" />
                    <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-indigo-500 text-white shadow-md">
                            <Award className="h-4 w-4" />
                        </div>
                        <div>
                            <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Top Companii ESG</h3>
                            <p className="font-rajdhani text-[10px] text-slate-400">{ranking.length} companii evaluate</p>
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b bg-slate-50/50">
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">#</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Companie</th>
                                    <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Total</th>
                                    <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">E</th>
                                    <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">S</th>
                                    <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">G</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">CAEN</th>
                                </tr>
                            </thead>
                            <tbody>
                                {ranking.map((item: any, idx: number) => (
                                    <motion.tr
                                        key={idx}
                                        custom={idx}
                                        variants={fadeUp}
                                        initial="hidden"
                                        animate="visible"
                                        className="border-b border-slate-50 transition-colors hover:bg-indigo-50/40"
                                    >
                                        <td className="px-4 py-3 font-orbitron text-xs font-bold text-slate-500">{idx + 1}</td>
                                        <td className="px-4 py-3">
                                            <p className="font-medium text-slate-700">{item.denumire}</p>
                                            <p className="font-rajdhani text-[10px] text-slate-400">CUI: {item.cui}</p>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold", scoreBadge(item.score_total))}>
                                                {item.score_total != null ? Number(item.score_total).toFixed(1) : "—"}
                                            </span>
                                        </td>
                                        <td className={cn("px-4 py-3 text-right font-semibold", scoreColor(item.score_e))}>
                                            {item.score_e != null ? Number(item.score_e).toFixed(1) : "—"}
                                        </td>
                                        <td className={cn("px-4 py-3 text-right font-semibold", scoreColor(item.score_s))}>
                                            {item.score_s != null ? Number(item.score_s).toFixed(1) : "—"}
                                        </td>
                                        <td className={cn("px-4 py-3 text-right font-semibold", scoreColor(item.score_g))}>
                                            {item.score_g != null ? Number(item.score_g).toFixed(1) : "—"}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="inline-flex items-center rounded-full bg-violet-100/60 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                                                {item.caen_principal}
                                            </span>
                                        </td>
                                    </motion.tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            )}
        </div>
    );
}
