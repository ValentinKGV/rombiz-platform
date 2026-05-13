import { cn } from "@/lib/utils";

interface DisclaimerBannerProps {
    title?: string;
    text?: string;
    variant?: "warning" | "info";
    className?: string;
    children?: React.ReactNode;
}

export type { DisclaimerBannerProps };

export default function DisclaimerBanner({
    title,
    text,
    variant = "warning",
    className,
    children,
}: DisclaimerBannerProps) {
    return (
        <div
            className={cn(
                "card-cosmic border-l-4 py-3 px-4 text-sm",
                variant === "warning"
                    ? "border-dragon-fire text-dragon-600"
                    : "border-nebula-400 text-nebula-600",
                className
            )}
        >
            {title && <strong>{title} </strong>}
            {text}
            {children}
        </div>
    );
}
