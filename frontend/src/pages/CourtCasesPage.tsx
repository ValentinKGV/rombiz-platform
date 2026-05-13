import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import {
    Search, Scale, ChevronDown, ChevronUp, Loader2,
    Calendar, ChevronLeft, ChevronRight, X, Filter,
    User, Building2, AlertCircle, ExternalLink,
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
interface SearchResult {
    total: number;
    page: number;
    page_size: number;
    dosare: Dosar[];
}

/* ── Constants ───────────────────────────────────────────────── */
const TIP_CAUTARE_OPTIONS = [
    { value: "parte", label: "Cauta parte" },
    { value: "obiect", label: "Obiect" },
    { value: "solutie", label: "În soluție" },
    { value: "cui", label: "După CUI" },
] as const;

const CALITATE_OPTIONS = [
    "Orice Calitate", "Creditor", "Debitor", "Intimat",
    "Petent", "Reclamant", "Parat", "Inculpat",
    "Contestator", "Condamnat",
];

const INSTANTE_OPTIONS = ["ICCJ", "Curte De Apel", "Tribunal", "Judecatorie"];
const MATERII_OPTIONS = [
    "Civil", "Litigii Munca", "Litpro", "Caf",
    "Proprietate Intelectuala", "Faliment", "Asigurari Sociale",
    "Minori Si Familie", "Drept Maritim", "Comercial", "Penal", "Alte Materii",
];
const STADII_OPTIONS = ["Recurs", "Apel", "Fond"];

const PAGE_SIZE = 15;

/* ── CheckboxGroup ───────────────────────────────────────────── */
function CheckboxGroup({
    title, options, selected, onChange,
}: {
    title: string;
    options: string[];
    selected: string[];
    onChange: (next: string[]) => void;
}) {
    const allSelected = options.every((o) => selected.includes(o));

    const toggle = (opt: string) =>
        onChange(
            selected.includes(opt)
                ? selected.filter((s) => s !== opt)
                : [...selected, opt],
        );

    const toggleAll = () => onChange(allSelected ? [] : [...options]);

    return (
        <div>
            <h4 className="mb-3 text-base font-semibold text-blue-600 dark:text-blue-400">
                {title}
            </h4>
            <div className="flex flex-wrap gap-x-8 gap-y-2">
                <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                    <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleAll}
                        className="h-4 w-4 accent-blue-600"
                    />
                    Deselectează Tot
                </label>
                {options.map((opt) => (
                    <label
                        key={opt}
                        className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-300"
                    >
                        <input
                            type="checkbox"
                            checked={selected.includes(opt)}
                            onChange={() => toggle(opt)}
                            className="h-4 w-4 accent-blue-600"
                        />
                        {opt}
                    </label>
                ))}
            </div>
        </div>
    );
}

/* ── Advanced Filters Panel ──────────────────────────────────── */
interface AdvancedFilters {
    dataStart: string;
    dataEnd: string;
    instante: string[];
    materii: string[];
    stadii: string[];
}

const defaultAdvanced: AdvancedFilters = {
    dataStart: "",
    dataEnd: "",
    instante: [...INSTANTE_OPTIONS],
    materii: [...MATERII_OPTIONS],
    stadii: [...STADII_OPTIONS],
};

function AdvancedFiltersPanel({
    open,
    filters,
    onApply,
    onClose,
}: {
    open: boolean;
    filters: AdvancedFilters;
    onApply: (f: AdvancedFilters) => void;
    onClose: () => void;
}) {
    const [draft, setDraft] = useState<AdvancedFilters>(filters);

    if (!open) return null;

    return (
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-6 shadow-lg dark:border-slate-700 dark:bg-slate-800/90">
            <h3 className="mb-6 text-lg font-bold text-slate-800 dark:text-slate-100">
                Filtre Avansate
            </h3>

            {/* Date range */}
            <div className="mb-6">
                <h4 className="mb-3 text-base font-semibold text-blue-600 dark:text-blue-400">
                    Filtrare dată
                </h4>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {(["dataStart", "dataEnd"] as const).map((field) => (
                        <div key={field}>
                            <label className="mb-1 block text-xs text-slate-500 dark:text-slate-400">
                                {field === "dataStart" ? "Selectează data de început" : "Selectează data de sfârșit"}
                            </label>
                            <div className="relative">
                                <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 pointer-events-none" />
                                <input
                                    type="date"
                                    value={draft[field]}
                                    onChange={(e) => setDraft((d) => ({ ...d, [field]: e.target.value }))}
                                    className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm
                                               focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-300
                                               dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200"
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="border-t border-slate-100 dark:border-slate-700/60" />

            {/* Tipul Instanței */}
            <div className="mb-6 mt-5">
                <CheckboxGroup
                    title="Tipul Instanței"
                    options={INSTANTE_OPTIONS}
                    selected={draft.instante}
                    onChange={(v) => setDraft((d) => ({ ...d, instante: v }))}
                />
            </div>

            <div className="border-t border-slate-100 dark:border-slate-700/60" />

            {/* Materia juridică */}
            <div className="mb-6 mt-5">
                <CheckboxGroup
                    title="Materia juridică"
                    options={MATERII_OPTIONS}
                    selected={draft.materii}
                    onChange={(v) => setDraft((d) => ({ ...d, materii: v }))}
                />
            </div>

            <div className="border-t border-slate-100 dark:border-slate-700/60" />

            {/* Stadiul Procesual */}
            <div className="mb-6 mt-5">
                <CheckboxGroup
                    title="Stadiul Procesual"
                    options={STADII_OPTIONS}
                    selected={draft.stadii}
                    onChange={(v) => setDraft((d) => ({ ...d, stadii: v }))}
                />
            </div>

            {/* Action buttons */}
            <div className="flex items-center justify-between border-t border-slate-200 pt-4 dark:border-slate-700">
                <button
                    onClick={() => setDraft(defaultAdvanced)}
                    className="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50
                               dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                    Resetează filtrele
                </button>
                <div className="flex gap-2">
                    <button
                        onClick={onClose}
                        className="rounded-lg bg-slate-500 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600"
                    >
                        Renunță
                    </button>
                    <button
                        onClick={() => { onApply(draft); onClose(); }}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                    >
                        Aplică și închide
                    </button>
                </div>
            </div>
        </div>
    );
}

/* ── helpers ─────────────────────────────────────────────────── */
function parseRoDate(s: string): number {
    if (!s) return 0;
    const p = s.split(".");
    if (p.length === 3) return new Date(+p[2], +p[1] - 1, +p[0]).getTime();
    const t = new Date(s).getTime();
    return isNaN(t) ? 0 : t;
}

/* ── Dosar Row ───────────────────────────────────────────────── */
function DosarRow({ dosar, onDetails }: { dosar: Dosar; onDetails: () => void }) {
    const [expanded, setExpanded] = useState(false);

    return (
        <>
            <tr
                onClick={() => setExpanded((e) => !e)}
                className={cn(
                    "cursor-pointer border-b border-slate-100 transition-colors hover:bg-blue-50/40",
                    "dark:border-slate-700/50 dark:hover:bg-blue-900/10",
                    expanded && "bg-blue-50/60 dark:bg-blue-900/20",
                )}
            >
                <td className="py-3 pl-4 pr-3">
                    <span className="font-mono text-xs font-semibold text-blue-700 dark:text-blue-400">
                        {dosar.numar || "—"}
                    </span>
                </td>
                <td className="py-3 pr-3 text-xs text-slate-600 dark:text-slate-300">
                    {dosar.instanta || "—"}
                </td>
                <td className="py-3 pr-3 text-xs text-slate-600 dark:text-slate-300 max-w-[160px] truncate" title={dosar.obiect}>
                    {dosar.obiect || "—"}
                </td>
                <td className="py-3 pr-3 text-xs text-slate-500 dark:text-slate-400">
                    {dosar.materie || "—"}
                </td>
                <td className="py-3 pr-3">
                    {dosar.stadiu ? (
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                            {dosar.stadiu}
                        </span>
                    ) : <span className="text-xs text-slate-400">—</span>}
                </td>
                <td className="py-3 pr-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    {dosar.data_dosar || "—"}
                </td>
                <td className="py-3 pr-4 text-center">
                    {expanded
                        ? <ChevronUp className="h-4 w-4 text-slate-400 inline" />
                        : <ChevronDown className="h-4 w-4 text-slate-400 inline" />}
                </td>
            </tr>

            {expanded && (
                <tr className="bg-slate-50/80 dark:bg-slate-800/60">
                    <td colSpan={7} className="px-6 pb-5 pt-3">
                        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                            {/* Parties */}
                            {dosar.parti.length > 0 && (
                                <div>
                                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                        Părți
                                    </p>
                                    <div className="space-y-1.5">
                                        {dosar.parti.map((p, i) => (
                                            <div key={i} className="flex items-center gap-2 text-xs">
                                                <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                                                    {p.calitate || "Parte"}
                                                </span>
                                                <span className="text-slate-700 dark:text-slate-200">{p.denumire || "—"}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Hearings */}
                            {dosar.termene.length > 0 && (
                                <div>
                                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                        Termene ({dosar.termene.length})
                                    </p>
                                    <div className="space-y-1.5">
                                        {dosar.termene.slice(0, 5).map((t, i) => (
                                            <div
                                                key={i}
                                                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
                                            >
                                                <span className="font-semibold text-slate-700 dark:text-slate-200">
                                                    {t.data}
                                                    {t.ora && ` • ${t.ora}`}
                                                </span>
                                                {t.complet && (
                                                    <span className="ml-2 text-slate-500">— {t.complet}</span>
                                                )}
                                                {(t.solutie || t.solutionare) && (
                                                    <p className="mt-0.5 text-emerald-600 dark:text-emerald-400">
                                                        {t.solutie || t.solutionare}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                        {dosar.termene.length > 5 && (
                                            <p className="text-[10px] text-slate-400 pl-1">
                                                +{dosar.termene.length - 5} termene suplimentare
                                            </p>
                                        )}
                                    </div>
                                </div>
                            )}

                            {dosar.parti.length === 0 && dosar.termene.length === 0 && (
                                <p className="text-xs text-slate-400">Nu există detalii suplimentare.</p>
                            )}
                        </div>

                        {/* Details button */}
                        <div className="mt-4 flex justify-end">
                            <button
                                onClick={(e) => { e.stopPropagation(); onDetails(); }}
                                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
                            >
                                <ExternalLink className="h-4 w-4" />
                                Detalii Suplimentare
                            </button>
                        </div>
                    </td>
                </tr>
            )}
        </>
    );
}

/* ── Main Page ───────────────────────────────────────────────── */
export default function CourtCasesPage() {
    const navigate = useNavigate();
    const [numeParte, setNumeParte] = useState("");
    const [numarDosar, setNumarDosar] = useState("");
    const [tipCautare, setTipCautare] = useState("parte");
    const [calitate, setCalitate] = useState("Orice Calitate");

    const [showAdvanced, setShowAdvanced] = useState(false);
    const [appliedFilters, setAppliedFilters] = useState<AdvancedFilters>(defaultAdvanced);

    const [page, setPage] = useState(1);
    const [submitted, setSubmitted] = useState<{
        q: string;
        tip: string;
        calitate: string;
        filters: AdvancedFilters;
    } | null>(null);

    const handleSearch = useCallback(() => {
        const q = numarDosar.trim() || numeParte.trim();
        if (!q) return;
        const tip = numarDosar.trim() ? "numar" : tipCautare;
        setSubmitted({ q, tip, calitate, filters: appliedFilters });
        setPage(1);
    }, [numarDosar, numeParte, tipCautare, calitate, appliedFilters]);

    const buildParams = () => {
        if (!submitted) return null;
        const { q, tip, calitate: cal, filters } = submitted;
        const params: Record<string, string | number> = {
            q,
            tip_cautare: tip,
            page,
            page_size: PAGE_SIZE,
        };
        if (cal && cal !== "Orice Calitate") params.calitate = cal;
        if (filters.instante.length && filters.instante.length < INSTANTE_OPTIONS.length) {
            params.instante = filters.instante.join(",");
        }
        if (filters.materii.length && filters.materii.length < MATERII_OPTIONS.length) {
            params.materii = filters.materii.join(",");
        }
        if (filters.stadii.length && filters.stadii.length < STADII_OPTIONS.length) {
            params.stadii = filters.stadii.join(",");
        }
        return params;
    };

    const params = buildParams();

    const { data, isLoading, isFetching, error } = useQuery<SearchResult>({
        queryKey: ["dosare-search", params],
        queryFn: async () => (await api.get("/dosare/search", { params: params! })).data,
        enabled: params !== null,
        staleTime: 60_000,
        retry: false,
    });

    const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

    const activeFilterCount = [
        !!appliedFilters.dataStart,
        !!appliedFilters.dataEnd,
        appliedFilters.instante.length < INSTANTE_OPTIONS.length,
        appliedFilters.materii.length < MATERII_OPTIONS.length,
        appliedFilters.stadii.length < STADII_OPTIONS.length,
    ].filter(Boolean).length;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="section-header">
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                        Motor Căutare Dosare
                    </h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Căutare dosare judecătorești · Portal Instanțe România
                    </p>
                </div>
                <span className="flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                    <Scale className="h-3.5 w-3.5" />
                    Gratuit
                </span>
            </div>

            {/* Search card */}
            <div className="rounded-xl border border-slate-200/60 bg-white p-6 shadow-sm dark:border-slate-700/60 dark:bg-slate-800">

                {/* Row 1: name input + Cauta parte + Calitate */}
                <div className="flex flex-wrap gap-3">
                    <div className="relative min-w-[220px] flex-1">
                        <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        <input
                            type="text"
                            placeholder="Introduceți numele, obiectul sau CUI..."
                            value={numeParte}
                            onChange={(e) => setNumeParte(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                            className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-sm
                                       focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-300
                                       dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:placeholder-slate-400"
                        />
                    </div>

                    <select
                        value={tipCautare}
                        onChange={(e) => setTipCautare(e.target.value)}
                        disabled={!!numarDosar.trim()}
                        className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-medium text-slate-700
                                   focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-300
                                   disabled:opacity-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200"
                    >
                        {TIP_CAUTARE_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                    </select>

                    <select
                        value={calitate}
                        onChange={(e) => setCalitate(e.target.value)}
                        className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-medium text-slate-700
                                   focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-300
                                   dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200"
                    >
                        {CALITATE_OPTIONS.map((o) => (
                            <option key={o} value={o}>{o}</option>
                        ))}
                    </select>
                </div>

                {/* Row 2: case number + advanced toggle + search button */}
                <div className="mt-3 flex flex-wrap items-center gap-3">
                    <div className="relative min-w-[220px] flex-1">
                        <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        <input
                            type="text"
                            placeholder="Număr Dosar (ex: 1234/123/2024)"
                            value={numarDosar}
                            onChange={(e) => setNumarDosar(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                            className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-8 text-sm
                                       focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-300
                                       dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:placeholder-slate-400"
                        />
                        {numarDosar && (
                            <button
                                onClick={() => setNumarDosar("")}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2"
                            >
                                <X className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600" />
                            </button>
                        )}
                    </div>

                    <button
                        onClick={() => setShowAdvanced((s) => !s)}
                        className={cn(
                            "flex items-center gap-1.5 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors",
                            showAdvanced || activeFilterCount > 0
                                ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                                : "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300",
                        )}
                    >
                        <Filter className="h-4 w-4" />
                        Filtre Avansate
                        {activeFilterCount > 0 && (
                            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                                {activeFilterCount}
                            </span>
                        )}
                        {showAdvanced
                            ? <ChevronUp className="h-3.5 w-3.5" />
                            : <ChevronDown className="h-3.5 w-3.5" />}
                    </button>

                    <button
                        onClick={handleSearch}
                        disabled={!numeParte.trim() && !numarDosar.trim()}
                        className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white
                                   shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                    >
                        {(isLoading || isFetching)
                            ? <Loader2 className="h-4 w-4 animate-spin" />
                            : <Search className="h-4 w-4" />}
                        Caută Dosare
                    </button>
                </div>

                {/* Advanced filters panel */}
                <AdvancedFiltersPanel
                    open={showAdvanced}
                    filters={appliedFilters}
                    onApply={setAppliedFilters}
                    onClose={() => setShowAdvanced(false)}
                />
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
                    <AlertCircle className="h-5 w-5 shrink-0" />
                    <span>
                        {(error as { response?: { data?: { detail?: string } } })
                            ?.response?.data?.detail
                            ?? "Eroare la comunicarea cu serviciul portal.just.ro. Verificați conexiunea și încercați din nou."}
                    </span>
                </div>
            )}

            {/* Results table */}
            {data && (
                <div className="rounded-xl border border-slate-200/60 bg-white shadow-sm dark:border-slate-700/60 dark:bg-slate-800">
                    <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                            {data.total > 0
                                ? `${data.total} dosar${data.total === 1 ? "" : "e"} găsite`
                                : "Niciun dosar găsit"}
                        </p>
                        <p className="text-xs text-slate-400">
                            Sursă: portalquery.just.ro · Date publice
                        </p>
                    </div>

                    {data.dosare.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                            <Scale className="mb-3 h-10 w-10 opacity-30" />
                            <p className="text-sm">Niciun rezultat pentru criteriile selectate</p>
                        </div>
                    ) : (
                        <>
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/60">
                                            {["Număr Dosar", "Instanță", "Obiect", "Materie", "Stadiu", "Dată Dosar", ""].map((h) => (
                                                <th
                                                    key={h}
                                                    className="py-3 pr-3 text-left text-xs font-semibold text-slate-600 first:pl-4 dark:text-slate-300"
                                                >
                                                    {h}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {[...data.dosare]
                                            .sort((a, b) => parseRoDate(b.data_dosar) - parseRoDate(a.data_dosar))
                                            .map((dosar, i) => (
                                                <DosarRow
                                                    key={`${dosar.numar}-${i}`}
                                                    dosar={dosar}
                                                    onDetails={() => navigate("/dosare/detalii", { state: { dosar } })}
                                                />
                                            ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4 dark:border-slate-700">
                                    <span className="text-xs text-slate-400">
                                        Pagina {page} din {totalPages} · {data.total} total
                                    </span>
                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                                            disabled={page === 1}
                                            className="rounded-lg p-1.5 text-slate-500 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-30 dark:hover:bg-blue-900/20"
                                        >
                                            <ChevronLeft className="h-4 w-4" />
                                        </button>
                                        {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                                            const p = totalPages <= 7
                                                ? i + 1
                                                : page <= 4
                                                    ? i + 1
                                                    : page >= totalPages - 3
                                                        ? totalPages - 6 + i
                                                        : page - 3 + i;
                                            return (
                                                <button
                                                    key={p}
                                                    onClick={() => setPage(p)}
                                                    className={cn(
                                                        "h-7 min-w-[1.75rem] rounded-lg text-xs font-medium transition-colors",
                                                        p === page
                                                            ? "bg-blue-600 text-white shadow-sm"
                                                            : "text-slate-500 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20",
                                                    )}
                                                >
                                                    {p}
                                                </button>
                                            );
                                        })}
                                        <button
                                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                            disabled={page >= totalPages}
                                            className="rounded-lg p-1.5 text-slate-500 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-30 dark:hover:bg-blue-900/20"
                                        >
                                            <ChevronRight className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* Empty / initial state */}
            {!submitted && !data && (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 py-20 text-slate-400 dark:border-slate-700">
                    <Scale className="mb-4 h-12 w-12 opacity-25" />
                    <p className="text-base font-medium">Introduceți un termen de căutare</p>
                    <p className="mt-1 text-sm opacity-70">
                        Căutați după numele unei persoane sau firme, numărul dosarului sau CUI
                    </p>
                </div>
            )}
        </div>
    );
}
