import { useState, useRef } from "react";
import { useAuthStore } from "@/store/auth";
import { Link } from "react-router-dom";
import { formatDate } from "@/lib/utils";
import api from "@/lib/api";
import {
    User as UserIcon, Mail, Building2, Shield, Calendar, Clock,
    CreditCard, CheckCircle2, XCircle, Edit3, Save, X, KeyRound, Camera,
} from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

export default function ProfilePage() {
    const { user, updateProfile, fetchUser } = useAuthStore();
    const [editing, setEditing] = useState(false);
    const [firstName, setFirstName] = useState(user?.first_name || "");
    const [lastName, setLastName] = useState(user?.last_name || "");
    const [saving, setSaving] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [uploadingAvatar, setUploadingAvatar] = useState(false);

    if (!user) return null;

    const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (file.size > 2 * 1024 * 1024) {
            toast.error("Imaginea depășește 2 MB");
            return;
        }

        const allowed = ["image/jpeg", "image/png", "image/webp"];
        if (!allowed.includes(file.type)) {
            toast.error("Format invalid. Acceptăm: JPG, PNG, WEBP");
            return;
        }

        setUploadingAvatar(true);
        try {
            const formData = new FormData();
            formData.append("file", file);
            await api.post("/auth/avatar", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            await fetchUser();
            toast.success("Avatar actualizat!");
        } catch {
            toast.error("Eroare la încărcarea avatarului");
        } finally {
            setUploadingAvatar(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateProfile({ first_name: firstName, last_name: lastName });
            toast.success("Profil actualizat cu succes!");
            setEditing(false);
        } catch {
            toast.error("Eroare la salvarea profilului");
        } finally {
            setSaving(false);
        }
    };

    const handleCancel = () => {
        setFirstName(user.first_name);
        setLastName(user.last_name);
        setEditing(false);
    };

    const roleLabel: Record<string, string> = {
        admin: "Administrator",
        analyst: "Analist",
        analist: "Analist",
        viewer: "Vizualizator",
    };

    return (
        <div className="mx-auto max-w-3xl space-y-6">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                <h1 className="font-orbitron text-xl font-bold tracking-wide text-slate-800 dark:text-white">
                    Profilul Meu
                </h1>
                <p className="mt-1 font-rajdhani text-sm text-muted-foreground">
                    Informații cont și setări personale
                </p>
            </motion.div>

            {/* Profile Card */}
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="relative overflow-hidden rounded-2xl border border-white/60 bg-white/80 backdrop-blur-sm shadow-lg dark:border-slate-700/60 dark:bg-slate-800/80"
            >
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-500" />

                {/* Avatar + Name Banner */}
                <div className="relative bg-gradient-to-br from-slate-900 via-indigo-950 to-violet-950 px-6 py-8">
                    <div className="pointer-events-none absolute inset-0 opacity-20"
                        style={{ backgroundImage: "radial-gradient(circle at 20% 50%, rgba(99,102,241,0.3) 0%, transparent 50%), radial-gradient(circle at 80% 30%, rgba(139,92,246,0.25) 0%, transparent 50%)" }}
                    />
                    <div className="relative flex items-center gap-5">
                        <div className="relative group">
                            {user.avatar_url ? (
                                <img
                                    src={user.avatar_url}
                                    alt="Avatar"
                                    className="h-20 w-20 rounded-2xl object-cover shadow-xl shadow-indigo-500/30"
                                />
                            ) : (
                                <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-xl shadow-indigo-500/30">
                                    <span className="font-orbitron text-2xl font-bold">
                                        {user.first_name?.[0]}{user.last_name?.[0]}
                                    </span>
                                </div>
                            )}
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploadingAvatar}
                                className="absolute inset-0 flex items-center justify-center rounded-2xl bg-black/0 opacity-0 transition-all group-hover:bg-black/40 group-hover:opacity-100"
                            >
                                {uploadingAvatar ? (
                                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                ) : (
                                    <Camera className="h-6 w-6 text-white" />
                                )}
                            </button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                onChange={handleAvatarUpload}
                                className="hidden"
                            />
                        </div>
                        <div>
                            <h2 className="font-orbitron text-lg font-bold text-white">
                                {user.first_name} {user.last_name}
                            </h2>
                            <p className="mt-0.5 font-rajdhani text-sm text-white/50">{user.email}</p>
                            <div className="mt-2 flex items-center gap-2">
                                <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-0.5 text-[10px] font-semibold text-white/70 backdrop-blur-sm">
                                    <Shield className="h-3 w-3" />
                                    {roleLabel[user.role] || user.role}
                                </span>
                                <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold backdrop-blur-sm ${user.is_active ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300"}`}>
                                    {user.is_active ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                                    {user.is_active ? "Activ" : "Inactiv"}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Info Grid */}
                <div className="p-6">
                    <div className="flex items-center justify-between mb-5">
                        <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700 dark:text-slate-300">
                            Informații Personale
                        </h3>
                        {!editing ? (
                            <button
                                onClick={() => setEditing(true)}
                                className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-600 transition-colors hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
                            >
                                <Edit3 className="h-3.5 w-3.5" />
                                Editează
                            </button>
                        ) : (
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCancel}
                                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-400"
                                >
                                    <X className="h-3.5 w-3.5" />
                                    Anulează
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-3 py-1.5 text-xs font-semibold text-white shadow-md transition-all hover:shadow-lg disabled:opacity-50"
                                >
                                    {saving ? (
                                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    ) : (
                                        <Save className="h-3.5 w-3.5" />
                                    )}
                                    Salvează
                                </button>
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        {/* First Name */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <UserIcon className="h-4 w-4 text-indigo-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Prenume</span>
                            </div>
                            {editing ? (
                                <input
                                    value={firstName}
                                    onChange={(e) => setFirstName(e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-exo text-sm text-slate-700 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                                />
                            ) : (
                                <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">{user.first_name || "—"}</p>
                            )}
                        </div>

                        {/* Last Name */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <UserIcon className="h-4 w-4 text-indigo-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Nume</span>
                            </div>
                            {editing ? (
                                <input
                                    value={lastName}
                                    onChange={(e) => setLastName(e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-exo text-sm text-slate-700 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                                />
                            ) : (
                                <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">{user.last_name || "—"}</p>
                            )}
                        </div>

                        {/* Email */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <Mail className="h-4 w-4 text-blue-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Email</span>
                            </div>
                            <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">{user.email}</p>
                        </div>

                        {/* Organization */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <Building2 className="h-4 w-4 text-violet-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Organizație</span>
                            </div>
                            <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">{user.org_name || "—"}</p>
                        </div>

                        {/* Role */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <Shield className="h-4 w-4 text-amber-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Rol</span>
                            </div>
                            <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">{roleLabel[user.role] || user.role}</p>
                        </div>

                        {/* Credits */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <CreditCard className="h-4 w-4 text-emerald-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Credite</span>
                            </div>
                            <p className="font-orbitron text-lg font-bold text-slate-700 dark:text-white">{user.credits_left ?? 0}</p>
                        </div>

                        {/* Created At */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <Calendar className="h-4 w-4 text-pink-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Cont Creat</span>
                            </div>
                            <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">
                                {user.created_at ? formatDate(user.created_at) : "—"}
                            </p>
                        </div>

                        {/* Last Login */}
                        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2 mb-2">
                                <Clock className="h-4 w-4 text-cyan-500" />
                                <span className="font-rajdhani text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Ultima Conectare</span>
                            </div>
                            <p className="font-exo text-sm font-semibold text-slate-700 dark:text-white">
                                {user.last_login ? formatDate(user.last_login) : "—"}
                            </p>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Quick Actions */}
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="relative overflow-hidden rounded-2xl border border-white/60 bg-white/80 backdrop-blur-sm p-6 shadow-lg dark:border-slate-700/60 dark:bg-slate-800/80"
            >
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-amber-500 to-orange-500" />
                <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700 dark:text-slate-300 mb-4">
                    Acțiuni Rapide
                </h3>
                <div className="flex flex-wrap gap-3">
                    <Link
                        to="/change-password"
                        className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-600 transition-all hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300 dark:hover:border-indigo-700 dark:hover:bg-indigo-900/30"
                    >
                        <KeyRound className="h-4 w-4" />
                        Schimbă Parola
                    </Link>
                </div>
            </motion.div>
        </div>
    );
}
