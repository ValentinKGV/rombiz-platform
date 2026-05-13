import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Zap, KeyRound, CheckCircle2, Eye, EyeOff } from "lucide-react";

export default function ChangePasswordPage() {
    const navigate = useNavigate();
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (newPassword !== confirmPassword) {
            setError("Parolele noi nu coincid");
            return;
        }

        if (newPassword.length < 8) {
            setError("Parola nouă trebuie să aibă minim 8 caractere");
            return;
        }

        if (currentPassword === newPassword) {
            setError("Parola nouă trebuie să fie diferită de cea curentă");
            return;
        }

        setIsLoading(true);
        try {
            await api.post("/auth/change-password", {
                current_password: currentPassword,
                new_password: newPassword,
            });
            setSuccess(true);
            setTimeout(() => navigate("/"), 2000);
        } catch (err: any) {
            const detail = err?.response?.data?.detail;
            setError(detail || "Eroare la schimbarea parolei");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="mx-auto max-w-lg space-y-6">
            <div>
                <h1 className="font-orbitron text-xl font-bold tracking-wide text-slate-800">
                    Schimbă Parola
                </h1>
                <p className="mt-1 font-rajdhani text-sm text-muted-foreground">
                    Înlocuiește parola curentă cu una nouă, aleasă de tine.
                </p>
            </div>

            <div className="relative overflow-hidden rounded-2xl border border-white/60 bg-white/80 backdrop-blur-sm p-8 shadow-lg">
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-500" />

                {success ? (
                    <div className="flex flex-col items-center gap-3 py-6 text-center">
                        <CheckCircle2 className="h-12 w-12 text-emerald-500" />
                        <h2 className="font-orbitron text-lg font-bold text-emerald-700">Parolă schimbată!</h2>
                        <p className="font-rajdhani text-sm text-emerald-600/70">
                            Parola a fost actualizată cu succes. Vei fi redirecționat...
                        </p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-md">
                                <KeyRound className="h-5 w-5" />
                            </div>
                            <div>
                                <h3 className="font-orbitron text-xs font-semibold tracking-wide text-slate-700">Securitate Cont</h3>
                                <p className="font-rajdhani text-[10px] text-slate-400">Schimbă parola de acces</p>
                            </div>
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 rounded-lg border border-dragon-200 bg-dragon-50 p-3 text-sm text-dragon-700">
                                <Zap className="h-4 w-4 flex-shrink-0" />
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="current" className="block font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                                Parola Curentă
                            </label>
                            <div className="relative mt-1.5">
                                <input
                                    id="current"
                                    type={showCurrent ? "text" : "password"}
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 bg-slate-50/80 px-4 py-2.5 pr-10 font-exo text-sm text-slate-700 placeholder:text-slate-300 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors"
                                    placeholder="Parola actuală"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrent(!showCurrent)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-indigo-500 transition-colors"
                                >
                                    {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                            </div>
                        </div>

                        <div>
                            <label htmlFor="new-pass" className="block font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                                Parolă Nouă
                            </label>
                            <div className="relative mt-1.5">
                                <input
                                    id="new-pass"
                                    type={showNew ? "text" : "password"}
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 bg-slate-50/80 px-4 py-2.5 pr-10 font-exo text-sm text-slate-700 placeholder:text-slate-300 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors"
                                    placeholder="Minim 8 caractere"
                                    required
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNew(!showNew)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-indigo-500 transition-colors"
                                >
                                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                            </div>
                        </div>

                        <div>
                            <label htmlFor="confirm-pass" className="block font-rajdhani text-xs font-semibold uppercase tracking-wider text-slate-400">
                                Confirmă Parola Nouă
                            </label>
                            <input
                                id="confirm-pass"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50/80 px-4 py-2.5 font-exo text-sm text-slate-700 placeholder:text-slate-300 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 transition-colors"
                                placeholder="Repetă parola nouă"
                                required
                                minLength={8}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-6 py-3 font-rajdhani text-sm font-bold uppercase tracking-wider text-white shadow-md transition-all hover:shadow-lg disabled:opacity-50"
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    Se procesează...
                                </span>
                            ) : (
                                "Schimbă Parola"
                            )}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}
