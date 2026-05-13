import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";
import { cn } from "@/lib/utils";
import {
    Leaf, Users2, Landmark, ClipboardList, Coins, Globe,
    TrendingUp, TrendingDown, Minus, ShieldCheck, Award, Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";

/* ═══ Dummy data (will be populated via ESG API) ═══════════════ */

interface EsgCategory {
    key: string;
    label: string;
    pct: number;
    delta: string;
    deltaPositive: boolean | null;
    color: string;
    colorFrom: string;
    colorTo: string;
    glowColor: string;
    iconBg: string;
    Icon: React.ElementType;
}

const categories: EsgCategory[] = [
    { key: "mediu", label: "MEDIU", pct: 72, delta: "+5% vs. luna anterioară", deltaPositive: true, color: "#10b981", colorFrom: "from-emerald-500", colorTo: "to-green-400", glowColor: "shadow-emerald-500/25", iconBg: "bg-emerald-500/10 text-emerald-500 ring-1 ring-emerald-500/20", Icon: Leaf },
    { key: "social", label: "SOCIAL", pct: 65, delta: "+3% vs. luna anterioară", deltaPositive: true, color: "#3b82f6", colorFrom: "from-blue-500", colorTo: "to-indigo-400", glowColor: "shadow-blue-500/25", iconBg: "bg-blue-500/10 text-blue-500 ring-1 ring-blue-500/20", Icon: Users2 },
    { key: "guvernanta", label: "GUVERNANȚĂ", pct: 80, delta: "−2% vs. luna anterioară", deltaPositive: false, color: "#8b5cf6", colorFrom: "from-violet-500", colorTo: "to-purple-400", glowColor: "shadow-violet-500/25", iconBg: "bg-violet-500/10 text-violet-500 ring-1 ring-violet-500/20", Icon: Landmark },
    { key: "sscs", label: "SSCS", pct: 55, delta: "+8% vs. luna anterioară", deltaPositive: true, color: "#f59e0b", colorFrom: "from-amber-500", colorTo: "to-yellow-400", glowColor: "shadow-amber-500/25", iconBg: "bg-amber-500/10 text-amber-500 ring-1 ring-amber-500/20", Icon: ClipboardList },
    { key: "finante", label: "FINANȚE", pct: 90, delta: "— stabil vs. luna anterioară", deltaPositive: null, color: "#14b8a6", colorFrom: "from-teal-500", colorTo: "to-cyan-400", glowColor: "shadow-teal-500/25", iconBg: "bg-teal-500/10 text-teal-500 ring-1 ring-teal-500/20", Icon: Coins },
    { key: "co2", label: "CO₂", pct: 45, delta: "+12% vs. luna anterioară", deltaPositive: true, color: "#06b6d4", colorFrom: "from-cyan-500", colorTo: "to-sky-400", glowColor: "shadow-cyan-500/25", iconBg: "bg-cyan-500/10 text-cyan-500 ring-1 ring-cyan-500/20", Icon: Globe },
];

const overallScore = Math.round(categories.reduce((s, c) => s + c.pct, 0) / categories.length);

const radarData = [
    { subject: "Politici de Mediu", value: 90 },
    { subject: "Proceduri de Mediu", value: 58 },
    { subject: "HR Mediu", value: 42 },
    { subject: "Traininguri Mediu", value: 70 },
];

const barData = [
    { month: "Oct", score: 55 },
    { month: "Nov", score: 58 },
    { month: "Dec", score: 60 },
    { month: "Ian", score: 62 },
    { month: "Feb", score: 68 },
    { month: "Mar", score: 72 },
];

const sparklineData = [
    { v: 40 }, { v: 48 }, { v: 45 }, { v: 52 }, { v: 58 }, { v: 55 }, { v: 63 }, { v: 60 }, { v: 68 }, { v: overallScore },
];

const pieData = [
    { name: "HR Mediu", value: 25, color: "#8b5cf6" },
    { name: "Politici de Mediu", value: 30, color: "#f59e0b" },
    { name: "Proceduri de Mediu", value: 28, color: "#3b82f6" },
    { name: "Traininguri Mediu", value: 17, color: "#f97316" },
];

const fadeUp = {
    hidden: { opacity: 0, y: 18 },
    visible: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.07, duration: 0.45, ease: "easeOut" as const } }),
};

/* ═══ Circular progress ring (SVG) ═════════════════════════════ */
function CircularProgress({ pct, color, size = 64 }: { pct: number; color: string; size?: number }) {
    const r = (size - 8) / 2;
    const circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - pct / 100);

    return (
        <svg width={size} height={size} className="-rotate-90 drop-shadow-sm">
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={4} opacity={0.5} />
            <circle
                cx={size / 2} cy={size / 2} r={r}
                fill="none" stroke={color} strokeWidth={5}
                strokeDasharray={circumference} strokeDashoffset={offset}
                strokeLinecap="round"
                className="transition-all duration-1000"
                filter="url(#glow)"
            />
            <defs>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="2" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>
            <text
                x={size / 2} y={size / 2}
                textAnchor="middle" dominantBaseline="central"
                className="rotate-90 origin-center fill-slate-700 text-xs font-bold"
                transform={`rotate(90, ${size / 2}, ${size / 2})`}
            >
                {pct}%
            </text>
        </svg>
    );
}

/* ═══ Big gauge for hero ═══════════════════════════════════════ */
function HeroGauge({ pct }: { pct: number }) {
    const size = 160;
    const r = 68;
    const circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - pct / 100);
    const grade = pct >= 80 ? "A" : pct >= 60 ? "B" : pct >= 40 ? "C" : "D";
    const gradeColor = pct >= 80 ? "text-emerald-400" : pct >= 60 ? "text-blue-400" : pct >= 40 ? "text-amber-400" : "text-red-400";

    return (
        <div className="relative">
            <svg width={size} height={size} className="-rotate-90">
                <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={8} />
                <circle
                    cx={size / 2} cy={size / 2} r={r}
                    fill="none" stroke="url(#heroGrad)" strokeWidth={8}
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round"
                    className="transition-all duration-1000"
                />
                <defs>
                    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#34d399" />
                        <stop offset="50%" stopColor="#60a5fa" />
                        <stop offset="100%" stopColor="#a78bfa" />
                    </linearGradient>
                </defs>
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-orbitron text-4xl font-black text-white drop-shadow-lg">{pct}</span>
                <span className="font-rajdhani text-xs uppercase tracking-[0.2em] text-white/60">din 100</span>
                <span className={cn("mt-1 font-orbitron text-lg font-bold", gradeColor)}>{grade}</span>
            </div>
        </div>
    );
}

/* ═══ Category card ════════════════════════════════════════════ */
function CategoryCard({ cat, index }: { cat: EsgCategory; index: number }) {
    const Icon = cat.Icon;
    const DeltaIcon = cat.deltaPositive === true ? TrendingUp : cat.deltaPositive === false ? TrendingDown : Minus;

    return (
        <motion.div
            custom={index}
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            className={cn(
                "group relative overflow-hidden rounded-2xl border border-white/60 bg-white/80 backdrop-blur-sm p-5",
                "shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5",
                `hover:${cat.glowColor}`,
            )}
        >
            {/* Colored accent bar */}
            <div className={cn("absolute inset-x-0 top-0 h-1 bg-gradient-to-r", cat.colorFrom, cat.colorTo)} />
            {/* Decorative glow blob */}
            <div
                className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-[0.07] blur-2xl transition-opacity group-hover:opacity-[0.15]"
                style={{ background: cat.color }}
            />

            <div className="relative flex items-start justify-between">
                <div className={cn("rounded-xl p-2.5 transition-transform group-hover:scale-110", cat.iconBg)}>
                    <Icon className="h-5 w-5" />
                </div>
                <CircularProgress pct={cat.pct} color={cat.color} />
            </div>

            <p className="mt-4 font-rajdhani text-[11px] font-bold uppercase tracking-[0.15em] text-slate-400">{cat.label}</p>
            <p className="mt-1 flex items-baseline gap-1.5">
                <span className="font-orbitron text-3xl font-black text-slate-800">{cat.pct}</span>
                <span className="font-rajdhani text-sm text-slate-400">% completat</span>
            </p>

            {/* Progress bar */}
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <motion.div
                    className={cn("h-full rounded-full bg-gradient-to-r", cat.colorFrom, cat.colorTo)}
                    initial={{ width: 0 }}
                    animate={{ width: `${cat.pct}%` }}
                    transition={{ duration: 1, delay: index * 0.07 + 0.3, ease: "easeOut" }}
                />
            </div>

            <div className={cn(
                "mt-3 flex items-center gap-1.5 text-xs font-medium",
                cat.deltaPositive === true && "text-emerald-600",
                cat.deltaPositive === false && "text-red-500",
                cat.deltaPositive === null && "text-slate-400",
            )}>
                <DeltaIcon className="h-3.5 w-3.5" />
                {cat.delta}
            </div>
        </motion.div>
    );
}

/* ═══ Chart wrapper ════════════════════════════════════════════ */
function ChartCard({ title, icon, accentFrom, accentTo, delay, children }: {
    title: string;
    icon: React.ReactNode;
    accentFrom: string;
    accentTo: string;
    delay: number;
    children: React.ReactNode;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className="group relative overflow-hidden rounded-2xl border border-white/60 bg-white/80 backdrop-blur-sm shadow-lg"
        >
            <div className={cn("absolute inset-x-0 top-0 h-1 bg-gradient-to-r", accentFrom, accentTo)} />
            <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
                <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-md", accentFrom, accentTo)}>
                    {icon}
                </div>
                <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">{title}</h3>
            </div>
            <div className="p-5">
                {children}
            </div>
        </motion.div>
    );
}

/* ═══ Main Page ════════════════════════════════════════════════ */
export default function MyESGDataPage() {
    return (
        <div className="space-y-6">
            {/* ── Hero Banner ── */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950 to-violet-950 p-6 shadow-2xl lg:p-8"
            >
                {/* Decorative mesh */}
                <div className="pointer-events-none absolute inset-0 opacity-30"
                    style={{ backgroundImage: "radial-gradient(circle at 20% 50%, rgba(99,102,241,0.3) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(139,92,246,0.25) 0%, transparent 50%), radial-gradient(circle at 60% 80%, rgba(16,185,129,0.2) 0%, transparent 50%)" }}
                />
                {/* Grid pattern */}
                <div className="pointer-events-none absolute inset-0 opacity-[0.04]"
                    style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)", backgroundSize: "40px 40px" }}
                />

                <div className="relative flex flex-col items-center gap-6 lg:flex-row lg:gap-10">
                    {/* Gauge */}
                    <HeroGauge pct={overallScore} />

                    {/* Text content */}
                    <div className="flex-1 text-center lg:text-left">
                        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 backdrop-blur-sm">
                            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                            <span className="font-rajdhani text-[11px] font-semibold uppercase tracking-[0.15em] text-white/70">Scor Compozit ESG</span>
                        </div>
                        <h1 className="mt-3 font-orbitron text-2xl font-bold tracking-wide text-white lg:text-3xl">
                            Datele mele ESG
                        </h1>
                        <p className="mt-2 max-w-lg font-rajdhani text-sm leading-relaxed text-white/50">
                            Prezentare generală ESG — agregate din toate cele 6 categorii de evaluare.
                            Scorul se recalculează automat pe baza datelor completate în ATH | ESG.
                        </p>

                        {/* Mini stats row */}
                        <div className="mt-5 flex flex-wrap items-center justify-center gap-4 lg:justify-start">
                            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2 backdrop-blur-sm">
                                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                                <div>
                                    <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Categorii Complete</p>
                                    <p className="font-orbitron text-sm font-bold text-white">{categories.filter(c => c.pct >= 80).length}/{categories.length}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2 backdrop-blur-sm">
                                <Award className="h-4 w-4 text-amber-400" />
                                <div>
                                    <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Cea mai bună</p>
                                    <p className="font-orbitron text-sm font-bold text-white">
                                        {categories.reduce((best, c) => c.pct > best.pct ? c : best).label}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2 backdrop-blur-sm">
                                <TrendingUp className="h-4 w-4 text-blue-400" />
                                <div>
                                    <p className="font-rajdhani text-[10px] uppercase tracking-wider text-white/40">Tendință</p>
                                    <p className="font-orbitron text-sm font-bold text-emerald-400">+4.5%</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Sparkline */}
                    <div className="hidden w-44 lg:block">
                        <p className="mb-1 text-center font-rajdhani text-[10px] uppercase tracking-[0.15em] text-white/30">Evoluție 10 luni</p>
                        <ResponsiveContainer width="100%" height={80}>
                            <AreaChart data={sparklineData}>
                                <defs>
                                    <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#818cf8" stopOpacity={0.4} />
                                        <stop offset="100%" stopColor="#818cf8" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <Area type="monotone" dataKey="v" stroke="#818cf8" strokeWidth={2} fill="url(#sparkGrad)" dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </motion.div>

            {/* ── Category Cards ── */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {categories.map((c, i) => (
                    <CategoryCard key={c.key} cat={c} index={i} />
                ))}
            </div>

            {/* ── Charts Row ── */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                {/* Radar */}
                <ChartCard
                    title="Scor pe Subcategorii"
                    icon={<ShieldCheck className="h-4 w-4" />}
                    accentFrom="from-emerald-500" accentTo="to-teal-400"
                    delay={0.15}
                >
                    <ResponsiveContainer width="100%" height={280}>
                        <RadarChart data={radarData} outerRadius="70%">
                            <PolarGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                            <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: "#64748b" }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                            <Radar
                                dataKey="value" stroke="#10b981" fill="url(#radarFill)" fillOpacity={1}
                                dot={{ r: 4, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
                            />
                            <defs>
                                <linearGradient id="radarFill" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.35} />
                                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.05} />
                                </linearGradient>
                            </defs>
                        </RadarChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Bar */}
                <ChartCard
                    title="Progres Lunar (6 luni)"
                    icon={<TrendingUp className="h-4 w-4" />}
                    accentFrom="from-blue-500" accentTo="to-indigo-400"
                    delay={0.25}
                >
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={barData}>
                            <defs>
                                <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.9} />
                                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.7} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <Tooltip
                                contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12, padding: "8px 14px" }}
                                formatter={(v: number) => [`${v}%`, "Scor"]}
                                cursor={{ fill: "rgba(99,102,241,0.06)" }}
                            />
                            <Bar dataKey="score" fill="url(#barGrad)" radius={[6, 6, 0, 0]} barSize={32} />
                        </BarChart>
                    </ResponsiveContainer>
                </ChartCard>

                {/* Donut */}
                <ChartCard
                    title="Distribuție Completare"
                    icon={<Award className="h-4 w-4" />}
                    accentFrom="from-violet-500" accentTo="to-purple-400"
                    delay={0.35}
                >
                    <ResponsiveContainer width="100%" height={280}>
                        <PieChart>
                            <defs>
                                {pieData.map((entry, i) => (
                                    <linearGradient key={i} id={`pieGrad${i}`} x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor={entry.color} stopOpacity={1} />
                                        <stop offset="100%" stopColor={entry.color} stopOpacity={0.6} />
                                    </linearGradient>
                                ))}
                            </defs>
                            <Pie
                                data={pieData}
                                cx="50%" cy="42%"
                                innerRadius={55} outerRadius={85}
                                paddingAngle={4}
                                dataKey="value"
                                strokeWidth={0}
                            >
                                {pieData.map((_entry, i) => (
                                    <Cell key={i} fill={`url(#pieGrad${i})`} />
                                ))}
                            </Pie>
                            <Legend
                                verticalAlign="bottom"
                                iconType="circle" iconSize={8}
                                wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
                            />
                            <Tooltip
                                contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.12)", fontSize: 12 }}
                                formatter={(v: number) => [`${v}%`, ""]}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </ChartCard>
            </div>
        </div>
    );
}
