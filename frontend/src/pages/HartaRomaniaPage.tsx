import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatNumber, cn } from "@/lib/utils";
import { MapPin, Search, TrendingUp } from "lucide-react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

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

const COUNTY_NAMES = Object.keys(COUNTY_COORDS).sort();

function getClusterColor(count: number): string {
    if (count >= 50000) return "#ef4444";
    if (count >= 20000) return "#f59e0b";
    if (count >= 5000) return "#818cf8";
    if (count >= 1000) return "#34d399";
    return "#94a3b8";
}

function getClusterRadius(count: number, maxCount: number): number {
    const min = 8, max = 40;
    if (maxCount === 0) return min;
    return min + (count / maxCount) * (max - min);
}

/* Fly to county component */
function FlyToCounty({ coords }: { coords: [number, number] | null }) {
    const map = useMap();
    if (coords) {
        map.flyTo(coords, 10, { duration: 0.8 });
    }
    return null;
}

export default function HartaRomaniaPage() {
    const [selectedCounty, setSelectedCounty] = useState<string | null>(null);
    const [flyTarget, setFlyTarget] = useState<[number, number] | null>(null);
    const [searchQ, setSearchQ] = useState("");

    /* Fetch company counts per county */
    const { data: heatmap, isLoading } = useQuery({
        queryKey: ["geo-heatmap"],
        queryFn: () => api.get("/geo/heatmap").then(r => r.data),
        staleTime: 300_000,
    });

    /* Fetch companies in selected county */
    const { data: countyCompanies, isLoading: loadingCompanies } = useQuery({
        queryKey: ["county-companies", selectedCounty],
        queryFn: () => api.post("/search", {
            query: "",
            judet: selectedCounty,
            per_page: 20,
            sort_by: "cifra_afaceri",
            sort_dir: "desc",
        }).then(r => r.data),
        enabled: !!selectedCounty,
    });

    const countyData = useMemo(() => {
        if (!heatmap) return [];
        const entries = Object.entries(heatmap as Record<string, number>);
        return entries.map(([judet, count]) => ({
            judet: judet.toUpperCase(),
            count: count as number,
            coords: COUNTY_COORDS[judet.toUpperCase()] || null,
        })).filter(e => e.coords);
    }, [heatmap]);

    const maxCount = useMemo(() => Math.max(...countyData.map(d => d.count), 1), [countyData]);

    const totalCompanies = useMemo(() => countyData.reduce((s, d) => s + d.count, 0), [countyData]);

    /* Top 5 counties */
    const topCounties = useMemo(
        () => [...countyData].sort((a, b) => b.count - a.count).slice(0, 5),
        [countyData]
    );

    const filteredCounties = searchQ
        ? COUNTY_NAMES.filter(c => c.toLowerCase().includes(searchQ.toLowerCase()))
        : COUNTY_NAMES;

    const handleCountyClick = (judet: string) => {
        setSelectedCounty(judet);
        const coords = COUNTY_COORDS[judet];
        if (coords) setFlyTarget([...coords]);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">Harta Interactivă România</h1>
                <p className="mt-1 font-exo text-sm text-muted-foreground">
                    Distribuția firmelor pe județe — click pe cluster pentru detalii
                </p>
            </div>

            {/* KPI Row */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="card-cosmic text-center">
                    <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-muted-foreground">Total Firme</p>
                    <p className="mt-1 font-orbitron text-2xl font-bold text-nebula">{formatNumber(totalCompanies)}</p>
                </div>
                <div className="card-cosmic text-center">
                    <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-muted-foreground">Județe Active</p>
                    <p className="mt-1 font-orbitron text-2xl font-bold text-nebula">{countyData.length}</p>
                </div>
                <div className="card-cosmic text-center">
                    <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-muted-foreground">#1 Județ</p>
                    <p className="mt-1 font-orbitron text-lg font-bold text-nebula">{topCounties[0]?.judet || "—"}</p>
                </div>
                <div className="card-cosmic text-center">
                    <p className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-muted-foreground">Media / Județ</p>
                    <p className="mt-1 font-orbitron text-2xl font-bold text-nebula">
                        {countyData.length ? formatNumber(Math.round(totalCompanies / countyData.length)) : "—"}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                {/* Map */}
                <div className="lg:col-span-2 card-cosmic overflow-hidden p-0" style={{ height: 520 }}>
                    {isLoading ? (
                        <div className="flex h-full items-center justify-center">
                            <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        </div>
                    ) : (
                        <MapContainer
                            center={[45.9432, 24.9668]}
                            zoom={7}
                            scrollWheelZoom={true}
                            className="h-full w-full"
                            style={{ background: "hsl(var(--background))" }}
                        >
                            <TileLayer
                                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
                            />
                            <FlyToCounty coords={flyTarget} />
                            {countyData.map(({ judet, count, coords }) => (
                                <CircleMarker
                                    key={judet}
                                    center={coords!}
                                    radius={getClusterRadius(count, maxCount)}
                                    pathOptions={{
                                        fillColor: getClusterColor(count),
                                        fillOpacity: 0.7,
                                        color: selectedCounty === judet ? "#fff" : getClusterColor(count),
                                        weight: selectedCounty === judet ? 3 : 1.5,
                                    }}
                                    eventHandlers={{
                                        click: () => handleCountyClick(judet),
                                    }}
                                >
                                    <Popup>
                                        <div className="text-center font-exo">
                                            <p className="font-semibold">{judet}</p>
                                            <p className="text-lg font-bold text-nebula-600">{formatNumber(count)} firme</p>
                                        </div>
                                    </Popup>
                                </CircleMarker>
                            ))}
                        </MapContainer>
                    )}
                </div>

                {/* Sidebar — County selector + details */}
                <div className="space-y-4">
                    {/* Search */}
                    <div className="card-cosmic p-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <input
                                type="text"
                                value={searchQ}
                                onChange={e => setSearchQ(e.target.value)}
                                placeholder="Caută județ..."
                                className="input-scifi w-full pl-10 text-sm"
                            />
                        </div>
                    </div>

                    {/* Top counties */}
                    <div className="card-cosmic">
                        <h3 className="mb-3 font-orbitron text-sm font-semibold text-foreground flex items-center gap-2">
                            <TrendingUp className="h-4 w-4 text-nebula-500" /> Top Județe
                        </h3>
                        <div className="space-y-2">
                            {topCounties.map((d, i) => (
                                <button
                                    key={d.judet}
                                    onClick={() => handleCountyClick(d.judet)}
                                    className={cn(
                                        "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                                        selectedCounty === d.judet ? "bg-nebula-100 dark:bg-nebula-900/30" : "hover:bg-nebula-50/50 dark:hover:bg-nebula-900/20"
                                    )}
                                >
                                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-nebula-gradient text-[10px] font-bold text-white">
                                        {i + 1}
                                    </span>
                                    <span className="flex-1 font-exo font-medium text-foreground">{d.judet}</span>
                                    <span className="font-rajdhani text-xs font-semibold text-muted-foreground">{formatNumber(d.count)}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* County list */}
                    <div className="card-cosmic max-h-60 overflow-y-auto scrollbar-cosmic">
                        <h3 className="mb-2 font-orbitron text-sm font-semibold text-foreground">Toate Județele</h3>
                        <div className="space-y-0.5">
                            {filteredCounties.map(judet => {
                                const d = countyData.find(x => x.judet === judet);
                                return (
                                    <button
                                        key={judet}
                                        onClick={() => handleCountyClick(judet)}
                                        className={cn(
                                            "flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-sm transition-colors",
                                            selectedCounty === judet ? "bg-nebula-100 dark:bg-nebula-900/30 font-semibold" : "hover:bg-nebula-50/50 dark:hover:bg-nebula-900/20"
                                        )}
                                    >
                                        <span className="font-exo text-foreground">{judet}</span>
                                        <span className="font-rajdhani text-xs text-muted-foreground">{d ? formatNumber(d.count) : "0"}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* Selected county — top companies */}
            {selectedCounty && (
                <div className="card-cosmic">
                    <h2 className="mb-4 font-orbitron text-lg font-semibold text-foreground flex items-center gap-2">
                        <MapPin className="h-5 w-5 text-nebula-500" />
                        Top Firme — {selectedCounty}
                    </h2>
                    {loadingCompanies ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="h-8 w-8 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="table-cosmic w-full text-sm">
                                <thead>
                                    <tr>
                                        <th className="text-left">Denumire</th>
                                        <th className="text-left">CUI</th>
                                        <th className="text-left">Localitate</th>
                                        <th className="text-left">CAEN</th>
                                        <th className="text-left">Stare</th>
                                        <th className="text-right">Scor Risc</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(countyCompanies?.items || countyCompanies?.results || []).map((c: {
                                        id: number; cui: string; denumire: string; localitate: string;
                                        caen_principal: string; stare: string; risk_score?: string; risk_rating?: string;
                                    }) => (
                                        <tr key={c.id}>
                                            <td>
                                                <Link to={`/company/${c.cui}`} className="font-medium text-nebula-600 dark:text-nebula-400 hover:underline">
                                                    {c.denumire}
                                                </Link>
                                            </td>
                                            <td className="text-muted-foreground">{c.cui}</td>
                                            <td className="text-muted-foreground">{c.localitate}</td>
                                            <td className="text-muted-foreground">{c.caen_principal}</td>
                                            <td>
                                                <span className={cn(
                                                    "rounded-full px-2 py-0.5 text-[10px] font-bold",
                                                    c.stare === "ACTIVA" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                                                )}>{c.stare}</span>
                                            </td>
                                            <td className="text-right">
                                                {c.risk_rating && (
                                                    <span className={cn(
                                                        "rounded-full px-2 py-0.5 text-[10px] font-bold",
                                                        c.risk_rating === "A" ? "bg-green-100 text-green-700" :
                                                            c.risk_rating === "B" ? "bg-blue-100 text-blue-700" :
                                                                c.risk_rating === "C" ? "bg-yellow-100 text-yellow-700" :
                                                                    c.risk_rating === "D" ? "bg-orange-100 text-orange-700" :
                                                                        "bg-red-100 text-red-700"
                                                    )}>{c.risk_rating}</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* Legend */}
            <div className="card-cosmic">
                <h3 className="mb-2 font-orbitron text-sm font-semibold text-foreground">Legendă Cluster</h3>
                <div className="flex flex-wrap gap-4 text-xs">
                    {[
                        { label: "< 1,000", color: "#94a3b8" },
                        { label: "1,000–5,000", color: "#34d399" },
                        { label: "5,000–20,000", color: "#818cf8" },
                        { label: "20,000–50,000", color: "#f59e0b" },
                        { label: "50,000+", color: "#ef4444" },
                    ].map(l => (
                        <div key={l.label} className="flex items-center gap-1.5">
                            <span className="inline-block h-3 w-3 rounded-full" style={{ background: l.color }} />
                            <span className="font-rajdhani text-muted-foreground">{l.label}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
