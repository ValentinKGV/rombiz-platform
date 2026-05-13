import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/lib/api";
import type { Portfolio } from "@/types";
import { Plus, Trash2, Building2, FolderOpen, Orbit, Rocket } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function PortfoliosPage() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState("");
    const [newDesc, setNewDesc] = useState("");

    const { data: portfolios, isLoading } = useQuery<Portfolio[]>({
        queryKey: ["portfolios"],
        queryFn: async () => {
            const { data } = await api.get("/portfolios");
            return data;
        },
    });

    const createMutation = useMutation({
        mutationFn: async () => {
            await api.post("/portfolios", { name: newName, description: newDesc });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["portfolios"] });
            setShowCreate(false);
            setNewName("");
            setNewDesc("");
        },
    });

    const deleteMutation = useMutation({
        mutationFn: async (id: number) => {
            await api.delete(`/portfolios/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["portfolios"] });
        },
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="section-header">
                    <div>
                        <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">Portofolii</h1>
                        <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">Monitorizează constelații de companii</p>
                    </div>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="btn-cosmic flex items-center gap-2 px-4 py-2.5 text-sm"
                >
                    <Plus className="h-4 w-4" />
                    Portofoliu Nou
                </button>
            </div>

            {showCreate && (
                <div className="card-cosmic">
                    <h3 className="mb-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Portofoliu Nou</h3>
                    <div className="space-y-3">
                        <input
                            type="text"
                            placeholder="Nume portofoliu"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            className="input-scifi"
                        />
                        <textarea
                            placeholder="Descriere (opțional)"
                            value={newDesc}
                            onChange={(e) => setNewDesc(e.target.value)}
                            className="input-scifi"
                            rows={2}
                        />
                        <div className="flex gap-2">
                            <button
                                onClick={() => createMutation.mutate()}
                                disabled={!newName}
                                className="btn-cosmic px-5 py-2 text-sm disabled:opacity-50"
                            >
                                Creează
                            </button>
                            <button
                                onClick={() => setShowCreate(false)}
                                className="rounded-xl border border-slate-200 px-5 py-2 font-exo text-sm text-slate-500 hover:bg-slate-50 transition-colors"
                            >
                                Anulează
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {isLoading ? (
                <div className="flex h-32 items-center justify-center">
                    <div className="relative">
                        <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                        <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {(portfolios || []).map((portfolio) => (
                        <div key={portfolio.id} className="card-cosmic group relative overflow-hidden">
                            {/* Top gradient */}
                            <div className="absolute inset-x-0 top-0 h-1 bg-nebula-gradient opacity-60" />
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cosmos-50 text-cosmos-500 transition-transform group-hover:scale-110">
                                        <FolderOpen className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <h3 className="font-exo font-semibold text-slate-700">{portfolio.name}</h3>
                                        {portfolio.description && (
                                            <p className="font-exo text-sm text-slate-400">{portfolio.description}</p>
                                        )}
                                    </div>
                                </div>
                                <button
                                    onClick={() => deleteMutation.mutate(portfolio.id)}
                                    className="rounded-lg p-1.5 text-slate-300 hover:bg-dragon-50 hover:text-dragon-500 transition-colors"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                            <div className="mt-4 flex items-center justify-between">
                                <span className="flex items-center gap-1.5 font-rajdhani text-sm text-slate-400">
                                    <Building2 className="h-4 w-4" />
                                    {portfolio.company_count} companii
                                </span>
                                <button
                                    onClick={() => navigate(`/portfolios/${portfolio.id}`)}
                                    className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:text-nebula-700 transition-colors"
                                >
                                    Detalii →
                                </button>
                            </div>
                        </div>
                    ))}

                    {portfolios?.length === 0 && (
                        <div className="col-span-full flex flex-col items-center justify-center py-12 text-slate-300">
                            <Rocket className="h-12 w-12 mb-3 animate-cosmic-float" />
                            <p className="font-rajdhani text-sm uppercase tracking-wider">Nu ai portofolii. Lansează primul tău portofoliu.</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
