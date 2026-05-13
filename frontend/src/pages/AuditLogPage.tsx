import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import {
    SectionHeader,
    StatCard,
    LoadingSpinner,
    DisclaimerBanner,
    TabNav,
    Badge,
    type TabItem,
} from "@/components/common";
import { toast } from "sonner";

const tabs: TabItem[] = [
    { id: "trail", label: "Audit Trail" },
    { id: "hash", label: "Hash Document" },
    { id: "contract", label: "Smart Contract" },
    { id: "custody", label: "Chain of Custody" },
    { id: "timestamp", label: "Timestamp" },
];

export default function AuditLogPage() {
    const [active, setActive] = useState("trail");
    const [companyId, setCompanyId] = useState("");
    const [searchId, setSearchId] = useState("");
    const [docName, setDocName] = useState("");
    const [docContent, setDocContent] = useState("");
    const [verifyContent, setVerifyContent] = useState("");
    const [tsData, setTsData] = useState("");

    const cid = parseInt(searchId) || 0;

    // Audit Trail
    const { data: trail, isLoading: loadTrail } = useQuery({
        queryKey: ["bc-trail", cid],
        queryFn: () => api.get(`/blockchain/audit-trail/${cid}`).then(r => r.data),
        enabled: active === "trail" && cid > 0,
    });

    // Smart Contract
    const { data: contract, isLoading: loadContract } = useQuery({
        queryKey: ["bc-contract", cid],
        queryFn: () => api.get(`/blockchain/smart-contract/${cid}`).then(r => r.data),
        enabled: active === "contract" && cid > 0,
    });

    // Custody
    const { data: custody, isLoading: loadCustody } = useQuery({
        queryKey: ["bc-custody", cid],
        queryFn: () => api.get(`/blockchain/custody/${cid}`).then(r => r.data),
        enabled: active === "custody" && cid > 0,
    });

    // Hash document
    const hashMut = useMutation({
        mutationFn: () =>
            api.post("/blockchain/hash-document", {
                document_content: docContent,
                document_name: docName || "Document",
                company_id: cid || null,
            }).then(r => r.data),
        onSuccess: (data) => {
            toast.success(data.status === "REGISTERED" ? "Document înregistrat!" : "Document deja existent");
        },
    });

    // Verify document
    const verifyMut = useMutation({
        mutationFn: () =>
            api.post("/blockchain/verify-document", {
                document_content: verifyContent,
            }).then(r => r.data),
    });

    // Timestamp
    const tsMut = useMutation({
        mutationFn: () =>
            api.post("/blockchain/timestamp", {
                data: tsData,
                proof_type: "generic",
                company_id: cid || null,
            }).then(r => r.data),
        onSuccess: () => toast.success("Timestamp creat cu succes!"),
    });

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Audit Log"
                subtitle="Audit trail imutabil, hashing documente, verificare integritate, chain of custody"
            />

            {/* Company ID */}
            <div className="card-cosmic p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs text-nebula-300 mb-1">ID Companie</label>
                    <input className="input-scifi w-full" placeholder="ex: 1" type="number"
                        value={companyId} onChange={e => setCompanyId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && setSearchId(companyId)} />
                </div>
                <button className="btn-cosmic" onClick={() => setSearchId(companyId)}>Încarcă</button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Audit Trail */}
            {active === "trail" && cid > 0 && (
                loadTrail ? <LoadingSpinner /> :
                    trail ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Total Intrări" value={trail.total_entries} />
                                <StatCard label="Lungime Lanț" value={trail.chain_length} />
                                <StatCard label="Integritate" value={trail.chain_valid ? "✓ VALID" : "✗ COMPROMIS"} />
                            </div>

                            {trail.entries?.length ? (
                                <div className="card-cosmic overflow-hidden max-h-[500px] overflow-y-auto">
                                    <table className="w-full text-sm">
                                        <thead className="sticky top-0 bg-nebula-800">
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Acțiune</th>
                                                <th className="p-3">Timestamp</th>
                                                <th className="p-3">Hash</th>
                                                <th className="p-3">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {trail.entries.map((e: any, i: number) => (
                                                <tr key={i} className="border-b border-nebula-800/30">
                                                    <td className="p-3 font-medium">{e.action}</td>
                                                    <td className="p-3 text-xs text-nebula-400">{e.timestamp?.slice(0, 19)?.replace("T", " ")}</td>
                                                    <td className="p-3 font-mono text-xs text-nebula-500 truncate max-w-[180px]">{e.hash}</td>
                                                    <td className="p-3">
                                                        <Badge variant={e.verified ? "success" : "danger"}>{e.verified ? "Verificat" : "Invalid"}</Badge>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : <div className="card-cosmic p-8 text-center text-nebula-400">Nicio intrare în audit trail.</div>}
                        </div>
                    ) : null
            )}

            {/* Hash Document */}
            {active === "hash" && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Register */}
                        <div className="card-cosmic p-4 space-y-3">
                            <h3 className="text-sm font-semibold text-nebula-300">Înregistrare Document</h3>
                            <input className="input-scifi w-full" placeholder="Nume document..."
                                value={docName} onChange={e => setDocName(e.target.value)} />
                            <textarea className="input-scifi w-full h-32 resize-none" placeholder="Conținut document..."
                                value={docContent} onChange={e => setDocContent(e.target.value)} />
                            <button className="btn-cosmic w-full" onClick={() => docContent && hashMut.mutate()}
                                disabled={hashMut.isPending}>
                                {hashMut.isPending ? "Se procesează..." : "Hash & Înregistrează"}
                            </button>

                            {hashMut.data && (
                                <div className="bg-nebula-900/50 rounded-lg p-3 text-xs space-y-1">
                                    <p><span className="text-nebula-500">Status:</span> <Badge variant={hashMut.data.status === "REGISTERED" ? "success" : "info"}>{hashMut.data.status}</Badge></p>
                                    <p><span className="text-nebula-500">Hash:</span> <span className="font-mono text-indigo-400">{hashMut.data.document_hash}</span></p>
                                    {hashMut.data.block_index !== undefined && (
                                        <p><span className="text-nebula-500">Block:</span> #{hashMut.data.block_index}</p>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Verify */}
                        <div className="card-cosmic p-4 space-y-3">
                            <h3 className="text-sm font-semibold text-nebula-300">Verificare Document</h3>
                            <textarea className="input-scifi w-full h-32 resize-none" placeholder="Conținut document de verificat..."
                                value={verifyContent} onChange={e => setVerifyContent(e.target.value)} />
                            <button className="btn-cosmic w-full" onClick={() => verifyContent && verifyMut.mutate()}
                                disabled={verifyMut.isPending}>
                                {verifyMut.isPending ? "Se verifică..." : "Verifică Autenticitate"}
                            </button>

                            {verifyMut.data && (
                                <div className={`rounded-lg p-3 text-sm ${verifyMut.data.verified ? "bg-green-900/30 border border-green-700/30" : "bg-red-900/30 border border-red-700/30"}`}>
                                    <p className="font-semibold mb-1">
                                        {verifyMut.data.verified ? "✓ Document Autentic" : "✗ Document Neverificat"}
                                    </p>
                                    <p className="text-xs text-nebula-400">{verifyMut.data.message}</p>
                                    <p className="text-xs font-mono text-nebula-500 mt-1">Hash: {verifyMut.data.document_hash}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Smart Contract */}
            {active === "contract" && cid > 0 && (
                loadContract ? <LoadingSpinner /> :
                    contract ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <StatCard label="Companie" value={contract.company_name} />
                                <StatCard label="Verificări Trecute" value={`${contract.checks_passed}/${contract.checks_total}`} />
                                <StatCard label="Scor Integritate" value={`${contract.integrity_score}%`} />
                                <StatCard label="Verdict" value={contract.verdict} />
                            </div>

                            <div className="card-cosmic p-4">
                                <p className="text-xs text-nebula-500 mb-3">
                                    Block #{contract.block_index} — <span className="font-mono">{contract.block_hash?.slice(0, 32)}...</span>
                                </p>
                            </div>

                            <div className="space-y-2">
                                {contract.checks?.map((c: any, i: number) => (
                                    <div key={i} className={`card-cosmic p-4 border-l-4 ${c.passed ? "border-green-500" : "border-red-500"}`}>
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="font-medium text-nebula-200">{c.rule.replace(/_/g, " ")}</p>
                                                <p className="text-xs text-nebula-400 mt-1">{c.description}</p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge variant={c.severity === "HIGH" ? "danger" : c.severity === "MEDIUM" ? "warning" : "neutral"}>
                                                    {c.severity}
                                                </Badge>
                                                <Badge variant={c.passed ? "success" : "danger"}>
                                                    {c.passed ? "PASS" : "FAIL"}
                                                </Badge>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : null
            )}

            {/* Chain of Custody */}
            {active === "custody" && cid > 0 && (
                loadCustody ? <LoadingSpinner /> :
                    custody ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Total Evenimente" value={custody.total_custody_events} />
                                <StatCard label="Înregistrări Audit" value={custody.chain_records} />
                                <StatCard label="Integritate Lanț" value={custody.chain_integrity ? "✓ VALID" : "✗ COMPROMIS"} />
                            </div>

                            {custody.records?.length ? (
                                <div className="space-y-2">
                                    {custody.records.slice(0, 30).map((r: any, i: number) => (
                                        <div key={i} className="card-cosmic p-3 flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-indigo-500 shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-nebula-200">{r.action}</p>
                                                {r.details && <p className="text-xs text-nebula-500 truncate">{r.details}</p>}
                                            </div>
                                            <span className="text-xs text-nebula-500 shrink-0">{r.timestamp?.slice(0, 16)?.replace("T", " ")}</span>
                                            <span className="font-mono text-xs text-nebula-600 hidden md:inline">{r.hash?.slice(0, 12)}...</span>
                                        </div>
                                    ))}
                                </div>
                            ) : <div className="card-cosmic p-8 text-center text-nebula-400">Nicio înregistrare custody.</div>}
                        </div>
                    ) : null
            )}

            {/* Timestamp */}
            {active === "timestamp" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 space-y-3">
                        <h3 className="text-sm font-semibold text-nebula-300">Creare Timestamp Proof</h3>
                        <textarea className="input-scifi w-full h-24 resize-none" placeholder="Date de timestampat..."
                            value={tsData} onChange={e => setTsData(e.target.value)} />
                        <button className="btn-cosmic" onClick={() => tsData && tsMut.mutate()} disabled={tsMut.isPending}>
                            {tsMut.isPending ? "Se creează..." : "Creează Proof"}
                        </button>
                    </div>

                    {tsMut.data && (
                        <div className="card-cosmic p-4 space-y-3">
                            <h3 className="text-sm font-semibold text-green-400">Timestamp Proof Creat</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                <div>
                                    <span className="text-nebula-500">Proof ID:</span>
                                    <p className="font-mono text-indigo-400">{tsMut.data.proof_id}</p>
                                </div>
                                <div>
                                    <span className="text-nebula-500">Data Hash:</span>
                                    <p className="font-mono text-indigo-400 truncate">{tsMut.data.data_hash}</p>
                                </div>
                                <div>
                                    <span className="text-nebula-500">Block Index:</span>
                                    <p className="text-nebula-200">#{tsMut.data.block_index}</p>
                                </div>
                                <div>
                                    <span className="text-nebula-500">Block Hash:</span>
                                    <p className="font-mono text-indigo-400 truncate">{tsMut.data.block_hash}</p>
                                </div>
                                <div>
                                    <span className="text-nebula-500">Timestamp:</span>
                                    <p className="text-nebula-200">{tsMut.data.timestamp?.replace("T", " ")}</p>
                                </div>
                                <div>
                                    <span className="text-nebula-500">Lanț Valid:</span>
                                    <Badge variant={tsMut.data.chain_valid ? "success" : "danger"}>
                                        {tsMut.data.chain_valid ? "DA" : "NU"}
                                    </Badge>
                                </div>
                            </div>

                            {tsMut.data.chain_stats && (
                                <div className="bg-nebula-900/30 rounded-lg p-3 mt-2">
                                    <h4 className="text-xs font-semibold text-nebula-400 mb-2">Statistici Lanț</h4>
                                    <div className="grid grid-cols-3 gap-2 text-xs">
                                        <div><span className="text-nebula-500">Total Blocuri:</span> <span className="text-nebula-200">{tsMut.data.chain_stats.total_blocks}</span></div>
                                        <div><span className="text-nebula-500">Documente:</span> <span className="text-nebula-200">{tsMut.data.chain_stats.total_documents}</span></div>
                                        <div><span className="text-nebula-500">Custody Records:</span> <span className="text-nebula-200">{tsMut.data.chain_stats.total_custody_records}</span></div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {!searchId && active !== "hash" && active !== "timestamp" && (
                <div className="card-cosmic p-8 text-center text-nebula-400">Introduceți un ID de companie pentru a începe.</div>
            )}

            <DisclaimerBanner text="Audit log-ul intern utilizează un lanț de hash-uri SHA-256 pentru integritate. Toate înregistrările sunt persistate în baza de date." />
        </div>
    );
}
