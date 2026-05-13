import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
    XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
    LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import { toast } from "sonner";

const tabs: TabItem[] = [
    { id: "keys", label: "Chei API" },
    { id: "usage", label: "Utilizare" },
    { id: "limits", label: "Rate Limits" },
    { id: "sdk", label: "SDK & Docs" },
    { id: "webhooks", label: "Webhooks" },
];

const COLORS = ["#818cf8", "#34d399", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

export default function APIMarketplacePage() {
    const [active, setActive] = useState("keys");
    const [keyName, setKeyName] = useState("");
    const [sdkLang, setSdkLang] = useState("python");
    const [whUrl, setWhUrl] = useState("");
    const qc = useQueryClient();

    // Keys
    const { data: keys, isLoading: loadKeys } = useQuery({
        queryKey: ["marketplace-keys"],
        queryFn: () => api.get("/marketplace/keys").then(r => r.data),
        enabled: active === "keys",
    });

    const createKeyMut = useMutation({
        mutationFn: (name: string) => api.post("/marketplace/keys", { name }).then(r => r.data),
        onSuccess: (data) => {
            toast.success("Cheie API creată!", { description: `Key: ${data.api_key?.slice(0, 20)}...` });
            qc.invalidateQueries({ queryKey: ["marketplace-keys"] });
            setKeyName("");
        },
    });

    const revokeKeyMut = useMutation({
        mutationFn: (keyId: string) => api.delete(`/marketplace/keys/${keyId}`).then(r => r.data),
        onSuccess: () => {
            toast.info("Cheie revocată");
            qc.invalidateQueries({ queryKey: ["marketplace-keys"] });
        },
    });

    // Usage
    const { data: usage, isLoading: loadUsage } = useQuery({
        queryKey: ["marketplace-usage"],
        queryFn: () => api.get("/marketplace/usage").then(r => r.data),
        enabled: active === "usage",
    });

    // Rate limits
    const { data: limits, isLoading: loadLimits } = useQuery({
        queryKey: ["marketplace-limits"],
        queryFn: () => api.get("/marketplace/rate-limits").then(r => r.data),
        enabled: active === "limits",
    });

    // SDK docs
    const { data: sdk, isLoading: loadSdk } = useQuery({
        queryKey: ["marketplace-sdk", sdkLang],
        queryFn: () => api.get(`/marketplace/sdk/${sdkLang}`).then(r => r.data),
        enabled: active === "sdk",
    });

    // Webhooks
    const { data: webhooks, isLoading: loadWh } = useQuery({
        queryKey: ["marketplace-webhooks"],
        queryFn: () => api.post("/marketplace/webhooks", { action: "list" }).then(r => r.data),
        enabled: active === "webhooks",
    });

    const createWhMut = useMutation({
        mutationFn: (url: string) =>
            api.post("/marketplace/webhooks", {
                action: "create",
                webhook_url: url,
                events: ["company.updated", "alert.created"],
            }).then(r => r.data),
        onSuccess: () => {
            toast.success("Webhook creat!");
            qc.invalidateQueries({ queryKey: ["marketplace-webhooks"] });
            setWhUrl("");
        },
    });

    return (
        <div className="space-y-6">
            <SectionHeader
                title="API Marketplace"
                subtitle="Chei API, utilizare, rate limits, SDK și webhooks"
            />

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Keys */}
            {active === "keys" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3 items-end">
                        <div className="flex-1">
                            <label className="block text-xs text-nebula-300 mb-1">Nume Cheie</label>
                            <input className="input-scifi w-full" placeholder="Production Key..."
                                value={keyName} onChange={e => setKeyName(e.target.value)} />
                        </div>
                        <button className="btn-cosmic" onClick={() => keyName && createKeyMut.mutate(keyName)}
                            disabled={createKeyMut.isPending}>
                            {createKeyMut.isPending ? "Se creează..." : "Creează Cheie"}
                        </button>
                    </div>

                    {loadKeys ? <LoadingSpinner /> :
                        keys?.keys?.length ? (
                            <div className="card-cosmic overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                            <th className="p-3">Nume</th>
                                            <th className="p-3">Key ID</th>
                                            <th className="p-3">Scope-uri</th>
                                            <th className="p-3">Creat</th>
                                            <th className="p-3">Status</th>
                                            <th className="p-3">Cereri</th>
                                            <th className="p-3"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {keys.keys.map((k: any) => (
                                            <tr key={k.key_id} className="border-b border-nebula-800/30">
                                                <td className="p-3 font-medium">{k.name}</td>
                                                <td className="p-3 font-mono text-xs">{k.key_id}</td>
                                                <td className="p-3">
                                                    {k.scopes?.map((s: string) => (
                                                        <Badge key={s} variant="info" className="mr-1">{s}</Badge>
                                                    ))}
                                                </td>
                                                <td className="p-3 text-xs text-nebula-400">{k.created_at?.slice(0, 10)}</td>
                                                <td className="p-3">
                                                    <Badge variant={k.is_active ? "success" : "danger"}>
                                                        {k.is_active ? "Activ" : "Revocat"}
                                                    </Badge>
                                                </td>
                                                <td className="p-3 text-right">{k.requests_count?.toLocaleString("ro-RO")}</td>
                                                <td className="p-3">
                                                    {k.is_active && (
                                                        <button className="text-xs text-red-400 hover:text-red-300"
                                                            onClick={() => revokeKeyMut.mutate(k.key_id)}>
                                                            Revocă
                                                        </button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Nu ai chei API create. Creează una mai sus.</div>}
                </div>
            )}

            {/* Usage */}
            {active === "usage" && (
                loadUsage ? <LoadingSpinner /> :
                    usage ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <StatCard label="Total Cereri" value={usage.total_requests?.toLocaleString("ro-RO")} />
                                <StatCard label="Latență Medie" value={`${usage.avg_latency_ms} ms`} />
                                <StatCard label="Rată Erori" value={`${usage.error_rate_pct}%`} />
                            </div>

                            {/* Daily chart */}
                            {usage.daily_breakdown?.length > 0 && (
                                <div className="card-cosmic p-4">
                                    <h3 className="text-sm font-medium text-nebula-300 mb-3">Cereri Zilnice</h3>
                                    <div className="h-56">
                                        <ResponsiveContainer>
                                            <LineChart data={usage.daily_breakdown}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                                <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                                                <YAxis stroke="#94a3b8" />
                                                <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                                <Line type="monotone" dataKey="requests" stroke="#818cf8" strokeWidth={2} dot={false} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            )}

                            {/* Status codes pie */}
                            {usage.status_codes?.length > 0 && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-medium text-nebula-300 mb-3">Status Codes</h3>
                                        <div className="h-48">
                                            <ResponsiveContainer>
                                                <PieChart>
                                                    <Pie data={usage.status_codes} dataKey="count" nameKey="code" cx="50%" cy="50%" outerRadius={70} label>
                                                        {usage.status_codes.map((_: any, i: number) => (
                                                            <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                                    <Legend />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    {/* Top endpoints */}
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-medium text-nebula-300 mb-3">Top Endpoints</h3>
                                        <div className="space-y-2">
                                            {usage.top_endpoints?.slice(0, 5).map((ep: any) => (
                                                <div key={ep.endpoint} className="flex justify-between text-sm">
                                                    <span className="text-nebula-300 font-mono text-xs truncate flex-1">{ep.endpoint}</span>
                                                    <span className="text-indigo-400 ml-2">{ep.requests}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : null
            )}

            {/* Rate Limits */}
            {active === "limits" && (
                loadLimits ? <LoadingSpinner /> :
                    limits ? (
                        <div className="space-y-4">
                            <div className="card-cosmic p-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="text-sm text-nebula-300">Plan Curent:</span>
                                    <Badge variant="info">{limits.plan?.toUpperCase()}</Badge>
                                </div>
                            </div>

                            {/* Keys limits */}
                            {limits.keys?.map((k: any) => (
                                <div key={k.key_id} className="card-cosmic p-4">
                                    <h3 className="text-sm font-semibold text-nebula-200 mb-3">{k.key_name} ({k.key_id})</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        {Object.entries(k.limits || {}).map(([key, val]) => (
                                            <div key={key} className="bg-nebula-900/30 rounded-lg p-3">
                                                <p className="text-xs text-nebula-500 mb-1">{key.replace(/_/g, " ")}</p>
                                                <p className="text-lg font-bold text-indigo-400">{String(val)}</p>
                                                {k.current_usage && (
                                                    <div className="mt-2">
                                                        <div className="flex justify-between text-xs text-nebula-500">
                                                            <span>Utilizat</span>
                                                            <span>{(k.current_usage as any)?.[key.split("_").pop()!] || 0}</span>
                                                        </div>
                                                        <div className="w-full bg-nebula-800 rounded-full h-1.5 mt-1">
                                                            <div className="bg-indigo-500 h-1.5 rounded-full"
                                                                style={{
                                                                    width: `${Math.min(
                                                                        ((k.current_usage as any)?.[key.split("_").pop()!] || 0) / Math.max(Number(val), 1) * 100,
                                                                        100
                                                                    )}%`
                                                                }} />
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}

                            {/* Plans */}
                            {limits.available_plans?.length > 0 && (
                                <>
                                    <h3 className="text-sm font-semibold text-nebula-300">Planuri Disponibile</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                        {limits.available_plans.map((p: any) => (
                                            <div key={p.name} className={`card-cosmic p-4 text-center ${p.name === limits.plan ? "ring-2 ring-indigo-500" : ""
                                                }`}>
                                                <h4 className="text-lg font-bold text-nebula-200 uppercase mb-2">{p.name}</h4>
                                                <p className="text-2xl font-bold text-indigo-400 mb-3">
                                                    {p.price_eur === 0 ? "Gratuit" : `€${p.price_eur}/lună`}
                                                </p>
                                                <div className="text-xs text-nebula-400 space-y-1">
                                                    <p>{p.rpm} req/min</p>
                                                    <p>{p.rph.toLocaleString()} req/oră</p>
                                                    <p>{p.rpd.toLocaleString()} req/zi</p>
                                                </div>
                                                {p.name === limits.plan && (
                                                    <Badge variant="success" className="mt-3">Plan Activ</Badge>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    ) : null
            )}

            {/* SDK & Docs */}
            {active === "sdk" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3">
                        {["python", "javascript", "curl"].map(lang => (
                            <button key={lang} onClick={() => setSdkLang(lang)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${sdkLang === lang ? "bg-indigo-600 text-white" : "bg-nebula-800 text-nebula-400 hover:text-nebula-200"
                                    }`}>
                                {lang.charAt(0).toUpperCase() + lang.slice(1)}
                            </button>
                        ))}
                    </div>

                    {loadSdk ? <LoadingSpinner /> :
                        sdk?.sdk ? (
                            <>
                                <div className="card-cosmic p-4">
                                    <h3 className="text-sm font-semibold text-nebula-300 mb-2">Instalare</h3>
                                    <pre className="bg-nebula-950 rounded-lg p-3 text-xs font-mono text-green-400 overflow-x-auto">
                                        {sdk.sdk.install}
                                    </pre>
                                </div>

                                {["auth_example", "search_example", "risk_example", "webhook_example"].map(key => (
                                    sdk.sdk[key] && (
                                        <div key={key} className="card-cosmic p-4">
                                            <h3 className="text-sm font-semibold text-nebula-300 mb-2">
                                                {key.replace("_example", "").replace("_", " ").toUpperCase()}
                                            </h3>
                                            <pre className="bg-nebula-950 rounded-lg p-3 text-xs font-mono text-nebula-300 overflow-x-auto whitespace-pre-wrap">
                                                {sdk.sdk[key]}
                                            </pre>
                                        </div>
                                    )
                                ))}

                                {/* API Endpoints */}
                                {sdk.endpoints?.length > 0 && (
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-semibold text-nebula-300 mb-3">Endpoints Disponibile</h3>
                                        <div className="space-y-2">
                                            {sdk.endpoints.map((ep: any) => (
                                                <div key={ep.path} className="flex items-center gap-3 text-sm">
                                                    <Badge variant={ep.method === "POST" ? "warning" : "success"}>{ep.method}</Badge>
                                                    <span className="font-mono text-xs text-nebula-300 flex-1">{ep.path}</span>
                                                    <span className="text-nebula-500 text-xs">{ep.description}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : null}
                </div>
            )}

            {/* Webhooks */}
            {active === "webhooks" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3 items-end">
                        <div className="flex-1">
                            <label className="block text-xs text-nebula-300 mb-1">Webhook URL</label>
                            <input className="input-scifi w-full" placeholder="https://your-app.com/webhook..."
                                value={whUrl} onChange={e => setWhUrl(e.target.value)} />
                        </div>
                        <button className="btn-cosmic" onClick={() => whUrl && createWhMut.mutate(whUrl)}
                            disabled={createWhMut.isPending}>
                            {createWhMut.isPending ? "Se creează..." : "Adaugă Webhook"}
                        </button>
                    </div>

                    {loadWh ? <LoadingSpinner /> :
                        webhooks?.webhooks?.length ? (
                            <div className="space-y-3">
                                {webhooks.webhooks.map((wh: any) => (
                                    <div key={wh.id} className="card-cosmic p-4">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <p className="font-mono text-sm text-nebula-200">{wh.url}</p>
                                                <div className="flex gap-1 mt-2">
                                                    {wh.events?.map((ev: string) => (
                                                        <Badge key={ev} variant="info" className="text-xs">{ev}</Badge>
                                                    ))}
                                                </div>
                                            </div>
                                            <Badge variant={wh.is_active ? "success" : "danger"}>
                                                {wh.is_active ? "Activ" : "Inactiv"}
                                            </Badge>
                                        </div>
                                        <div className="mt-3 flex gap-4 text-xs text-nebula-500">
                                            <span>Livrări: {wh.deliveries}</span>
                                            <span>Ultima: {wh.last_delivery?.slice(0, 16)?.replace("T", " ") || "—"}</span>
                                            <span>Creat: {wh.created_at?.slice(0, 10)}</span>
                                        </div>
                                    </div>
                                ))}

                                {/* Available events */}
                                {webhooks.available_events?.length > 0 && (
                                    <div className="card-cosmic p-4">
                                        <h3 className="text-sm font-semibold text-nebula-300 mb-2">Evenimente Disponibile</h3>
                                        <div className="flex flex-wrap gap-2">
                                            {webhooks.available_events.map((ev: string) => (
                                                <Badge key={ev} variant="neutral">{ev}</Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Niciun webhook configurat.</div>}
                </div>
            )}

            <DisclaimerBanner text="Cheile API oferă acces la toate endpoint-urile conform scope-urilor selectate. Păstrați cheile în siguranță." />
        </div>
    );
}
