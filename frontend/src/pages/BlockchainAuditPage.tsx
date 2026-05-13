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
import { Shield, Hash, Link2, Clock, Search, CheckCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

const tabs: TabItem[] = [
    { id: "trail", label: "Audit Trail" },
    { id: "verify", label: "Verificare" },
    { id: "custody", label: "Chain of Custody" },
    { id: "timestamp", label: "Timestamping" },
    { id: "contract", label: "Smart Contract" },
];

export default function BlockchainAuditPage() {
    const [active, setActive] = useState("trail");
    const [companyId, setCompanyId] = useState("");
    const [searchId, setSearchId] = useState("");
    const [verifyContent, setVerifyContent] = useState("");
    const [tsData, setTsData] = useState("");
    const [docContent, setDocContent] = useState("");
    const [docName, setDocName] = useState("");

    const cid = parseInt(searchId) || 0;

    const { data: trail, isLoading: loadTrail } = useQuery({
        queryKey: ["ba-trail", cid],
        queryFn: () => api.get(`/blockchain/audit-trail/${cid}`).then(r => r.data),
        enabled: active === "trail" && cid > 0,
    });

    const { data: contract, isLoading: loadContract } = useQuery({
        queryKey: ["ba-contract", cid],
        queryFn: () => api.get(`/blockchain/smart-contract/${cid}`).then(r => r.data),
        enabled: active === "contract" && cid > 0,
    });

    const { data: custody, isLoading: loadCustody } = useQuery({
        queryKey: ["ba-custody", cid],
        queryFn: () => api.get(`/blockchain/custody/${cid}`).then(r => r.data),
        enabled: active === "custody" && cid > 0,
    });

    const verifyMut = useMutation({
        mutationFn: () =>
            api.post("/blockchain/verify-document", { document_content: verifyContent }).then(r => r.data),
    });

    const hashMut = useMutation({
        mutationFn: () =>
            api.post("/blockchain/hash-document", {
                document_content: docContent,
                document_name: docName || "Document",
                company_id: cid || null,
            }).then(r => r.data),
        onSuccess: (data) => {
            toast.success(data.status === "REGISTERED" ? "Document înregistrat pe blockchain!" : "Document deja existent");
        },
    });

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
                title="Blockchain Audit"
                subtitle="Audit trail imutabil, verificare integritate documente, chain of custody, timestamping"
            />

            {/* Company ID input */}
            <div className="card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs text-nebula-300 mb-1">ID Companie</label>
                    <input
                        className="input-scifi w-full"
                        placeholder="ex: 1"
                        type="number"
                        value={companyId}
                        onChange={e => setCompanyId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && setSearchId(companyId)}
                    />
                </div>
                <button className="btn-cosmic" onClick={() => setSearchId(companyId)}>
                    <Search className="w-4 h-4 mr-1 inline" /> Încarcă
                </button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* ── Audit Trail ─────────────────────────────────────── */}
            {active === "trail" && (
                !cid ? (
                    <div className="card-cosmic p-12 text-center text-nebula-400">
                        <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        Introduceți ID-ul companiei pentru a vizualiza audit trail-ul blockchain.
                    </div>
                ) : loadTrail ? <LoadingSpinner /> : trail ? (
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <StatCard label="Total Intrări" value={trail.total_entries ?? 0} />
                            <StatCard label="Lungime Lanț" value={trail.chain_length ?? 0} />
                            <StatCard
                                label="Integritate"
                                value={trail.chain_valid ? "✓ VALID" : "✗ COMPROMIS"}
                            />
                        </div>

                        {trail.entries?.length ? (
                            <div className="card-cosmic overflow-hidden">
                                <div className="max-h-[480px] overflow-y-auto">
                                    <table className="w-full text-sm">
                                        <thead className="sticky top-0 bg-nebula-900">
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Acțiune</th>
                                                <th className="p-3">Utilizator</th>
                                                <th className="p-3">Timestamp</th>
                                                <th className="p-3">Hash</th>
                                                <th className="p-3 text-center">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {trail.entries.map((e: Record<string, unknown>, i: number) => (
                                                <tr key={i} className="border-b border-nebula-800/30 hover:bg-nebula-800/20">
                                                    <td className="p-3 font-medium text-nebula-200">{e.action as string}</td>
                                                    <td className="p-3 text-xs text-nebula-400">{e.user_email as string || "—"}</td>
                                                    <td className="p-3 text-xs text-nebula-400">
                                                        {(e.timestamp as string)?.slice(0, 19)?.replace("T", " ")}
                                                    </td>
                                                    <td className="p-3 font-mono text-xs text-indigo-400 truncate max-w-[160px]">
                                                        {e.hash as string}
                                                    </td>
                                                    <td className="p-3 text-center">
                                                        {e.verified
                                                            ? <CheckCircle className="w-4 h-4 text-emerald-400 inline" />
                                                            : <XCircle className="w-4 h-4 text-red-400 inline" />}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : (
                            <div className="card-cosmic p-8 text-center text-nebula-400">
                                Nicio intrare în audit trail pentru această companie.
                            </div>
                        )}
                    </div>
                ) : null
            )}

            {/* ── Verificare Document ──────────────────────────────── */}
            {active === "verify" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Hash & Register */}
                    <div className="card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md p-5 space-y-3">
                        <h3 className="font-orbitron text-sm text-nebula-300 flex items-center gap-2">
                            <Hash className="w-4 h-4 text-nebula-500" /> Înregistrare pe Blockchain
                        </h3>
                        <input
                            className="input-scifi w-full"
                            placeholder="Nume document..."
                            value={docName}
                            onChange={e => setDocName(e.target.value)}
                        />
                        <textarea
                            className="input-scifi w-full h-36 resize-y"
                            placeholder="Conținut document de înregistrat..."
                            value={docContent}
                            onChange={e => setDocContent(e.target.value)}
                        />
                        <button
                            className="btn-cosmic w-full"
                            onClick={() => docContent && hashMut.mutate()}
                            disabled={!docContent || hashMut.isPending}
                        >
                            {hashMut.isPending ? "Se procesează..." : "Hash & Înregistrează"}
                        </button>
                        {hashMut.data && (
                            <div className="bg-nebula-900/60 rounded-lg p-3 space-y-1 text-xs">
                                <p><span className="text-nebula-500">Status:</span>{" "}
                                    <Badge variant={hashMut.data.status === "REGISTERED" ? "success" : "info"}>
                                        {hashMut.data.status}
                                    </Badge>
                                </p>
                                <p><span className="text-nebula-500">Hash:</span>{" "}
                                    <span className="font-mono text-indigo-400 break-all">{hashMut.data.document_hash}</span>
                                </p>
                                {hashMut.data.block_index !== undefined && (
                                    <p><span className="text-nebula-500">Block:</span> #{hashMut.data.block_index}</p>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Verify */}
                    <div className="card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md p-5 space-y-3">
                        <h3 className="font-orbitron text-sm text-nebula-300 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-nebula-500" /> Verificare Autenticitate
                        </h3>
                        <textarea
                            className="input-scifi w-full h-36 resize-y"
                            placeholder="Conținut document de verificat..."
                            value={verifyContent}
                            onChange={e => setVerifyContent(e.target.value)}
                        />
                        <button
                            className="btn-cosmic w-full"
                            onClick={() => verifyContent && verifyMut.mutate()}
                            disabled={!verifyContent || verifyMut.isPending}
                        >
                            {verifyMut.isPending ? "Se verifică..." : "Verifică pe Blockchain"}
                        </button>
                        {verifyMut.data && (
                            <div className={`rounded-lg p-3 text-sm border ${verifyMut.data.verified
                                ? "bg-emerald-900/30 border-emerald-700/40"
                                : "bg-red-900/30 border-red-700/40"}`}>
                                <p className="font-semibold mb-1">
                                    {verifyMut.data.verified ? "✓ Document Autentic" : "✗ Document Neverificat"}
                                </p>
                                <p className="text-xs text-nebula-400">{verifyMut.data.message}</p>
                                {verifyMut.data.document_hash && (
                                    <p className="text-xs font-mono text-nebula-500 mt-1 break-all">
                                        Hash: {verifyMut.data.document_hash}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Chain of Custody ──────────────────────────────────── */}
            {active === "custody" && (
                !cid ? (
                    <div className="card-cosmic p-12 text-center text-nebula-400">
                        <Link2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        Introduceți ID-ul companiei pentru chain of custody.
                    </div>
                ) : loadCustody ? <LoadingSpinner /> : custody ? (
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <StatCard label="Documente" value={custody.total_documents ?? 0} />
                            <StatCard label="Transferuri" value={custody.total_transfers ?? 0} />
                            <StatCard label="Companie" value={custody.company_name ?? "—"} />
                        </div>
                        {custody.chain?.length ? (
                            <div className="card-cosmic p-4 space-y-3">
                                {custody.chain.map((step: Record<string, unknown>, i: number) => (
                                    <div key={i} className="flex items-start gap-3 p-3 bg-nebula-900/40 rounded-lg border border-nebula-700/30">
                                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-600/30 flex items-center justify-center text-xs font-bold text-indigo-300">
                                            {i + 1}
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-nebula-200 font-medium">{step.action as string}</p>
                                            <p className="text-xs text-nebula-500">{step.actor as string}</p>
                                            <p className="text-xs text-nebula-600">
                                                {(step.timestamp as string)?.slice(0, 19)?.replace("T", " ")}
                                            </p>
                                        </div>
                                        <Badge variant={step.verified ? "success" : "warning"}>
                                            {step.verified ? "Verificat" : "Neverificat"}
                                        </Badge>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="card-cosmic p-8 text-center text-nebula-400">
                                Niciun lanț de custodie înregistrat.
                            </div>
                        )}
                    </div>
                ) : null
            )}

            {/* ── Timestamp ──────────────────────────────────────────── */}
            {active === "timestamp" && (
                <div className="card-cosmic border-[1.5px] border-indigo-100/80 dark:border-slate-700/60 shadow-md p-5 space-y-4 max-w-xl">
                    <h3 className="font-orbitron text-sm text-nebula-300 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-nebula-500" /> Creare Timestamp Imutabil
                    </h3>
                    <textarea
                        className="input-scifi w-full h-32 resize-y"
                        placeholder="Date de timestampat (JSON, text, hash)..."
                        value={tsData}
                        onChange={e => setTsData(e.target.value)}
                    />
                    <button
                        className="btn-cosmic w-full"
                        onClick={() => tsData && tsMut.mutate()}
                        disabled={!tsData || tsMut.isPending}
                    >
                        {tsMut.isPending ? "Se creează..." : "Creează Timestamp"}
                    </button>
                    {tsMut.data && (
                        <div className="bg-nebula-900/60 rounded-lg p-4 space-y-2 text-xs">
                            <p className="font-semibold text-emerald-400">✓ Timestamp Înregistrat</p>
                            <p><span className="text-nebula-500">Timestamp:</span>{" "}
                                <span className="text-nebula-200">{tsMut.data.timestamp?.slice(0, 19)?.replace("T", " ")}</span>
                            </p>
                            <p><span className="text-nebula-500">Hash:</span>{" "}
                                <span className="font-mono text-indigo-400 break-all">{tsMut.data.hash}</span>
                            </p>
                            {tsMut.data.block_index !== undefined && (
                                <p><span className="text-nebula-500">Block:</span> #{tsMut.data.block_index}</p>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── Smart Contract ─────────────────────────────────────── */}
            {active === "contract" && (
                !cid ? (
                    <div className="card-cosmic p-12 text-center text-nebula-400">
                        <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        Introduceți ID-ul companiei pentru a vizualiza contractul smart.
                    </div>
                ) : loadContract ? <LoadingSpinner /> : contract ? (
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <StatCard label="Status Contract" value={contract.status ?? "—"} />
                            <StatCard label="Versiune" value={contract.version ?? "—"} />
                            <StatCard label="Companie" value={contract.company_name ?? "—"} />
                        </div>

                        {contract.clauses?.length ? (
                            <div className="card-cosmic p-4">
                                <h4 className="font-rajdhani text-nebula-300 mb-3">Clauze Contract</h4>
                                <div className="space-y-2">
                                    {contract.clauses.map((clause: Record<string, unknown>, i: number) => (
                                        <div key={i} className="p-3 bg-nebula-900/40 rounded border border-nebula-700/30 text-sm">
                                            <span className="font-medium text-nebula-200 mr-2">{clause.id as string}.</span>
                                            <span className="text-nebula-400">{clause.text as string}</span>
                                            {clause.auto_execute && (
                                                <Badge variant="info" className="ml-2">Auto-exec</Badge>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <DisclaimerBanner variant="info">
                                Niciun smart contract activ pentru această companie.
                            </DisclaimerBanner>
                        )}
                    </div>
                ) : null
            )}
        </div>
    );
}
