import { Orbit, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
    icon?: LucideIcon;
    message: string;
    subtitle?: string;
    className?: string;
    action?: React.ReactNode;
}

export default function EmptyState({
    icon: Icon = Orbit,
    message,
    subtitle,
    className,
    action,
}: EmptyStateProps) {
    return (
        <div
            className={cn(
                "flex flex-col items-center justify-center py-12 text-slate-300",
                className
            )}
        >
            <Icon className="h-12 w-12 mb-3 animate-[orbit-spin_8s_linear_infinite]" />
            <p className="font-rajdhani text-sm uppercase tracking-wider">{message}</p>
            {subtitle && (
                <p className="mt-1 font-exo text-xs text-slate-400">{subtitle}</p>
            )}
            {action && <div className="mt-4">{action}</div>}
        </div>
    );
}
