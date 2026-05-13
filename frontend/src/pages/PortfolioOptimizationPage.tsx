import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
    LineChart, Line, Legend, PieChart, Pie, Cell,
} from "recharts";

const tabs: TabItem[] = [
    { id: "optimize", label: "Optimizare" },
    { id: "rebalance", label: "Rebalansare" },
    { id: "benchmark", label: "Benchmark" },
    { id: "attribution", label: "Atribuire" },
    { id: "scenarios", label: "Scenarii" },
];

const COLORS = ["#818cf8", "#34d399", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

function actionBadge(action: string) {
    const m: Record<string, "success" | "danger" | "neutral"> = { BUY: "success", SELL: "danger", HOLD: "neutral" };
    return <Badge variant={m[action] || "neutral"}>{action}</Badge>;
}

function probBadge(p: string) {
    const m: Record<string, "success" | "warning" | "danger" | "neutral"> = { HIGH: "danger", MEDIUM: "warning", LOW: "success" };
    return <Badge variant={m[p] || "neutral"}>{p}</Badge>;
}

export default function PortfolioOptimizationPage() {
    const [active, setActive] = useState("optimize");
    const [portfolioId, setPortfolioId] = useState("");
    const [searchId, setSearchId] = useState("");
    const [riskTol, setRiskTol] = useState("moderate");
    const [strategy, setStrategy] = useState("risk_parity");

    const pid = parseInt(searchId) || 0;

    const { data: opt, isLoading: loadOpt } = useQuery({
        queryKey: ["port-opt", pid, riskTol],
        queryFn: () => api.get(`/portfolio-opt/optimize/${pid}?risk_tolerance=${riskTol}`).then(r => r.data),
        enabled: active === "optimize" && pid > 0,
    });

    const { data: rebal, isLoading: loadReb } = useQuery({
        queryKey: ["port-rebal", pid, strategy],
        queryFn: () => api.get(`/portfolio-opt/rebalance/${pid}?strategy=${strategy}`).then(r => r.data),
        enabled: active === "rebalance" && pid > 0,
    });

    const { data: bench, isLoading: loadBench } = useQuery({
        queryKey: ["port-bench", pid],
        queryFn: () => api.get(`/portfolio-opt/benchmark/${pid}`).then(r => r.data),
        enabled: active === "benchmark" && pid > 0,
    });

    const { data: attr, isLoading: loadAttr } = useQuery({
        queryKey: ["port-attr", pid],
        queryFn: () => api.get(`/portfolio-opt/attribution/${pid}`).then(r => r.data),
        enabled: active === "attribution" && pid > 0,
    });

    const { data: scen, isLoading: loadScen } = useQuery({
        queryKey: ["port-scen", pid],
        queryFn: () => api.get(`/portfolio-opt/scenarios/${pid}`).then(r => r.data),
        enabled: active === "scenarios" && pid > 0,
    });

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Optimizare Portofoliu"
                subtitle="Markowitz, rebalansare, benchmark, atribuire și scenarii"
            />

            {/* Portfolio ID input */}
            <div className="card-cosmic p-4 flex gap-3 items-end">
                <div className="flex-1">
                    <label className="block text-xs text-nebula-300 mb-1">ID Portofoliu</label>
                    <input className="input-scifi w-full" placeholder="ex: 1" type="number"
                        value={portfolioId} onChange={e => setPortfolioId(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && setSearchId(portfolioId)} />
                </div>
                <button className="btn-cosmic" onClick={() => setSearchId(portfolioId)}>Analizează</button>
            </div>

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Optimize */}
            {active === "optimize" && pid > 0 && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3">
                        {["conservative", "moderate", "aggressive"].map(t => (
                            <button key={t} onClick={() => setRiskTol(t)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${riskTol === t ? "bg-indigo-600 text-white" : "bg-nebula-800 text-nebula-400 hover:text-nebula-200"
                                    }`}>
                                {t.charAt(0).toUpperCase() + t.slice(1)}
                            </button>
                        ))}
                    </div>

                    {loadOpt ? <LoadingSpinner /> :
                        opt?.holdings?.length ? (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <StatCard label="Randament Estimat" value={`${opt.portfolio_metrics?.expected_return_pct}%`} />
                                    <StatCard label="Volatilitate" value={`${opt.portfolio_metrics?.portfolio_volatility_pct}%`} />
                                    <StatCard label="Sharpe Ratio" value={opt.portfolio_metrics?.sharpe_ratio} />
                                    <StatCard label="Beneficiu Diversif." value={`${opt.portfolio_metrics?.diversification_benefit}%`} />
                                </div>

                                {/* Weight chart */}
                                <div className="h-64">
                                    <ResponsiveContainer>
                                        <BarChart data={opt.holdings} layout="vertical">
                                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                            <XAxis type="number" stroke="#94a3b8" />
                                            <YAxis type="category" dataKey="name" stroke="#94a3b8" width={120} tick={{ fontSize: 10 }} />
                                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                            <Legend />
                                            <Bar dataKey="current_weight_pct" name="Actual %" fill="#64748b" />
                                            <Bar dataKey="optimal_weight_pct" name="Optim %" fill="#818cf8" />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>

                                {opt.recommendations?.length > 0 && (
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-semibold text-nebula-300 mb-2">Recomandări</h3>
                                        <ul className="space-y-1">
                                            {opt.recommendations.map((r: string, i: number) => (
                                                <li key={i} className="text-sm text-nebula-400 flex items-start gap-2">
                                                    <span className="text-indigo-400 mt-0.5">▸</span> {r}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Introduceți un ID de portofoliu valid.</div>}
                </div>
            )}

            {/* Rebalance */}
            {active === "rebalance" && pid > 0 && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3">
                        {["risk_parity", "equal_weight", "momentum"].map(s => (
                            <button key={s} onClick={() => setStrategy(s)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${strategy === s ? "bg-indigo-600 text-white" : "bg-nebula-800 text-nebula-400 hover:text-nebula-200"
                                    }`}>
                                {s.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase())}
                            </button>
                        ))}
                    </div>

                    {loadReb ? <LoadingSpinner /> :
                        rebal?.actions?.length ? (
                            <>
                                <StatCard label="Acțiuni Necesare" value={rebal.total_actions} />
                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Companie</th>
                                                <th className="p-3 text-right">Actual %</th>
                                                <th className="p-3 text-right">Target %</th>
                                                <th className="p-3 text-right">Delta</th>
                                                <th className="p-3">Acțiune</th>
                                                <th className="p-3 text-right">Risc</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {rebal.actions.map((a: any) => (
                                                <tr key={a.company_id} className="border-b border-nebula-800/30">
                                                    <td className="p-3">{a.name}</td>
                                                    <td className="p-3 text-right">{a.current_weight_pct}%</td>
                                                    <td className="p-3 text-right">{a.target_weight_pct}%</td>
                                                    <td className={`p-3 text-right ${a.delta_pct > 0 ? "text-green-400" : a.delta_pct < 0 ? "text-red-400" : ""}`}>
                                                        {a.delta_pct > 0 ? "+" : ""}{a.delta_pct}%
                                                    </td>
                                                    <td className="p-3">{actionBadge(a.action)}</td>
                                                    <td className="p-3 text-right">{a.risk_score}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </>
                        ) : null}
                </div>
            )}

            {/* Benchmark */}
            {active === "benchmark" && pid > 0 && (
                loadBench ? <LoadingSpinner /> :
                    bench?.periods?.length ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Alpha Total" value={`${bench.total_alpha_pct}%`} />
                                <StatCard label="Randament Mediu Port." value={`${bench.summary?.avg_portfolio_return}%`} />
                                <StatCard label="Randament Mediu Bench." value={`${bench.summary?.avg_benchmark_return}%`} />
                            </div>

                            <div className="card-cosmic p-4">
                                <h3 className="text-sm font-medium text-nebula-300 mb-3">Performanță Cumulativă</h3>
                                <div className="h-64">
                                    <ResponsiveContainer>
                                        <LineChart data={bench.periods}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                            <XAxis dataKey="year" stroke="#94a3b8" />
                                            <YAxis stroke="#94a3b8" />
                                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                            <Legend />
                                            <Line type="monotone" dataKey="cumulative_portfolio" name="Portofoliu" stroke="#818cf8" strokeWidth={2} />
                                            <Line type="monotone" dataKey="cumulative_benchmark" name="Benchmark" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            <div className="h-56">
                                <ResponsiveContainer>
                                    <BarChart data={bench.periods}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                        <XAxis dataKey="year" stroke="#94a3b8" />
                                        <YAxis stroke="#94a3b8" />
                                        <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                        <Legend />
                                        <Bar dataKey="portfolio_return_pct" name="Portofoliu %" fill="#818cf8" />
                                        <Bar dataKey="benchmark_return_pct" name="Benchmark %" fill="#f59e0b" />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    ) : <div className="card-cosmic p-8 text-center text-nebula-400">Date insuficiente pentru benchmark.</div>
            )}

            {/* Attribution */}
            {active === "attribution" && pid > 0 && (
                loadAttr ? <LoadingSpinner /> :
                    attr ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <StatCard label="Total Companii" value={attr.total_companies} />
                                <StatCard label="Scor Diversificare" value={`${Math.round(attr.diversification_score || 0)}%`} />
                            </div>

                            {/* Sector pie */}
                            {attr.sector_attribution?.length > 0 && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-medium text-nebula-300 mb-3">Atribuire Sectorială</h3>
                                        <div className="h-52">
                                            <ResponsiveContainer>
                                                <PieChart>
                                                    <Pie data={attr.sector_attribution} dataKey="weight_pct" nameKey="sector" cx="50%" cy="50%" outerRadius={80} label>
                                                        {attr.sector_attribution.map((_: any, i: number) => (
                                                            <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-medium text-nebula-300 mb-3">Contribuție pe Sector</h3>
                                        <div className="space-y-2">
                                            {attr.sector_attribution.map((s: any) => (
                                                <div key={s.sector} className="flex justify-between items-center text-sm">
                                                    <span className="text-nebula-300">CAEN {s.sector} ({s.companies} firme)</span>
                                                    <span className={s.avg_contribution_pct >= 0 ? "text-green-400" : "text-red-400"}>
                                                        {s.avg_contribution_pct > 0 ? "+" : ""}{s.avg_contribution_pct}%
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Top / bottom */}
                            {attr.top_contributors?.length > 0 && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-semibold text-green-400 mb-3">Top Contribuitori</h3>
                                        {attr.top_contributors.map((c: any) => (
                                            <div key={c.company_id} className="flex justify-between text-sm py-1 border-b border-nebula-800/30 last:border-0">
                                                <span className="text-nebula-300">{c.name}</span>
                                                <span className="text-green-400">+{c.contribution_pct}%</span>
                                            </div>
                                        ))}
                                    </div>
                                    {attr.bottom_contributors?.length > 0 && (
                                        <div className="card-cosmic p-4">
                                            <h3 className="text-sm font-semibold text-red-400 mb-3">Cei Mai Slabi</h3>
                                            {attr.bottom_contributors.map((c: any) => (
                                                <div key={c.company_id} className="flex justify-between text-sm py-1 border-b border-nebula-800/30 last:border-0">
                                                    <span className="text-nebula-300">{c.name}</span>
                                                    <span className="text-red-400">{c.contribution_pct}%</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ) : null
            )}

            {/* Scenarios */}
            {active === "scenarios" && pid > 0 && (
                loadScen ? <LoadingSpinner /> :
                    scen?.scenarios?.length ? (
                        <div className="space-y-4">
                            <StatCard label="Valoare Curentă Portofoliu" value={scen.current_total_revenue?.toLocaleString("ro-RO")} />
                            <div className="grid grid-cols-1 gap-4">
                                {scen.scenarios.map((s: any) => (
                                    <div key={s.name} className={`card-cosmic p-4 border-l-4 ${s.change_pct >= 0 ? "border-green-500" : "border-red-500"
                                        }`}>
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <h3 className="font-semibold text-nebula-200">{s.name}</h3>
                                                <p className="text-xs text-nebula-500 mt-1">{s.description}</p>
                                            </div>
                                            <div className="text-right">
                                                {probBadge(s.probability)}
                                                <p className={`text-xl font-bold mt-1 ${s.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                                                    {s.change_pct > 0 ? "+" : ""}{s.change_pct}%
                                                </p>
                                            </div>
                                        </div>
                                        <div className="mt-3 grid grid-cols-3 gap-3 text-center">
                                            {Object.entries(s.impact_factors || {}).map(([k, v]) => (
                                                <div key={k} className="bg-nebula-900/30 rounded-lg p-2">
                                                    <p className="text-xs text-nebula-500">{k}</p>
                                                    <p className={`text-sm font-bold ${(v as number) >= 0 ? "text-green-400" : "text-red-400"}`}>
                                                        {(v as number) > 0 ? "+" : ""}{((v as number) * 100).toFixed(0)}%
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                        {s.company_impacts?.length > 0 && (
                                            <details className="mt-3">
                                                <summary className="text-xs text-nebula-500 cursor-pointer hover:text-nebula-300">
                                                    Impact per companie ({s.company_impacts.length})
                                                </summary>
                                                <div className="mt-2 space-y-1">
                                                    {s.company_impacts.map((ci: any, i: number) => (
                                                        <div key={i} className="flex justify-between text-xs">
                                                            <span className="text-nebula-400">{ci.name}</span>
                                                            <span className={ci.impact >= 0 ? "text-green-400" : "text-red-400"}>
                                                                {ci.impact >= 0 ? "+" : ""}{ci.impact.toLocaleString("ro-RO")}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </details>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : <div className="card-cosmic p-8 text-center text-nebula-400">Introduceți un ID de portofoliu valid.</div>
            )}

            {!searchId && <div className="card-cosmic p-8 text-center text-nebula-400">Introduceți un ID de portofoliu pentru a începe analiza.</div>}

            <DisclaimerBanner text="Optimizarea este indicativă. Nu constituie consiliere financiară. Deciziile de investiție rămân responsabilitatea utilizatorului." />
        </div>
    );
}
