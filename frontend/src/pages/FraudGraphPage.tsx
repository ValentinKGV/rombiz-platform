import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { AlertTriangle, Orbit, Shield, Eye, Users, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { SectionHeader, DisclaimerBanner } from "@/components/common";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend,
    AreaChart, Area,
    LineChart, Line,
} from "recharts";
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    type Node,
    type Edge,
    MarkerType,
    useNodesState,
    useEdgesState,
    Position,
} from "reactflow";
import "reactflow/dist/style.css";

/* ------------------------------------------------------------------ */
/* Custom node types for fraud graph                                   */
/* ------------------------------------------------------------------ */
function CompanyNode({ data }: { data: { label: string; risk?: string; type?: string } }) {
    const bg =
        data.risk === "HIGH" || data.risk === "CRITICAL"
            ? "bg-red-100 border-red-400"
            : data.risk === "MEDIUM"
                ? "bg-yellow-100 border-yellow-400"
                : "bg-slate-100 border-slate-300";

    return (
        <div className={cn("rounded-lg border-2 px-4 py-2 shadow-sm min-w-[120px] text-center", bg)}>
            <p className="font-exo text-xs font-semibold text-slate-800">{data.label}</p>
            {data.type && <p className="font-rajdhani text-[10px] text-slate-500">{data.type}</p>}
        </div>
    );
}

function PersonNode({ data }: { data: { label: string; role?: string } }) {
    return (
        <div className="rounded-full border-2 border-indigo-300 bg-indigo-50 px-4 py-2 shadow-sm min-w-[100px] text-center">
            <p className="font-exo text-xs font-semibold text-indigo-800">{data.label}</p>
            {data.role && <p className="font-rajdhani text-[10px] text-indigo-500">{data.role}</p>}
        </div>
    );
}

const nodeTypes = {
    company: CompanyNode,
    person: PersonNode,
};

/* ------------------------------------------------------------------ */
/* Convert API graph data to ReactFlow nodes & edges                   */
/* ------------------------------------------------------------------ */
function toReactFlowGraph(apiGraph: { nodes?: any[]; edges?: any[] }) {
    const nodes: Node[] = (apiGraph.nodes || []).map((n: any, i: number) => ({
        id: String(n.id || i),
        type: n.type === "PERSOANA" || n.type === "person" ? "person" : "company",
        position: {
            x: 200 + (i % 5) * 220,
            y: 100 + Math.floor(i / 5) * 160,
        },
        data: {
            label: n.label || n.name || n.denumire || `Nod ${i}`,
            risk: n.risk_level || n.risk,
            type: n.entity_type || n.type,
            role: n.role,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
    }));

    const edges: Edge[] = (apiGraph.edges || []).map((e: any, i: number) => ({
        id: `e-${i}`,
        source: String(e.source || e.from),
        target: String(e.target || e.to),
        label: e.label || e.relationship || e.type,
        type: "smoothstep",
        animated: e.suspicious || false,
        style: {
            stroke: e.suspicious ? "#ef4444" : "#94a3b8",
            strokeWidth: e.suspicious ? 2.5 : 1.5,
        },
        markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12 },
    }));

    return { nodes, edges };
}

/* ------------------------------------------------------------------ */
/* Graph visualization component                                       */
/* ------------------------------------------------------------------ */
function FraudGraph({ graph }: { graph: { nodes?: any[]; edges?: any[] } }) {
    const { nodes: initNodes, edges: initEdges } = useMemo(() => toReactFlowGraph(graph), [graph]);
    const [nodes, , onNodesChange] = useNodesState(initNodes);
    const [edges, , onEdgesChange] = useEdgesState(initEdges);

    return (
        <div className="h-[500px] w-full rounded-lg border bg-white">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
                className="rounded-lg"
            >
                <Background gap={20} size={1} color="#f1f5f9" />
                <Controls />
                <MiniMap
                    nodeStrokeWidth={2}
                    nodeColor={(n) =>
                        n.type === "person" ? "#818cf8" : n.data?.risk === "HIGH" ? "#ef4444" : "#94a3b8"
                    }
                    pannable
                    zoomable
                />
            </ReactFlow>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Demo data for alerts overview                                        */
/* ------------------------------------------------------------------ */
const DEMO_ALERTS = [
    { id: 1, alert_type: "Circular Ownership", descriere: "Lanț circular de proprietate detectat: Alpha SRL → Gamma Import → Epsilon Trade → Alpha SRL", severity: "CRITICAL" },
    { id: 2, alert_type: "Rapid Succession", descriere: "3 firme înființate în 30 zile de aceeași persoană (Ion Popescu)", severity: "HIGH" },
    { id: 3, alert_type: "Shell Company Risk", descriere: "Gamma Import SRL — 0 angajați, sediu virtual, cifră de afaceri 2.3M RON", severity: "HIGH" },
    { id: 4, alert_type: "Unusual Transactions", descriere: "Tranzacții repetitive de valori fixe (49.999 RON) între Alpha SRL și Gamma Import", severity: "MEDIUM" },
    { id: 5, alert_type: "PEP Connection", descriere: "Asociat Maria Ionescu — rudă grad I cu persoană expusă politic", severity: "MEDIUM" },
    { id: 6, alert_type: "Address Anomaly", descriere: "4 firme înregistrate la aceeași adresă: Str. Exemplu 15, București", severity: "LOW" },
];

const MONTHLY_ALERTS = [
    { month: "Oct", critical: 2, high: 5, medium: 8, low: 12 },
    { month: "Nov", critical: 1, high: 7, medium: 10, low: 15 },
    { month: "Dec", critical: 3, high: 4, medium: 6, low: 9 },
    { month: "Ian", critical: 2, high: 8, medium: 12, low: 18 },
    { month: "Feb", critical: 4, high: 6, medium: 9, low: 14 },
    { month: "Mar", critical: 3, high: 9, medium: 11, low: 16 },
];

const RISK_DISTRIBUTION = [
    { name: "Critical", value: 15, color: "#ef4444" },
    { name: "High", value: 39, color: "#f97316" },
    { name: "Medium", value: 56, color: "#eab308" },
    { name: "Low", value: 127, color: "#22c55e" },
];

const ANOMALY_TREND = [
    { month: "Oct", score: 42 },
    { month: "Nov", score: 38 },
    { month: "Dec", score: 55 },
    { month: "Ian", score: 48 },
    { month: "Feb", score: 62 },
    { month: "Mar", score: 58 },
];

const FRAUD_TYPES = [
    { name: "Ownership circular", value: 23, color: "#ef4444" },
    { name: "Shell company", value: 18, color: "#f97316" },
    { name: "Tranzacții suspecte", value: 31, color: "#8b5cf6" },
    { name: "Adresă fictivă", value: 14, color: "#3b82f6" },
    { name: "PEP connections", value: 9, color: "#14b8a6" },
    { name: "Altele", value: 5, color: "#94a3b8" },
];

/* ------------------------------------------------------------------ */
/* Demo Overview Section                                               */
/* ------------------------------------------------------------------ */
function DemoOverview() {
    return (
        <div className="space-y-6">
            {/* KPI summary */}
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[
                    { label: "Companii Monitorizate", value: "237", icon: Eye, color: "text-blue-500", bg: "bg-blue-50" },
                    { label: "Alerte Active", value: "39", icon: AlertTriangle, color: "text-red-500", bg: "bg-red-50" },
                    { label: "Rețele Suspecte", value: "12", icon: Users, color: "text-orange-500", bg: "bg-orange-50" },
                    { label: "Scor Mediu Anomalie", value: "58", icon: Zap, color: "text-violet-500", bg: "bg-violet-50" },
                ].map((kpi) => (
                    <div key={kpi.label} className="card-cosmic flex items-center gap-4 p-5">
                        <div className={cn("rounded-xl p-3", kpi.bg)}>
                            <kpi.icon className={cn("h-6 w-6", kpi.color)} />
                        </div>
                        <div>
                            <p className="font-orbitron text-2xl font-bold text-slate-800">{kpi.value}</p>
                            <p className="font-rajdhani text-xs text-slate-400">{kpi.label}</p>
                        </div>
                    </div>
                ))}
            </div>



            {/* Charts row */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {/* Alerts by month — stacked bar */}
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-xs font-semibold tracking-wide text-slate-700">
                        Alerte pe Lună
                    </h3>
                    <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={MONTHLY_ALERTS}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
                            <Bar dataKey="critical" stackId="a" fill="#ef4444" radius={[0, 0, 0, 0]} name="Critical" />
                            <Bar dataKey="high" stackId="a" fill="#f97316" name="High" />
                            <Bar dataKey="medium" stackId="a" fill="#eab308" name="Medium" />
                            <Bar dataKey="low" stackId="a" fill="#22c55e" radius={[4, 4, 0, 0]} name="Low" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Risk distribution — donut */}
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-xs font-semibold tracking-wide text-slate-700">
                        Distribuție Risc
                    </h3>
                    <ResponsiveContainer width="100%" height={240}>
                        <PieChart>
                            <Pie data={RISK_DISTRIBUTION} cx="50%" cy="45%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                                {RISK_DISTRIBUTION.map((e, i) => <Cell key={i} fill={e.color} />)}
                            </Pie>
                            <Legend verticalAlign="bottom" iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Anomaly trend — area */}
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-xs font-semibold tracking-wide text-slate-700">
                        Trend Scor Anomalie (6 luni)
                    </h3>
                    <ResponsiveContainer width="100%" height={240}>
                        <AreaChart data={ANOMALY_TREND}>
                            <defs>
                                <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} formatter={(v: number) => [`${v}/100`, "Scor"]} />
                            <Area type="monotone" dataKey="score" stroke="#8b5cf6" strokeWidth={2.5} fill="url(#anomalyGrad)" dot={{ r: 4, fill: "#8b5cf6" }} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Second row: fraud types + line chart */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {/* Fraud types — horizontal bar */}
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-xs font-semibold tracking-wide text-slate-700">
                        Tipuri Fraudă Detectate
                    </h3>
                    <div className="space-y-3">
                        {FRAUD_TYPES.map((ft) => {
                            const maxVal = Math.max(...FRAUD_TYPES.map((f) => f.value));
                            return (
                                <div key={ft.name} className="flex items-center gap-3">
                                    <span className="w-36 text-xs text-slate-600 truncate">{ft.name}</span>
                                    <div className="flex-1 h-5 rounded-full bg-slate-100 overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all duration-500"
                                            style={{ width: `${(ft.value / maxVal) * 100}%`, backgroundColor: ft.color }}
                                        />
                                    </div>
                                    <span className="w-8 text-right text-xs font-semibold text-slate-700">{ft.value}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Active alerts over time — line */}
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-xs font-semibold tracking-wide text-slate-700">
                        Evoluție Alerte Active
                    </h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <LineChart data={MONTHLY_ALERTS.map((m) => ({ month: m.month, total: m.critical + m.high + m.medium + m.low, critical: m.critical }))}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                            <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }} />
                            <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4 }} name="Total" />
                            <Line type="monotone" dataKey="critical" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} name="Critical" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Demo alerts table */}
            <div className="card-cosmic">
                <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">
                    Alerte Recente
                </h3>
                <div className="space-y-3">
                    {DEMO_ALERTS.map((alert) => (
                        <div key={alert.id} className="flex items-start gap-3 rounded-lg border p-3">
                            <AlertTriangle
                                className={cn(
                                    "mt-0.5 h-5 w-5 flex-shrink-0",
                                    alert.severity === "CRITICAL" && "text-red-500",
                                    alert.severity === "HIGH" && "text-orange-500",
                                    alert.severity === "MEDIUM" && "text-yellow-500",
                                    alert.severity === "LOW" && "text-green-500",
                                )}
                            />
                            <div className="min-w-0 flex-1">
                                <p className="font-exo font-semibold text-slate-700">{alert.alert_type}</p>
                                <p className="font-rajdhani text-sm text-slate-400">{alert.descriere}</p>
                            </div>
                            <span className={cn(
                                "rounded-full px-2 py-0.5 text-xs font-medium flex-shrink-0",
                                alert.severity === "CRITICAL" && "bg-red-100 text-red-700",
                                alert.severity === "HIGH" && "bg-orange-100 text-orange-700",
                                alert.severity === "MEDIUM" && "bg-yellow-100 text-yellow-700",
                                alert.severity === "LOW" && "bg-green-100 text-green-700",
                            )}>
                                {alert.severity}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Main Page                                                           */
/* ------------------------------------------------------------------ */
export default function FraudGraphPage() {
    const [cuiSearch, setCuiSearch] = useState("");
    const [selectedCui, setSelectedCui] = useState<string | null>(null);

    const { data: profile, isLoading } = useQuery({
        queryKey: ["fraud", selectedCui],
        queryFn: async () => {
            const { data } = await api.get(`/fraud/${selectedCui}/profile`);
            return data;
        },
        enabled: !!selectedCui,
    });

    const { data: graph } = useQuery({
        queryKey: ["fraud", selectedCui, "graph"],
        queryFn: async () => {
            const { data } = await api.get(`/fraud/${selectedCui}/graph`);
            return data;
        },
        enabled: !!selectedCui,
    });

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSelectedCui(cuiSearch);
    };

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Fraud Graph Engine"
                subtitle="Detectare fraudă prin analiza grafurilor de relații"
            />

            <DisclaimerBanner
                title="Aviz Important:"
                text="Rezultatele prezentate sunt suspiciuni algoritmice bazate pe analiza datelor publice. Acestea nu constituie probe sau acuzații și trebuie verificate independent înainte de a lua orice decizie."
            />

            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2">
                <input
                    type="text"
                    placeholder="Introdu CUI pentru analiză fraud..."
                    value={cuiSearch}
                    onChange={(e) => setCuiSearch(e.target.value)}
                    className="input-scifi flex-1"
                />
                <button type="submit" className="btn-cosmic px-6 py-2.5 text-sm">
                    Analizează
                </button>
            </form>

            {isLoading && (
                <div className="flex h-32 items-center justify-center">
                    <div className="relative">
                        <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                    </div>
                </div>
            )}

            {/* Show demo overview when no search has been made */}
            {!selectedCui && !isLoading && <DemoOverview />}

            {profile && (
                <div className="space-y-6">
                    {/* Summary cards */}
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                        <div className="card-cosmic text-center">
                            <Shield className="mx-auto h-8 w-8 text-nebula-500" />
                            <p className="mt-2 font-orbitron text-2xl font-bold text-slate-800">
                                {profile.anomaly_score}
                            </p>
                            <p className="font-rajdhani text-sm text-slate-400">Scor Anomalie</p>
                        </div>
                        <div className="card-cosmic text-center">
                            <p className="font-orbitron text-2xl font-bold text-slate-800">
                                {profile.graph_summary?.nodes || 0}
                            </p>
                            <p className="font-rajdhani text-sm text-slate-400">Noduri Graf</p>
                        </div>
                        <div className="card-cosmic text-center">
                            <p className="font-orbitron text-2xl font-bold text-slate-800">
                                {profile.graph_summary?.edges || 0}
                            </p>
                            <p className="font-rajdhani text-sm text-slate-400">Relații</p>
                        </div>
                        <div className="card-cosmic text-center">
                            <p className="font-orbitron text-2xl font-bold text-slate-800">
                                {profile.alerts?.length || 0}
                            </p>
                            <p className="font-rajdhani text-sm text-slate-400">Alerte</p>
                        </div>
                    </div>

                    {/* Interactive ReactFlow Graph */}
                    {graph && (graph.nodes?.length || graph.edges?.length) ? (
                        <div className="card-cosmic">
                            <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">
                                Graf Relații — Vizualizare Interactivă
                            </h3>
                            <FraudGraph graph={graph} />
                        </div>
                    ) : graph ? (
                        <div className="card-cosmic">
                            <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">
                                Graf Relații
                            </h3>
                            <div className="flex h-48 items-center justify-center text-slate-400">
                                <p>Nu au fost găsite relații de tip graf pentru acest CUI.</p>
                            </div>
                        </div>
                    ) : null}

                    {/* Alerts list */}
                    {profile.alerts?.length > 0 && (
                        <div className="card-cosmic">
                            <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">
                                Alerte Fraud
                            </h3>
                            <div className="space-y-3">
                                {profile.alerts.map(
                                    (alert: {
                                        id: number;
                                        alert_type: string;
                                        descriere: string;
                                        severity: string;
                                    }) => (
                                        <div key={alert.id} className="flex items-start gap-3 rounded-lg border p-3">
                                            <AlertTriangle
                                                className={cn(
                                                    "mt-0.5 h-5 w-5 flex-shrink-0",
                                                    alert.severity === "CRITICAL" && "text-red-500",
                                                    alert.severity === "HIGH" && "text-orange-500",
                                                    alert.severity === "MEDIUM" && "text-yellow-500",
                                                    alert.severity === "LOW" && "text-green-500",
                                                )}
                                            />
                                            <div>
                                                <p className="font-exo font-semibold text-slate-700">
                                                    {alert.alert_type}
                                                </p>
                                                <p className="font-rajdhani text-sm text-slate-400">
                                                    {alert.descriere}
                                                </p>
                                            </div>
                                            <span
                                                className={cn(
                                                    "ml-auto rounded-full px-2 py-0.5 text-xs font-medium flex-shrink-0",
                                                    alert.severity === "CRITICAL" && "bg-red-100 text-red-700",
                                                    alert.severity === "HIGH" && "bg-orange-100 text-orange-700",
                                                    alert.severity === "MEDIUM" && "bg-yellow-100 text-yellow-700",
                                                    alert.severity === "LOW" && "bg-green-100 text-green-700",
                                                )}
                                            >
                                                {alert.severity}
                                            </span>
                                        </div>
                                    ),
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
