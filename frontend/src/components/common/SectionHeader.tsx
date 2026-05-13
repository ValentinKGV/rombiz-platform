import { cn } from "@/lib/utils";

interface SectionHeaderProps {
    title: string;
    subtitle?: string;
    className?: string;
    actions?: React.ReactNode;
}

export default function SectionHeader({ title, subtitle, className, actions }: SectionHeaderProps) {
    return (
        <div className={cn("section-header flex items-start justify-between", className)}>
            <div>
                <h1 className="font-orbitron text-2xl font-bold tracking-wide text-nebula">
                    {title}
                </h1>
                {subtitle && (
                    <p className="mt-1 font-rajdhani text-sm uppercase tracking-wider text-slate-400">
                        {subtitle}
                    </p>
                )}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    );
}
