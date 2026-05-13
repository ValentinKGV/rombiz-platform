import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import type { NewCompany } from "@/types";
import { cn, formatDate, formatNumber } from "@/lib/utils";
import {
    Building2, MapPin, Orbit, TrendingUp, Calendar, CalendarDays,
    Factory, Search,
    ChevronLeft, ChevronRight, ExternalLink,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { motion, type Variants } from "framer-motion";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    AreaChart, Area, PieChart, Pie, Cell, Legend,
} from "recharts";

const CAEN_COLORS = [
    "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
    "#f43f5e", "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#06b6d4", "#3b82f6", "#2563eb", "#7c3aed", "#c026d3",
    "#e11d48", "#ea580c", "#ca8a04", "#16a34a", "#0d9488",
];

const fadeUp: Variants = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.4, ease: "easeOut" } }),
};

/* ═══ Stat Card ════════════════════════════════════════════════ */
function StatWidget({ icon, iconBg, label, value, sub, delay }: {
    icon: React.ReactNode; iconBg: string; label: string; value: number; sub: string; delay: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay }}
            className="group relative overflow-hidden rounded-2xl border-[1.5px] border-indigo-100/80 bg-white/70 backdrop-blur-sm p-5 shadow-md shadow-indigo-500/5 hover:shadow-xl hover:border-indigo-200 transition-all duration-300 hover:-translate-y-0.5"
        >
            <div className="pointer-events-none absolute -right-4 -top-4 h-20 w-20 rounded-full opacity-[0.07] blur-2xl" style={{ background: "currentColor" }} />
            <div className="flex items-center gap-4">
                <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-md transition-transform group-hover:scale-110", iconBg)}>
                    {icon}
                </div>
                <div className="min-w-0 flex-1">
                    <p className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">{label}</p>
                    <p className="font-orbitron text-2xl font-black text-slate-800">{formatNumber(value)}</p>
                </div>
            </div>
            <div className="mt-3 flex items-center gap-1.5">
                <span className="inline-flex items-center gap-0.5 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                    {sub}
                </span>
            </div>
        </motion.div>
    );
}

/* ═══ Chart wrapper ════════════════════════════════════════════ */
function ChartCard({ title, icon, accentFrom, accentTo, delay, children, className }: {
    title: string; icon: React.ReactNode; accentFrom: string; accentTo: string; delay: number; children: React.ReactNode; className?: string;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className={cn("group relative overflow-hidden rounded-2xl border-[1.5px] border-indigo-100/80 bg-white/70 backdrop-blur-sm shadow-md shadow-indigo-500/5", className)}
        >
            <div className={cn("absolute inset-x-0 top-0 h-1 bg-gradient-to-r", accentFrom, accentTo)} />
            <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4 dark:border-slate-700">
                <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-md", accentFrom, accentTo)}>
                    {icon}
                </div>
                <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700 dark:text-slate-200">{title}</h3>
            </div>
            <div className="p-5">{children}</div>
        </motion.div>
    );
}

/* ═══ Main Page ════════════════════════════════════════════════ */
export default function NewCompaniesPage() {
    const navigate = useNavigate();
    const [judet, setJudet] = useState("");
    const [searchTerm, setSearchTerm] = useState("");
    const [page, setPage] = useState(1);

    const { data: companies, isLoading } = useQuery({
        queryKey: ["new-companies", judet, page],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (judet) params.set("judet", judet);
            params.set("page", String(page));
            params.set("page_size", "25");
            const { data } = await api.get(`/new-companies?${params}`);
            return data;
        },
    });

    const { data: rawStats } = useQuery({
        queryKey: ["new-companies", "stats"],
        queryFn: async () => {
            const { data } = await api.get("/new-companies/stats");
            return data;
        },
    });

    const stats = rawStats ?? null;

    const filteredItems = (companies?.items || []).filter((c: NewCompany) =>
        !searchTerm || c.denumire?.toLowerCase().includes(searchTerm.toLowerCase()) || c.cui?.includes(searchTerm)
    );

    const totalPages = Math.ceil((companies?.total || 0) / 25);

    return (
        <div className="min-h-screen -m-6 p-6 space-y-6 bg-gradient-to-br from-slate-50 via-indigo-50/40 to-violet-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(99,102,241,0.06) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.05) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(236,72,153,0.04) 0%, transparent 50%)' }}>

            {/* ── KPI Cards ── */}
            {stats && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <StatWidget
                        icon={<TrendingUp className="h-5 w-5" />}
                        iconBg="from-emerald-500 to-green-400"
                        label="Înregistrate Azi"
                        value={stats.today || 0}
                        sub="firme noi astăzi"
                        delay={0.05}
                    />
                    <StatWidget
                        icon={<CalendarDays className="h-5 w-5" />}
                        iconBg="from-blue-500 to-indigo-400"
                        label="Săptămâna Aceasta"
                        value={stats.this_week || 0}
                        sub="din ultima săptămână"
                        delay={0.1}
                    />
                    <StatWidget
                        icon={<Calendar className="h-5 w-5" />}
                        iconBg="from-violet-500 to-purple-400"
                        label="Luna Aceasta"
                        value={stats.this_month || 0}
                        sub="din luna curentă"
                        delay={0.15}
                    />
                    <StatWidget
                        icon={<MapPin className="h-5 w-5" />}
                        iconBg="from-amber-500 to-orange-400"
                        label="Județe Active"
                        value={stats.by_county?.length || 0}
                        sub="județe cu firme noi"
                        delay={0.2}
                    />
                </div>
            )}

            {/* ── Charts Row 1: Daily Trend + County Bar ── */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {/* Daily Trend Area Chart */}
                {stats?.daily_trend?.length > 0 && (
                    <ChartCard
                        title="Tendință Zilnică Înregistrări"
                        icon={<TrendingUp className="h-4 w-4" />}
                        accentFrom="from-emerald-500" accentTo="to-teal-400"
                        delay={0.2}
                    >
                        <ResponsiveContainer width="100%" height={280}>
                            <AreaChart data={stats.daily_trend}>
                                <defs>
                                    <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                                        <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis
                                    dataKey="date"
                                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                                    axisLine={false} tickLine={false}
                                    tickFormatter={(v: string) => v?.slice(5) || ""}
                                />
                                <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <Tooltip
                                    contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12, padding: "8px 14px" }}
                                    formatter={(v: number) => [v, "Firme noi"]}
                                    labelFormatter={(l: string) => `Data: ${l}`}
                                />
                                <Area
                                    type="monotone" dataKey="count"
                                    stroke="#10b981" strokeWidth={2.5}
                                    fill="url(#trendFill)"
                                    dot={{ r: 3, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
                                    activeDot={{ r: 5, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </ChartCard>
                )}

                {/* Bar — County */}
                {stats?.by_county?.length > 0 && (
                    <ChartCard
                        title="Top 10 Județe — Firme Noi"
                        icon={<MapPin className="h-4 w-4" />}
                        accentFrom="from-violet-500" accentTo="to-indigo-400"
                        delay={0.3}
                    >
                        <ResponsiveContainer width="100%" height={280}>
                            <BarChart data={stats.by_county.slice(0, 10)} layout="vertical">
                                <defs>
                                    <linearGradient id="barGradH" x1="0" y1="0" x2="1" y2="0">
                                        <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.9} />
                                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0.7} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                                <XAxis type="number" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <YAxis type="category" dataKey="judet" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} width={60} />
                                <Tooltip
                                    contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12, padding: "8px 14px" }}
                                    formatter={(v: number) => [v, "Firme"]}
                                    cursor={{ fill: "rgba(99,102,241,0.06)" }}
                                />
                                <Bar dataKey="count" fill="url(#barGradH)" radius={[0, 6, 6, 0]} barSize={18} />
                            </BarChart>
                        </ResponsiveContainer>
                    </ChartCard>
                )}
            </div>

            {/* ── Charts Row 2: CAEN Sectors Donut ── */}
            {stats?.by_caen_sector?.length > 0 && (
                <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                    <ChartCard
                        title="Distribuție Sectoare CAEN"
                        icon={<Factory className="h-4 w-4" />}
                        accentFrom="from-pink-500" accentTo="to-rose-400"
                        delay={0.35}
                    >
                        <ResponsiveContainer width="100%" height={280}>
                            <PieChart>
                                <defs>
                                    {stats.by_caen_sector.slice(0, 10).map((_: any, i: number) => (
                                        <linearGradient key={i} id={`caenGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                                            <stop offset="0%" stopColor={CAEN_COLORS[i % CAEN_COLORS.length]} stopOpacity={1} />
                                            <stop offset="100%" stopColor={CAEN_COLORS[i % CAEN_COLORS.length]} stopOpacity={0.6} />
                                        </linearGradient>
                                    ))}
                                </defs>
                                <Pie
                                    data={stats.by_caen_sector.slice(0, 10).map((s: any) => ({ name: `CAEN ${s.sector}`, value: s.count }))}
                                    cx="50%" cy="45%"
                                    innerRadius={50} outerRadius={80}
                                    paddingAngle={3} dataKey="value" strokeWidth={0}
                                >
                                    {stats.by_caen_sector.slice(0, 10).map((_: any, i: number) => (
                                        <Cell key={i} fill={`url(#caenGrad${i})`} />
                                    ))}
                                </Pie>
                                <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10, paddingTop: 12 }} />
                                <Tooltip
                                    contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }}
                                    formatter={(v: number) => [v, "Firme"]}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </ChartCard>

                    {/* CAEN Sector Top list */}
                    <ChartCard
                        title="Top Sectoare CAEN"
                        icon={<Building2 className="h-4 w-4" />}
                        accentFrom="from-blue-500" accentTo="to-cyan-400"
                        delay={0.4}
                        className="lg:col-span-2"
                    >
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {stats.by_caen_sector.slice(0, 10).map((s: any, i: number) => {
                                const maxVal = stats.by_caen_sector[0]?.count || 1;
                                const pct = Math.round((s.count / maxVal) * 100);
                                return (
                                    <motion.div
                                        key={s.sector}
                                        custom={i}
                                        variants={fadeUp}
                                        initial="hidden"
                                        animate="visible"
                                        className="flex items-center gap-3 rounded-xl border-[1.5px] border-indigo-100/60 bg-white/50 px-4 py-3 transition-colors hover:bg-indigo-50/30 hover:border-indigo-200 dark:border-indigo-800/40 dark:bg-slate-800/60 dark:hover:bg-indigo-900/20 dark:hover:border-indigo-700/60"
                                    >
                                        <div
                                            className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-white text-xs font-bold shadow-md"
                                            style={{ background: CAEN_COLORS[i % CAEN_COLORS.length] }}
                                        >
                                            {s.sector}
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-center justify-between">
                                                <span className="font-rajdhani text-xs font-semibold text-slate-600 dark:text-slate-300">Sector {s.sector}</span>
                                                <span className="font-orbitron text-xs font-bold text-slate-800 dark:text-slate-100">{formatNumber(s.count)}</span>
                                            </div>
                                            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200/60 dark:bg-slate-700/60">
                                                <motion.div
                                                    className="h-full rounded-full"
                                                    style={{ background: CAEN_COLORS[i % CAEN_COLORS.length] }}
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${pct}%` }}
                                                    transition={{ duration: 0.8, delay: i * 0.06 + 0.3 }}
                                                />
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    </ChartCard>
                </div>
            )}

            {/* ── Company Table ── */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="relative overflow-hidden rounded-2xl border-[1.5px] border-indigo-100/80 bg-white/70 backdrop-blur-sm shadow-md shadow-indigo-500/5"
            >
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-500" />

                {/* Table header with search & filter */}
                <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700">
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-md">
                            <Building2 className="h-4 w-4" />
                        </div>
                        <div>
                            <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700 dark:text-slate-200">Companii Noi</h3>
                            <p className="font-rajdhani text-[10px] text-slate-400 dark:text-slate-500">{formatNumber(companies?.total || 0)} rezultate</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                            <input
                                type="text"
                                placeholder="Caută firmă sau CUI…"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="h-8 w-52 rounded-lg border border-slate-200 bg-slate-50/80 pl-9 pr-3 font-rajdhani text-xs text-slate-600 placeholder:text-slate-300 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:placeholder:text-slate-500 dark:focus:border-indigo-500 dark:focus:ring-indigo-900/30"
                            />
                        </div>
                        <select
                            value={judet}
                            onChange={(e) => { setJudet(e.target.value); setPage(1); }}
                            className="h-8 rounded-lg border border-slate-200 bg-slate-50/80 px-3 font-rajdhani text-xs text-slate-600 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:focus:border-indigo-500 dark:focus:ring-indigo-900/30"
                        >
                            <option value="">Toate județele</option>
                            {(stats?.by_county || []).map((c: any) => (
                                <option key={c.judet} value={c.judet}>{c.judet} ({c.count})</option>
                            ))}
                        </select>
                    </div>
                </div>

                {isLoading ? (
                    <div className="flex h-48 items-center justify-center">
                        <div className="relative">
                            <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                            <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                        </div>
                    </div>
                ) : filteredItems.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-slate-300">
                        <Building2 className="mb-3 h-10 w-10" />
                        <p className="font-rajdhani text-sm uppercase tracking-wider">Nu s-au găsit firme noi</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b bg-slate-50/50 dark:bg-slate-800/60 dark:border-slate-700">
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-400">CUI</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-400">Denumire</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-400">Județ</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-400">CAEN</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-400">Data Înreg.</th>
                                    <th className="px-4 py-3 w-10" />
                                </tr>
                            </thead>
                            <tbody>
                                {filteredItems.map((c: NewCompany, i: number) => (
                                    <motion.tr
                                        key={c.id}
                                        custom={i}
                                        variants={fadeUp}
                                        initial="hidden"
                                        animate="visible"
                                        onClick={() => navigate(`/company/${c.cui}`)}
                                        className="cursor-pointer border-b border-slate-50 transition-colors hover:bg-indigo-50/40 dark:border-slate-700/50 dark:hover:bg-indigo-900/20"
                                    >
                                        <td className="px-4 py-3">
                                            <span className="inline-flex items-center rounded-lg bg-indigo-100/60 px-2 py-0.5 font-mono text-[11px] font-bold text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
                                                {c.cui}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-200">{c.denumire}</td>
                                        <td className="px-4 py-3">
                                            <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400">
                                                <MapPin className="h-3 w-3" /> {c.judet}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="inline-flex items-center rounded-full bg-violet-100/60 px-2 py-0.5 text-[10px] font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                                                {c.caen_principal}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 font-rajdhani text-slate-400 dark:text-slate-500">{formatDate(c.registration_date)}</td>
                                        <td className="px-4 py-3">
                                            <ExternalLink className="h-3.5 w-3.5 text-slate-300 group-hover:text-indigo-400" />
                                        </td>
                                    </motion.tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 dark:border-slate-700">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page <= 1}
                            className="flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-700"
                        >
                            <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                        </button>
                        <div className="flex items-center gap-1">
                            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                                let pNum: number;
                                if (totalPages <= 7) pNum = i + 1;
                                else if (page <= 4) pNum = i + 1;
                                else if (page >= totalPages - 3) pNum = totalPages - 6 + i;
                                else pNum = page - 3 + i;
                                return (
                                    <button
                                        key={pNum}
                                        onClick={() => setPage(pNum)}
                                        className={cn(
                                            "flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium transition-colors",
                                            page === pNum ? "bg-indigo-500 text-white shadow-md" : "text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"
                                        )}
                                    >
                                        {pNum}
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-700"
                        >
                            Următor <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                    </div>
                )}
            </motion.div>
        </div>
    );
}
