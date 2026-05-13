import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    Network, Users, Shield, GitBranch, Clock,
    Search, AlertTriangle, Target,
} from "lucide-react";
import api from "../lib/api";
import { SectionHeader, StatCard, LoadingSpinner, TabNav, Badge, DisclaimerBanner } from "../components/common";
import type { TabItem } from "../components/common";

const TABS: TabItem[] = [
    { id: "ubo", label: "UBO", icon: Users },
    { id: "contagion", label: "Contagiune", icon: AlertTriangle },
    { id: "directors", label: "Directori", icon: Network },
    { id: "group", label: "Grup Corporativ", icon: GitBranch },
    { id: "timeline", label: "Cronologie", icon: Clock },
];

export default function RelationshipsPage() {
    const [tab, setTab] = useState("ubo");
    const [companyId, setCompanyId] = useState("");

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Relationship Intelligence"
                subtitle="Beneficiari reali, riscuri de contagiune, directori comuni, structuri de grup"
            />
            <TabNav tabs={TABS} activeTab={tab} onTabChange={setTab} variant="pills" />

            <div className="card-cosmic p-4">
                <label className="text-xs text-cyan-400/70 mb-1 block">Company ID</label>
                <input
                    type="number"
                    className="input-scifi w-full"
                    placeholder="Introdu ID-ul companiei..."
                    value={companyId}
                    onChange={e => setCompanyId(e.target.value)}
                />
            </div>

            {!companyId ? (
                <div className="card-cosmic p-12 text-center">
                    <Search className="w-12 h-12 text-cyan-500/30 mx-auto mb-4" />
                    <p className="text-cyan-300/50">Introdu un Company ID pentru a explora relațiile</p>
                </div>
            ) : (
                <>
                    {tab === "ubo" && <UBOTab companyId={Number(companyId)} />}
                    {tab === "contagion" && <ContagionTab companyId={Number(companyId)} />}
                    {tab === "directors" && <DirectorsTab companyId={Number(companyId)} />}
                    {tab === "group" && <GroupTab companyId={Number(companyId)} />}
                    {tab === "timeline" && <TimelineTab companyId={Number(companyId)} />}
                </>
            )}
        </div>
    );
}

/* ── UBO Tab ──────────────────────────────────────────────────────── */
function UBOTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery({
        queryKey: ["ubo", companyId],
        queryFn: () => api.get(`/relationships/ubo/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Descoperire UBO..." />;
    if (!data) return null;
    if (data.error) return <DisclaimerBanner variant="warning">{data.error}</DisclaimerBanner>;

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard title="UBO Identificați" value={data.ubo_count} icon={Users} />
                <StatCard title="Asociați Direcți" value={data.total_associates} icon={Target} />
                <StatCard title="Prag Deținere" value={`${data.threshold_pct}%`} icon={Shield} />
            </div>

            {data.ubos?.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Beneficiari Reali Identificați</h3>
                    <div className="space-y-3">
                        {data.ubos.map((ubo: Record<string, unknown>, i: number) => (
                            <div key={i} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg border border-cyan-900/30">
                                <div>
                                    <p className="text-cyan-200 font-medium">{ubo.name as string}</p>
                                    <p className="text-cyan-400/60 text-xs">
                                        {ubo.type === "DIRECT" ? "Deținere directă" : `Deținere indirectă (${(ubo.chain as string[])?.length || 0} niveluri)`}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <span className="text-xl font-orbitron text-amber-300">{(ubo.ownership_pct as number)?.toFixed(1)}%</span>
                                    <Badge variant={ubo.type === "DIRECT" ? "success" : "info"} size="sm">{ubo.type as string}</Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {data.direct_associates?.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Asociați Direcți</h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-cyan-500/70 border-b border-cyan-500/20">
                                    <th className="text-left py-2 px-3">Nume</th>
                                    <th className="text-right py-2 px-3">Deținere %</th>
                                    <th className="text-center py-2 px-3">Tip</th>
                                    <th className="text-center py-2 px-3">Activ</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.direct_associates.map((a: Record<string, unknown>, i: number) => (
                                    <tr key={i} className="border-b border-cyan-900/30">
                                        <td className="py-2 px-3 text-cyan-200">{a.name as string}</td>
                                        <td className="py-2 px-3 text-right">{(a.pct as number)?.toFixed(1)}%</td>
                                        <td className="py-2 px-3 text-center"><Badge variant="info" size="sm">{a.type as string}</Badge></td>
                                        <td className="py-2 px-3 text-center">{a.active ? "✓" : "✗"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Contagion Tab ────────────────────────────────────────────────── */
function ContagionTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery({
        queryKey: ["contagion", companyId],
        queryFn: () => api.get(`/relationships/contagion/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Mapare contagiune..." />;
    if (!data) return null;

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard title="Scor Risc Rețea" value={data.network_risk_score} icon={Shield} />
                <StatCard title="Firme Conectate" value={data.total_connected} icon={Network} />
                <StatCard title="Risc Ridicat" value={data.high_risk_connected} icon={AlertTriangle} />
                <StatCard title="Adâncime Max" value={data.max_depth_reached} icon={GitBranch} />
            </div>

            {data.nodes?.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Rețea de Contagiune</h3>
                    <div className="space-y-2">
                        {data.nodes.map((n: Record<string, unknown>, i: number) => (
                            <div key={i} className={`flex items-center justify-between p-3 rounded-lg border ${(n.depth as number) === 0 ? "bg-cyan-900/20 border-cyan-500/30" : "bg-slate-900/50 border-cyan-900/30"
                                }`}>
                                <div className="flex items-center gap-3">
                                    <span className="text-xs text-cyan-500/50 w-6">L{n.depth as number}</span>
                                    <div>
                                        <p className="text-cyan-200 text-sm">{n.name as string}</p>
                                        <p className="text-cyan-400/50 text-xs">CUI: {n.cui as number}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <Badge variant={
                                        (n.risk_score as number) >= 60 ? "success" :
                                            (n.risk_score as number) >= 40 ? "warning" : "danger"
                                    }>{n.risk_rating as string || "?"} ({n.risk_score as number})</Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Directors Tab ────────────────────────────────────────────────── */
function DirectorsTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery({
        queryKey: ["directors", companyId],
        queryFn: () => api.get(`/relationships/directors/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Analiză directori..." />;
    if (!data) return null;

    return (
        <div className="space-y-6">
            <StatCard title="Firme Conectate" value={data.total_connections} icon={Network} />

            {data.directors?.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Administratori</h3>
                    <div className="flex flex-wrap gap-2">
                        {data.directors.map((d: Record<string, unknown>, i: number) => (
                            <span key={i} className="badge-cosmic px-3 py-1 text-sm">{d.name as string}</span>
                        ))}
                    </div>
                </div>
            )}

            {data.connected_companies?.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Firme cu Directori Comuni</h3>
                    <div className="space-y-3">
                        {data.connected_companies.map((c: Record<string, unknown>, i: number) => (
                            <div key={i} className="p-3 bg-slate-900/50 rounded-lg border border-cyan-900/30">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <p className="text-cyan-200 font-medium">{c.name as string}</p>
                                        <p className="text-cyan-400/50 text-xs">CUI: {c.cui as number}</p>
                                    </div>
                                    {!!c.risk_rating && <Badge variant={
                                        (c.risk_score as number) >= 60 ? "success" : (c.risk_score as number) >= 40 ? "warning" : "danger"
                                    }>{c.risk_rating as string}</Badge>}
                                </div>
                                <div className="flex flex-wrap gap-1 mt-2">
                                    {(c.shared_persons as Record<string, unknown>[])?.map((p, j) => (
                                        <span key={j} className="text-xs bg-cyan-900/30 text-cyan-300 px-2 py-0.5 rounded">
                                            {p.name as string} ({p.role as string})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Group Tab ────────────────────────────────────────────────────── */
function GroupTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery({
        queryKey: ["group", companyId],
        queryFn: () => api.get(`/relationships/group/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Detectare grup..." />;
    if (!data) return null;

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard title="Membri Grup" value={data.group_size} icon={GitBranch} />
                <StatCard title="CA Total Grup" value={data.group_total_ca ? `${(data.group_total_ca / 1000000).toFixed(0)}M` : "N/A"} icon={Target} />
                <StatCard title="Angajați Total" value={data.group_total_employees?.toLocaleString() || "N/A"} icon={Users} />
            </div>

            {data.group_members?.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Membri Grup Corporativ</h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-cyan-500/70 border-b border-cyan-500/20">
                                    <th className="text-left py-2 px-3">Firmă</th>
                                    <th className="text-left py-2 px-3">CUI</th>
                                    <th className="text-left py-2 px-3">CAEN</th>
                                    <th className="text-left py-2 px-3">Stare</th>
                                    <th className="text-right py-2 px-3">CA</th>
                                    <th className="text-right py-2 px-3">Angajați</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.group_members.map((m: Record<string, unknown>, i: number) => (
                                    <tr key={i} className={`border-b border-cyan-900/30 ${m.is_target ? "bg-cyan-900/20" : ""}`}>
                                        <td className="py-2 px-3 text-cyan-200">{m.name as string} {!!m.is_target && <Badge variant="info" size="sm">TARGET</Badge>}</td>
                                        <td className="py-2 px-3">{m.cui as number}</td>
                                        <td className="py-2 px-3">{m.caen as string}</td>
                                        <td className="py-2 px-3"><Badge variant={m.stare === "ACTIVA" ? "success" : "warning"} size="sm">{m.stare as string}</Badge></td>
                                        <td className="py-2 px-3 text-right">{m.cifra_afaceri ? `${((m.cifra_afaceri as number) / 1000000).toFixed(1)}M` : "—"}</td>
                                        <td className="py-2 px-3 text-right">{(m.nr_angajati as number) ?? "—"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ── Timeline Tab ─────────────────────────────────────────────────── */
function TimelineTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery({
        queryKey: ["timeline", companyId],
        queryFn: () => api.get(`/relationships/timeline/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Construire cronologie..." />;
    if (!data) return null;

    const typeColors: Record<string, string> = {
        PERSON_JOINED: "border-emerald-500",
        PERSON_LEFT: "border-red-500",
        RELATION_CREATED: "border-cyan-500",
        RELATION_ENDED: "border-amber-500",
    };

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard title="Total Evenimente" value={data.total_events} icon={Clock} />
                <StatCard title="Asociați Activi" value={data.active_associates} icon={Users} />
                <StatCard title="Administratori" value={data.active_administrators} icon={Shield} />
            </div>

            <div className="card-cosmic p-6">
                <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Cronologie Relații</h3>
                <div className="relative">
                    <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-cyan-900/30" />
                    <div className="space-y-4 pl-10">
                        {data.events?.map((ev: Record<string, unknown>, i: number) => (
                            <div key={i} className={`relative p-3 bg-slate-900/50 rounded-lg border-l-4 ${typeColors[ev.type as string] || "border-cyan-500"}`}>
                                <div className="absolute -left-[1.65rem] top-4 w-3 h-3 rounded-full bg-cyan-500" />
                                <div className="flex justify-between items-start">
                                    <div>
                                        <p className="text-cyan-200 text-sm">{ev.detail as string}</p>
                                        <Badge variant={
                                            ev.type === "PERSON_JOINED" ? "success" :
                                                ev.type === "PERSON_LEFT" ? "danger" : "info"
                                        } size="sm">{(ev.type as string).replace(/_/g, " ")}</Badge>
                                    </div>
                                    <span className="text-xs text-cyan-500/50">{ev.date as string}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
