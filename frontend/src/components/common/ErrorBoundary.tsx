import { Component, type ErrorInfo, type ReactNode } from "react";
import { Orbit } from "lucide-react";

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * Catches render-time errors in child components so the
 * entire app (and auth state) doesn't blow up.
 */
export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false, error: null };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: ErrorInfo) {
        console.error("[ErrorBoundary]", error, info.componentStack);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;

            return (
                <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-dragon-50">
                        <Orbit className="h-8 w-8 text-dragon-500 animate-spin" />
                    </div>
                    <h2 className="font-orbitron text-lg font-bold text-slate-700">
                        Eroare de randare
                    </h2>
                    <p className="max-w-md font-exo text-sm text-slate-400">
                        {this.state.error?.message || "O eroare neașteptată a apărut."}
                    </p>
                    <button
                        onClick={() => this.setState({ hasError: false, error: null })}
                        className="btn-cosmic mt-2 px-6 py-2 text-sm"
                    >
                        Reîncearcă
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
