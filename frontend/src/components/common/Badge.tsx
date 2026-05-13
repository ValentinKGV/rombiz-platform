import { cn } from "@/lib/utils";

interface BadgeProps {
    children: React.ReactNode;
    variant?: "success" | "warning" | "danger" | "info" | "neutral";
    size?: "sm" | "md";
    className?: string;
}

const VARIANTS = {
    success: "bg-green-100 text-green-700",
    warning: "bg-yellow-100 text-yellow-700",
    danger: "bg-red-100 text-red-700",
    info: "bg-blue-100 text-blue-700",
    neutral: "bg-slate-100 text-slate-500",
};

export default function Badge({ children, variant = "neutral", size = "sm", className }: BadgeProps) {
    return (
        <span
            className={cn(
                "inline-flex items-center rounded-full font-medium",
                VARIANTS[variant],
                size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
                className
            )}
        >
            {children}
        </span>
    );
}
