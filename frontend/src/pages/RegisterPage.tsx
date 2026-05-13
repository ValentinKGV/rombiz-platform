import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { Rocket, Zap, User, Building2, Mail, Lock, ShieldCheck } from "lucide-react";

export default function RegisterPage() {
    const [form, setForm] = useState({
        email: "",
        password: "",
        confirmPassword: "",
        first_name: "",
        last_name: "",
        org_name: "",
    });
    const [error, setError] = useState("");
    const { register, isLoading } = useAuthStore();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (form.password !== form.confirmPassword) {
            setError("Parolele nu coincid");
            return;
        }

        try {
            await register({
                email: form.email,
                password: form.password,
                first_name: form.first_name,
                last_name: form.last_name,
                org_name: form.org_name,
            });
            navigate("/login");
        } catch {
            setError("Eroare la înregistrare. Verifică datele introduse.");
        }
    };

    const updateField = (field: string, value: string) => {
        setForm((prev) => ({ ...prev, [field]: value }));
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center bg-nebula bg-stars overflow-hidden py-10">
            {/* Decorative orbit rings */}
            <div className="orbit-ring w-[500px] h-[500px] -top-[180px] -left-[180px] opacity-25" />
            <div className="orbit-ring w-[700px] h-[700px] -bottom-[280px] -right-[280px] opacity-15" style={{ animationDirection: 'reverse', animationDuration: '35s' }} />

            <div className="relative z-10 w-full max-w-lg animate-star-appear px-4">
                {/* Cosmic card */}
                <div className="relative overflow-hidden rounded-2xl border border-nebula-200/60 bg-white/90 p-10 shadow-cosmic-lg backdrop-blur-sm">
                    {/* Top gradient bar */}
                    <div className="absolute inset-x-0 top-0 h-1.5 bg-dragon-gradient" />

                    <div className="text-center">
                        <div className="relative mx-auto flex h-20 w-20 items-center justify-center">
                            <div className="absolute inset-0 rounded-full border-2 border-dashed border-dragon-300/40 animate-[orbit-spin_15s_linear_infinite]" />
                            <div className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-dragon-gradient shadow-dragon">
                                <Rocket className="h-7 w-7 text-white" />
                            </div>
                        </div>
                        <h1 className="mt-5 font-orbitron text-2xl font-bold tracking-wide text-dragon">
                            Înregistrare
                        </h1>
                        <p className="mt-2 font-rajdhani text-sm tracking-wider text-muted-foreground uppercase">
                            Alătură-te flotei intergalactice
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="mt-8 space-y-4">
                        {error && (
                            <div className="flex items-center gap-2 rounded-lg border border-dragon-200 bg-dragon-50 p-3 text-sm text-dragon-700">
                                <Zap className="h-4 w-4 flex-shrink-0" />
                                {error}
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="flex items-center gap-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                    <User className="h-3.5 w-3.5" /> Prenume
                                </label>
                                <input
                                    type="text"
                                    value={form.first_name}
                                    onChange={(e) => updateField("first_name", e.target.value)}
                                    className="input-scifi mt-1.5"
                                    placeholder="Ion"
                                    required
                                />
                            </div>
                            <div>
                                <label className="flex items-center gap-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                    <User className="h-3.5 w-3.5" /> Nume
                                </label>
                                <input
                                    type="text"
                                    value={form.last_name}
                                    onChange={(e) => updateField("last_name", e.target.value)}
                                    className="input-scifi mt-1.5"
                                    placeholder="Popescu"
                                    required
                                />
                            </div>
                        </div>

                        <div>
                            <label className="flex items-center gap-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                <Building2 className="h-3.5 w-3.5" /> Organizație
                            </label>
                            <input
                                type="text"
                                value={form.org_name}
                                onChange={(e) => updateField("org_name", e.target.value)}
                                className="input-scifi mt-1.5"
                                placeholder="Andromeda Corp SRL"
                                required
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                <Mail className="h-3.5 w-3.5" /> Email
                            </label>
                            <input
                                type="email"
                                value={form.email}
                                onChange={(e) => updateField("email", e.target.value)}
                                className="input-scifi mt-1.5"
                                placeholder="navigator@cosmos.ro"
                                required
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                <Lock className="h-3.5 w-3.5" /> Parolă
                            </label>
                            <input
                                type="password"
                                value={form.password}
                                onChange={(e) => updateField("password", e.target.value)}
                                className="input-scifi mt-1.5"
                                placeholder="••••••••••"
                                required
                                minLength={8}
                            />
                        </div>

                        <div>
                            <label className="flex items-center gap-1.5 font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                <ShieldCheck className="h-3.5 w-3.5" /> Confirmă Parola
                            </label>
                            <input
                                type="password"
                                value={form.confirmPassword}
                                onChange={(e) => updateField("confirmPassword", e.target.value)}
                                className="input-scifi mt-1.5"
                                placeholder="••••••••••"
                                required
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
                                    Lansare...
                                </span>
                            ) : (
                                "Creează Cont"
                            )}
                        </button>
                    </form>

                    <p className="mt-6 text-center font-exo text-sm text-muted-foreground">
                        Ai deja cont?{" "}
                        <Link to="/login" className="font-semibold text-nebula hover:underline">
                            Autentifică-te
                        </Link>
                    </p>

                    {/* Bottom draconic fire line */}
                    <div className="absolute inset-x-0 bottom-0 h-0.5 bg-nebula-gradient opacity-40" />
                </div>
            </div>
        </div>
    );
}
