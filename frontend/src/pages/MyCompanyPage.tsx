import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import api from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { cn } from "@/lib/utils";
import {
    Building2, MapPin, Phone, Globe, Mail, Landmark,
    AlertTriangle, CheckCircle2, Shield, Leaf, ChevronRight,
    Calendar, Hash, Briefcase, Flame,
} from "lucide-react";

export default function MyCompanyPage() {
    const user = useAuthStore((s) => s.user);
    const navigate = useNavigate();
    const orgCui = user?.org_cui;

    const { data: company, isLoading, isError } = useQuery({
        queryKey: ["my-company", orgCui],
        queryFn: async () => (await api.get(`/companies/${orgCui}`)).data,
        enabled: !!orgCui,
    });

    const { data: financials } = useQuery({
        queryKey: ["my-company-financials", orgCui],
        queryFn: async () => (await api.get(`/companies/${orgCui}/financial`)).data,
        enabled: !!orgCui,
    });

    const { data: persons } = useQuery({
        queryKey: ["my-company-persons", orgCui],
        queryFn: async () => (await api.get(`/companies/${orgCui}/persons`)).data,
        enabled: !!orgCui,
    });

    if (!orgCui) {
        return (
            <div className="space-y-6">
                <PageHeader title="My Company" subtitle="Datele companiei tale" />
                <div className="card-cosmic flex flex-col items-center justify-center py-16 text-center">
                    <Landmark className="h-14 w-14 text-slate-300 dark:text-slate-600 mb-4" />
                    <h3 className="font-orbitron text-lg font-bold text-slate-500 mb-2">
                        CUI neconfigurat
                    </h3>
                    <p className="font-exo text-sm text-slate-400 max-w-xs">
                        Organizația ta nu are un CUI asociat. Contactează administratorul platformei
                        pentru a lega un CUI de contul tău.
                    </p>
                </div>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="space-y-6">
                <PageHeader title="My Company" subtitle="Se încarcă..." />
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="card-cosmic h-40 animate-pulse bg-slate-100 dark:bg-slate-800/50 rounded-2xl" />
                    ))}
                </div>
            </div>
        );
    }

    if (isError || !company) {
        return (
            <div className="space-y-6">
                <PageHeader title="My Company" subtitle="Datele companiei tale" />
                <div className="card-cosmic flex flex-col items-center justify-center py-16 text-center">
                    <AlertTriangle className="h-14 w-14 text-amber-300 mb-4" />
                    <h3 className="font-orbitron text-lg font-bold text-slate-500 mb-2">
                        Companie negăsită
                    </h3>
                    <p className="font-exo text-sm text-slate-400">
                        CUI <span className="font-bold">{orgCui}</span> nu a fost găsit în baza de date.
                    </p>
                </div>
            </div>
        );
    }

    const latestFinancial = Array.isArray(financials) ? financials[0] : null;
    const administrators = (Array.isArray(persons) ? persons : []).filter(
        (p: any) => p.tip === "ADMINISTRATOR" && p.activ
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <PageHeader
                    title={company.denumire}
                    subtitle={`CUI: ${company.cui} · ${user?.org_name || ""}`}
                />
                <button
                    onClick={() => navigate(`/company/${company.cui}`)}
                    className="btn-cosmic flex items-center gap-2 px-4 py-2 text-sm shrink-0"
                >
                    Profil complet <ChevronRight className="h-4 w-4" />
                </button>
            </div>

            {/* Status badges */}
            <div className="flex flex-wrap gap-2">
                <span className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold",
                    company.stare === "ACTIVA" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                )}>
                    {company.stare === "ACTIVA"
                        ? <CheckCircle2 className="h-3.5 w-3.5" />
                        : <AlertTriangle className="h-3.5 w-3.5" />
                    }
                    {company.stare}
                </span>
                {company.platitor_tva && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 text-blue-700 px-3 py-1 text-sm font-semibold">
                        Plătitor TVA
                    </span>
                )}
                {company.has_debts && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 text-amber-700 px-3 py-1 text-sm font-semibold">
                        <AlertTriangle className="h-3.5 w-3.5" /> Datorii ANAF
                    </span>
                )}
                {company.has_insolvency && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 text-red-700 px-3 py-1 text-sm font-semibold">
                        <Flame className="h-3.5 w-3.5" /> Insolvență
                    </span>
                )}
                {company.status_ro_efactura && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 text-green-700 px-3 py-1 text-sm font-semibold">
                        e-Factură
                    </span>
                )}
            </div>

            {/* Info grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {/* Identificare */}
                <div className="card-cosmic space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                        <Building2 className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Identificare
                        </h3>
                    </div>
                    <InfoRow label="CUI" value={String(company.cui)} icon={<Hash className="h-3.5 w-3.5" />} />
                    <InfoRow label="Nr. Reg. Com." value={company.j_nr || "—"} icon={<Briefcase className="h-3.5 w-3.5" />} />
                    <InfoRow label="Formă juridică" value={company.forma_juridica || "—"} icon={<Shield className="h-3.5 w-3.5" />} />
                    <InfoRow label="Înființată" value={company.data_infiintare || "—"} icon={<Calendar className="h-3.5 w-3.5" />} />
                    <InfoRow label="CAEN principal" value={company.caen_principal || "—"} icon={<Briefcase className="h-3.5 w-3.5" />} />
                </div>

                {/* Sediu */}
                <div className="card-cosmic space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                        <MapPin className="h-4 w-4 text-cosmos-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Sediu
                        </h3>
                    </div>
                    <p className="font-exo text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                        {company.adresa_completa || "Adresă nedisponibilă"}
                    </p>
                    {company.telefon && (
                        <InfoRow label="Telefon" value={company.telefon} icon={<Phone className="h-3.5 w-3.5" />} />
                    )}
                    {company.email && (
                        <InfoRow label="Email" value={company.email} icon={<Mail className="h-3.5 w-3.5" />} />
                    )}
                    {company.website && (
                        <InfoRow label="Website" value={company.website} icon={<Globe className="h-3.5 w-3.5" />} />
                    )}
                </div>

                {/* Financiar */}
                <div className="card-cosmic space-y-3">
                    <div className="flex items-center gap-2 mb-1">
                        <Leaf className="h-4 w-4 text-emerald-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Financiar {latestFinancial ? `(${latestFinancial.an_fiscal})` : ""}
                        </h3>
                    </div>
                    {latestFinancial ? (
                        <>
                            <InfoRow label="Cifra afaceri" value={`${formatNumber(latestFinancial.cifra_afaceri)} RON`} />
                            <InfoRow label="Profit net" value={`${formatNumber(latestFinancial.profit_net)} RON`} />
                            <InfoRow label="Angajați" value={String(latestFinancial.nr_angajati ?? "—")} />
                            <InfoRow label="Total active" value={`${formatNumber(latestFinancial.total_active)} RON`} />
                            <InfoRow label="Total datorii" value={`${formatNumber(latestFinancial.total_datorii)} RON`} />
                        </>
                    ) : (
                        <p className="font-exo text-sm text-slate-400">Date financiare indisponibile</p>
                    )}
                </div>
            </div>

            {/* Administrators */}
            {administrators.length > 0 && (
                <div className="card-cosmic">
                    <div className="flex items-center gap-2 mb-4">
                        <Shield className="h-4 w-4 text-nebula-500" />
                        <h3 className="font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Administratori Activi
                        </h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {administrators.map((p: any) => (
                            <span
                                key={p.id}
                                className="inline-flex items-center rounded-xl bg-nebula-50 dark:bg-nebula-900/30 text-nebula-700 dark:text-nebula-300 px-3 py-1.5 text-sm font-exo font-medium"
                            >
                                {p.nume_complet}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
    return (
        <div>
            <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">{title}</h1>
            <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">{subtitle}</p>
        </div>
    );
}

function InfoRow({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-slate-400 font-rajdhani shrink-0">
                {icon}
                {label}
            </span>
            <span className="font-exo font-medium text-slate-700 dark:text-slate-200 text-right max-w-[60%] truncate">
                {value}
            </span>
        </div>
    );
}
