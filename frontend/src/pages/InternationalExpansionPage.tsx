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
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

const tabs: TabItem[] = [
    { id: "cross", label: "Cross-border" },
    { id: "fx", label: "Risc FX" },
    { id: "entry", label: "Market Entry" },
    { id: "regulatory", label: "Reglementare" },
    { id: "translate", label: "Traduceri" },
];

function recBadge(r: string) {
    const m: Record<string, "success" | "warning" | "danger"> = {
        RECOMANDAT: "success", POSIBIL: "warning", DIFICIL: "danger",
        FAVORABIL: "success", MODERAT: "warning", NEFAVORABIL: "danger",
    };
    return <Badge variant={m[r] || "default"}>{r}</Badge>;
}

function riskBadge(r: string) {
    const m: Record<string, "success" | "warning" | "danger"> = { LOW: "success", MEDIUM: "warning", HIGH: "danger" };
    return <Badge variant={m[r] || "default"}>{r}</Badge>;
}

export default function InternationalExpansionPage() {
    const [active, setActive] = useState("cross");
    const [companyId, setCompanyId] = useState("");
    const [searchId, setSearchId] = useState("");
    const [caen, setCaen] = useState("");
    const [targetCountry, setTargetCountry] = useState("DE");
    const [transLang, setTransLang] = useState("en");

    const cid = parseInt(searchId) || 0;

    const { data: cross, isLoading: loadCross } = useQuery({
        queryKey: ["intl-cross", cid],
        queryFn: () => api.get(`/international/cross-border/${cid}`).then(r => r.data),
        enabled: active === "cross" && cid > 0,
    });

    const { data: fx, isLoading: loadFx } = useQuery({
        queryKey: ["intl-fx", cid],
        queryFn: () => api.get(`/international/fx-risk/${cid}`).then(r => r.data),
        enabled: active === "fx" && cid > 0,
    });

    const { data: entry, isLoading: loadEntry } = useQuery({
        queryKey: ["intl-entry", caen, targetCountry],
        queryFn: () => api.get(`/international/market-entry/${caen}?target_country=${targetCountry}`).then(r => r.data),
        enabled: active === "entry" && !!caen,
    });

    const { data: reg, isLoading: loadReg } = useQuery({
        queryKey: ["intl-reg"],
        queryFn: () => api.get("/international/regulatory-comparison").then(r => r.data),
        enabled: active === "regulatory",
    });

    const transMut = useMutation({
        mutationFn: () => api.post("/international/translate", { target_language: transLang }).then(r => r.data),
    });

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Expansiune Internațională"
                subtitle="Analiză cross-border, risc valutar, intrare pe piață, comparare reglementare"
            />

            {/* Company ID input */}
            <div className="card-cosmic p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs text-nebula-300 mb-1">ID Companie</label>
                    <input className="input-scifi w-full" placeholder="ex: 1" type="number"
                        value={companyId} onChange={e => setCompanyId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && setSearchId(companyId)} />
                </div>
                <button className="btn-cosmic" onClick={() => setSearchId(companyId)}>Analizează</button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Cross-border */}
            {active === "cross" && cid > 0 && (
                loadCross ? <LoadingSpinner /> :
                    cross?.target_markets?.length ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Companie" value={cross.company_name} />
                                <StatCard label="Revenue Curent" value={cross.current_revenue?.toLocaleString("ro-RO")} />
                                <StatCard label="Cea Mai Bună Piață" value={cross.best_market} />
                            </div>

                            <div className="card-cosmic overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                            <th className="p-3">Țară</th>
                                            <th className="p-3">Monedă</th>
                                            <th className="p-3 text-right">TVA</th>
                                            <th className="p-3 text-right">Impozit Corp.</th>
                                            <th className="p-3 text-right">PIB (Mld €)</th>
                                            <th className="p-3 text-right">Potențial Rev.</th>
                                            <th className="p-3 text-center">Dificultate</th>
                                            <th className="p-3">Verdict</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {cross.target_markets.map((m: any) => (
                                            <tr key={m.country_code} className="border-b border-nebula-800/30">
                                                <td className="p-3 font-medium">{m.country_name}</td>
                                                <td className="p-3">{m.currency}</td>
                                                <td className="p-3 text-right">{m.vat_rate}%</td>
                                                <td className="p-3 text-right">{m.corporate_tax}%</td>
                                                <td className="p-3 text-right">{m.gdp_billions_eur}</td>
                                                <td className="p-3 text-right">{m.estimated_revenue_potential?.toLocaleString("ro-RO")}</td>
                                                <td className="p-3 text-center">{m.entry_difficulty}/10</td>
                                                <td className="p-3">{recBadge(m.recommendation)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : null
            )}

            {/* FX Risk */}
            {active === "fx" && cid > 0 && (
                loadFx ? <LoadingSpinner /> :
                    fx?.exposures?.length ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Expunere FX Totală" value={fx.total_fx_exposure_ron?.toLocaleString("ro-RO") + " RON"} />
                                <StatCard label="VaR 95%" value={fx.total_var_95_ron?.toLocaleString("ro-RO") + " RON"} />
                                <StatCard label="Risc FX Global" value={fx.overall_fx_risk} />
                            </div>

                            <div className="h-56">
                                <ResponsiveContainer>
                                    <BarChart data={fx.exposures}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                        <XAxis dataKey="currency" stroke="#94a3b8" />
                                        <YAxis stroke="#94a3b8" />
                                        <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                        <Legend />
                                        <Bar dataKey="exposure_value_ron" name="Expunere RON" fill="#818cf8" />
                                        <Bar dataKey="var_95_ron" name="VaR 95%" fill="#ef4444" />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>

                            {fx.exposures.map((e: any) => (
                                <div key={e.currency} className="card-cosmic p-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <h3 className="font-semibold text-nebula-200">{e.pair} — Curs: {e.current_rate}</h3>
                                        {riskBadge(e.risk_level)}
                                    </div>
                                    <div className="grid grid-cols-3 gap-3 text-sm mb-3">
                                        <div><span className="text-nebula-500">Volatilitate:</span> <span className="text-nebula-200">{e.annual_volatility_pct}%</span></div>
                                        <div><span className="text-nebula-500">Expunere:</span> <span className="text-nebula-200">{e.exposure_pct}%</span></div>
                                        <div><span className="text-nebula-500">VaR:</span> <span className="text-red-400">{e.var_95_ron?.toLocaleString("ro-RO")} RON</span></div>
                                    </div>
                                    {e.hedging_recommendations?.length > 0 && (
                                        <ul className="space-y-1">
                                            {e.hedging_recommendations.map((r: string, i: number) => (
                                                <li key={i} className="text-xs text-nebula-400 flex items-start gap-2">
                                                    <span className="text-indigo-400 mt-0.5">▸</span> {r}
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : null
            )}

            {/* Market Entry */}
            {active === "entry" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex flex-wrap gap-3 items-end">
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Cod CAEN</label>
                            <input className="input-scifi w-32" value={caen} onChange={e => setCaen(e.target.value)} placeholder="ex: 6201" />
                        </div>
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Țară Țintă</label>
                            <select className="input-scifi w-40" value={targetCountry} onChange={e => setTargetCountry(e.target.value)}>
                                {["DE", "FR", "PL", "HU", "BG", "CZ", "SK", "IT", "AT", "MD", "RS"].map(c => (
                                    <option key={c} value={c}>{c}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {loadEntry ? <LoadingSpinner /> :
                        entry ? (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <StatCard label="Scor General" value={`${entry.overall_score}/100`} />
                                    <StatCard label="Verdict" value={entry.verdict} />
                                    <StatCard label="Timeline Estimat" value={entry.estimated_timeline} />
                                </div>

                                {/* Radar chart */}
                                {entry.score_breakdown && (
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-medium text-nebula-300 mb-3">Scoring Detaliat</h3>
                                        <div className="h-64">
                                            <ResponsiveContainer>
                                                <RadarChart data={Object.entries(entry.score_breakdown).map(([k, v]) => ({ metric: k.replace("_", " "), value: v as number }))}>
                                                    <PolarGrid stroke="#334155" />
                                                    <PolarAngleAxis dataKey="metric" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                                                    <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#475569" />
                                                    <Radar name="Score" dataKey="value" fill="#818cf8" fillOpacity={0.3} stroke="#818cf8" strokeWidth={2} />
                                                </RadarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>
                                )}

                                {/* Entry steps */}
                                {entry.entry_steps?.length > 0 && (
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-semibold text-nebula-300 mb-3">Pași Intrare pe Piață</h3>
                                        <div className="space-y-2">
                                            {entry.entry_steps.map((s: any) => (
                                                <div key={s.step} className="flex items-center gap-3 text-sm">
                                                    <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-bold">{s.step}</span>
                                                    <span className="flex-1 text-nebula-200">{s.action}</span>
                                                    <span className="text-nebula-500">{s.duration}</span>
                                                    <span className="text-indigo-400 font-mono text-xs">€{s.cost_eur}</span>
                                                </div>
                                            ))}
                                        </div>
                                        <p className="mt-3 text-sm text-nebula-400">
                                            Cost total estimat: <span className="text-indigo-400 font-semibold">€{entry.estimated_total_cost_eur}</span>
                                        </p>
                                    </div>
                                )}
                            </>
                        ) : null}
                </div>
            )}

            {/* Regulatory */}
            {active === "regulatory" && (
                loadReg ? <LoadingSpinner /> :
                    reg?.comparisons?.length ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <StatCard label="Cel Mai Bun Mediu" value={reg.easiest_business} />
                                <StatCard label="Cel Mai Bun Fiscal" value={reg.best_tax_environment} />
                            </div>

                            <div className="h-56">
                                <ResponsiveContainer>
                                    <BarChart data={reg.comparisons}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                        <XAxis dataKey="country_name" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                                        <YAxis stroke="#94a3b8" />
                                        <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                        <Legend />
                                        <Bar dataKey="ease_of_business_score" name="Business Score" fill="#818cf8" />
                                        <Bar dataKey="corporate_tax_pct" name="Impozit Corp. %" fill="#f59e0b" />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>

                            <div className="card-cosmic overflow-hidden overflow-x-auto">
                                <table className="w-full text-sm min-w-[700px]">
                                    <thead>
                                        <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                            <th className="p-3">Țară</th>
                                            <th className="p-3">Monedă</th>
                                            <th className="p-3 text-center">UE</th>
                                            <th className="p-3 text-right">Impozit</th>
                                            <th className="p-3 text-right">TVA</th>
                                            <th className="p-3 text-right">Salariu Min (€)</th>
                                            <th className="p-3 text-right">Înreg. (zile)</th>
                                            <th className="p-3 text-right">Capital Min (€)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {reg.comparisons.map((c: any) => (
                                            <tr key={c.country_code} className="border-b border-nebula-800/30">
                                                <td className="p-3 font-medium">{c.country_name}</td>
                                                <td className="p-3">{c.currency}</td>
                                                <td className="p-3 text-center">{c.eu_member ? "✓" : "✗"}</td>
                                                <td className="p-3 text-right">{c.corporate_tax_pct}%</td>
                                                <td className="p-3 text-right">{c.vat_rate_pct}%</td>
                                                <td className="p-3 text-right">{c.labor_regulations?.min_wage_eur?.toLocaleString("ro-RO")}</td>
                                                <td className="p-3 text-right">{c.company_registration_days}</td>
                                                <td className="p-3 text-right">{c.minimum_capital_eur?.toLocaleString("ro-RO")}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : null
            )}

            {/* Translation */}
            {active === "translate" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3 items-end">
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Limba Țintă</label>
                            <div className="flex gap-2">
                                {[{ k: "en", l: "English" }, { k: "de", l: "Deutsch" }, { k: "fr", l: "Français" }].map(({ k, l }) => (
                                    <button key={k} onClick={() => setTransLang(k)}
                                        className={`px-4 py-2 rounded-lg text-sm ${transLang === k ? "bg-indigo-600 text-white" : "bg-nebula-800 text-nebula-400 hover:text-nebula-200"}`}>
                                        {l}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <button className="btn-cosmic" onClick={() => transMut.mutate()} disabled={transMut.isPending}>
                            {transMut.isPending ? "Se traduce..." : "Translatează Termeni"}
                        </button>
                    </div>

                    {transMut.data?.translations?.length ? (
                        <div className="card-cosmic overflow-hidden max-h-[500px] overflow-y-auto">
                            <table className="w-full text-sm">
                                <thead className="sticky top-0 bg-nebula-800">
                                    <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                        <th className="p-3">Termen (RO)</th>
                                        <th className="p-3">Traducere ({transLang.toUpperCase()})</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {transMut.data.translations.map((t: any) => (
                                        <tr key={t.term_ro} className="border-b border-nebula-800/30">
                                            <td className="p-3 text-nebula-300">{t.term_ro}</td>
                                            <td className="p-3 text-indigo-400">{t.translation}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : null}
                </div>
            )}

            <DisclaimerBanner text="Datele despre piețe externe sunt orientative. Consultați un specialist înainte de decizii de expansiune." />
        </div>
    );
}
