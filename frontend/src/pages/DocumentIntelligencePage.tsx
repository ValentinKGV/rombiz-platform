import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
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
    { id: "classify", label: "Clasificare" },
    { id: "financial", label: "Bilanț" },
    { id: "contract", label: "Contract" },
    { id: "entities", label: "Entități" },
    { id: "compare", label: "Comparare" },
];

export default function DocumentIntelligencePage() {
    const [active, setActive] = useState("classify");
    const [text, setText] = useState("");
    const [textA, setTextA] = useState("");
    const [textB, setTextB] = useState("");

    const classifyMut = useMutation({
        mutationFn: (t: string) => api.post("/documents/classify", { text: t }).then(r => r.data),
    });
    const financialMut = useMutation({
        mutationFn: (t: string) => api.post("/documents/parse-financial", { text: t }).then(r => r.data),
    });
    const contractMut = useMutation({
        mutationFn: (t: string) => api.post("/documents/analyze-contract", { text: t }).then(r => r.data),
    });
    const entitiesMut = useMutation({
        mutationFn: (t: string) => api.post("/documents/extract-entities", { text: t }).then(r => r.data),
    });
    const compareMut = useMutation({
        mutationFn: (d: { text_a: string; text_b: string }) => api.post("/documents/compare", d).then(r => r.data),
    });

    const handleAnalyze = () => {
        if (active === "compare") {
            compareMut.mutate({ text_a: textA, text_b: textB });
        } else if (active === "classify") {
            classifyMut.mutate(text);
        } else if (active === "financial") {
            financialMut.mutate(text);
        } else if (active === "contract") {
            contractMut.mutate(text);
        } else if (active === "entities") {
            entitiesMut.mutate(text);
        }
    };

    const isLoading = classifyMut.isPending || financialMut.isPending || contractMut.isPending || entitiesMut.isPending || compareMut.isPending;

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Document Intelligence"
                subtitle="Clasificare documente, parsare bilanțuri, analiză contracte, extracție entități"
            />

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Text input */}
            {active !== "compare" ? (
                <div className="card-cosmic p-4 space-y-3">
                    <label className="block text-xs text-nebula-300">Text document</label>
                    <textarea
                        className="input-scifi w-full h-48 resize-y"
                        placeholder="Inserați textul documentului aici..."
                        value={text}
                        onChange={e => setText(e.target.value)}
                    />
                    <button className="btn-cosmic" onClick={handleAnalyze} disabled={!text.trim() || isLoading}>
                        {isLoading ? "Se procesează..." : "Analizează"}
                    </button>
                </div>
            ) : (
                <div className="card-cosmic p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Document A</label>
                            <textarea className="input-scifi w-full h-40 resize-y" placeholder="Text versiunea A..."
                                value={textA} onChange={e => setTextA(e.target.value)} />
                        </div>
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Document B</label>
                            <textarea className="input-scifi w-full h-40 resize-y" placeholder="Text versiunea B..."
                                value={textB} onChange={e => setTextB(e.target.value)} />
                        </div>
                    </div>
                    <button className="btn-cosmic" onClick={handleAnalyze} disabled={!textA.trim() || !textB.trim() || isLoading}>
                        {isLoading ? "Se compară..." : "Compară"}
                    </button>
                </div>
            )}

            {isLoading && <LoadingSpinner />}

            {/* Classify Results */}
            {active === "classify" && classifyMut.data && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Tip Document" value={classifyMut.data.document_type} />
                        <StatCard label="Încredere" value={`${classifyMut.data.confidence}%`} />
                        <StatCard label="Lungime Text" value={`${classifyMut.data.text_length} chars`} />
                    </div>
                    {classifyMut.data.all_scores && Object.keys(classifyMut.data.all_scores).length > 0 && (
                        <div className="card-cosmic p-4">
                            <h3 className="text-sm font-semibold text-nebula-300 mb-2">Scoruri pe Tipuri</h3>
                            <div className="space-y-2">
                                {Object.entries(classifyMut.data.all_scores)
                                    .sort(([, a], [, b]) => (b as number) - (a as number))
                                    .map(([type, score]) => (
                                        <div key={type} className="flex items-center justify-between bg-nebula-900/40 rounded p-2">
                                            <span className="font-mono text-xs">{type}</span>
                                            <span className="text-nebula-300">{score as number} potriviri</span>
                                        </div>
                                    ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Financial Parser Results */}
            {active === "financial" && financialMut.data && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="An Fiscal" value={financialMut.data.fiscal_year ?? "—"} />
                        <StatCard label="Câmpuri Extrase" value={financialMut.data.fields_found} />
                        <StatCard label="Completitudine" value={`${financialMut.data.completeness}%`} />
                    </div>
                    <div className="card-cosmic p-4">
                        <h3 className="text-sm font-semibold text-nebula-300 mb-2">Date Extrase</h3>
                        <div className="grid grid-cols-2 gap-3">
                            {Object.entries(financialMut.data.extracted_fields || {}).map(([key, val]) => (
                                <div key={key} className="bg-nebula-900/40 rounded p-3 flex justify-between">
                                    <span className="text-nebula-400 text-sm">{key}</span>
                                    <span className="font-mono">{(val as number).toLocaleString("ro-RO")}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Contract Analysis Results */}
            {active === "contract" && contractMut.data && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Clauze Găsite" value={`${contractMut.data.clauses_found}/${contractMut.data.total_clauses_checked}`} />
                        <StatCard label="Părți (CUI)" value={contractMut.data.parties_cui?.length ?? 0} />
                        <StatCard label="Riscuri" value={contractMut.data.risk_count} />
                    </div>
                    <div className="card-cosmic p-4">
                        <h3 className="text-sm font-semibold text-nebula-300 mb-2">Clauze</h3>
                        <div className="space-y-2">
                            {Object.entries(contractMut.data.clauses || {}).map(([name, clause]: [string, any]) => (
                                <div key={name} className="bg-nebula-900/40 rounded p-3">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-mono text-xs">{name}</span>
                                        <Badge variant={clause.found ? "success" : "danger"}>
                                            {clause.found ? "GĂSIT" : "LIPSĂ"}
                                        </Badge>
                                    </div>
                                    {clause.context && (
                                        <p className="text-xs text-nebula-400 mt-1 italic">...{clause.context}...</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                    {contractMut.data.contract_risks?.length > 0 && (
                        <div className="card-cosmic p-4 border-l-4 border-l-orange-500">
                            <h3 className="text-sm font-semibold text-orange-400 mb-2">Riscuri Contract</h3>
                            {contractMut.data.contract_risks.map((r: any, i: number) => (
                                <div key={i} className="text-sm text-nebula-400">• {r.detail}</div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Entity Extraction Results */}
            {active === "entities" && entitiesMut.data && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Total Entități" value={entitiesMut.data.total_entities} />
                        <StatCard label="Tipuri" value={entitiesMut.data.entity_types_found} />
                    </div>
                    <div className="card-cosmic p-4">
                        {Object.entries(entitiesMut.data.entities || {}).map(([type, items]: [string, any]) =>
                            items?.length > 0 && (
                                <div key={type} className="mb-4">
                                    <h3 className="text-sm font-semibold text-nebula-300 mb-1 capitalize">{type}</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {items.map((item: any, i: number) => (
                                            <Badge key={i} variant="info">
                                                {typeof item === "string" ? item : `${item.value} ${item.currency}`}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )
                        )}
                    </div>
                </div>
            )}

            {/* Compare Results */}
            {active === "compare" && compareMut.data && (
                <div className="space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <StatCard label="Similaritate" value={`${compareMut.data.similarity_pct}%`} />
                        <StatCard label="Linii Adăugate" value={compareMut.data.added_lines} />
                        <StatCard label="Linii Șterse" value={compareMut.data.removed_lines} />
                        <StatCard label="Neschimbate" value={compareMut.data.unchanged_lines} />
                    </div>
                    {compareMut.data.added_sample?.length > 0 && (
                        <div className="card-cosmic p-4">
                            <h3 className="text-sm font-semibold text-emerald-400 mb-2">+ Linii adăugate (eșantion)</h3>
                            {compareMut.data.added_sample.map((line: string, i: number) => (
                                <div key={i} className="text-xs text-nebula-400 bg-emerald-900/20 p-1 rounded my-1 font-mono">
                                    + {line}
                                </div>
                            ))}
                        </div>
                    )}
                    {compareMut.data.removed_sample?.length > 0 && (
                        <div className="card-cosmic p-4">
                            <h3 className="text-sm font-semibold text-red-400 mb-2">- Linii șterse (eșantion)</h3>
                            {compareMut.data.removed_sample.map((line: string, i: number) => (
                                <div key={i} className="text-xs text-nebula-400 bg-red-900/20 p-1 rounded my-1 font-mono">
                                    - {line}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <DisclaimerBanner text="Analiza documentelor este automatizată și bazată pe pattern matching. Verificați manual rezultatele pentru decizii critice." />
        </div>
    );
}
