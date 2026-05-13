import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
    FileText, Clock, CheckCircle2, AlertTriangle,
    Search, ChevronDown, ChevronUp, Download,
    BarChart3, Building2, CreditCard, Eye,
} from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, AreaChart, Area, Legend,
} from "recharts";

/* ───── Dummy Data ───── */
const FURNIZORI = [
    "MEGA DISTRIBUTION SRL", "TECH SUPPLIES SA", "OFFICE DEPOT SRL",
    "GLOBAL LOGISTICS SA", "PRINT & PAPER SRL", "AUTO SERVICE PLUS SRL",
    "CLEAN SOLUTIONS SRL", "ENERGY PRO SA", "SMART IT SRL", "DELTA MATERIALS SRL",
];

type StatusFactura = "plătită" | "în așteptare" | "scadentă" | "anulată";

interface Factura {
    id: string;
    numar: string;
    furnizor: string;
    cui_furnizor: string;
    data_emitere: string;
    data_scadenta: string;
    valoare: number;
    tva: number;
    total: number;
    status: StatusFactura;
    moneda: string;
    descriere: string;
}

const STATUS_STYLES: Record<StatusFactura, { bg: string; text: string; dot: string }> = {
    "plătită": { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
    "în așteptare": { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
    "scadentă": { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
    "anulată": { bg: "bg-slate-50", text: "text-slate-500", dot: "bg-slate-400" },
};

const generateFacturi = (): Factura[] => {
    const statuses: StatusFactura[] = ["plătită", "în așteptare", "scadentă", "anulată"];
    const facturi: Factura[] = [];
    const descriptions = [
        "Servicii consultanță IT", "Materiale birou", "Transport marfă", "Servicii curățenie",
        "Licențe software", "Mentenanță echipamente", "Consumabile imprimantă", "Energie electrică",
        "Servicii hosting", "Piese auto", "Materiale construcții", "Servicii contabilitate",
        "Echipamente protecție", "Servicii marketing", "Abonament telecomunicații",
    ];

    for (let i = 0; i < 42; i++) {
        const val = Math.round((500 + Math.random() * 25000) * 100) / 100;
        const tva = Math.round(val * 0.19 * 100) / 100;
        const month = Math.floor(Math.random() * 6);
        const day = 1 + Math.floor(Math.random() * 28);
        const emitere = `2026-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const scDay = Math.min(day + 30, 28);
        const scMonth = month + 1 >= 6 ? month + 2 : month + 2;
        const scadenta = `2026-${String(Math.min(scMonth, 12)).padStart(2, "0")}-${String(scDay).padStart(2, "0")}`;

        facturi.push({
            id: `f-${i + 1}`,
            numar: `FRN-${2026}${String(i + 1).padStart(4, "0")}`,
            furnizor: FURNIZORI[i % FURNIZORI.length],
            cui_furnizor: String(10000000 + Math.floor(Math.random() * 90000000)),
            data_emitere: emitere,
            data_scadenta: scadenta,
            valoare: val,
            tva,
            total: Math.round((val + tva) * 100) / 100,
            status: statuses[i < 22 ? 0 : i < 32 ? 1 : i < 38 ? 2 : 3],
            moneda: "RON",
            descriere: descriptions[i % descriptions.length],
        });
    }
    return facturi;
};

const FACTURI = generateFacturi();

const MONTHLY_DATA = [
    { luna: "Ian", platite: 45200, asteptare: 12300, scadente: 4100 },
    { luna: "Feb", platite: 38700, asteptare: 18600, scadente: 2800 },
    { luna: "Mar", platite: 52100, asteptare: 8900, scadente: 6200 },
    { luna: "Apr", platite: 41300, asteptare: 22100, scadente: 3500 },
    { luna: "Mai", platite: 61800, asteptare: 15400, scadente: 5100 },
    { luna: "Jun", platite: 48500, asteptare: 19200, scadente: 7800 },
];

const TOP_FURNIZORI = [
    { name: "MEGA DISTRIBUTION SRL", value: 87500, color: "#6366f1" },
    { name: "TECH SUPPLIES SA", value: 62300, color: "#8b5cf6" },
    { name: "GLOBAL LOGISTICS SA", value: 45800, color: "#a855f7" },
    { name: "ENERGY PRO SA", value: 38200, color: "#c084fc" },
    { name: "SMART IT SRL", value: 29100, color: "#d8b4fe" },
    { name: "Alții", value: 52400, color: "#e2e8f0" },
];

const CASHFLOW_TREND = [
    { luna: "Ian", intrari: 78000, iesiri: 61600 },
    { luna: "Feb", intrari: 82000, iesiri: 60100 },
    { luna: "Mar", intrari: 91000, iesiri: 67200 },
    { luna: "Apr", intrari: 85000, iesiri: 66900 },
    { luna: "Mai", intrari: 95000, iesiri: 82300 },
    { luna: "Jun", intrari: 88000, iesiri: 75500 },
];

const formatRON = (v: number) => v.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

type SortKey = "numar" | "furnizor" | "data_emitere" | "total" | "status";
type TabFilter = "toate" | "plătită" | "în așteptare" | "scadentă";

export default function FacturiFurnizoriPage() {
    const [activeTab, setActiveTab] = useState<TabFilter>("toate");
    const [searchTerm, setSearchTerm] = useState("");
    const [sortKey, setSortKey] = useState<SortKey>("data_emitere");
    const [sortAsc, setSortAsc] = useState(false);
    const [page, setPage] = useState(1);
    const perPage = 10;

    const filtered = useMemo(() => {
        let list = [...FACTURI];
        if (activeTab !== "toate") list = list.filter((f) => f.status === activeTab);
        if (searchTerm) {
            const q = searchTerm.toLowerCase();
            list = list.filter((f) =>
                f.furnizor.toLowerCase().includes(q) ||
                f.numar.toLowerCase().includes(q) ||
                f.cui_furnizor.includes(q)
            );
        }
        list.sort((a, b) => {
            const av = a[sortKey], bv = b[sortKey];
            if (typeof av === "number" && typeof bv === "number") return sortAsc ? av - bv : bv - av;
            return sortAsc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
        });
        return list;
    }, [activeTab, searchTerm, sortKey, sortAsc]);

    const paged = filtered.slice((page - 1) * perPage, page * perPage);
    const totalPages = Math.ceil(filtered.length / perPage);

    const handleSort = (key: SortKey) => {
        if (sortKey === key) setSortAsc(!sortAsc);
        else { setSortKey(key); setSortAsc(false); }
        setPage(1);
    };

    const SortIcon = ({ col }: { col: SortKey }) => {
        if (sortKey !== col) return null;
        return sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />;
    };

    /* KPIs */
    const totalVal = FACTURI.reduce((s, f) => s + f.total, 0);
    const platiteVal = FACTURI.filter((f) => f.status === "plătită").reduce((s, f) => s + f.total, 0);
    const asteptareVal = FACTURI.filter((f) => f.status === "în așteptare").reduce((s, f) => s + f.total, 0);
    const scadenteVal = FACTURI.filter((f) => f.status === "scadentă").reduce((s, f) => s + f.total, 0);

    const kpis = [
        { label: "Total Facturi", value: FACTURI.length, sub: `${formatRON(totalVal)} RON`, icon: FileText, color: "from-blue-500 to-indigo-600" },
        { label: "Plătite", value: FACTURI.filter((f) => f.status === "plătită").length, sub: `${formatRON(platiteVal)} RON`, icon: CheckCircle2, color: "from-emerald-500 to-green-600" },
        { label: "În Așteptare", value: FACTURI.filter((f) => f.status === "în așteptare").length, sub: `${formatRON(asteptareVal)} RON`, icon: Clock, color: "from-amber-500 to-orange-600" },
        { label: "Scadente", value: FACTURI.filter((f) => f.status === "scadentă").length, sub: `${formatRON(scadenteVal)} RON`, icon: AlertTriangle, color: "from-red-500 to-rose-600" },
    ];

    const tabs: { key: TabFilter; label: string; count: number }[] = [
        { key: "toate", label: "Toate", count: FACTURI.length },
        { key: "plătită", label: "Plătite", count: FACTURI.filter((f) => f.status === "plătită").length },
        { key: "în așteptare", label: "În Așteptare", count: FACTURI.filter((f) => f.status === "în așteptare").length },
        { key: "scadentă", label: "Scadente", count: FACTURI.filter((f) => f.status === "scadentă").length },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-orbitron text-2xl font-bold tracking-wide text-dragon">Facturi Furnizori</h1>
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        Centralizare facturi din aplicația de facturare
                    </p>
                </div>
                <button className="flex items-center gap-2 rounded-xl border border-nebula-200 bg-white px-4 py-2 font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:bg-nebula-50 transition-colors shadow-sm">
                    <Download className="h-4 w-4" />
                    Export CSV
                </button>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {kpis.map((k) => {
                    const Icon = k.icon;
                    return (
                        <div key={k.label} className="card-cosmic p-4 flex items-center gap-4">
                            <div className={cn("flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg", k.color)}>
                                <Icon className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">{k.label}</p>
                                <p className="font-orbitron text-xl font-bold text-slate-800">{k.value}</p>
                                <p className="font-rajdhani text-xs text-slate-400">{k.sub}</p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Stacked bar – facturi pe luna */}
                <div className="card-cosmic p-5 lg:col-span-2">
                    <div className="flex items-center gap-2 mb-4">
                        <BarChart3 className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700">Valoare Facturi pe Lună (RON)</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={260}>
                        <BarChart data={MONTHLY_DATA} barGap={2}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="luna" tick={{ fontSize: 12, fontFamily: "Rajdhani" }} />
                            <YAxis tick={{ fontSize: 11, fontFamily: "Rajdhani" }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                            <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 13 }} formatter={(v: number) => formatRON(v) + " RON"} />
                            <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12 }} />
                            <Bar dataKey="platite" stackId="a" fill="#10b981" name="Plătite" />
                            <Bar dataKey="asteptare" stackId="a" fill="#f59e0b" name="În Așteptare" />
                            <Bar dataKey="scadente" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} name="Scadente" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Donut – top furnizori */}
                <div className="card-cosmic p-5">
                    <div className="flex items-center gap-2 mb-4">
                        <Building2 className="h-4 w-4 text-violet-500" />
                        <h3 className="font-orbitron text-sm font-semibold text-slate-700">Top Furnizori</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                            <Pie data={TOP_FURNIZORI} cx="50%" cy="50%" innerRadius={45} outerRadius={78} paddingAngle={3} dataKey="value">
                                {TOP_FURNIZORI.map((d, i) => (
                                    <Cell key={i} fill={d.color} stroke="white" strokeWidth={2} />
                                ))}
                            </Pie>
                            <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 12 }} formatter={(v: number) => formatRON(v) + " RON"} />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 justify-center">
                        {TOP_FURNIZORI.map((d) => (
                            <span key={d.name} className="flex items-center gap-1 text-[10px] font-rajdhani text-slate-500">
                                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                                {d.name.length > 18 ? d.name.substring(0, 18) + "…" : d.name}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Cash-flow trend */}
            <div className="card-cosmic p-5">
                <div className="flex items-center gap-2 mb-4">
                    <CreditCard className="h-4 w-4 text-emerald-500" />
                    <h3 className="font-orbitron text-sm font-semibold text-slate-700">Cash-flow Furnizori (Intrări vs. Ieșiri)</h3>
                </div>
                <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={CASHFLOW_TREND}>
                        <defs>
                            <linearGradient id="cfIn" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="cfOut" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="luna" tick={{ fontSize: 12, fontFamily: "Rajdhani" }} />
                        <YAxis tick={{ fontSize: 11, fontFamily: "Rajdhani" }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                        <Tooltip contentStyle={{ borderRadius: 12, fontFamily: "Exo 2", fontSize: 13 }} formatter={(v: number) => formatRON(v) + " RON"} />
                        <Legend wrapperStyle={{ fontFamily: "Rajdhani", fontSize: 12 }} />
                        <Area type="monotone" dataKey="intrari" stroke="#10b981" strokeWidth={2} fill="url(#cfIn)" name="Încasări" />
                        <Area type="monotone" dataKey="iesiri" stroke="#ef4444" strokeWidth={2} fill="url(#cfOut)" name="Plăți Furnizori" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Filter Tabs + Search */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-1 rounded-xl bg-slate-100/80 p-1">
                    {tabs.map((t) => (
                        <button
                            key={t.key}
                            onClick={() => { setActiveTab(t.key); setPage(1); }}
                            className={cn(
                                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider transition-all",
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
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Caută furnizor, nr. factură, CUI..."
                        value={searchTerm}
                        onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
                        className="w-64 rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-4 font-exo text-sm text-slate-700 placeholder:text-slate-300 focus:border-nebula-300 focus:outline-none focus:ring-2 focus:ring-nebula-100 transition-all"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="card-cosmic overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-slate-100 bg-slate-50/60">
                                {([
                                    ["numar", "Nr. Factură"],
                                    ["furnizor", "Furnizor"],
                                    ["data_emitere", "Data Emitere"],
                                    ["total", "Total (RON)"],
                                    ["status", "Status"],
                                ] as [SortKey, string][]).map(([key, label]) => (
                                    <th
                                        key={key}
                                        onClick={() => handleSort(key)}
                                        className="cursor-pointer px-4 py-3 text-left font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-500 hover:text-nebula-600 transition-colors select-none"
                                    >
                                        <span className="flex items-center gap-1">
                                            {label} <SortIcon col={key} />
                                        </span>
                                    </th>
                                ))}
                                <th className="px-4 py-3 text-right font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-500">
                                    Acțiuni
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {paged.map((f) => {
                                const st = STATUS_STYLES[f.status];
                                return (
                                    <tr key={f.id} className="border-b border-slate-50 hover:bg-nebula-50/30 transition-colors">
                                        <td className="px-4 py-3">
                                            <span className="font-orbitron text-xs font-bold text-slate-700">{f.numar}</span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <p className="font-exo text-sm font-medium text-slate-700">{f.furnizor}</p>
                                            <p className="font-rajdhani text-[11px] text-slate-400">CUI: {f.cui_furnizor} · {f.descriere}</p>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="font-rajdhani text-sm text-slate-600">{f.data_emitere}</span>
                                            <p className="font-rajdhani text-[11px] text-slate-400">Scadență: {f.data_scadenta}</p>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="font-orbitron text-sm font-bold text-slate-800">{formatRON(f.total)}</span>
                                            <p className="font-rajdhani text-[11px] text-slate-400">TVA: {formatRON(f.tva)}</p>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-rajdhani font-semibold uppercase", st.bg, st.text)}>
                                                <span className={cn("h-1.5 w-1.5 rounded-full", st.dot)} />
                                                {f.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <button className="rounded-lg p-1.5 text-slate-400 hover:bg-nebula-50 hover:text-nebula-600 transition-colors" title="Vizualizare">
                                                <Eye className="h-4 w-4" />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
                        <p className="font-rajdhani text-sm text-slate-400">
                            {filtered.length} facturi · Pagina {page} din {totalPages}
                        </p>
                        <div className="flex gap-1">
                            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                                <button
                                    key={p}
                                    onClick={() => setPage(p)}
                                    className={cn(
                                        "h-8 w-8 rounded-lg font-rajdhani text-sm font-semibold transition-all",
                                        page === p
                                            ? "bg-nebula-500 text-white shadow-sm"
                                            : "text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                                    )}
                                >
                                    {p}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
