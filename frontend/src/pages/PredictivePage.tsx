import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    TrendingUp, TrendingDown, AlertTriangle, Activity,
    BarChart3, Target, Zap, Layers, Search,
} from "lucide-react";
import {
    LineChart, Line, BarChart, Bar, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import api from "../lib/api";
import { SectionHeader, StatCard, DisclaimerBanner, LoadingSpinner, TabNav, Badge } from "../components/common";
import type { TabItem } from "../components/common";
import type {
    ForecastResponse, BankruptcyPrediction,
    RiskDegradationResponse, SectorTrendResponse,
} from "../types";

const TABS: TabItem[] = [
    { id: "forecast", label: "Forecasting", icon: TrendingUp },
    { id: "bankruptcy", label: "Faliment", icon: AlertTriangle },
    { id: "degradation", label: "Degradare Risc", icon: Activity },
    { id: "sector", label: "Trend Sectorial", icon: BarChart3 },
];

export default function PredictivePage() {
    const [tab, setTab] = useState("forecast");
    const [companyId, setCompanyId] = useState("");
    const [caenCode, setCaenCode] = useState("");
    const [yearsAhead, setYearsAhead] = useState(3);

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Predictive Analytics & ML Pipeline"
                subtitle="Forecasting financiar, probabilitate faliment, tendințe sectoriale și simulări Monte Carlo"
            />

            <TabNav tabs={TABS} activeTab={tab} onTabChange={setTab} variant="pills" />

            {/* Company ID input for company-based tabs */}
            {["forecast", "bankruptcy", "degradation"].includes(tab) && (
                <div className="card-cosmic p-4">
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <label className="text-xs text-cyan-400/70 mb-1 block">Company ID</label>
                            <div className="flex gap-2">
                                <input
                                    type="number"
                                    className="input-scifi flex-1"
                                    placeholder="Introdu ID-ul companiei..."
                                    value={companyId}
                                    onChange={e => setCompanyId(e.target.value)}
                                />
                                {tab === "forecast" && (
                                    <select
                                        className="input-scifi w-32"
                                        value={yearsAhead}
                                        onChange={e => setYearsAhead(Number(e.target.value))}
                                    >
                                        {[1, 2, 3, 4, 5].map(y => (
                                            <option key={y} value={y}>{y} ani</option>
                                        ))}
                                    </select>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* CAEN input for sector tab */}
            {tab === "sector" && (
                <div className="card-cosmic p-4">
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <label className="text-xs text-cyan-400/70 mb-1 block">Cod CAEN (primele 2 cifre)</label>
                            <input
                                type="text"
                                className="input-scifi w-full"
                                placeholder="ex: 46 (Comerț cu ridicata)"
                                maxLength={4}
                                value={caenCode}
                                onChange={e => setCaenCode(e.target.value)}
                            />
                        </div>
                    </div>
                </div>
            )}

            {tab === "forecast" && companyId && <ForecastTab companyId={Number(companyId)} years={yearsAhead} />}
            {tab === "bankruptcy" && companyId && <BankruptcyTab companyId={Number(companyId)} />}
            {tab === "degradation" && companyId && <DegradationTab companyId={Number(companyId)} />}
            {tab === "sector" && caenCode && <SectorTab caenCode={caenCode} />}

            {!companyId && tab !== "sector" && (
                <div className="card-cosmic p-12 text-center">
                    <Search className="w-12 h-12 text-cyan-500/30 mx-auto mb-4" />
                    <p className="text-cyan-300/50">Introdu un Company ID pentru a începe analiza predictivă</p>
                </div>
            )}
            {!caenCode && tab === "sector" && (
                <div className="card-cosmic p-12 text-center">
                    <Layers className="w-12 h-12 text-cyan-500/30 mx-auto mb-4" />
                    <p className="text-cyan-300/50">Introdu un cod CAEN pentru analiza sectorială</p>
                </div>
            )}
        </div>
    );
}

/* ── Forecast Tab ─────────────────────────────────────────────────── */

function ForecastTab({ companyId, years }: { companyId: number; years: number }) {
    const { data, isLoading } = useQuery<ForecastResponse>({
        queryKey: ["forecast", companyId, years],
        queryFn: () => api.get(`/predictive/forecast/${companyId}?years_ahead=${years}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Calculez predicții..." />;
    if (!data) return null;
    if (data.error) return <DisclaimerBanner variant="warning">{data.error}</DisclaimerBanner>;

    const chartData = [
        ...data.historical.map(h => ({ an: h.an, ca_real: h.cifra_afaceri, profit_real: h.profit_net, ang_real: h.nr_angajati })),
        ...data.predictions.map(p => ({ an: p.an, ca_pred: p.cifra_afaceri, profit_pred: p.profit_net, ang_pred: p.nr_angajati })),
    ];

    const TrendIcon = data.trend === "CRESTERE" ? TrendingUp : data.trend === "SCADERE" ? TrendingDown : Activity;

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard title="Trend General" value={data.trend || "N/A"} icon={TrendIcon} />
                <StatCard title="Puncte Date" value={data.data_points} icon={BarChart3} />
                <StatCard title="Ani Prognozați" value={data.years_ahead} icon={Target} />
            </div>

            {/* CA Chart */}
            <div className="card-cosmic p-6">
                <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Cifra de Afaceri — Istoric & Predicție</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                        <XAxis dataKey="an" stroke="#67e8f9" />
                        <YAxis stroke="#67e8f9" tickFormatter={v => `${(v / 1000000).toFixed(0)}M`} />
                        <Tooltip
                            contentStyle={{ backgroundColor: "#0a1628", border: "1px solid #22d3ee", borderRadius: 8 }}
                            formatter={(v: number) => [`${(v / 1000000).toFixed(2)}M RON`, undefined]}
                        />
                        <Legend />
                        <Area type="monotone" dataKey="ca_real" name="CA Real" stroke="#22d3ee" fill="#22d3ee20" />
                        <Area type="monotone" dataKey="ca_pred" name="CA Predicție" stroke="#a78bfa" fill="#a78bfa20" strokeDasharray="5 5" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Predictions Table */}
            <div className="card-cosmic p-6">
                <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Detalii Predicții</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-cyan-500/70 border-b border-cyan-500/20">
                                <th className="text-left py-2 px-3">An</th>
                                <th className="text-right py-2 px-3">CA Prognoză</th>
                                <th className="text-right py-2 px-3">Conf.</th>
                                <th className="text-right py-2 px-3">Profit Prognoză</th>
                                <th className="text-right py-2 px-3">Conf.</th>
                                <th className="text-right py-2 px-3">Angajați</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.predictions.map(p => (
                                <tr key={p.an} className="border-b border-cyan-900/30 hover:bg-cyan-900/10">
                                    <td className="py-2 px-3 font-medium text-cyan-300">{p.an}</td>
                                    <td className="py-2 px-3 text-right">{p.cifra_afaceri ? `${(p.cifra_afaceri / 1000000).toFixed(2)}M` : "—"}</td>
                                    <td className="py-2 px-3 text-right">
                                        <ConfidenceBadge value={p.cifra_afaceri_confidence} />
                                    </td>
                                    <td className="py-2 px-3 text-right">{p.profit_net ? `${(p.profit_net / 1000000).toFixed(2)}M` : "—"}</td>
                                    <td className="py-2 px-3 text-right">
                                        <ConfidenceBadge value={p.profit_net_confidence} />
                                    </td>
                                    <td className="py-2 px-3 text-right">{p.nr_angajati ?? "—"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <DisclaimerBanner>{data.disclaimer}</DisclaimerBanner>
        </div>
    );
}

/* ── Bankruptcy Tab ───────────────────────────────────────────────── */

function BankruptcyTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery<BankruptcyPrediction>({
        queryKey: ["bankruptcy", companyId],
        queryFn: () => api.get(`/predictive/bankruptcy/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Calculez probabilitate faliment..." />;
    if (!data) return null;
    if (data.error) return <DisclaimerBanner variant="warning">{data.error}</DisclaimerBanner>;

    const probPct = (data.probability * 100).toFixed(1);
    const catColor = {
        CRITIC: "text-red-400",
        RIDICAT: "text-orange-400",
        MODERAT: "text-amber-400",
        SCAZUT: "text-emerald-400",
    }[data.category] || "text-cyan-400";

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard title="Probabilitate" value={`${probPct}%`} icon={AlertTriangle} />
                <div className="card-cosmic p-4 flex flex-col items-center justify-center">
                    <span className="text-xs text-cyan-500/70 mb-1">Categorie</span>
                    <span className={`text-2xl font-orbitron ${catColor}`}>{data.category}</span>
                </div>
                <StatCard title="Factori Risc" value={data.risk_factors_count} icon={Zap} />
                <StatCard title="Scor Risc Actual" value={data.risk_score_actual ?? "N/A"} icon={Target} />
            </div>

            {/* Probability gauge */}
            <div className="card-cosmic p-6">
                <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Indicator Probabilitate Faliment</h3>
                <div className="w-full bg-gray-800 rounded-full h-6 overflow-hidden">
                    <div
                        className={`h-full rounded-full transition-all duration-1000 ${data.probability > 0.7 ? "bg-red-500" :
                            data.probability > 0.4 ? "bg-orange-500" :
                                data.probability > 0.2 ? "bg-amber-500" : "bg-emerald-500"
                            }`}
                        style={{ width: `${data.probability * 100}%` }}
                    />
                </div>
                <div className="flex justify-between text-xs text-cyan-500/50 mt-1">
                    <span>0% — Scăzut</span>
                    <span>50% — Moderat</span>
                    <span>100% — Critic</span>
                </div>
            </div>

            {/* Risk factors */}
            {data.risk_factors.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Factori de Risc Identificați</h3>
                    <div className="space-y-3">
                        {data.risk_factors.map((rf, i) => (
                            <div key={i} className="flex items-start gap-3 p-3 bg-slate-900/50 rounded-lg border border-cyan-900/30">
                                <Badge variant={
                                    rf.impact === "CRITICAL" ? "danger" :
                                        rf.impact === "HIGH" ? "warning" :
                                            "info"
                                }>{rf.impact}</Badge>
                                <div>
                                    <p className="text-cyan-200 text-sm font-medium">{rf.factor.replace(/_/g, " ")}</p>
                                    <p className="text-cyan-400/60 text-xs mt-1">{rf.detail}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <DisclaimerBanner>{data.disclaimer}</DisclaimerBanner>
        </div>
    );
}

/* ── Degradation Tab ──────────────────────────────────────────────── */

function DegradationTab({ companyId }: { companyId: number }) {
    const { data, isLoading } = useQuery<RiskDegradationResponse>({
        queryKey: ["degradation", companyId],
        queryFn: () => api.get(`/predictive/degradation/${companyId}`).then(r => r.data),
        enabled: companyId > 0,
    });

    if (isLoading) return <LoadingSpinner label="Analizez tendințe de degradare..." />;
    if (!data) return null;

    const predColor = {
        DEGRADARE_PROBABILA: "text-red-400",
        RISC_MODERAT_DEGRADARE: "text-amber-400",
        STABIL: "text-emerald-400",
    }[data.prediction] || "text-cyan-400";

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="card-cosmic p-4 text-center">
                    <span className="text-xs text-cyan-500/70 block mb-1">Scor Actual</span>
                    <span className="text-3xl font-orbitron text-cyan-300">{data.current_score}</span>
                    <span className="text-lg text-cyan-500/50 ml-2">{data.current_rating}</span>
                </div>
                <div className="card-cosmic p-4 text-center">
                    <span className="text-xs text-cyan-500/70 block mb-1">Proiecție 6 Luni</span>
                    <span className="text-3xl font-orbitron text-amber-300">{data.projected_score_6m}</span>
                    <span className="text-lg text-cyan-500/50 ml-2">{data.projected_rating_6m}</span>
                </div>
                <div className="card-cosmic p-4 text-center">
                    <span className="text-xs text-cyan-500/70 block mb-1">Predicție</span>
                    <span className={`text-xl font-orbitron ${predColor}`}>{data.prediction.replace(/_/g, " ")}</span>
                </div>
                <StatCard
                    title="Semnale"
                    value={`${data.signals_detected} / ${data.total_signals_checked}`}
                    icon={Activity}
                />
            </div>

            {/* Warnings */}
            {data.warnings.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Semnale de Avertizare</h3>
                    <div className="space-y-3">
                        {data.warnings.map((w, i) => (
                            <div key={i} className="flex items-start gap-3 p-3 bg-slate-900/50 rounded-lg border border-cyan-900/30">
                                <Badge variant={
                                    w.severity === "CRITICAL" ? "danger" :
                                        w.severity === "HIGH" ? "warning" :
                                            "info"
                                }>{w.severity}</Badge>
                                <div>
                                    <p className="text-cyan-200 text-sm font-medium">{w.signal.replace(/_/g, " ")}</p>
                                    <p className="text-cyan-400/60 text-xs mt-1">{w.detail}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <DisclaimerBanner>{data.disclaimer}</DisclaimerBanner>
        </div>
    );
}

/* ── Sector Tab ───────────────────────────────────────────────────── */

function SectorTab({ caenCode }: { caenCode: string }) {
    const { data, isLoading } = useQuery<SectorTrendResponse>({
        queryKey: ["sector-trend", caenCode],
        queryFn: () => api.get(`/predictive/sector/${caenCode}`).then(r => r.data),
        enabled: caenCode.length >= 2,
    });

    if (isLoading) return <LoadingSpinner label="Analizez sector..." />;
    if (!data) return null;

    const trendColor = data.sector_trend === "CRESTERE" ? "text-emerald-400" :
        data.sector_trend === "SCADERE" ? "text-red-400" : "text-amber-400";

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard title="Total Firme" value={data.total_companies.toLocaleString()} icon={Layers} />
                <StatCard title="Firme Active" value={data.active_companies.toLocaleString()} icon={Target} />
                <div className="card-cosmic p-4 text-center">
                    <span className="text-xs text-cyan-500/70 block mb-1">Trend Sector</span>
                    <span className={`text-xl font-orbitron ${trendColor}`}>{data.sector_trend}</span>
                </div>
                <StatCard title="Rata Insolvență" value={`${(data.insolvency_rate * 100).toFixed(1)}%`} icon={AlertTriangle} />
            </div>

            {/* Yearly CA chart */}
            {data.yearly_data.length > 0 && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Evoluție CA Sector</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data.yearly_data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                            <XAxis dataKey="an" stroke="#67e8f9" />
                            <YAxis stroke="#67e8f9" tickFormatter={v => `${(v / 1000000000).toFixed(0)}B`} />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#0a1628", border: "1px solid #22d3ee", borderRadius: 8 }}
                                formatter={(v: number) => [`${(v / 1000000).toFixed(0)}M RON`, undefined]}
                            />
                            <Legend />
                            <Bar dataKey="total_ca" name="Total CA" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Births vs Deaths chart */}
            {(data.births.length > 0 || data.deaths.length > 0) && (
                <div className="card-cosmic p-6">
                    <h3 className="text-lg font-orbitron text-cyan-300 mb-4">Nașteri vs. Decese Firme</h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={_mergeBirthsDeath(data.births, data.deaths)}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                            <XAxis dataKey="an" stroke="#67e8f9" />
                            <YAxis stroke="#67e8f9" />
                            <Tooltip contentStyle={{ backgroundColor: "#0a1628", border: "1px solid #22d3ee", borderRadius: 8 }} />
                            <Legend />
                            <Line type="monotone" dataKey="births" name="Înregistrări noi" stroke="#22d3ee" strokeWidth={2} />
                            <Line type="monotone" dataKey="deaths" name="Radieri" stroke="#f87171" strokeWidth={2} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}

/* ── Helpers ──────────────────────────────────────────────────────── */

function ConfidenceBadge({ value }: { value: number | null }) {
    if (value === null || value === undefined) return <span className="text-cyan-500/30">—</span>;
    const pct = (value * 100).toFixed(0);
    const variant = value > 0.7 ? "success" : value > 0.4 ? "warning" : "danger";
    return <Badge variant={variant}>{pct}%</Badge>;
}

function _mergeBirthsDeath(
    births: { an: number; count: number }[],
    deaths: { an: number; count: number }[],
) {
    const map = new Map<number, { an: number; births: number; deaths: number }>();
    for (const b of births) {
        map.set(b.an, { an: b.an, births: b.count, deaths: 0 });
    }
    for (const d of deaths) {
        const existing = map.get(d.an);
        if (existing) {
            existing.deaths = d.count;
        } else {
            map.set(d.an, { an: d.an, births: 0, deaths: d.count });
        }
    }
    return Array.from(map.values()).sort((a, b) => a.an - b.an);
}
