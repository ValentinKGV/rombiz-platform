import { useState, useMemo, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { SearchResult, SearchFilters } from "@/types";
import { Search, Eye, EyeOff, ChevronDown, SlidersHorizontal } from "lucide-react";
import { LoadingSpinner, SectionHeader, Pagination } from "@/components/common";
import { CompanyRow } from "@/components/company";

const JUDETE = [
    "Alba", "Arad", "Argeș", "Bacău", "Bihor", "Bistrița-Năsăud", "Botoșani",
    "Brașov", "Brăila", "București", "Buzău", "Caraș-Severin", "Călărași",
    "Cluj", "Constanța", "Covasna", "Dâmbovița", "Dolj", "Galați", "Giurgiu",
    "Gorj", "Harghita", "Hunedoara", "Ialomița", "Iași", "Ilfov", "Maramureș",
    "Mehedinți", "Mureș", "Neamț", "Olt", "Prahova", "Satu Mare", "Sălaj",
    "Sibiu", "Suceava", "Teleorman", "Timiș", "Tulcea", "Vaslui", "Vâlcea",
    "Vrancea",
];

const DEBOUNCE_MS = 400;
const MIN_QUERY_LENGTH = 2;

export default function SearchPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const [filtersOpen, setFiltersOpen] = useState(false);
    const [searchTrigger, setSearchTrigger] = useState(0);

    const [filters, setFilters] = useState<SearchFilters>({
        query: "",
        page: 1,
        page_size: 25,
        sort_by: "denumire",
        sort_dir: "asc",
    });

    // --- Debounce: search automat dupa DEBOUNCE_MS ms de la ultima tastare ---
    useEffect(() => {
        if (debounceTimer.current) clearTimeout(debounceTimer.current);

        if ((filters.query?.length ?? 0) >= MIN_QUERY_LENGTH) {
            debounceTimer.current = setTimeout(() => {
                setFilters((prev) => ({ ...prev, page: 1 }));
                setSearchTrigger((prev) => prev + 1);
            }, DEBOUNCE_MS);
        }

        return () => {
            if (debounceTimer.current) clearTimeout(debounceTimer.current);
        };
    }, [filters.query]);

    // --- Numarul de filtre active (fara query, page, sort) ---
    const activeFiltersCount = useMemo(() => {
        const ignored = new Set(["query", "page", "page_size", "sort_by", "sort_dir"]);
        return Object.entries(filters).filter(([key, val]) => {
            if (ignored.has(key)) return false;
            if (val === undefined || val === "" || val === false) return false;
            return true;
        }).length;
    }, [filters]);

    const { data, isLoading } = useQuery<SearchResult>({
        queryKey: ["search", filters, searchTrigger],
        queryFn: async () => {
            const { data } = await api.post("/search", filters);
            return data;
        },
        enabled: searchTrigger > 0,
    });

    // Watchlist
    const { data: watchlist } = useQuery({
        queryKey: ["watchlist"],
        queryFn: async () => (await api.get("/watch")).data,
    });
    const watchedCuis = useMemo(
        () => new Set<string>((watchlist?.companies || []).map((c: any) => String(c.cui))),
        [watchlist]
    );

    const watchMutation = useMutation({
        mutationFn: async ({ cui, watching }: { cui: number; watching: boolean }) => {
            if (watching) {
                await api.delete(`/watch/${cui}`);
            } else {
                await api.post(`/watch/${cui}`);
            }
        },
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
    });

    // Submit manual (Enter / buton Caută) — declanseaza imediat, fara debounce
    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (debounceTimer.current) clearTimeout(debounceTimer.current);
        setFilters((prev) => ({ ...prev, page: 1 }));
        setSearchTrigger((prev) => prev + 1);
    };

    const updateFilter = (key: string, value: unknown) => {
        setFilters((prev) => ({ ...prev, [key]: value }));
    };

    const clearFilters = () => {
        setFilters((prev) => ({
            query: prev.query,       // pastram query-ul curent
            page: 1,
            page_size: 25,
            sort_by: "denumire",
            sort_dir: "asc",
        }));
    };

    return (
        <div className="space-y-6">
            <SectionHeader
                title="Căutare Companii"
                subtitle="Caută una dintre afacerile românești"
            />

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-nebula-400" />
                    <input
                        type="text"
                        placeholder="Identifică o companie după denumire, CUI sau date de identificare..."
                        value={filters.query || ""}
                        onChange={(e) => updateFilter("query", e.target.value)}
                        className="input-scifi pl-10"
                        autoComplete="off"
                    />
                </div>
                <button
                    type="submit"
                    className="btn-cosmic px-6 py-2.5 text-sm"
                >
                    Caută
                </button>
            </form>

            
            <div className="card-cosmic">
                <button
                    type="button"
                    onClick={() => setFiltersOpen((prev) => !prev)}
                    className="flex w-full items-center justify-between"
                >
                    <div className="flex items-center gap-2">
                        <SlidersHorizontal className="h-4 w-4 text-nebula-400" />
                        <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700 dark:text-slate-200">
                            Filtre Avansate
                        </h3>
                        {/* Badge filtre active */}
                        {activeFiltersCount > 0 && (
                            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-nebula-500 px-1.5 text-xs font-bold text-white">
                                {activeFiltersCount}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        {activeFiltersCount > 0 && ( 
                            <span
                                role="button"
                                tabIndex={0}
                                onClick={(e) => { e.stopPropagation(); clearFilters(); }}
                                onKeyDown={(e) => e.key === "Enter" && (e.stopPropagation(), clearFilters())}
                                className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-nebula-500 hover:text-nebula-700"
                            >
                                Resetează 
                            </span>
                        )}
                        <ChevronDown
                            className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${filtersOpen ? "rotate-180" : ""}`}
                        />
                    </div>
                </button>

                {/* Panoul de filtre */}
                {filtersOpen && (
                    <div className="mt-4 grid grid-cols-1 gap-4 border-t border-slate-200 pt-4 dark:border-slate-700 sm:grid-cols-2 lg:grid-cols-4">
                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Județ</label>
                            <select
                                value={filters.judet || ""}
                                onChange={(e) => updateFilter("judet", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                            >
                                <option value="">Toate</option>
                                {JUDETE.map((j) => (
                                    <option key={j} value={j}>{j}</option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Stare Firmă</label>
                            <select
                                value={filters.stare || ""}
                                onChange={(e) => updateFilter("stare", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                            >
                                <option value="">Toate</option>
                                <option value="ACTIV">Activă</option>
                                <option value="INACTIV">Inactivă</option>
                                <option value="RADIAT">Radiată</option>
                                <option value="SUSPENDAT">Suspendată</option>
                            </select>
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Cifra de Afaceri Min</label>
                            <input
                                type="number"
                                value={filters.cifra_afaceri_min || ""}
                                onChange={(e) => updateFilter("cifra_afaceri_min", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                                placeholder="0"
                            />
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Cifra de Afaceri Max</label>
                            <input
                                type="number"
                                value={filters.cifra_afaceri_max || ""}
                                onChange={(e) => updateFilter("cifra_afaceri_max", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                                placeholder="∞"
                            />
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Angajați Min</label>
                            <input
                                type="number"
                                value={filters.angajati_min || ""}
                                onChange={(e) => updateFilter("angajati_min", parseInt(e.target.value) || undefined)}
                                className="input-scifi mt-1.5"
                            />
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Angajați Max</label>
                            <input
                                type="number"
                                value={filters.angajati_max || ""}
                                onChange={(e) => updateFilter("angajati_max", parseInt(e.target.value) || undefined)}
                                className="input-scifi mt-1.5"
                            />
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Cod CAEN</label>
                            <input
                                type="text"
                                value={filters.caen_principal || ""}
                                onChange={(e) => updateFilter("caen_principal", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                                placeholder="ex: 6201"
                            />
                        </div>

                        <div>
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Țară</label>
                            <select
                                value={filters.tara || ""}
                                onChange={(e) => updateFilter("tara", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                            >
                                <option value="">Toate</option>
                                <option value="Romania">România</option>
                            </select>
                        </div>

                        <div className="sm:col-span-2">
                            <label className="block font-rajdhani text-sm font-semibold tracking-wider text-slate-400">Administrator</label>
                            <input
                                type="text"
                                value={filters.administrator || ""}
                                onChange={(e) => updateFilter("administrator", e.target.value || undefined)}
                                className="input-scifi mt-1.5"
                                placeholder="Nume administrator..."
                            />
                        </div>

                        <div className="flex items-end gap-4">
                            <label className="flex items-center gap-2 font-exo text-sm text-slate-600">
                                <input
                                    type="checkbox"
                                    checked={filters.has_debts || false}
                                    onChange={(e) => updateFilter("has_debts", e.target.checked || undefined)}
                                    className="rounded border-nebula-300 text-nebula-500 focus:ring-nebula-400"
                                />
                                Cu datorii
                            </label>
                            <label className="flex items-center gap-2 font-exo text-sm text-slate-600">
                                <input
                                    type="checkbox"
                                    checked={filters.has_insolvency || false}
                                    onChange={(e) => updateFilter("has_insolvency", e.target.checked || undefined)}
                                    className="rounded border-nebula-300 text-nebula-500 focus:ring-nebula-400"
                                />
                                Insolvente
                            </label>
                        </div>
                    </div>
                )}
            </div>

            {/* Results */}
            {data && (
                <div>
                    <div className="mb-4 flex items-center justify-between">
                        <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">
                            {formatNumber(data.total)} rezultate
                        </p>
                        <select
                            value={`${filters.sort_by}:${filters.sort_dir}`}
                            onChange={(e) => {
                                const [sortBy, sortDir] = e.target.value.split(":");
                                setFilters((prev) => ({
                                    ...prev,
                                    sort_by: sortBy,
                                    sort_dir: sortDir as "asc" | "desc",
                                    page: 1,
                                }));
                                setSearchTrigger((p) => p + 1);
                            }}
                            className="input-scifi py-1.5 text-sm"
                        >
                            <option value="denumire:asc">Denumire de la A-Z</option>
                            <option value="denumire:desc">Denumire de la Z-A</option>
                            <option value="cifra_afaceri:desc">Cifra Afaceri ↓</option>
                            <option value="cifra_afaceri:asc">Cifra Afaceri ↑</option>
                            <option value="risk_score:asc">Risc ↑</option>
                            <option value="risk_score:desc">Risc ↓</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                        {data.items.map((company) => {
                            const isWatching = watchedCuis.has(String(company.cui));
                            return (
                                <div key={company.id} className="relative group">
                                    <CompanyRow company={company} />
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            watchMutation.mutate({ cui: Number(company.cui), watching: isWatching });
                                        }}
                                        title={isWatching ? "Scoate din watchlist" : "Adaugă la watchlist"}
                                        className={`absolute right-3 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-lg border transition-all opacity-0 group-hover:opacity-100 ${isWatching
                                            ? "border-nebula-300 bg-nebula-50 text-nebula-600 hover:bg-red-50 hover:text-red-500 hover:border-red-200"
                                            : "border-slate-200 bg-white/80 text-slate-400 hover:bg-nebula-50 hover:text-nebula-600 hover:border-nebula-200"
                                            }`}
                                    >
                                        {isWatching ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                                    </button>
                                </div>
                            );
                        })}
                    </div>

                    <Pagination
                        page={filters.page || 1}
                        pageSize={filters.page_size || 25}
                        total={data.total}
                        onPageChange={(p) => {
                            updateFilter("page", p);
                            setSearchTrigger((prev) => prev + 1);
                        }}
                        className="mt-4"
                    />
                </div>
            )}

            {isLoading && <LoadingSpinner className="h-32" />}
        </div>
    );
}