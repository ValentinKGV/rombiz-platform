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
} from "@/components/common";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    LineChart, Line, CartesianGrid, Legend,
} from "recharts";

const tabs: TabItem[] = [
    { id: "competitors", label: "Competitori" },
    { id: "benchmarks", label: "Benchmarks" },
    { id: "market", label: "Market Sizing" },
    { id: "targets", label: "M&A Targets" },
    { id: "pricing", label: "Price Intelligence" },
    { id: "macro", label: "Macro INS" },
];

export default function MarketIntelligencePage() {
    const [active, setActive] = useState("competitors");
    const [companyId, setCompanyId] = useState("");
    const [caenCode, setCaenCode] = useState("");
    const [searchId, setSearchId] = useState("");
    const [searchCaen, setSearchCaen] = useState("");

    const handleSearchCompany = () => { if (companyId.trim()) setSearchId(companyId.trim()); };
    const handleSearchCaen = () => { if (caenCode.trim()) setSearchCaen(caenCode.trim()); };

    const { data: competitors, isLoading: loadComp } = useQuery({
        queryKey: ["mkt-competitors", searchId],
        queryFn: () => api.get(`/market/competitors/${searchId}`).then(r => r.data),
        enabled: active === "competitors" && !!searchId,
    });

    const { data: benchmarks, isLoading: loadBench } = useQuery({
        queryKey: ["mkt-benchmarks", searchCaen],
        queryFn: () => api.get(`/market/benchmarks/${searchCaen}`).then(r => r.data),
        enabled: active === "benchmarks" && !!searchCaen,
    });

    const { data: marketSize, isLoading: loadMarket } = useQuery({
        queryKey: ["mkt-size", searchCaen],
        queryFn: () => api.get(`/market/market-size/${searchCaen}`).then(r => r.data),
        enabled: active === "market" && !!searchCaen,
    });

    const { data: targets, isLoading: loadTargets } = useQuery({
        queryKey: ["mkt-targets", searchCaen],
        queryFn: () => api.get(`/market/ma-targets/${searchCaen}`).then(r => r.data),
        enabled: active === "targets" && !!searchCaen,
    });

    const { data: pricing, isLoading: loadPricing } = useQuery({
        queryKey: ["mkt-pricing", searchId],
        queryFn: () => api.get(`/market/price-intelligence/${searchId}`).then(r => r.data),
        enabled: active === "pricing" && !!searchId,
    });

    const { data: macro, isLoading: loadMacro } = useQuery({
        queryKey: ["mkt-macro"],
        queryFn: () => api.get("/market/macro-indicators", { params: { limit: 20 } }).then(r => r.data),
        enabled: active === "macro",
    });

    const needsCompany = active === "competitors" || active === "pricing";

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Market Intelligence"
                subtitle="Analiză competitivă, benchmarks sectoriale, market sizing, screening M&A"
            />

            <div className="card-cosmic p-4 flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-[200px]">
                    <label className="block text-xs text-nebula-300 mb-1">Company ID</label>
                    <input className="input-scifi w-full" placeholder="ID companie..."
                        value={companyId} onChange={e => setCompanyId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSearchCompany()} />
                </div>
                <div className="flex-1 min-w-[200px]">
                    <label className="block text-xs text-nebula-300 mb-1">CAEN Code</label>
                    <input className="input-scifi w-full" placeholder="ex: 6201..."
                        value={caenCode} onChange={e => setCaenCode(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleSearchCaen()} />
                </div>
                <button className="btn-cosmic" onClick={needsCompany ? handleSearchCompany : handleSearchCaen}>
                    Analizează
                </button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Competitors */}
            {active === "competitors" && (
                !searchId ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un Company ID.</div> :
                    loadComp ? <LoadingSpinner /> :
                        competitors?.competitors ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <StatCard label="Competitori Găsiți" value={competitors.competitor_count} />
                                    <StatCard label="CAEN" value={competitors.caen} />
                                    <StatCard label="An" value={competitors.analysis_year} />
                                </div>
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Denumire</th>
                                                <th className="p-3">CUI</th>
                                                <th className="p-3 text-right">Cifră Afaceri</th>
                                                <th className="p-3 text-right">Profit</th>
                                                <th className="p-3 text-right">Angajați</th>
                                                <th className="p-3 text-right">Marjă %</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {competitors.competitors.map((c: any) => (
                                                <tr key={c.company_id} className="border-b border-nebula-800/30 hover:bg-nebula-900/30">
                                                    <td className="p-3">{c.name}</td>
                                                    <td className="p-3 font-mono text-xs">{c.cui}</td>
                                                    <td className="p-3 text-right">{c.cifra_afaceri.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{c.profit_net.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{c.nr_angajati}</td>
                                                    <td className="p-3 text-right">{c.profit_margin}%</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : null
            )}

            {/* Benchmarks */}
            {active === "benchmarks" && (
                !searchCaen ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un cod CAEN.</div> :
                    loadBench ? <LoadingSpinner /> :
                        benchmarks?.benchmarks?.length ? (
                            <div className="space-y-4">
                                <div className="h-72">
                                    <ResponsiveContainer>
                                        <BarChart data={[...benchmarks.benchmarks].reverse()}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                            <XAxis dataKey="year" stroke="#94a3b8" />
                                            <YAxis stroke="#94a3b8" />
                                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                            <Legend />
                                            <Bar dataKey="avg_cifra_afaceri" name="Medie CA" fill="#818cf8" />
                                            <Bar dataKey="avg_profit_net" name="Medie Profit" fill="#34d399" />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">An</th>
                                                <th className="p-3 text-right">Firme</th>
                                                <th className="p-3 text-right">Medie CA</th>
                                                <th className="p-3 text-right">Medie Profit</th>
                                                <th className="p-3 text-right">Medie Angajați</th>
                                                <th className="p-3 text-right">ROA</th>
                                                <th className="p-3 text-right">ROE</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {benchmarks.benchmarks.map((b: any) => (
                                                <tr key={b.year} className="border-b border-nebula-800/30">
                                                    <td className="p-3 font-bold">{b.year}</td>
                                                    <td className="p-3 text-right">{b.company_count}</td>
                                                    <td className="p-3 text-right">{b.avg_cifra_afaceri.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{b.avg_profit_net.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{b.avg_nr_angajati}</td>
                                                    <td className="p-3 text-right">{b.avg_roa}%</td>
                                                    <td className="p-3 text-right">{b.avg_roe}%</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Nicio dată disponibilă.</div>
            )}

            {/* Market Sizing */}
            {active === "market" && (
                !searchCaen ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un cod CAEN.</div> :
                    loadMarket ? <LoadingSpinner /> :
                        marketSize ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <StatCard label="Firme Active" value={marketSize.active_companies} />
                                    <StatCard label="Rata Supraviețuire" value={`${marketSize.survival_rate}%`} />
                                    <StatCard label="Total Revenue" value={`${(marketSize.market_data?.total_revenue / 1_000_000)?.toFixed(1) ?? "—"}M`} />
                                    <StatCard label="Concentrare Top 5" value={`${marketSize.concentration_top5_pct}%`} />
                                </div>
                                {marketSize.market_leaders?.length > 0 && (
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-semibold text-nebula-300 mb-3">Lideri de Piață</h3>
                                        <div className="space-y-2">
                                            {marketSize.market_leaders.map((l: any, i: number) => (
                                                <div key={l.company_id} className="flex items-center justify-between bg-nebula-900/40 rounded-lg p-3">
                                                    <span>
                                                        <span className="text-nebula-500 font-mono text-xs mr-2">#{i + 1}</span>
                                                        {l.name}
                                                    </span>
                                                    <span className="text-nebula-300 font-mono">{l.revenue.toLocaleString("ro-RO")} RON</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : null
            )}

            {/* M&A Targets */}
            {active === "targets" && (
                !searchCaen ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un cod CAEN.</div> :
                    loadTargets ? <LoadingSpinner /> :
                        targets?.targets?.length ? (
                            <div className="space-y-4">
                                <StatCard label="Ținte Identificate" value={targets.target_count} />
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Denumire</th>
                                                <th className="p-3 text-right">CA</th>
                                                <th className="p-3 text-right">Marjă %</th>
                                                <th className="p-3 text-right">Angajați</th>
                                                <th className="p-3 text-right">EV estimat</th>
                                                <th className="p-3">Județ</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {targets.targets.map((t: any) => (
                                                <tr key={t.company_id} className="border-b border-nebula-800/30 hover:bg-nebula-900/30">
                                                    <td className="p-3">{t.name}</td>
                                                    <td className="p-3 text-right">{t.cifra_afaceri.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{t.profit_margin}%</td>
                                                    <td className="p-3 text-right">{t.nr_angajati}</td>
                                                    <td className="p-3 text-right font-mono">{t.ev_estimate.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-nebula-400">{t.judet}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Nicio țintă identificată.</div>
            )}

            {/* Price Intelligence */}
            {active === "pricing" && (
                !searchId ? <div className="card-cosmic p-12 text-center text-nebula-400">Introduceți un Company ID.</div> :
                    loadPricing ? <LoadingSpinner /> :
                        pricing?.metrics?.length ? (
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <StatCard label="Media Sector Rev/Emp" value={pricing.sector_avg_rev_per_employee?.toLocaleString("ro-RO")} />
                                    <StatCard label="Media Sector Marjă" value={`${pricing.sector_avg_margin}%`} />
                                </div>
                                <div className="h-72">
                                    <ResponsiveContainer>
                                        <LineChart data={pricing.metrics}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                            <XAxis dataKey="year" stroke="#94a3b8" />
                                            <YAxis stroke="#94a3b8" />
                                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                            <Legend />
                                            <Line type="monotone" dataKey="revenue_per_employee" name="Revenue/Angajat" stroke="#818cf8" />
                                            <Line type="monotone" dataKey="profit_per_employee" name="Profit/Angajat" stroke="#34d399" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">An</th>
                                                <th className="p-3 text-right">Revenue</th>
                                                <th className="p-3 text-right">Rev/Emp</th>
                                                <th className="p-3 text-right">Marjă</th>
                                                <th className="p-3 text-right">ROA</th>
                                                <th className="p-3 text-right">ROE</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {pricing.metrics.map((m: any) => (
                                                <tr key={m.year} className="border-b border-nebula-800/30">
                                                    <td className="p-3 font-bold">{m.year}</td>
                                                    <td className="p-3 text-right">{m.revenue.toLocaleString("ro-RO")}</td>
                                                    <td className="p-3 text-right">{m.revenue_per_employee?.toLocaleString("ro-RO") ?? "—"}</td>
                                                    <td className="p-3 text-right">{m.profit_margin}%</td>
                                                    <td className="p-3 text-right">{m.roa}%</td>
                                                    <td className="p-3 text-right">{m.roe}%</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Fără date disponibile.</div>
            )}

            <DisclaimerBanner text="Datele de piață sunt bazate pe informații publice și estimări. Nu constituie recomandări de investiții." />

            {/* Macro INS */}
            {active === "macro" && (
                loadMacro ? <LoadingSpinner /> :
                    macro?.length ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                {macro.map((ind: any, i: number) => (
                                    <div key={i} className="card-cosmic p-4">
                                        <div className="flex items-start justify-between mb-2">
                                            <div>
                                                <p className="font-orbitron text-xs font-semibold text-slate-700 uppercase tracking-wide">{ind.category}</p>
                                                <p className="font-rajdhani text-sm text-slate-500 mt-0.5">{ind.indicator_name}</p>
                                            </div>
                                            <span className="rounded-full bg-nebula-100 px-2 py-0.5 text-xs text-nebula-700">{ind.measure_unit}</span>
                                        </div>
                                        {ind.data?.series?.length ? (
                                            <ResponsiveContainer width="100%" height={80}>
                                                <LineChart data={ind.data.series.slice(-6)}>
                                                    <Line type="monotone" dataKey="value" stroke="#6366f1" dot={false} strokeWidth={2} />
                                                    <Tooltip formatter={(v: any) => [v, ind.indicator_name]} />
                                                </LineChart>
                                            </ResponsiveContainer>
                                        ) : (
                                            <p className="font-orbitron text-xl font-bold text-slate-800 mt-2">
                                                {ind.data?.last_value ?? "—"}
                                            </p>
                                        )}
                                        <p className="font-rajdhani text-xs text-slate-400 mt-2">Perioadă: {ind.period ?? "—"} &middot; Sursa: INS</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : <div className="card-cosmic p-12 text-center text-nebula-400">Nu există date INS în baza de date. Rulați sync-ul INS din Admin.</div>
            )}
        </div>
    );
}
