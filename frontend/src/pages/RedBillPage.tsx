import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatMoney, cn } from "@/lib/utils";
import { FileText, Orbit, Search, TrendingUp } from "lucide-react";

export default function RedBillPage() {
    const [cuiSearch, setCuiSearch] = useState("");
    const [selectedCui, setSelectedCui] = useState<string | null>(null);

    const { data: profile, isLoading } = useQuery({
        queryKey: ["redbill", selectedCui],
        queryFn: async () => {
            const { data } = await api.get(`/redbill/${selectedCui}`);
            return data;
        },
        enabled: !!selectedCui,
    });

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSelectedCui(cuiSearch);
    };

    const riskColor = (classification: string) => {
        const map: Record<string, string> = {
            green: "bg-green-100 text-green-700",
            yellow: "bg-yellow-100 text-yellow-700",
            orange: "bg-orange-100 text-orange-700",
            red: "bg-red-100 text-red-700",
        };
        return map[classification] || "bg-muted text-muted-foreground";
    };

    return (
        <div className="space-y-6">
            <div className="section-header">
                <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">ATH | INV — Evaluare Datorii</h1>
                <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                    Profil de datorii bugetare și clasificare risc
                </p>
            </div>

            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-nebula-400" />
                    <input
                        type="text"
                        placeholder="Introdu CUI pentru evaluare datorii..."
                        value={cuiSearch}
                        onChange={(e) => setCuiSearch(e.target.value)}
                        className="input-scifi pl-10"
                    />
                </div>
                <button
                    type="submit"
                    className="btn-cosmic px-6 py-2.5 text-sm"
                >
                    Evaluează
                </button>
            </form>

            {isLoading && (
                <div className="flex h-32 items-center justify-center">
                    <div className="relative">
                        <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                    </div>
                </div>
            )}

            {profile && (
                <div className="space-y-6">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                        <div className="card-cosmic text-center">
                            <TrendingUp className="mx-auto h-8 w-8 text-nebula-500" />
                            <p className="mt-2 font-orbitron text-3xl font-bold text-slate-800">
                                {formatMoney(profile.total_datorii || "0")}
                            </p>
                            <p className="font-rajdhani text-sm text-slate-400">Total Datorii</p>
                        </div>
                        <div className="card-cosmic text-center">
                            <span
                                className={cn(
                                    "inline-block rounded-full px-4 py-1 text-lg font-semibold",
                                    riskColor(profile.risk_classification)
                                )}
                            >
                                {profile.risk_classification?.toUpperCase()}
                            </span>
                            <p className="mt-2 font-rajdhani text-sm text-slate-400">Clasificare Risc</p>
                        </div>
                        <div className="card-cosmic text-center">
                            <p className="font-orbitron text-3xl font-bold text-slate-800">{profile.freshness_days}</p>
                            <p className="font-rajdhani text-sm text-slate-400">Zile de la Ultima Actualizare</p>
                            {profile.freshness_days > 90 && (
                                <p className="mt-1 text-xs text-orange-500">
                                    ⚠ Datele depășesc 90 de zile
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Debt Details */}
                    {profile.datorii?.length > 0 && (
                        <div className="card-cosmic p-0 overflow-hidden">
                            <h3 className="border-b px-6 py-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Detaliu Datorii</h3>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b bg-nebula-50/30">
                                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Tip</th>
                                            <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Sumă</th>
                                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Data Constatare</th>
                                            <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Sursă</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {profile.datorii.map((d: { tip: string; suma: string; data_constatare: string; sursa: string }, i: number) => (
                                            <tr key={i} className="border-b">
                                                <td className="px-4 py-3">{d.tip}</td>
                                                <td className="px-4 py-3 text-right font-medium">
                                                    {formatMoney(d.suma)}
                                                </td>
                                                <td className="px-4 py-3">{d.data_constatare}</td>
                                                <td className="px-4 py-3">{d.sursa}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Generate Report */}
                    <div className="flex justify-end">
                        <button
                            onClick={async () => {
                                await api.post(`/redbill/report`, { cui: selectedCui });
                            }}
                            className="btn-cosmic flex items-center gap-2 px-4 py-2 text-sm"
                        >
                            <FileText className="h-4 w-4" />
                            Generează Raport ATH | INV
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
