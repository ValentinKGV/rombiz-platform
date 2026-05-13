import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { Zap } from "lucide-react";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const { login, isLoading } = useAuthStore();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        try {
            await login(email, password);
            navigate("/");
        } catch {
            setError("Email sau parolă incorectă");
        }
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center bg-nebula bg-stars overflow-hidden">
            {/* Decorative orbit rings */}
            <div className="orbit-ring w-[600px] h-[600px] -top-[200px] -right-[200px] opacity-30" />
            <div className="orbit-ring w-[400px] h-[400px] -bottom-[150px] -left-[150px] opacity-20" style={{ animationDirection: 'reverse', animationDuration: '30s' }} />

            <div className="relative z-10 w-full max-w-md animate-star-appear">
                {/* Cosmic card */}
                <div className="relative overflow-hidden rounded-2xl border border-nebula-200/60 bg-white/90 p-10 shadow-cosmic-lg backdrop-blur-sm">
                    {/* Top gradient bar — nebula spectrum */}
                    <div className="absolute inset-x-0 top-0 h-1.5 bg-nebula-gradient" />

                    {/* Logo area */}
                    <div className="text-center">
                        <div className="relative mx-auto flex h-20 w-20 items-center justify-center">
                            {/* Orbiting ring */}
                            <div className="absolute inset-0 rounded-full border-2 border-dashed border-nebula-300/40 animate-[orbit-spin_12s_linear_infinite]" />
                            <div className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-nebula-gradient shadow-nebula">
                                <img src="/favicon.png" alt="ATH Rating" className="h-10 w-10 object-contain" />
                            </div>
                        </div>
                        <h1 className="mt-5 font-orbitron text-2xl font-bold tracking-wide text-nebula">
                            ATH | RATING
                        </h1>
                        <p className="mt-2 font-rajdhani text-sm tracking-wider text-muted-foreground uppercase">
                            Ecosistem complet de Analiză Strategică
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                        {error && (
                            <div className="flex items-center gap-2 rounded-lg border border-dragon-200 bg-dragon-50 p-3 text-sm text-dragon-700">
                                <Zap className="h-4 w-4 flex-shrink-0" />
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="email" className="block font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="input-scifi mt-1.5"
                                placeholder="navigator@cosmos.ro"
                                required
                            />
                        </div>

                        <div>
                            <label htmlFor="password" className="block font-rajdhani text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                                Parolă
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="input-scifi mt-1.5"
                                placeholder="••••••••••"
                                required
                            />
                        </div>

                        <div className="flex justify-end">
                            <Link to="/forgot-password" className="font-rajdhani text-xs font-semibold text-nebula/70 hover:text-nebula transition-colors hover:underline">
                                Ți-ai uitat parola?
                            </Link>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="btn-cosmic w-full py-3.5 text-sm disabled:opacity-50"
                        >
                            {isLoading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    Warp Drive...
                                </span>
                            ) : (
                                "Autentificare"
                            )}
                        </button>
                    </form>

                    <p className="mt-6 text-center font-exo text-sm text-muted-foreground">
                        Nu ai cont?{" "}
                        <Link to="/register" className="font-semibold text-nebula hover:underline">
                            Înregistrează-te
                        </Link>
                    </p>

                    {/* Bottom decoration — draconic fire line */}
                    <div className="absolute inset-x-0 bottom-0 h-0.5 bg-dragon-gradient opacity-40" />
                </div>
            </div>
        </div>
    );
}
