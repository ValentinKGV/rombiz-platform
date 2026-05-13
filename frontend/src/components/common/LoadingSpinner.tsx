import { Orbit } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
    size?: "sm" | "md" | "lg";
    className?: string;
    label?: string;
}

const SIZES = {
    sm: { outer: "h-6 w-6", inner: "h-3 w-3" },
    md: { outer: "h-10 w-10", inner: "h-4 w-4" },
    lg: { outer: "h-12 w-12", inner: "h-5 w-5" },
};

export default function LoadingSpinner({ size = "md", className, label }: LoadingSpinnerProps) {
    const s = SIZES[size];

    return (
        <div className={cn("flex flex-col items-center justify-center gap-3", className)}>
            <div className="relative">
                <div
                    className={cn(
                        "animate-spin rounded-full border-4 border-nebula-200 border-t-nebula-500",
                        s.outer
                    )}
                />
                <Orbit
                    className={cn(
                        "absolute inset-0 m-auto text-nebula-400 animate-pulse",
                        s.inner
                    )}
                />
            </div>
            {label && (
                <p className="font-rajdhani text-sm uppercase tracking-wider text-slate-400">{label}</p>
            )}
        </div>
    );
}
