import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TabItem {
    id: string;
    label: string;
    icon?: LucideIcon;
    badge?: number;
}

interface TabNavProps {
    tabs: TabItem[];
    activeTab: string;
    onTabChange: (tabId: string) => void;
    className?: string;
    variant?: "pills" | "underline";
}

export default function TabNav({
    tabs,
    activeTab,
    onTabChange,
    className,
    variant = "pills",
}: TabNavProps) {
    if (variant === "underline") {
        return (
            <div className={cn("flex border-b border-slate-200", className)}>
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = tab.id === activeTab;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => onTabChange(tab.id)}
                            className={cn(
                                "flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
                                isActive
                                    ? "border-nebula-500 text-nebula-600"
                                    : "border-transparent text-slate-400 hover:text-slate-600"
                            )}
                        >
                            {Icon && <Icon className="h-4 w-4" />}
                            {tab.label}
                            {tab.badge !== undefined && tab.badge > 0 && (
                                <span className="ml-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-dragon-100 px-1.5 text-[10px] font-semibold text-dragon-600">
                                    {tab.badge}
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>
        );
    }

    // Pills variant (default)
    return (
        <div className={cn("flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1", className)}>
            {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = tab.id === activeTab;
                return (
                    <button
                        key={tab.id}
                        onClick={() => onTabChange(tab.id)}
                        className={cn(
                            "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
                            isActive
                                ? "bg-nebula-500 text-white"
                                : "text-slate-500 hover:bg-slate-100"
                        )}
                    >
                        {Icon && <Icon className="h-4 w-4" />}
                        {tab.label}
                        {tab.badge !== undefined && tab.badge > 0 && (
                            <span
                                className={cn(
                                    "ml-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[10px] font-semibold",
                                    isActive
                                        ? "bg-white/20 text-white"
                                        : "bg-dragon-100 text-dragon-600"
                                )}
                            >
                                {tab.badge}
                            </span>
                        )}
                    </button>
                );
            })}
        </div>
    );
}
