import { cn } from "@/lib/utils";
import type { ReactNode, ComponentType } from "react";

interface StatCardProps {
    title?: string;
    label?: string;
    value: string | number;
    icon?: ReactNode | ComponentType<{ className?: string }>;
    className?: string;
    /** Optional gradient accent for top line (e.g. "from-nebula-400 to-cosmos-400") */
    gradient?: string;
    /** Optional icon background classes */
    iconBg?: string;
    /** Optional icon color classes */
    iconColor?: string;
    /** Optional border color */
    borderColor?: string;
}

export type { StatCardProps };

export default function StatCard({
    title,
    label,
    value,
    icon,
    className,
    gradient,
    iconBg = "bg-nebula-50",
    iconColor = "text-nebula-400",
    borderColor,
}: StatCardProps) {
    const displayTitle = title || label || "";

    // Support both ReactNode and Lucide component types for icon
    let iconElement: ReactNode = null;
    if (icon) {
        if (typeof icon === "function") {
            const IconComp = icon as ComponentType<{ className?: string }>;
            iconElement = <IconComp className="h-5 w-5" />;
        } else {
            iconElement = icon;
        }
    }
    return (
        <div
            className={cn(
                "card-cosmic group relative overflow-hidden",
                borderColor && `border ${borderColor}`,
                className
            )}
        >
            {gradient && (
                <div
                    className={cn(
                        "absolute inset-x-0 top-0 h-1 bg-gradient-to-r opacity-60",
                        gradient
                    )}
                />
            )}
            <div className="flex items-center justify-between">
                <p className="font-rajdhani text-sm font-semibold uppercase tracking-wider text-slate-400">
                    {displayTitle}
                </p>
                {iconElement && (
                    <div
                        className={cn(
                            "flex h-10 w-10 items-center justify-center rounded-xl transition-transform group-hover:scale-110",
                            iconBg,
                            iconColor
                        )}
                    >
                        {iconElement}
                    </div>
                )}
            </div>
            <p className="mt-3 font-orbitron text-3xl font-bold text-slate-800">
                {value}
            </p>
        </div>
    );
}
