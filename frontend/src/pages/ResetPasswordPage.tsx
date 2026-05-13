import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { Zap, ShieldCheck, ArrowLeft, CheckCircle2, Eye, EyeOff } from "lucide-react";

export default function ResetPasswordPage() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token") || "";

    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (password !== confirmPassword) {
            setError("Parolele nu coincid");
            return;
        }

        if (password.length < 8) {
            setError("Parola trebuie să aibă minim 8 caractere");
            return;
        }

        setIsLoading(true);
        try {
            await api.post("/auth/reset-password", {
                token,
                new_password: password,
            });
            setSuccess(true);
        } catch (err: any) {
            const detail = err?.response?.data?.detail;
            setError(detail || "Token invalid sau expirat. Solicită un link nou.");
        } finally {
            setIsLoading(false);
        }
    };

    if (!token) {
        return (
            <div className="relative flex min-h-screen items-center justify-center bg-nebula bg-stars overflow-hidden">
                <div className="relative z-10 w-full max-w-md animate-star-appear">
                    <div className="relative overflow-hidden rounded-2xl border border-nebula-200/60 bg-white/90 p-10 shadow-cosmic-lg backdrop-blur-sm text-center">
                        <div className="absolute inset-x-0 top-0 h-1.5 bg-nebula-gradient" />
                        <Zap className="mx-auto h-10 w-10 text-dragon-500 mb-4" />
                        <h2 className="font-orbitron text-lg font-bold text-slate-800">Link invalid</h2>
                        <p className="mt-2 font-rajdhani text-sm text-muted-foreground">
                            Token-ul de resetare lipsește. Solicită un link nou din pagina de autentificare.
                        </p>
                        <Link to="/forgot-password" className="mt-6 inline-flex items-center gap-2 font-rajdhani text-sm font-semibold text-nebula hover:underline">
                            <ArrowLeft className="h-4 w-4" /> Solicită link nou
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="relative flex min-h-screen items-center justify-center bg-nebula bg-stars overflow-hidden">
            <div className="orbit-ring w-[600px] h-[600px] -top-[200px] -right-[200px] opacity-30" />
            <div className="orbit-ring w-[400px] h-[400px] -bottom-[150px] -left-[150px] opacity-20" style={{ animationDirection: "reverse", animationDuration: "30s" }} />

            <div className="relative z-10 w-full max-w-md animate-star-appear">
                <div className="relative overflow-hidden rounded-2xl border border-nebula-200/60 bg-white/90 p-10 shadow-cosmic-lg backdrop-blur-sm">
                    <div className="absolute inset-x-0 top-0 h-1.5 bg-nebula-gradient" />

                    <div className="text-center">
                        <div className="relative mx-auto flex h-20 w-20 items-center justify-center">
                            <div className="absolute inset-0 rounded-full border-2 border-dashed border-nebula-300/40 animate-[orbit-spin_12s_linear_infinite]" />
                            <div className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-nebula-gradient shadow-nebula">
                                <ShieldCheck className="h-7 w-7 text-white" />
                            </div>
                        </div>
                        <h1 className="mt-5 font-orbitron text-xl font-bold tracking-wide text-nebula">
                            Parolă Nouă
                        </h1>
                        <p className="mt-2 font-rajdhani text-sm tracking-wider text-muted-foreground">
                            Setează o parolă nouă pentru contul tău
                        </p>
                    </div>

                    {success ? (
                        <div className="mt-8 space-y-5">
                            <div className="flex flex-col items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-center">
                                <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                                <p className="font-rajdhani text-sm font-semibold text-emerald-700">
                                    Parola a fost resetată!
                                </p>
                                <p className="font-exo text-xs text-emerald-600/70">
                                    Te poți autentifica acum cu noua parolă.
                                </p>
                            </div>
                            <Link
                                to="/login"
                                className="btn-cosmic flex w-full items-center justify-center gap-2 py-3.5 text-sm"
                            >
                                Mergi la autentificare
                            </Link>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                            {error && (
                                <div className="flex items-center gap-2 rounded-lg border border-dragon-200 bg-dragon-50 p-3 text-sm text-dragon-700">
                                    <Zap className="h-4 w-4 flex-shrink-0" />
                                    {error}
                                </div>
                            )}

                            <div>
                                <label htmlFor="password" className="block font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                    Parolă Nouă
                                </label>
                                <div className="relative mt-1.5">
                                    <input
                                        id="password"
                                        type={showPassword ? "text" : "password"}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="input-scifi pr-10"
                                        placeholder="Minim 8 caractere"
                                        required
                                        minLength={8}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-nebula transition-colors"
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label htmlFor="confirm" className="block font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                    Confirmă Parola
                                </label>
                                <input
                                    id="confirm"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="input-scifi mt-1.5"
                                    placeholder="Repetă parola nouă"
                                    required
                                    minLength={8}
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="btn-cosmic w-full py-3.5 text-sm disabled:opacity-50"
                            >
                                {isLoading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                        Se procesează...
                                    </span>
                                ) : (
                                    "Resetează Parola"
                                )}
                            </button>

                            <Link
                                to="/login"
                                className="flex w-full items-center justify-center gap-2 rounded-lg border border-nebula-200 bg-white px-4 py-2.5 font-rajdhani text-sm font-semibold text-nebula transition-colors hover:bg-nebula-50"
                            >
                                <ArrowLeft className="h-4 w-4" />
                                Înapoi la autentificare
                            </Link>
                        </form>
                    )}

                    <div className="absolute inset-x-0 bottom-0 h-0.5 bg-dragon-gradient opacity-40" />
                </div>
            </div>
        </div>
    );
}
