import { useLocation, useNavigate } from "react-router-dom";
import {
    ArrowLeft, Scale, Building2, BookOpen, Hash, Calendar,
    Users, Gavel, ChevronRight, ClipboardList, BadgeCheck,
    Clock, Layers, FileText, AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Types ───────────────────────────────────────────────────── */
interface Parte {
    calitate: string;
    denumire: string;
}
interface Termen {
    data: string;
    ora: string;
    complet: string;
    solutie: string;
    solutionare: string;
}
interface Dosar {
    numar: string;
    instanta: string;
    departament: string;
    materie: string;
    obiect: string;
    stadiu: string;
    data_dosar: string;
    parti: Parte[];
    termene: Termen[];
}

/* ── Helpers ─────────────────────────────────────────────────── */
function parseRoDate(s: string): number {
    if (!s) return 0;
    const p = s.split(".");
    if (p.length === 3) return new Date(+p[2], +p[1] - 1, +p[0]).getTime();
    const t = new Date(s).getTime();
    return isNaN(t) ? 0 : t;
}

function calitateColor(calitate: string) {
    const c = calitate?.toLowerCase() || "";
    if (c.includes("reclamant") || c.includes("petent") || c.includes("creditor")) return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300";
    if (c.includes("parat") || c.includes("intimat") || c.includes("debitor") || c.includes("inculpat")) return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
    return "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300";
}

/* ── Section wrapper ─────────────────────────────────────────── */
function Section({ icon, title, children, className }: {
    icon: React.ReactNode;
    title: string;
    children: React.ReactNode;
    className?: string;
}) {
    return (
        <div className={cn("card-cosmic", className)}>
            <div className="flex items-center gap-2.5 mb-5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                    {icon}
                </div>
                <h2 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">{title}</h2>
            </div>
            {children}
        </div>
    );
}

/* ── Main Page ───────────────────────────────────────────────── */
export default function DosarDetaliilePage() {
    const navigate = useNavigate();
    const location = useLocation();
    const dosar = (location.state as { dosar: Dosar } | null)?.dosar;

    /* ── Guard ── */
    if (!dosar) {
        return (
            <div className="flex flex-col items-center justify-center py-24 gap-4 text-slate-400">
                <AlertCircle className="h-12 w-12 opacity-30" />
                <p className="text-base font-medium">Niciun dosar selectat.</p>
                <button
                    onClick={() => navigate("/dosare")}
                    className="mt-2 flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Înapoi la căutare
                </button>
            </div>
        );
    }

    const sortedTermene = [...dosar.termene].sort(
        (a, b) => parseRoDate(b.data) - parseRoDate(a.data)
    );

    const lastTermen = sortedTermene[0];
    const nextTermen = [...dosar.termene]
        .filter((t) => parseRoDate(t.data) > Date.now())
        .sort((a, b) => parseRoDate(a.data) - parseRoDate(b.data))[0];

    return (
        <div className="space-y-6">
            {/* ── Breadcrumb + Back ── */}
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
                <button
                    onClick={() => navigate("/dosare")}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:text-blue-600 transition-colors"
                >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    Înapoi
                </button>
                <ChevronRight className="h-3.5 w-3.5" />
                <span className="cursor-pointer hover:text-blue-500 transition-colors" onClick={() => navigate("/dosare")}>Motor Căutare Dosare</span>
                <ChevronRight className="h-3.5 w-3.5" />
                <span className="font-semibold text-slate-600 dark:text-slate-300 font-mono">{dosar.numar || "Dosar"}</span>
            </div>

            {/* ── Hero ── */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 p-6 shadow-2xl lg:p-8">
                <div className="pointer-events-none absolute inset-0 opacity-25"
                    style={{ backgroundImage: "radial-gradient(circle at 15% 50%, rgba(59,130,246,0.4) 0%, transparent 50%), radial-gradient(circle at 85% 20%, rgba(99,102,241,0.3) 0%, transparent 50%)" }}
                />
                <div className="pointer-events-none absolute inset-0 opacity-[0.03]"
                    style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.15) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.15) 1px, transparent 1px)", backgroundSize: "32px 32px" }}
                />
                <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 mb-3">
                            <Scale className="h-3.5 w-3.5 text-blue-400" />
                            <span className="font-rajdhani text-[11px] font-semibold uppercase tracking-[0.12em] text-white/60">Dosar Judiciar</span>
                        </div>
                        <h1 className="font-orbitron text-2xl font-bold tracking-wide text-white lg:text-3xl">
                            {dosar.numar || "Număr nedisponibil"}
                        </h1>
                        <p className="mt-2 font-rajdhani text-sm text-white/50 max-w-lg leading-relaxed">
                            {dosar.obiect || "Obiect nedisponibil"}
                        </p>
                    </div>

                    {/* Quick stats */}
                    <div className="flex flex-wrap gap-3">
                        {dosar.stadiu && (
                            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                                <Layers className="h-4 w-4 text-blue-400" />
                                <div>
                                    <p className="font-rajdhani text-[9px] uppercase tracking-wider text-white/40">Stadiu</p>
                                    <p className="font-orbitron text-sm font-bold text-white">{dosar.stadiu}</p>
                                </div>
                            </div>
                        )}
                        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                            <Users className="h-4 w-4 text-indigo-400" />
                            <div>
                                <p className="font-rajdhani text-[9px] uppercase tracking-wider text-white/40">Părți</p>
                                <p className="font-orbitron text-sm font-bold text-white">{dosar.parti.length}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                            <Gavel className="h-4 w-4 text-purple-400" />
                            <div>
                                <p className="font-rajdhani text-[9px] uppercase tracking-wider text-white/40">Termene</p>
                                <p className="font-orbitron text-sm font-bold text-white">{dosar.termene.length}</p>
                            </div>
                        </div>
                        {dosar.data_dosar && (
                            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
                                <Calendar className="h-4 w-4 text-emerald-400" />
                                <div>
                                    <p className="font-rajdhani text-[9px] uppercase tracking-wider text-white/40">Data Dosar</p>
                                    <p className="font-orbitron text-sm font-bold text-white">{dosar.data_dosar}</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* ── Info grid ── */}
            <Section icon={<ClipboardList className="h-4 w-4" />} title="Informații Generale">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                    {[
                        { label: "Număr Dosar", value: dosar.numar, icon: <Hash className="h-3.5 w-3.5" /> },
                        { label: "Instanță", value: dosar.instanta, icon: <Building2 className="h-3.5 w-3.5" /> },
                        { label: "Departament", value: dosar.departament, icon: <Layers className="h-3.5 w-3.5" /> },
                        { label: "Materie", value: dosar.materie, icon: <BookOpen className="h-3.5 w-3.5" /> },
                        { label: "Stadiu Procesual", value: dosar.stadiu, icon: <BadgeCheck className="h-3.5 w-3.5" /> },
                        { label: "Data Dosar", value: dosar.data_dosar, icon: <Calendar className="h-3.5 w-3.5" /> },
                        ...(lastTermen ? [{ label: "Ultimul Termen", value: `${lastTermen.data}${lastTermen.ora ? ` · ${lastTermen.ora}` : ""}`, icon: <Clock className="h-3.5 w-3.5" /> }] : []),
                        ...(nextTermen ? [{ label: "Următor Termen", value: `${nextTermen.data}${nextTermen.ora ? ` · ${nextTermen.ora}` : ""}`, icon: <Clock className="h-3.5 w-3.5" /> }] : []),
                    ].map((item) => (
                        <div key={item.label} className="rounded-xl border border-slate-100 dark:border-slate-700/60 bg-slate-50/60 dark:bg-slate-800/50 p-3">
                            <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                                {item.icon}
                                <p className="font-rajdhani text-[10px] font-semibold uppercase tracking-wider">{item.label}</p>
                            </div>
                            <p className={cn("text-sm font-semibold break-words", item.label === "Număr Dosar" ? "font-mono text-blue-600 dark:text-blue-400" : "text-slate-700 dark:text-slate-200")}>
                                {item.value || "—"}
                            </p>
                        </div>
                    ))}
                </div>
                {/* Obiect full text */}
                {dosar.obiect && (
                    <div className="mt-4 rounded-xl border border-slate-100 dark:border-slate-700/60 bg-slate-50/60 dark:bg-slate-800/50 p-4">
                        <div className="flex items-center gap-1.5 text-slate-400 mb-1.5">
                            <FileText className="h-3.5 w-3.5" />
                            <p className="font-rajdhani text-[10px] font-semibold uppercase tracking-wider">Obiect Dosar</p>
                        </div>
                        <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">{dosar.obiect}</p>
                    </div>
                )}
            </Section>

            {/* ── Parties + Hearings side by side ── */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Parties */}
                <Section icon={<Users className="h-4 w-4" />} title={`Părți (${dosar.parti.length})`}>
                    {dosar.parti.length === 0 ? (
                        <p className="text-sm text-slate-400">Nu există informații despre părți.</p>
                    ) : (
                        <div className="space-y-2">
                            {dosar.parti.map((p, i) => (
                                <div
                                    key={i}
                                    className="flex items-center gap-3 rounded-xl border border-slate-100 dark:border-slate-700/60 bg-slate-50/60 dark:bg-slate-800/50 p-3"
                                >
                                    <div className={cn("shrink-0 rounded-lg px-2 py-1 text-[10px] font-bold uppercase tracking-wider", calitateColor(p.calitate))}>
                                        {p.calitate || "Parte"}
                                    </div>
                                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200 min-w-0">
                                        {p.denumire || "—"}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </Section>

                {/* Last solution / quick summary */}
                <Section icon={<Gavel className="h-4 w-4" />} title="Soluții Recente">
                    {sortedTermene.filter(t => t.solutie || t.solutionare).length === 0 ? (
                        <p className="text-sm text-slate-400">Nu există soluții înregistrate.</p>
                    ) : (
                        <div className="space-y-2">
                            {sortedTermene
                                .filter(t => t.solutie || t.solutionare)
                                .slice(0, 6)
                                .map((t, i) => (
                                    <div key={i} className="rounded-xl border border-emerald-100 dark:border-emerald-900/30 bg-emerald-50/60 dark:bg-emerald-900/10 p-3">
                                        <p className="font-rajdhani text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-0.5">
                                            {t.data}{t.ora ? ` · ${t.ora}` : ""}{t.complet ? ` — ${t.complet}` : ""}
                                        </p>
                                        <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
                                            {t.solutie || t.solutionare}
                                        </p>
                                    </div>
                                ))
                            }
                        </div>
                    )}
                </Section>
            </div>

            {/* ── Full hearings timeline ── */}
            <Section icon={<Scale className="h-4 w-4" />} title={`Toate Termenele (${dosar.termene.length}) · ordin cronologic invers`}>
                {dosar.termene.length === 0 ? (
                    <p className="text-sm text-slate-400">Nu există termene înregistrate.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60">
                                    {["#", "Dată", "Oră", "Complet", "Soluție / Soluționare"].map((h) => (
                                        <th key={h} className="py-2.5 px-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 first:pl-4">
                                            {h}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {sortedTermene.map((t, i) => {
                                    const hasSol = !!(t.solutie || t.solutionare);
                                    return (
                                        <tr
                                            key={i}
                                            className={cn(
                                                "border-b border-slate-100 dark:border-slate-700/50 text-xs",
                                                i === 0 && "bg-blue-50/40 dark:bg-blue-900/10",
                                            )}
                                        >
                                            <td className="py-2.5 pl-4 pr-3 font-mono text-slate-400 dark:text-slate-500">{i + 1}</td>
                                            <td className="py-2.5 pr-3 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">{t.data || "—"}</td>
                                            <td className="py-2.5 pr-3 text-slate-500 dark:text-slate-400">{t.ora || "—"}</td>
                                            <td className="py-2.5 pr-3 text-slate-500 dark:text-slate-400 max-w-[180px] truncate" title={t.complet}>{t.complet || "—"}</td>
                                            <td className="py-2.5 pr-4">
                                                {hasSol ? (
                                                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                                        {t.solutie || t.solutionare}
                                                    </span>
                                                ) : (
                                                    <span className="text-slate-400">—</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </Section>

            {/* ── Footer action ── */}
            <div className="flex justify-start pb-4">
                <button
                    onClick={() => navigate("/dosare")}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:text-blue-600 transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Înapoi la căutare
                </button>
            </div>
        </div>
    );
}
