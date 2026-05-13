import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AdminDashboard, DataSourceHealth } from "@/types";
import { formatNumber, formatDateTime, cn } from "@/lib/utils";
import { toast } from "sonner";
import {
    Activity,
    Bell,
    Building2,
    Database,
    Orbit,
    RefreshCw,
    Users,
    Shield,
    Settings,
    UserPlus,
    ToggleLeft,
    ToggleRight,
    Link2,
    CheckCircle2,
    XCircle,
    ChevronLeft,
    ChevronRight,
    FileText,
    Hash,
} from "lucide-react";

type Tab = "overview" | "users" | "orgs" | "gdpr" | "flags" | "blockchain";

export default function AdminPage() {
    const [tab, setTab] = useState<Tab>("overview");

    const { data: dashboard, isLoading } = useQuery<AdminDashboard>({
        queryKey: ["admin", "dashboard"],
        queryFn: async () => (await api.get("/admin/dashboard")).data,
    });

    const { data: sources } = useQuery<DataSourceHealth[]>({
        queryKey: ["admin", "data-sources"],
        queryFn: async () => (await api.get("/admin/data-sources")).data,
    });

    const triggerSync = async (source: string) => {
        try {
            await api.post(`/admin/sync/${source}`);
            toast.success(`Sincronizare ${source} pornită`);
        } catch {
            toast.error(`Eroare la sincronizare ${source}`);
        }
    };

    if (isLoading) {
        return (
            <div className="flex h-64 items-center justify-center">
                <div className="relative">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                    <Orbit className="absolute inset-0 m-auto h-4 w-4 text-nebula-400 animate-pulse" />
                </div>
            </div>
        );
    }

    const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
        { key: "overview", label: "Prezentare", icon: <Activity className="h-4 w-4" /> },
        { key: "users", label: "Utilizatori", icon: <Users className="h-4 w-4" /> },
        { key: "orgs", label: "Organizații", icon: <Building2 className="h-4 w-4" /> },
        { key: "gdpr", label: "GDPR", icon: <Shield className="h-4 w-4" /> },
        { key: "flags", label: "Feature Flags", icon: <Settings className="h-4 w-4" /> },
        { key: "blockchain", label: "Audit Log", icon: <Link2 className="h-4 w-4" /> },
    ];

    return (
        <div className="space-y-6">
            <div className="section-header">
                <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">Admin Dashboard</h1>
                <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                    Administrare platformă, utilizatori și configurare
                </p>
            </div>

            {/* Tab nav */}
            <div className="flex gap-1 rounded-xl border border-slate-200 bg-white p-1">
                {tabs.map((t) => (
                    <button
                        key={t.key}
                        onClick={() => setTab(t.key)}
                        className={cn(
                            "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
                            tab === t.key
                                ? "bg-nebula-500 text-white"
                                : "text-slate-500 hover:bg-slate-100"
                        )}
                    >
                        {t.icon}
                        {t.label}
                    </button>
                ))}
            </div>

            {tab === "overview" && (
                <>
                    {/* KPIs */}
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <StatCard title="Total Companii" value={formatNumber(dashboard?.total_companies || 0)} icon={<Building2 className="h-5 w-5" />} />
                        <StatCard title="Utilizatori" value={formatNumber(dashboard?.total_users || 0)} icon={<Users className="h-5 w-5" />} />
                        <StatCard title="Organizații" value={formatNumber(dashboard?.total_organizations || 0)} icon={<Database className="h-5 w-5" />} />
                        <StatCard title="Alerte Azi" value={formatNumber(dashboard?.total_alerts_today || 0)} icon={<Bell className="h-5 w-5" />} />
                        <StatCard title="Apeluri API Azi" value={formatNumber(dashboard?.api_calls_today || 0)} icon={<Activity className="h-5 w-5" />} />
                    </div>

                    {/* Data Sources */}
                    <div className="card-cosmic p-0 overflow-hidden">
                        <h3 className="border-b px-6 py-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">Surse de Date</h3>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b bg-nebula-50/30">
                                        <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Sursă</th>
                                        <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Status</th>
                                        <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Ultima Sincronizare</th>
                                        <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Înregistrări</th>
                                        <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Erori</th>
                                        <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Acțiuni</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(sources || []).map((src) => (
                                        <tr key={src.source_name} className="border-b hover:bg-slate-50/50">
                                            <td className="px-4 py-3 font-medium">{src.source_name}</td>
                                            <td className="px-4 py-3">
                                                <span className={cn(
                                                    "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                                                    src.status === "healthy" && "bg-green-100 text-green-700",
                                                    src.status === "degraded" && "bg-yellow-100 text-yellow-700",
                                                    src.status === "down" && "bg-red-100 text-red-700",
                                                    !src.status && "bg-slate-100 text-slate-500",
                                                )}>
                                                    <Activity className="h-3 w-3" />
                                                    {src.status || "unknown"}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-slate-400">
                                                {src.last_sync_at ? formatDateTime(src.last_sync_at) : "—"}
                                            </td>
                                            <td className="px-4 py-3 text-right">{formatNumber(src.records_processed)}</td>
                                            <td className="px-4 py-3 text-right text-red-500">{src.records_failed}</td>
                                            <td className="px-4 py-3 text-right">
                                                <button
                                                    onClick={() => triggerSync(src.source_name.toLowerCase())}
                                                    className="inline-flex items-center gap-1 rounded-md border border-nebula-200 px-2.5 py-1 text-xs hover:bg-nebula-50/50 transition-colors"
                                                >
                                                    <RefreshCw className="h-3 w-3" />
                                                    Sync
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}

            {tab === "users" && <UsersTab />}
            {tab === "orgs" && <OrgsTab />}
            {tab === "gdpr" && <GDPRTab />}
            {tab === "flags" && <FlagsTab />}
            {tab === "blockchain" && <BlockchainTab />}
        </div>
    );
}

// ── 11.1: Users Tab ──
function UsersTab() {
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [page, setPage] = useState(1);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteRole, setInviteRole] = useState("viewer");
    const [inviteFirstName, setInviteFirstName] = useState("");
    const [inviteLastName, setInviteLastName] = useState("");
    const queryClient = useQueryClient();
    const PER_PAGE = 20;

    // Debounce search to avoid a query on every keystroke
    const handleSearch = (v: string) => {
        setSearch(v);
        setPage(1);
        clearTimeout((handleSearch as any)._t);
        (handleSearch as any)._t = setTimeout(() => setDebouncedSearch(v), 350);
    };

    const { data: usersData, isLoading: usersLoading } = useQuery({
        queryKey: ["admin", "users", debouncedSearch, page],
        queryFn: async () =>
            (await api.get("/admin/users", {
                params: { search: debouncedSearch || undefined, page, per_page: PER_PAGE },
            })).data,
    });

    const totalPages = usersData ? Math.ceil((usersData.total || 0) / PER_PAGE) : 1;

    const inviteMutation = useMutation({
        mutationFn: async () => {
            const { data } = await api.post("/admin/users/invite", {
                email: inviteEmail,
                role: inviteRole,
                first_name: inviteFirstName || undefined,
                last_name: inviteLastName || undefined,
            });
            return data;
        },
        onSuccess: () => {
            setInviteEmail("");
            setInviteFirstName("");
            setInviteLastName("");
            queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
            toast.success("Utilizator invitat cu succes");
        },
        onError: () => toast.error("Eroare la invitarea utilizatorului"),
    });

    const toggleMutation = useMutation({
        mutationFn: async (userId: string) => {
            await api.put(`/admin/users/${userId}/toggle-active`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
            toast.success("Status utilizator actualizat");
        },
    });

    const roleMutation = useMutation({
        mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
            await api.put(`/admin/users/${userId}/role`, { role });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
            toast.success("Rol actualizat cu succes");
        },
    });

    return (
        <div className="space-y-4">
            {/* Invite */}
            <div className="card-cosmic">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                    <UserPlus className="h-4 w-4 text-nebula" />
                    Invită Utilizator
                </h3>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    <input
                        type="text"
                        placeholder="Prenume..."
                        value={inviteFirstName}
                        onChange={(e) => setInviteFirstName(e.target.value)}
                        className="input-scifi"
                    />
                    <input
                        type="text"
                        placeholder="Nume..."
                        value={inviteLastName}
                        onChange={(e) => setInviteLastName(e.target.value)}
                        className="input-scifi"
                    />
                    <input
                        type="email"
                        placeholder="Email..."
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        className="input-scifi"
                    />
                    <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className="input-scifi">
                        <option value="viewer">Viewer</option>
                        <option value="analyst">Analyst</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <button
                    onClick={() => inviteMutation.mutate()}
                    disabled={!inviteEmail || inviteMutation.isPending}
                    className="btn-cosmic mt-3 px-4 py-2 disabled:opacity-50"
                >
                    {inviteMutation.isPending ? "Se trimite..." : "Invită"}
                </button>
                {inviteMutation.data && (
                    <p className="mt-2 text-xs text-emerald-600">
                        Utilizator creat! Parolă temporară:{" "}
                        <code className="font-mono">{inviteMutation.data.temp_password}</code>
                    </p>
                )}
            </div>

            {/* Search + count */}
            <div className="flex items-center gap-3">
                <input
                    type="text"
                    placeholder="Caută utilizatori după email sau nume..."
                    value={search}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="input-scifi flex-1"
                />
                {usersData && (
                    <span className="shrink-0 font-rajdhani text-xs text-slate-400">
                        {usersData.total} utilizatori
                    </span>
                )}
            </div>

            {/* Users table */}
            <div className="card-cosmic p-0 overflow-hidden">
                {usersLoading ? (
                    <div className="flex h-32 items-center justify-center">
                        <div className="h-6 w-6 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                    </div>
                ) : (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b bg-nebula-50/30">
                                <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Email</th>
                                <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Nume</th>
                                <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Rol</th>
                                <th className="px-4 py-3 text-center font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Activ</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Credite</th>
                                <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Ultimul Login</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(usersData?.users || []).map((u: any) => (
                                <tr key={u.id} className="border-b hover:bg-slate-50/50">
                                    <td className="px-4 py-3 font-medium">{u.email}</td>
                                    <td className="px-4 py-3 text-slate-500">{u.full_name || "—"}</td>
                                    <td className="px-4 py-3">
                                        <select
                                            value={u.role}
                                            onChange={(e) => roleMutation.mutate({ userId: u.id, role: e.target.value })}
                                            className="rounded border px-2 py-0.5 text-xs"
                                        >
                                            <option value="viewer">viewer</option>
                                            <option value="analyst">analyst</option>
                                            <option value="admin">admin</option>
                                        </select>
                                    </td>
                                    <td className="px-4 py-3 text-center">
                                        <button onClick={() => toggleMutation.mutate(u.id)} title={u.is_active ? "Dezactivează" : "Activează"}>
                                            {u.is_active ? (
                                                <ToggleRight className="h-5 w-5 text-emerald-500" />
                                            ) : (
                                                <ToggleLeft className="h-5 w-5 text-slate-400" />
                                            )}
                                        </button>
                                    </td>
                                    <td className="px-4 py-3 text-right font-mono text-xs">{u.credits_left}</td>
                                    <td className="px-4 py-3 text-right text-xs text-slate-400">
                                        {u.last_login ? formatDateTime(u.last_login) : "—"}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t px-4 py-3">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page <= 1}
                            className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors"
                        >
                            <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                        </button>
                        <span className="font-rajdhani text-xs text-slate-400">
                            Pagina {page} / {totalPages}
                        </span>
                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors"
                        >
                            Următor <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

// ── 11.2: Organizations Tab ──
function OrgsTab() {
    const queryClient = useQueryClient();

    const { data: orgs } = useQuery({
        queryKey: ["admin", "organizations"],
        queryFn: async () => (await api.get("/admin/organizations")).data,
    });

    const planMutation = useMutation({
        mutationFn: async ({ orgId, plan }: { orgId: string; plan: string }) => {
            await api.put(`/admin/organizations/${orgId}/plan`, { plan });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin", "organizations"] });
            toast.success("Plan actualizat cu succes");
        },
    });

    return (
        <div className="card-cosmic p-0 overflow-hidden">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b bg-nebula-50/30">
                        <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Organizație</th>
                        <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Plan</th>
                        <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">API Calls</th>
                        <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Limit</th>
                        <th className="px-4 py-3 text-right font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Utilizatori</th>
                    </tr>
                </thead>
                <tbody>
                    {(orgs || []).map((org: any) => (
                        <tr key={org.id} className="border-b hover:bg-slate-50/50">
                            <td className="px-4 py-3 font-medium">{org.name}</td>
                            <td className="px-4 py-3">
                                <select
                                    value={org.plan}
                                    onChange={(e) => planMutation.mutate({ orgId: org.id, plan: e.target.value })}
                                    className="rounded border px-2 py-0.5 text-xs"
                                >
                                    <option value="FREE">FREE</option>
                                    <option value="STARTER">STARTER</option>
                                    <option value="PROFESSIONAL">PROFESSIONAL</option>
                                    <option value="ENTERPRISE">ENTERPRISE</option>
                                </select>
                            </td>
                            <td className="px-4 py-3 text-right font-mono">{formatNumber(org.api_calls)}</td>
                            <td className="px-4 py-3 text-right font-mono">{formatNumber(org.api_limit)}</td>
                            <td className="px-4 py-3 text-right">{org.user_count}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ── 11.4: GDPR Tab ──
function GDPRTab() {
    const [userId, setUserId] = useState("");
    const [reason, setReason] = useState("");

    const exportMutation = useMutation({
        mutationFn: async () => (await api.post(`/admin/gdpr/export/${userId}`)).data,
    });

    const anonymizeMutation = useMutation({
        mutationFn: async () => (await api.post(`/admin/gdpr/anonymize/${userId}`, { reason })).data,
    });

    return (
        <div className="space-y-4">
            <div className="card-cosmic">
                <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                    <Shield className="h-4 w-4 text-nebula" />
                    Operațiuni GDPR
                </h3>
                <div className="space-y-3">
                    <input
                        type="text"
                        placeholder="User ID (UUID)..."
                        value={userId}
                        onChange={(e) => setUserId(e.target.value)}
                        className="input-scifi w-full"
                    />
                    <input
                        type="text"
                        placeholder="Motiv (pentru anonimizare)..."
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="input-scifi w-full"
                    />
                    <div className="flex gap-2">
                        <button
                            onClick={() => exportMutation.mutate()}
                            disabled={!userId || exportMutation.isPending}
                            className="btn-cosmic px-4 py-2 text-sm disabled:opacity-50"
                        >
                            Export Date
                        </button>
                        <button
                            onClick={() => {
                                if (confirm("Sigur dorești să anonimizezi acest utilizator?")) {
                                    anonymizeMutation.mutate();
                                }
                            }}
                            disabled={!userId || !reason || anonymizeMutation.isPending}
                            className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-600 hover:bg-red-100 disabled:opacity-50"
                        >
                            Anonimizare
                        </button>
                    </div>
                </div>
                {exportMutation.data && (
                    <pre className="mt-4 max-h-64 overflow-auto rounded-lg bg-slate-900 p-4 text-xs text-emerald-400">
                        {JSON.stringify(exportMutation.data, null, 2)}
                    </pre>
                )}
                {anonymizeMutation.data && (
                    <p className="mt-2 text-sm text-emerald-600">Utilizator anonimizat cu succes.</p>
                )}
            </div>

            {/* Audit Log */}
            <AuditLogSection />
        </div>
    );
}

function AuditLogSection() {
    const { data: logs } = useQuery({
        queryKey: ["admin", "audit-log"],
        queryFn: async () => (await api.get("/admin/audit-log", { params: { per_page: 20 } })).data,
    });

    return (
        <div className="card-cosmic p-0 overflow-hidden">
            <h3 className="border-b px-6 py-4 font-orbitron text-sm font-semibold tracking-wide text-slate-700">
                Jurnal Audit
            </h3>
            <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-white">
                        <tr className="border-b">
                            <th className="px-4 py-2 text-left text-slate-400">Acțiune</th>
                            <th className="px-4 py-2 text-left text-slate-400">Entitate</th>
                            <th className="px-4 py-2 text-left text-slate-400">IP</th>
                            <th className="px-4 py-2 text-left text-slate-400">Data</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(logs || []).map((log: any) => (
                            <tr key={log.id} className="border-b">
                                <td className="px-4 py-2 font-medium">{log.action}</td>
                                <td className="px-4 py-2 text-slate-500">{log.entity_type || "—"}</td>
                                <td className="px-4 py-2 font-mono text-slate-400">{log.ip_address || "—"}</td>
                                <td className="px-4 py-2 text-slate-400">{log.created_at ? formatDateTime(log.created_at) : "—"}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── 11.5: Feature Flags Tab ──
function FlagsTab() {
    const queryClient = useQueryClient();

    const { data: flags } = useQuery<Record<string, boolean>>({
        queryKey: ["admin", "feature-flags"],
        queryFn: async () => (await api.get("/admin/config/feature-flags")).data,
    });

    const flagMutation = useMutation({
        mutationFn: async ({ key, value }: { key: string; value: boolean }) => {
            await api.put("/admin/config/feature-flags", { [key]: value });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["admin", "feature-flags"] });
            toast.success("Feature flag actualizat");
        },
    });

    const FLAG_LABELS: Record<string, string> = {
        esg_scoring_enabled: "Scoring ESG",
        fraud_detection_enabled: "Detecție Fraudă",
        ai_agent_enabled: "AI Agent",
        redbill_enabled: "RedBill",
        seap_sync_enabled: "Sincronizare SEAP",
        email_notifications_enabled: "Notificări Email",
        sms_notifications_enabled: "Notificări SMS",
        maintenance_mode: "Mod Mentenanță",
    };

    return (
        <div className="card-cosmic">
            <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                <Settings className="h-4 w-4 text-nebula" />
                Feature Flags
            </h3>
            <div className="space-y-3">
                {Object.entries(flags || {}).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3">
                        <div>
                            <p className="text-sm font-medium">{FLAG_LABELS[key] || key}</p>
                            <p className="text-xs text-slate-400">{key}</p>
                        </div>
                        <button
                            onClick={() => flagMutation.mutate({ key, value: !value })}
                            className="transition"
                            title={value ? "Dezactivează" : "Activează"}
                        >
                            {value ? (
                                <ToggleRight className="h-6 w-6 text-emerald-500" />
                            ) : (
                                <ToggleLeft className="h-6 w-6 text-slate-400" />
                            )}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Audit Log Tab ──
function BlockchainTab() {
    const [page, setPage] = useState(1);
    const PER_PAGE = 10;

    const { data, isLoading } = useQuery({
        queryKey: ["admin", "blockchain-trail", page],
        queryFn: async () => (await api.get("/admin/blockchain-trail", { params: { page, per_page: PER_PAGE } })).data,
    });

    const blocks = data?.blocks || [];
    const pagination = data?.pagination || { page: 1, pages: 1, total: 0 };
    const stats = data?.stats || {};

    return (
        <div className="space-y-4">
            {/* KPI cards */}
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <div className="card-cosmic flex items-center gap-3 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
                        <Link2 className="h-5 w-5" />
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">Total Blocuri</p>
                        <p className="font-orbitron text-xl font-bold text-slate-800">{formatNumber(stats.total_blocks || 0)}</p>
                    </div>
                </div>
                <div className="card-cosmic flex items-center gap-3 p-4">
                    <div className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-xl text-white",
                        stats.chain_valid ? "bg-gradient-to-br from-emerald-500 to-green-600" : "bg-gradient-to-br from-red-500 to-rose-600"
                    )}>
                        {stats.chain_valid ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">Chain Valid</p>
                        <p className={cn("font-orbitron text-xl font-bold", stats.chain_valid ? "text-emerald-600" : "text-red-600")}>
                            {stats.chain_valid ? "DA" : "NU"}
                        </p>
                    </div>
                </div>
                <div className="card-cosmic flex items-center gap-3 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 text-white">
                        <FileText className="h-5 w-5" />
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">Documente Hash</p>
                        <p className="font-orbitron text-xl font-bold text-slate-800">{formatNumber(stats.total_documents || 0)}</p>
                    </div>
                </div>
                <div className="card-cosmic flex items-center gap-3 p-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 text-white">
                        <Hash className="h-5 w-5" />
                    </div>
                    <div>
                        <p className="font-rajdhani text-xs uppercase tracking-wider text-slate-400">Custody Records</p>
                        <p className="font-orbitron text-xl font-bold text-slate-800">{formatNumber(stats.total_custody_records || 0)}</p>
                    </div>
                </div>
            </div>

            {/* Blocks table */}
            <div className="card-cosmic p-0 overflow-hidden">
                <div className="flex items-center justify-between border-b px-6 py-4">
                    <h3 className="font-orbitron text-sm font-semibold tracking-wide text-slate-700">
                        Audit Log Blocks
                    </h3>
                    <span className="font-rajdhani text-xs text-slate-400">
                        {pagination.total} blocuri · Pagina {pagination.page}/{pagination.pages || 1}
                    </span>
                </div>

                {isLoading ? (
                    <div className="flex h-48 items-center justify-center">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500" />
                    </div>
                ) : blocks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 text-slate-300">
                        <Link2 className="mb-3 h-10 w-10" />
                        <p className="font-rajdhani text-sm uppercase tracking-wider">Nu există blocuri în chain</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b bg-nebula-50/30">
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400 w-16">#</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Hash</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Prev Hash</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Tip / Acțiune</th>
                                    <th className="px-4 py-3 text-left font-rajdhani font-semibold uppercase tracking-wider text-slate-400">Data</th>
                                </tr>
                            </thead>
                            <tbody>
                                {blocks.map((block: any) => {
                                    const actionType = block.data?.type || block.data?.action || "—";
                                    return (
                                        <tr key={block.index} className="border-b hover:bg-slate-50/50 transition-colors">
                                            <td className="px-4 py-3">
                                                <span className="inline-flex items-center justify-center rounded-lg bg-indigo-100 px-2 py-0.5 font-orbitron text-xs font-bold text-indigo-700">
                                                    {block.index}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="font-mono text-[11px] text-slate-500" title={block.hash}>
                                                    {block.hash?.slice(0, 16)}…
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="font-mono text-[11px] text-slate-400" title={block.previous_hash}>
                                                    {block.previous_hash?.slice(0, 16)}…
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={cn(
                                                    "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                                                    actionType === "genesis" ? "bg-violet-100 text-violet-700" :
                                                        actionType === "document_hash" ? "bg-cyan-100 text-cyan-700" :
                                                            actionType === "custody" ? "bg-amber-100 text-amber-700" :
                                                                actionType === "timestamp_proof" ? "bg-emerald-100 text-emerald-700" :
                                                                    "bg-slate-100 text-slate-600"
                                                )}>
                                                    {actionType}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 font-rajdhani text-slate-400">
                                                {block.created_at ? formatDateTime(block.created_at) : "—"}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Pagination */}
                {pagination.pages > 1 && (
                    <div className="flex items-center justify-between border-t px-6 py-3">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page <= 1}
                            className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors"
                        >
                            <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                        </button>
                        <div className="flex items-center gap-1">
                            {Array.from({ length: Math.min(pagination.pages, 7) }, (_, i) => {
                                let pageNum: number;
                                if (pagination.pages <= 7) {
                                    pageNum = i + 1;
                                } else if (page <= 4) {
                                    pageNum = i + 1;
                                } else if (page >= pagination.pages - 3) {
                                    pageNum = pagination.pages - 6 + i;
                                } else {
                                    pageNum = page - 3 + i;
                                }
                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => setPage(pageNum)}
                                        className={cn(
                                            "flex h-7 w-7 items-center justify-center rounded-lg text-xs font-medium transition-colors",
                                            page === pageNum
                                                ? "bg-nebula-500 text-white"
                                                : "text-slate-500 hover:bg-slate-100"
                                        )}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            })}
                        </div>
                        <button
                            onClick={() => setPage(p => Math.min(pagination.pages, p + 1))}
                            disabled={page >= pagination.pages}
                            className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors"
                        >
                            Următor <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

function StatCard({
    title,
    value,
    icon,
}: {
    title: string;
    value: string;
    icon: React.ReactNode;
}) {
    return (
        <div className="card-cosmic">
            <div className="flex items-center justify-between">
                <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">{title}</p>
                <div className="text-nebula-400">{icon}</div>
            </div>
            <p className="mt-2 font-orbitron text-3xl font-bold text-slate-800">{value}</p>
        </div>
    );
}
