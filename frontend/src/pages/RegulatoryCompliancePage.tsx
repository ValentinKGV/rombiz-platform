import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import {
    SectionHeader,
    StatCard,
    LoadingSpinner,
    DisclaimerBanner,
    TabNav,
    type TabItem,
    Badge,
} from "@/components/common";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

const tabs: TabItem[] = [
    { id: "gdpr", label: "GDPR" },
    { id: "fiscal", label: "Fiscal" },
    { id: "environmental", label: "Mediu" },
    { id: "labor", label: "Muncă" },
    { id: "aml", label: "AML" },
];

function statusBadge(status: string) {
    switch (status) {
        case "PASS": return <Badge variant="success">PASS</Badge>;
        case "FAIL": return <Badge variant="danger">FAIL</Badge>;
        case "WARNING": return <Badge variant="warning">WARNING</Badge>;
        case "INFO": return <Badge variant="info">INFO</Badge>;
        default: return <Badge>{status}</Badge>;
    }
}

export default function RegulatoryCompliancePage() {
    const [active, setActive] = useState("gdpr");
    const [companyId, setCompanyId] = useState("");
    const [searchId, setSearchId] = useState("");

    const handleSearch = () => { if (companyId.trim()) setSearchId(companyId.trim()); };

    const { data: gdpr, isLoading: loadGdpr } = useQuery({
        queryKey: ["compl-gdpr", searchId],
        queryFn: () => api.get(`/compliance/gdpr/${searchId}`).then(r => r.data),
        enabled: active === "gdpr" && !!searchId,
    });
    const { data: fiscal, isLoading: loadFiscal } = useQuery({
        queryKey: ["compl-fiscal", searchId],
        queryFn: () => api.get(`/compliance/fiscal/${searchId}`).then(r => r.data),
        enabled: active === "fiscal" && !!searchId,
    });
    const { data: env, isLoading: loadEnv } = useQuery({
        queryKey: ["compl-env", searchId],
        queryFn: () => api.get(`/compliance/environmental/${searchId}`).then(r => r.data),
        enabled: active === "environmental" && !!searchId,
    });
    const { data: labor, isLoading: loadLabor } = useQuery({
        queryKey: ["compl-labor", searchId],
        queryFn: () => api.get(`/compliance/labor/${searchId}`).then(r => r.data),
        enabled: active === "labor" && !!searchId,
    });
    const { data: aml, isLoading: loadAml } = useQuery({
        queryKey: ["compl-aml", searchId],
        queryFn: () => api.get(`/compliance/aml/${searchId}`).then(r => r.data),
        enabled: active === "aml" && !!searchId,
    });

    const isLoading = loadGdpr || loadFiscal || loadEnv || loadLabor || loadAml;

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Regulatory Compliance"
                subtitle="GDPR, fiscal, mediu, dreptul muncii, AML — verificare conformitate"
            />

            <div className="card-cosmic p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs text-nebula-300 mb-1">Company ID</label>
                    <input className="input-scifi w-full" placeholder="ID companie..."
                        value={companyId} onChange={e => setCompanyId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSearch()} />
                </div>
                <button className="btn-cosmic" onClick={handleSearch}>Verifică</button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {!searchId && (
                <div className="card-cosmic p-12 text-center text-nebula-400">
                    Introduceți ID-ul companiei pentru verificarea de conformitate.
                </div>
            )}

            {isLoading && <LoadingSpinner />}

            {/* Generic checks renderer */}
            {active === "gdpr" && searchId && !loadGdpr && gdpr && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Scor GDPR" value={`${gdpr.gdpr_score}/100`} />
                        <StatCard label="Nivel Risc" value={gdpr.risk_level} />
                        <StatCard label="Firmă" value={gdpr.company_name} />
                    </div>
                    <div className="card-cosmic overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                    <th className="p-3">Verificare</th>
                                    <th className="p-3">Status</th>
                                    <th className="p-3">Detalii</th>
                                </tr>
                            </thead>
                            <tbody>
                                {gdpr.checks?.map((c: any, i: number) => (
                                    <tr key={i} className="border-b border-nebula-800/30">
                                        <td className="p-3">{c.name}</td>
                                        <td className="p-3">{statusBadge(c.status)}</td>
                                        <td className="p-3 text-nebula-400 text-xs">{c.detail}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {gdpr.recommendations?.filter(Boolean).length > 0 && (
                        <div className="card-cosmic p-4">
                            <h3 className="text-sm font-semibold text-nebula-300 mb-2">Recomandări</h3>
                            <ul className="list-disc list-inside text-sm text-nebula-400 space-y-1">
                                {gdpr.recommendations.filter(Boolean).map((r: string, i: number) => (
                                    <li key={i}>{r}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {active === "fiscal" && searchId && !loadFiscal && fiscal && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Scor Fiscal" value={`${fiscal.fiscal_score}/100`} />
                        <StatCard label="Status" value={fiscal.status?.replace(/_/g, " ")} />
                        <StatCard label="Datorii Restante" value={`${fiscal.total_debt?.toLocaleString("ro-RO")} RON`} />
                    </div>
                    <div className="card-cosmic overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                    <th className="p-3">Verificare</th>
                                    <th className="p-3">Status</th>
                                    <th className="p-3">Detalii</th>
                                </tr>
                            </thead>
                            <tbody>
                                {fiscal.checks?.map((c: any, i: number) => (
                                    <tr key={i} className="border-b border-nebula-800/30">
                                        <td className="p-3">{c.name}</td>
                                        <td className="p-3">{statusBadge(c.status)}</td>
                                        <td className="p-3 text-nebula-400 text-xs">{c.detail}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {active === "environmental" && searchId && !loadEnv && env && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <StatCard label="Scor Mediu" value={`${env.environmental_score}/100`} />
                        <StatCard label="Amenzi" value={env.fines_count} />
                        <StatCard label="Total Amenzi" value={`${env.total_fines_amount?.toLocaleString("ro-RO")} RON`} />
                        <StatCard label="Sector Industrial" value={env.is_industrial_sector ? "Da" : "Nu"} />
                    </div>
                    <div className="space-y-2">
                        {env.checks?.map((c: any, i: number) => (
                            <div key={i} className="card-cosmic p-3 flex items-center gap-3">
                                {statusBadge(c.status)}
                                <span className="text-sm text-nebula-400">{c.detail}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {active === "labor" && searchId && !loadLabor && labor && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Scor Muncă" value={`${labor.labor_score}/100`} />
                        <StatCard label="Angajați Curenți" value={labor.current_employees} />
                    </div>
                    <div className="space-y-2">
                        {labor.checks?.map((c: any, i: number) => (
                            <div key={i} className="card-cosmic p-3 flex items-center gap-3">
                                {statusBadge(c.status)}
                                <span className="text-sm text-nebula-400">{c.detail}</span>
                            </div>
                        ))}
                    </div>
                    {labor.employee_history?.length > 0 && (
                        <div className="h-60">
                            <ResponsiveContainer>
                                <BarChart data={labor.employee_history}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                    <XAxis dataKey="year" stroke="#94a3b8" />
                                    <YAxis stroke="#94a3b8" />
                                    <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                    <Bar dataKey="employees" name="Angajați" fill="#818cf8" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </div>
            )}

            {active === "aml" && searchId && !loadAml && aml && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Scor AML" value={`${aml.aml_score}/100`} />
                        <StatCard label="Nivel Risc" value={aml.aml_risk_level?.replace(/_/g, " ")} />
                        <StatCard label="Factori Risc" value={aml.risk_factors_count} />
                    </div>
                    {aml.risk_factors?.length > 0 && (
                        <div className="space-y-2">
                            {aml.risk_factors.map((rf: any, i: number) => (
                                <div key={i} className={`card-cosmic p-3 border-l-4 ${rf.risk === "HIGH" ? "border-l-red-500" : "border-l-yellow-500"
                                    }`}>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-mono text-xs">{rf.factor}</span>
                                        <Badge variant={rf.risk === "HIGH" ? "danger" : "warning"}>{rf.risk}</Badge>
                                    </div>
                                    <p className="text-sm text-nebula-400">{rf.detail}</p>
                                </div>
                            ))}
                        </div>
                    )}
                    {aml.recommendations?.filter(Boolean).length > 0 && (
                        <div className="card-cosmic p-4">
                            <h3 className="text-sm font-semibold text-nebula-300 mb-2">Recomandări</h3>
                            <ul className="list-disc list-inside text-sm text-nebula-400 space-y-1">
                                {aml.recommendations.filter(Boolean).map((r: string, i: number) => (
                                    <li key={i}>{r}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            <DisclaimerBanner text="Verificările de conformitate sunt bazate pe date publice și nu constituie consultanță juridică." />
        </div>
    );
}
