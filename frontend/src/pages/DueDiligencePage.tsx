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
    
/* ── Tabs ─────────────────────────────────────────────────────── */
const tabs: TabItem[] = [
    { id: "checklist", label: "Checklist DD" },
    { id: "redflags", label: "Red Flags" },
    { id: "peers", label: "Comparație Peers" },
    { id: "compliance", label: "Conformitate KYC" },
    { id: "report", label: "Raport DD" },
];

/* ── Helpers ──────────────────────────────────────────────────── */
function checkStatusBadge(status: string) {
    switch (status) {
        case "PASS":
            return <Badge variant="success">PASS</Badge>;
        case "WARNING":
            return <Badge variant="warning">WARNING</Badge>;
        case "FAIL":
            return <Badge variant="danger">FAIL</Badge>;
        default:
            return <Badge>{status}</Badge>;
    }
}

function severityBadge(severity: string) {
    switch (severity) {
        case "CRITICAL":
            return <Badge variant="danger">CRITIC</Badge>;
        case "HIGH":
            return <Badge variant="danger">RIDICAT</Badge>;
        case "MEDIUM":
            return <Badge variant="warning">MEDIU</Badge>;
        case "LOW":
            return <Badge variant="info">SCĂZUT</Badge>;
        default:
            return <Badge>{severity}</Badge>;
    }
}

function verdictBadge(verdict: string) {
    switch (verdict) {
        case "FAVORABIL":
            return <Badge variant="success">FAVORABIL</Badge>;
        case "CONDITIONAT":
            return <Badge variant="warning">CONDIȚIONAT</Badge>;
        case "NEFAVORABIL":
            return <Badge variant="danger">NEFAVORABIL</Badge>;
        default:
            return <Badge>{verdict}</Badge>;
    }
}

function comparisonColor(verdict: string) {
    if (verdict === "PESTE_MEDIE") return "text-emerald-400";
    if (verdict === "SUB_MEDIE") return "text-red-400";
    return "text-yellow-300";
}

/* ── Page ─────────────────────────────────────────────────────── */
export default function DueDiligencePage() {
    const [active, setActive] = useState("checklist");
    const [companyId, setCompanyId] = useState("");
    const [searchId, setSearchId] = useState("");

    const { data: checklist, isLoading: loadingCL } = useQuery({
        queryKey: ["dd-checklist", searchId],
        queryFn: () => api.get(`/due-diligence/checklist/${searchId}`).then((r) => r.data),
        enabled: active === "checklist" && !!searchId,
    });

    const { data: redflags, isLoading: loadingRF } = useQuery({
        queryKey: ["dd-redflags", searchId],
        queryFn: () => api.get(`/due-diligence/redflags/${searchId}`).then((r) => r.data),
        enabled: active === "redflags" && !!searchId,
    });

    const { data: peers, isLoading: loadingPeers } = useQuery({
        queryKey: ["dd-peers", searchId],
        queryFn: () => api.get(`/due-diligence/peers/${searchId}`).then((r) => r.data),
        enabled: active === "peers" && !!searchId,
    });

    const { data: compliance, isLoading: loadingComp } = useQuery({
        queryKey: ["dd-compliance", searchId],
        queryFn: () => api.get(`/due-diligence/compliance/${searchId}`).then((r) => r.data),
        enabled: active === "compliance" && !!searchId,
    });

    const { data: report, isLoading: loadingReport } = useQuery({
        queryKey: ["dd-report", searchId],
        queryFn: () => api.get(`/due-diligence/report/${searchId}`).then((r) => r.data),
        enabled: active === "report" && !!searchId,
    });

    const handleSearch = () => {
        if (companyId.trim()) setSearchId(companyId.trim());
    };

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Due Diligence Engine"
                subtitle="Checklist automatizat, red flags, comparație peers și scoring conformitate"
            />

            {/* Company selector */}
            <div className="card-cosmic p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs text-nebula-300 mb-1">Company ID</label>
                    <input
                        type="text"
                        className="input-scifi w-full"
                        placeholder="ID-ul companiei..."
                        value={companyId}
                        onChange={(e) => setCompanyId(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    />
                </div>
                <button className="btn-cosmic" onClick={handleSearch}>
                    Analizează
                </button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {!searchId && (
                <div className="card-cosmic p-12 text-center text-nebula-400">
                    Introduceți ID-ul unei companii pentru a genera analiza de due diligence.
                </div>
            )}

            {/* TAB: Checklist */}
            {active === "checklist" && searchId && (
                <>
                    {loadingCL ? (
                        <LoadingSpinner />
                    ) : checklist?.error ? (
                        <div className="card-cosmic p-6 text-red-400">{checklist.error}</div>
                    ) : checklist ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <StatCard label="Scor DD" value={`${checklist.dd_score}/100`} />
                                <StatCard label="Verdict" value={checklist.verdict} />
                                <StatCard label="Pass" value={checklist.summary?.passed ?? 0} />
                                <StatCard label="Fail" value={checklist.summary?.failed ?? 0} />
                            </div>
                            <div className="card-cosmic overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                            <th className="p-3">Categorie</th>
                                            <th className="p-3">Verificare</th>
                                            <th className="p-3">Status</th>
                                            <th className="p-3">Detalii</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {checklist.checks?.map((c: any, i: number) => (
                                            <tr key={i} className="border-b border-nebula-800/30">
                                                <td className="p-3 font-mono text-xs text-nebula-300">{c.category}</td>
                                                <td className="p-3">{c.name}</td>
                                                <td className="p-3">{checkStatusBadge(c.status)}</td>
                                                <td className="p-3 text-nebula-400 text-xs">{c.detail}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : null}
                </>
            )}

            {/* TAB: Red Flags */}
            {active === "redflags" && searchId && (
                <>
                    {loadingRF ? (
                        <LoadingSpinner />
                    ) : redflags?.error ? (
                        <div className="card-cosmic p-6 text-red-400">{redflags.error}</div>
                    ) : redflags ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Total Red Flags" value={redflags.red_flags_count} />
                                <StatCard label="Critical" value={redflags.critical_count} />
                                <StatCard label="Nivel Risc" value={redflags.risk_level} />
                            </div>
                            {redflags.red_flags?.length > 0 ? (
                                <div className="space-y-3">
                                    {redflags.red_flags.map((rf: any, i: number) => (
                                        <div
                                            key={i}
                                            className={`card-cosmic p-4 border-l-4 ${rf.severity === "CRITICAL"
                                                    ? "border-l-red-500"
                                                    : rf.severity === "HIGH"
                                                        ? "border-l-orange-500"
                                                        : "border-l-yellow-500"
                                                }`}
                                        >
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-mono text-sm">{rf.flag}</span>
                                                {severityBadge(rf.severity)}
                                            </div>
                                            <p className="text-sm text-nebula-400">{rf.detail}</p>
                                            <span className="text-xs text-nebula-500">Categorie: {rf.category}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="card-cosmic p-8 text-center text-emerald-400">
                                    ✓ Niciun red flag detectat
                                </div>
                            )}
                        </div>
                    ) : null}
                </>
            )}

            {/* TAB: Peers */}
            {active === "peers" && searchId && (
                <>
                    {loadingPeers ? (
                        <LoadingSpinner />
                    ) : peers?.error ? (
                        <div className="card-cosmic p-6 text-red-400">{peers.error}</div>
                    ) : peers ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Performanță" value={peers.overall_performance?.replace(/_/g, " ")} />
                                <StatCard label="Peers Analizați" value={peers.peer_count} />
                                <StatCard label="An Analiză" value={peers.analysis_year} />
                            </div>
                            <div className="card-cosmic overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                            <th className="p-3">Indicator</th>
                                            <th className="p-3 text-right">Valoare Companie</th>
                                            <th className="p-3 text-right">Media Sector</th>
                                            <th className="p-3">Verdict</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {peers.comparisons &&
                                            Object.entries(peers.comparisons).map(([key, val]: [string, any]) => (
                                                <tr key={key} className="border-b border-nebula-800/30">
                                                    <td className="p-3 font-mono text-xs">{key}</td>
                                                    <td className="p-3 text-right">
                                                        {val.value != null ? val.value.toLocaleString("ro-RO") : "—"}
                                                    </td>
                                                    <td className="p-3 text-right text-nebula-400">
                                                        {val.sector_avg != null ? val.sector_avg.toLocaleString("ro-RO") : "—"}
                                                    </td>
                                                    <td className={`p-3 ${comparisonColor(val.verdict)}`}>
                                                        {val.verdict?.replace(/_/g, " ")}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : null}
                </>
            )}

            {/* TAB: Compliance */}
            {active === "compliance" && searchId && (
                <>
                    {loadingComp ? (
                        <LoadingSpinner />
                    ) : compliance?.error ? (
                        <div className="card-cosmic p-6 text-red-400">{compliance.error}</div>
                    ) : compliance ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Scor Conformitate" value={`${compliance.compliance_score}/100`} />
                                <StatCard label="Nivel Risc KYC" value={compliance.kyc_risk_level?.replace(/_/g, " ")} />
                                <StatCard label="Factori Risc" value={compliance.risk_factors_count} />
                            </div>

                            {compliance.risk_factors?.length > 0 && (
                                <div className="card-cosmic p-4 space-y-3">
                                    <h3 className="text-sm font-semibold text-nebula-300 mb-2">
                                        Factori de risc identificați
                                    </h3>
                                    {compliance.risk_factors.map((rf: any, i: number) => (
                                        <div key={i} className="flex items-center justify-between bg-nebula-900/40 rounded-lg p-3">
                                            <div>
                                                <span className="font-mono text-xs text-nebula-300">{rf.factor}</span>
                                                <p className="text-sm text-nebula-400 mt-1">{rf.detail}</p>
                                            </div>
                                            <span className="text-red-400 font-bold">{rf.impact}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {compliance.recommendations?.length > 0 && (
                                <div className="card-cosmic p-4">
                                    <h3 className="text-sm font-semibold text-nebula-300 mb-2">Recomandări</h3>
                                    <ul className="list-disc list-inside space-y-1 text-sm text-nebula-400">
                                        {compliance.recommendations.map((rec: string, i: number) => (
                                            <li key={i}>{rec}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ) : null}
                </>
            )}

            {/* TAB: Full Report */}
            {active === "report" && searchId && (
                <>
                    {loadingReport ? (
                        <LoadingSpinner />
                    ) : report?.error ? (
                        <div className="card-cosmic p-6 text-red-400">{report.error}</div>
                    ) : report ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <StatCard label="Scor DD" value={`${report.dd_score}/100`} />
                                <StatCard label="Verdict" value={report.verdict} />
                                <StatCard label="Risk Score" value={report.risk_score?.score ?? "—"} />
                                <StatCard label="ESG Score" value={report.esg_score?.total ?? "—"} />
                            </div>

                            <div className="card-cosmic p-4">
                                <h3 className="text-sm font-semibold text-nebula-300 mb-2">Verdict general</h3>
                                <div className="flex items-center gap-3">
                                    {verdictBadge(report.verdict)}
                                    <span className="text-nebula-400 text-sm">
                                        Red Flags: {report.red_flags?.length ?? 0} |
                                        Performanță Sector: {report.peer_performance?.replace(/_/g, " ") ?? "—"}
                                    </span>
                                </div>
                            </div>

                            {report.checklist?.length > 0 && (
                                <div className="card-cosmic overflow-hidden">
                                    <div className="p-3 border-b border-nebula-700/40">
                                        <h3 className="text-sm font-semibold text-nebula-300">Checklist Detaliat</h3>
                                    </div>
                                    <table className="w-full text-sm">
                                        <tbody>
                                            {report.checklist.map((c: any, i: number) => (
                                                <tr key={i} className="border-b border-nebula-800/30">
                                                    <td className="p-3">{c.name}</td>
                                                    <td className="p-3">{checkStatusBadge(c.status)}</td>
                                                    <td className="p-3 text-nebula-400 text-xs">{c.detail}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {report.disclaimer && (
                                <DisclaimerBanner text={report.disclaimer} />
                            )}
                        </div>
                    ) : null}
                </>
            )}

            <DisclaimerBanner text="Analiza de due diligence este generată automat din surse publice și nu înlocuiește consultanța profesională." />
        </div>
    );
}
