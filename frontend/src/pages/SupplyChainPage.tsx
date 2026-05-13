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

const tabs: TabItem[] = [
    { id: "network", label: "Rețea Furnizori" },
    { id: "dependencies", label: "Dependențe" },
    { id: "disruptions", label: "Alerte Perturbări" },
    { id: "alternatives", label: "Furnizori Alternativi" },
    { id: "score", label: "Scor Supply Chain" },
];

export default function SupplyChainPage() {
    const [active, setActive] = useState("network");
    const [companyId, setCompanyId] = useState("");
    const [searchId, setSearchId] = useState("");
    const [caenCode, setCaenCode] = useState("");
    const [searchCaen, setSearchCaen] = useState("");

    const handleSearch = () => { if (companyId.trim()) setSearchId(companyId.trim()); };
    const handleSearchCaen = () => { if (caenCode.trim()) setSearchCaen(caenCode.trim()); };

    const { data: network, isLoading: loadNet } = useQuery({
        queryKey: ["sc-network", searchId],
        queryFn: () => api.get(`/supply-chain/network/${searchId}`).then(r => r.data),
        enabled: active === "network" && !!searchId,
    });

    const { data: deps, isLoading: loadDeps } = useQuery({
        queryKey: ["sc-deps", searchId],
        queryFn: () => api.get(`/supply-chain/dependencies/${searchId}`).then(r => r.data),
        enabled: active === "dependencies" && !!searchId,
    });

    const { data: disruptions, isLoading: loadDisr } = useQuery({
        queryKey: ["sc-disruptions", searchId],
        queryFn: () => api.get(`/supply-chain/disruptions/${searchId}`).then(r => r.data),
        enabled: active === "disruptions" && !!searchId,
    });

    const { data: alternatives, isLoading: loadAlt } = useQuery({
        queryKey: ["sc-alternatives", searchCaen],
        queryFn: () => api.get(`/supply-chain/alternatives/${searchCaen}`).then(r => r.data),
        enabled: active === "alternatives" && !!searchCaen,
    });

    const { data: score, isLoading: loadScore } = useQuery({
        queryKey: ["sc-score", searchId],
        queryFn: () => api.get(`/supply-chain/score/${searchId}`).then(r => r.data),
        enabled: active === "score" && !!searchId,
    });

    const needsCaen = active === "alternatives";

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Supply Chain Risk"
                subtitle="Monitorizare furnizori, dependențe critice, alerte de perturbări"
            />

            <div className="card-cosmic p-4 flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[200px]">
                    <label className="block text-xs text-nebula-300 mb-1">Company ID</label>
                    <input className="input-scifi w-full" placeholder="ID companie..."
                        value={companyId} onChange={e => setCompanyId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSearch()} />
                </div>
                {needsCaen && (
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-xs text-nebula-300 mb-1">CAEN Code</label>
                        <input className="input-scifi w-full" placeholder="ex: 6201..."
                            value={caenCode} onChange={e => setCaenCode(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && handleSearchCaen()} />
                    </div>
                )}
                <button className="btn-cosmic" onClick={needsCaen ? handleSearchCaen : handleSearch}>
                    Analizează
                </button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Network */}
            {active === "network" && (
                !searchId ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un Company ID.</div> :
                    loadNet ? <LoadingSpinner /> :
                        network?.suppliers ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <StatCard label="Total Furnizori" value={network.supplier_count} />
                                    <StatCard label="Furnizori Activi" value={network.active_suppliers} />
                                    <StatCard label="Firmă" value={network.company_name} />
                                </div>
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Furnizor</th>
                                                <th className="p-3">CUI</th>
                                                <th className="p-3">Relație</th>
                                                <th className="p-3">Stare</th>
                                                <th className="p-3 text-right">Scor Risc</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {network.suppliers.map((s: any) => (
                                                <tr key={s.company_id} className="border-b border-nebula-800/30">
                                                    <td className="p-3">{s.name}</td>
                                                    <td className="p-3 font-mono text-xs">{s.cui}</td>
                                                    <td className="p-3 text-xs">{s.relation_type}</td>
                                                    <td className="p-3">
                                                        <Badge variant={s.stare === "ACTIVA" ? "success" : "danger"}>{s.stare}</Badge>
                                                    </td>
                                                    <td className="p-3 text-right">{s.risk_score ?? "—"}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : null
            )}

            {/* Dependencies */}
            {active === "dependencies" && (
                !searchId ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un Company ID.</div> :
                    loadDeps ? <LoadingSpinner /> :
                        deps?.dependencies ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <StatCard label="Total Dependențe" value={deps.total_dependencies} />
                                    <StatCard label="Critice" value={deps.critical_dependencies} />
                                    <StatCard label="Single Source" value={deps.single_source_risks?.length ?? 0} />
                                </div>
                                {deps.single_source_risks?.length > 0 && (
                                    <div className="card-cosmic p-4 border-l-4 border-l-red-500">
                                        <h3 className="text-sm font-semibold text-red-400 mb-2">⚠ Riscuri Single-Source</h3>
                                        {deps.single_source_risks.map((r: any, i: number) => (
                                            <div key={i} className="text-sm text-nebula-400">
                                                CAEN {r.caen}: unic furnizor — {r.supplier}
                                            </div>
                                        ))}
                                    </div>
                                )}
                                <div className="space-y-2">
                                    {deps.dependencies.map((d: any, i: number) => (
                                        <div key={i} className="card-cosmic p-3 flex items-center justify-between">
                                            <div>
                                                <span className="font-medium">{d.supplier_name}</span>
                                                <span className="text-xs text-nebula-500 ml-2">({d.relation_type})</span>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="w-32 bg-nebula-900 rounded-full h-2">
                                                    <div
                                                        className={`h-2 rounded-full ${d.dependency_level === "CRITICAL" ? "bg-red-500" :
                                                                d.dependency_level === "HIGH" ? "bg-orange-500" :
                                                                    d.dependency_level === "MEDIUM" ? "bg-yellow-500" : "bg-emerald-500"
                                                            }`}
                                                        style={{ width: `${d.weight * 100}%` }}
                                                    />
                                                </div>
                                                <Badge variant={
                                                    d.dependency_level === "CRITICAL" ? "danger" :
                                                        d.dependency_level === "HIGH" ? "warning" : "info"
                                                }>{d.dependency_level}</Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : null
            )}

            {/* Disruptions */}
            {active === "disruptions" && (
                !searchId ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un Company ID.</div> :
                    loadDisr ? <LoadingSpinner /> :
                        disruptions ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <StatCard label="Alerte" value={disruptions.alert_count} />
                                    <StatCard label="Critice" value={disruptions.critical_count} />
                                    <StatCard label="Furnizori Monitorizați" value={disruptions.suppliers_monitored} />
                                </div>
                                {disruptions.alerts?.length > 0 ? (
                                    <div className="space-y-3">
                                        {disruptions.alerts.map((a: any, i: number) => (
                                            <div key={i} className={`card-cosmic p-4 border-l-4 ${a.max_severity === "CRITICAL" ? "border-l-red-500" : "border-l-orange-500"
                                                }`}>
                                                <div className="font-medium mb-2">{a.supplier_name} <span className="text-xs text-nebula-500">({a.supplier_cui})</span></div>
                                                <div className="space-y-1">
                                                    {a.alerts.map((al: any, j: number) => (
                                                        <div key={j} className="flex items-center gap-2 text-sm">
                                                            <Badge variant={al.severity === "CRITICAL" ? "danger" : "warning"} >{al.type}</Badge>
                                                            <span className="text-nebula-400">{al.detail}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="card-cosmic p-8 text-center text-emerald-400">
                                        ✓ Nicio alertă de perturbări
                                    </div>
                                )}
                            </div>
                        ) : null
            )}

            {/* Alternatives */}
            {active === "alternatives" && (
                !searchCaen ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un cod CAEN.</div> :
                    loadAlt ? <LoadingSpinner /> :
                        alternatives?.alternatives?.length ? (
                            <div className="space-y-4">
                                <StatCard label="Furnizori Alternativi" value={alternatives.count} />
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Denumire</th>
                                                <th className="p-3">Județ</th>
                                                <th className="p-3 text-right">CA</th>
                                                <th className="p-3 text-right">Angajați</th>
                                                <th className="p-3 text-right">Scor Risc</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {alternatives.alternatives.map((a: any) => (
                                                <tr key={a.company_id} className="border-b border-nebula-800/30">
                                                    <td className="p-3">{a.name}</td>
                                                    <td className="p-3">{a.judet}</td>
                                                    <td className="p-3 text-right">{a.cifra_afaceri.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{a.nr_angajati}</td>
                                                    <td className="p-3 text-right">{a.risk_score ?? "—"}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Niciun furnizor alternativ găsit.</div>
            )}

            {/* Score */}
            {active === "score" && (
                !searchId ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un Company ID.</div> :
                    loadScore ? <LoadingSpinner /> :
                        score ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <StatCard label="Scor Supply Chain" value={`${score.supply_chain_score}/100`} />
                                    <StatCard label="Nivel Risc" value={score.risk_level} />
                                    <StatCard label="Furnizori" value={score.supplier_count} />
                                    <StatCard label="Furnizori Risc" value={score.breakdown?.high_risk_suppliers ?? 0} />
                                </div>
                                <div className="card-cosmic p-4">
                                    <h3 className="text-sm font-semibold text-nebula-300 mb-3">Detalii</h3>
                                    <div className="grid grid-cols-3 gap-4 text-center">
                                        <div>
                                            <div className="text-2xl font-bold text-red-400">{score.breakdown?.inactive_suppliers ?? 0}</div>
                                            <div className="text-xs text-nebula-400">Furnizori Inactivi</div>
                                        </div>
                                        <div>
                                            <div className="text-2xl font-bold text-orange-400">{score.breakdown?.insolvent_suppliers ?? 0}</div>
                                            <div className="text-xs text-nebula-400">Furnizori Insolvabili</div>
                                        </div>
                                        <div>
                                            <div className="text-2xl font-bold text-yellow-400">{score.breakdown?.high_risk_suppliers ?? 0}</div>
                                            <div className="text-xs text-nebula-400">Risc Ridicat</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : null
            )}

            <DisclaimerBanner text="Analiza supply chain este bazată pe date publice și relații declarate. Verificați informațiile independent." />
        </div>
    );
}
