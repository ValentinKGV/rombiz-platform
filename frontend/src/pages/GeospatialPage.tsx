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
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
    PieChart, Pie, Cell, Legend,
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup, Circle } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const tabs: TabItem[] = [
    { id: "heatmap", label: "Heatmap" },
    { id: "zones", label: "Regiuni" },
    { id: "proximity", label: "Proximitate" },
    { id: "county", label: "Județ" },
    { id: "counties", label: "Toate Județele" },
];

const COLORS = ["#818cf8", "#34d399", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316", "#ec4899"];

/* Romania county approximate center coordinates */
const COUNTY_COORDS: Record<string, [number, number]> = {
    "BUCURESTI": [44.4268, 26.1025], "ALBA": [46.07, 23.57], "ARAD": [46.17, 21.32],
    "ARGES": [44.85, 24.87], "BACAU": [46.57, 26.91], "BIHOR": [47.05, 22.0],
    "BISTRITA-NASAUD": [47.14, 24.50], "BOTOSANI": [47.75, 26.67], "BRASOV": [45.65, 25.61],
    "BRAILA": [45.27, 27.97], "BUZAU": [45.15, 26.83], "CARAS-SEVERIN": [45.0, 21.95],
    "CALARASI": [44.2, 26.98], "CLUJ": [46.77, 23.6], "CONSTANTA": [44.18, 28.63],
    "COVASNA": [45.85, 26.18], "DAMBOVITA": [44.93, 25.46], "DOLJ": [44.33, 23.8],
    "GALATI": [45.43, 28.05], "GIURGIU": [43.9, 25.97], "GORJ": [45.05, 23.28],
    "HARGHITA": [46.36, 25.8], "HUNEDOARA": [45.75, 22.9], "IALOMITA": [44.57, 26.83],
    "IASI": [47.16, 27.58], "ILFOV": [44.5, 26.08], "MARAMURES": [47.66, 24.0],
    "MEHEDINTI": [44.63, 22.65], "MURES": [46.55, 24.56], "NEAMT": [46.93, 26.37],
    "OLT": [44.43, 24.37], "PRAHOVA": [45.1, 25.95], "SATU MARE": [47.8, 22.88],
    "SALAJ": [47.2, 23.06], "SIBIU": [45.8, 24.15], "SUCEAVA": [47.65, 25.92],
    "TELEORMAN": [43.98, 25.35], "TIMIS": [45.75, 21.23], "TULCEA": [45.18, 28.8],
    "VASLUI": [46.64, 27.73], "VALCEA": [45.1, 24.37], "VRANCEA": [45.7, 27.18],
};

export default function GeospatialPage() {
    const [active, setActive] = useState("heatmap");
    const [judet, setJudet] = useState("");
    const [searchJudet, setSearchJudet] = useState("");
    const [lat, setLat] = useState("44.4268");
    const [lng, setLng] = useState("26.1025");
    const [radius, setRadius] = useState("10");

    const { data: heatmap, isLoading: loadHeat } = useQuery({
        queryKey: ["geo-heatmap"],
        queryFn: () => api.get("/geo/heatmap").then(r => r.data),
        enabled: active === "heatmap",
    });

    const { data: zones, isLoading: loadZones } = useQuery({
        queryKey: ["geo-zones"],
        queryFn: () => api.get("/geo/zones").then(r => r.data),
        enabled: active === "zones",
    });

    const { data: proximity, isLoading: loadProx } = useQuery({
        queryKey: ["geo-proximity", lat, lng, radius],
        queryFn: () => api.get(`/geo/proximity?lat=${lat}&lng=${lng}&radius_km=${radius}`).then(r => r.data),
        enabled: active === "proximity" && !!lat && !!lng,
    });

    const { data: geodemo, isLoading: loadGeo } = useQuery({
        queryKey: ["geo-demo", searchJudet],
        queryFn: () => api.get(`/geo/geodemographic/${searchJudet}`).then(r => r.data),
        enabled: active === "county" && !!searchJudet,
    });

    const { data: counties, isLoading: loadCounties } = useQuery({
        queryKey: ["geo-counties"],
        queryFn: () => api.get("/geo/counties").then(r => r.data),
        enabled: active === "counties",
    });

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Geospatial BI"
                subtitle="Heatmap firme, regiuni economice, analiză proximitate, statistici județe"
            />

            <TabNav tabs={tabs} activeTab={active} onTabChange={setActive} />

            {/* Heatmap */}
            {active === "heatmap" && (
                loadHeat ? <LoadingSpinner /> :
                    heatmap?.regions?.length ? (
                        <div className="space-y-4">
                            <StatCard label="Total Firme" value={heatmap.total_companies} />

                            {/* Leaflet Heatmap */}
                            <div className="card-cosmic overflow-hidden" style={{ height: 420 }}>
                                <MapContainer
                                    center={[45.9432, 24.9668]}
                                    zoom={7}
                                    style={{ height: "100%", width: "100%", borderRadius: "0.5rem" }}
                                    scrollWheelZoom
                                >
                                    <TileLayer
                                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                        attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>'
                                    />
                                    {heatmap.regions.map((r: any) => {
                                        const coords = COUNTY_COORDS[r.judet?.toUpperCase()];
                                        if (!coords) return null;
                                        const maxCount = Math.max(...heatmap.regions.map((x: any) => x.company_count || 1));
                                        const ratio = (r.company_count || 0) / maxCount;
                                        return (
                                            <CircleMarker
                                                key={r.judet}
                                                center={coords}
                                                radius={8 + ratio * 25}
                                                pathOptions={{
                                                    color: ratio > 0.6 ? "#ef4444" : ratio > 0.3 ? "#f59e0b" : "#818cf8",
                                                    fillColor: ratio > 0.6 ? "#ef4444" : ratio > 0.3 ? "#f59e0b" : "#818cf8",
                                                    fillOpacity: 0.5 + ratio * 0.3,
                                                    weight: 2,
                                                }}
                                            >
                                                <Popup>
                                                    <strong>{r.judet}</strong><br />
                                                    Firme: {r.company_count?.toLocaleString("ro-RO")}<br />
                                                    Cotă: {r.share_pct}%
                                                </Popup>
                                            </CircleMarker>
                                        );
                                    })}
                                </MapContainer>
                            </div>

                            <div className="h-80">
                                <ResponsiveContainer>
                                    <BarChart data={heatmap.regions.slice(0, 20)} layout="vertical">
                                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                        <XAxis type="number" stroke="#94a3b8" />
                                        <YAxis type="category" dataKey="judet" stroke="#94a3b8" width={100} tick={{ fontSize: 11 }} />
                                        <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                        <Bar dataKey="company_count" name="Firme" fill="#818cf8" />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="card-cosmic overflow-hidden max-h-96 overflow-y-auto">
                                <table className="w-full text-sm">
                                    <thead className="sticky top-0 bg-nebula-800">
                                        <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                            <th className="p-3">Județ</th>
                                            <th className="p-3 text-right">Firme</th>
                                            <th className="p-3 text-right">Cotă %</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {heatmap.regions.map((r: any) => (
                                            <tr key={r.judet} className="border-b border-nebula-800/30">
                                                <td className="p-3">{r.judet}</td>
                                                <td className="p-3 text-right">{r.company_count.toLocaleString("ro-RO")}</td>
                                                <td className="p-3 text-right text-nebula-400">{r.share_pct}%</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : null
            )}

            {/* Zones */}
            {active === "zones" && (
                loadZones ? <LoadingSpinner /> :
                    zones?.zones?.length ? (
                        <div className="space-y-4">
                            <div className="h-72">
                                <ResponsiveContainer>
                                    <PieChart>
                                        <Pie data={zones.zones} dataKey="company_count" nameKey="region" cx="50%" cy="50%" outerRadius={100} label>
                                            {zones.zones.map((_: any, i: number) => (
                                                <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                        <Legend />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {zones.zones.map((z: any) => (
                                    <div key={z.region} className="card-cosmic p-4">
                                        <h3 className="font-semibold text-nebula-200 mb-2">{z.region}</h3>
                                        <p className="text-2xl font-bold text-indigo-400">{z.company_count.toLocaleString("ro-RO")}</p>
                                        <p className="text-xs text-nebula-500 mt-1">{z.counties.join(", ")}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : null
            )}

            {/* Proximity */}
            {active === "proximity" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex flex-wrap gap-3 items-end">
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Latitudine</label>
                            <input className="input-scifi w-32" value={lat} onChange={e => setLat(e.target.value)} />
                        </div>
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Longitudine</label>
                            <input className="input-scifi w-32" value={lng} onChange={e => setLng(e.target.value)} />
                        </div>
                        <div>
                            <label className="block text-xs text-nebula-300 mb-1">Rază (km)</label>
                            <input className="input-scifi w-24" value={radius} onChange={e => setRadius(e.target.value)} />
                        </div>
                    </div>
                    {loadProx ? <LoadingSpinner /> :
                        proximity?.companies?.length ? (
                            <>
                                <StatCard label="Firme Găsite" value={proximity.count} />

                                {/* Proximity map */}
                                <div className="card-cosmic overflow-hidden" style={{ height: 380 }}>
                                    <MapContainer
                                        center={[parseFloat(lat), parseFloat(lng)]}
                                        zoom={11}
                                        style={{ height: "100%", width: "100%", borderRadius: "0.5rem" }}
                                        scrollWheelZoom
                                    >
                                        <TileLayer
                                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                            attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>'
                                        />
                                        <Circle
                                            center={[parseFloat(lat), parseFloat(lng)]}
                                            radius={parseFloat(radius) * 1000}
                                            pathOptions={{ color: "#818cf8", fillOpacity: 0.1 }}
                                        />
                                        {proximity.companies.map((c: any) => {
                                            if (!c.lat || !c.lng) return null;
                                            return (
                                                <CircleMarker
                                                    key={c.company_id}
                                                    center={[c.lat, c.lng]}
                                                    radius={6}
                                                    pathOptions={{ color: "#ef4444", fillColor: "#ef4444", fillOpacity: 0.6 }}
                                                >
                                                    <Popup>
                                                        <strong>{c.name}</strong><br />
                                                        CAEN: {c.caen}<br />
                                                        Distanță: {c.distance_km} km
                                                    </Popup>
                                                </CircleMarker>
                                            );
                                        })}
                                    </MapContainer>
                                </div>

                                <div className="card-cosmic overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                                <th className="p-3">Denumire</th>
                                                <th className="p-3">CAEN</th>
                                                <th className="p-3">Județ</th>
                                                <th className="p-3 text-right">Distanță (km)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {proximity.companies.map((c: any) => (
                                                <tr key={c.company_id} className="border-b border-nebula-800/30">
                                                    <td className="p-3">{c.name}</td>
                                                    <td className="p-3 font-mono text-xs">{c.caen}</td>
                                                    <td className="p-3">{c.judet}</td>
                                                    <td className="p-3 text-right">{c.distance_km}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </>
                        ) : <div className="card-cosmic p-8 text-center text-nebula-400">Nicio firmă găsită în raza specificată.</div>}
                </div>
            )}

            {/* County Detail */}
            {active === "county" && (
                <div className="space-y-4">
                    <div className="card-cosmic p-4 flex gap-3 items-end">
                        <div className="flex-1">
                            <label className="block text-xs text-nebula-300 mb-1">Județ</label>
                            <input className="input-scifi w-full" placeholder="ex: BUCURESTI..."
                                value={judet} onChange={e => setJudet(e.target.value.toUpperCase())}
                                onKeyDown={e => e.key === "Enter" && setSearchJudet(judet)} />
                        </div>
                        <button className="btn-cosmic" onClick={() => setSearchJudet(judet)}>Analizează</button>
                    </div>
                    {loadGeo ? <LoadingSpinner /> :
                        geodemo ? (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <StatCard label="Firme Active" value={geodemo.active_companies} />
                                    <StatCard label="Rata Supraviețuire" value={`${geodemo.survival_rate}%`} />
                                    <StatCard label="Total Revenue" value={`${(geodemo.financials?.total_revenue / 1_000_000)?.toFixed(1)}M`} />
                                    <StatCard label="Total Angajați" value={geodemo.financials?.total_employees?.toLocaleString("ro-RO")} />
                                </div>
                                {geodemo.top_sectors?.length > 0 && (
                                    <div className="h-60">
                                        <ResponsiveContainer>
                                            <BarChart data={geodemo.top_sectors}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                                <XAxis dataKey="caen_prefix" stroke="#94a3b8" />
                                                <YAxis stroke="#94a3b8" />
                                                <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155" }} />
                                                <Bar dataKey="company_count" name="Firme" fill="#34d399" />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            </>
                        ) : null}
                </div>
            )}

            {/* All Counties */}
            {active === "counties" && (
                loadCounties ? <LoadingSpinner /> :
                    counties?.counties?.length ? (
                        <div className="card-cosmic overflow-hidden max-h-[600px] overflow-y-auto">
                            <table className="w-full text-sm">
                                <thead className="sticky top-0 bg-nebula-800">
                                    <tr className="border-b border-nebula-700/40 text-nebula-400 text-left">
                                        <th className="p-3">Județ</th>
                                        <th className="p-3 text-right">Total</th>
                                        <th className="p-3 text-right">Active</th>
                                        <th className="p-3 text-right">Revenue Total</th>
                                        <th className="p-3 text-right">Angajați</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {counties.counties.map((c: any) => (
                                        <tr key={c.judet} className="border-b border-nebula-800/30 hover:bg-nebula-900/30">
                                            <td className="p-3 font-medium">{c.judet}</td>
                                            <td className="p-3 text-right">{c.total_companies.toLocaleString("ro-RO")}</td>
                                            <td className="p-3 text-right">{c.active_companies.toLocaleString("ro-RO")}</td>
                                            <td className="p-3 text-right">{c.total_revenue.toLocaleString("ro-RO")}</td>
                                            <td className="p-3 text-right">{c.total_employees.toLocaleString("ro-RO")}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : null
            )}

            <DisclaimerBanner text="Datele geospațiale sunt aproximative. Coordonatele pot avea o marjă de eroare." />
        </div>
    );
}
