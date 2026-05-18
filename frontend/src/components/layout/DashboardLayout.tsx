import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";
import {
    LayoutDashboard,
    Search,
    Briefcase,
    Bell,
    Building2,
    Shield,
    Leaf,
    FileText,
    Users,
    Bot,
    Gavel,
    Scale,
    LogOut,
    Menu,
    X,
    Orbit,
    Sparkles,
    Cloud,
    ReceiptText,
    Sun,
    Moon,
    GitCompareArrows,
    MapPin,
    TrendingUp,
    Headset,
    ExternalLink,
    Check,
    Landmark,
} from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import { AnimatePresence, motion } from "framer-motion";

const navItems = [
    { path: "/", label: "Dashboard", icon: LayoutDashboard },
    { path: "/my-company", label: "My Company", icon: Landmark },
    { path: "/search", label: "Căutare", icon: Search },
    { path: "/portfolios", label: "Portofolii", icon: Briefcase },
    { path: "/alerts", label: "Alerte", icon: Bell },
    { path: "/seap", label: "SEAP", icon: Gavel },
    { path: "/dosare", label: "Motor Dosare", icon: Scale },
    { path: "/new-companies", label: "Firme Noi", icon: Building2 },
    { path: "/fraud", label: "Fraud Graph", icon: Shield },
    // { path: "/esg", label: "ESG", icon: Leaf },
    { path: "/reports", label: "Rapoarte", icon: FileText },
    { path: "/ai", label: "AI Agent", icon: Bot },
    { path: "/compare", label: "Comparare Firme", icon: GitCompareArrows },
    { path: "/harta", label: "Harta România", icon: MapPin },
    { path: "/bvb", label: "BVB", icon: TrendingUp },
    { path: "/facturi-furnizori", label: "ATH | INVOICING", icon: ReceiptText },
    { path: "/crm", label: "ATH | CRM", icon: Sparkles },
    { path: "/co2", label: "ATH | CO2", icon: Cloud },
    { path: "/my-esg", label: "ATH | ESG", icon: Orbit },
];

const adminItems = [
    { path: "/admin", label: "Admin", icon: Users },
];

function SupportButton({ collapsed }: { collapsed?: boolean }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText("suport@crm.nineinternational.ro");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    if (collapsed) {
        return (
            <button
                onClick={handleCopy}
                className="flex justify-center rounded-lg bg-nebula-500 p-2 text-white hover:bg-nebula-600 transition-colors"
                title={copied ? "Copiat!" : "Suport Tehnic"}
            >
                {copied ? <Check className="h-4 w-4" /> : <Headset className="h-4 w-4" />}
            </button>
        );
    }
    return (
        <button
            onClick={handleCopy}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-nebula-500 px-2 py-1.5 text-[10px] font-semibold text-white shadow-sm transition-all hover:bg-nebula-600 hover:shadow-md"
        >
            {copied ? <Check className="h-3 w-3" /> : <Headset className="h-3 w-3" />}
            {copied ? "Copiat!" : "Suport Tehnic"}
        </button>
    );
}

export default function DashboardLayout() {
    const { user, logout } = useAuthStore();
    const { dark, toggle: toggleTheme } = useThemeStore();
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [mobileOpen, setMobileOpen] = useState(false);

    // Unread alerts count
    const { data: unreadCount } = useQuery({
        queryKey: ["alerts", "unread-count"],
        queryFn: async () => {
            const { data } = await api.get<{ count: number }>("/alerts/unread-count");
            return data.count;
        },
        refetchInterval: 30000,
    });

    // Close mobile sidebar on route change
    useEffect(() => {
        setMobileOpen(false);
    }, [location.pathname]);

    const allItems = user?.role === "admin"
        ? [...navItems, ...adminItems]
        : navItems;

    return (
        <div className="flex h-screen overflow-hidden bg-gradient-to-br from-background via-nebula-50/30 to-cosmos-50/20 dark:from-background dark:via-nebula-900/10 dark:to-cosmos-900/10 transition-colors duration-300">
            {/* ── Sidebar ── */}
            <aside
                className={cn(
                    "sidebar-cosmic fixed inset-y-0 left-0 z-50 flex flex-col transition-all duration-300 lg:relative",
                    sidebarOpen ? "w-64" : "w-[72px]",
                    mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
                )}
            >
                {/* Logo area */}
                <div className="relative flex h-16 items-center justify-between px-4">
                    {sidebarOpen && (
                        <Link to="/" className="flex items-center gap-2.5 group">
                            <img src="/favicon-2.png" alt="ATH" className="h-9 w-9 rounded-lg object-contain shadow-nebula transition-transform group-hover:scale-110" />
                            <div>
                                <span className="font-orbitron text-base font-bold tracking-wider text-nebula-800 dark:text-nebula-200">
                                    ATH | RATING
                                </span>
                                <span className="block font-rajdhani text-[10px] uppercase tracking-[0.2em] text-nebula-400">

                                </span>
                            </div>
                        </Link>
                    )}
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="hidden rounded-lg p-1.5 text-nebula-400 hover:bg-nebula-100/60 dark:hover:bg-nebula-800/40 hover:text-nebula-600 transition-colors lg:block"
                    >
                        <Menu className="h-5 w-5" />
                    </button>
                    <button
                        onClick={() => setMobileOpen(false)}
                        className="rounded-lg p-1.5 text-nebula-400 hover:bg-nebula-100/60 dark:hover:bg-nebula-800/40 lg:hidden"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-cosmic">
                    <ul className="space-y-1">
                        {allItems.map((item) => {
                            const isActive = location.pathname === item.path;
                            const Icon = item.icon;
                            const isAthGroup = item.label.startsWith("ATH |");
                            const prevItem = allItems[allItems.indexOf(item) - 1];
                            const showSeparator = isAthGroup && (!prevItem || !prevItem.label.startsWith("ATH |"));
                            return (
                                <li key={item.path}>
                                    {showSeparator && (
                                        <div className={cn("mb-2 mt-3 flex items-center gap-2", sidebarOpen ? "px-1" : "justify-center")}>
                                            <div className="h-px flex-1 bg-nebula-200/60 dark:bg-nebula-700/40" />
                                            {sidebarOpen && (
                                                <span className="font-rajdhani text-[9px] font-bold uppercase tracking-[0.2em] text-nebula-400/70 dark:text-nebula-500/60">
                                                    ATH Apps
                                                </span>
                                            )}
                                            <div className="h-px flex-1 bg-nebula-200/60 dark:bg-nebula-700/40" />
                                        </div>
                                    )}
                                    <Link
                                        to={item.path}
                                        className={cn(
                                            "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                                            isActive
                                                ? "nav-active"
                                                : "text-slate-500 dark:text-slate-400 hover:bg-nebula-50/80 dark:hover:bg-nebula-900/30 hover:text-nebula-700 dark:hover:text-nebula-300"
                                        )}
                                    >
                                        <Icon className={cn(
                                            "h-5 w-5 flex-shrink-0 transition-colors",
                                            isActive ? "text-white" : "text-slate-400 dark:text-slate-500 group-hover:text-nebula-500"
                                        )} />
                                        {sidebarOpen && (
                                            <span className="flex-1 font-exo">{item.label}</span>
                                        )}
                                        {item.path === "/alerts" && unreadCount && unreadCount > 0 && sidebarOpen && (
                                            <span className="rounded-full bg-dragon-500 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm animate-pulse">
                                                {unreadCount}
                                            </span>
                                        )}
                                        {/* Active indicator line */}
                                        {isActive && (
                                            <div className="absolute -left-3 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-nebula-400" />
                                        )}
                                    </Link>
                                </li>
                            );
                        })}
                    </ul>
                </nav>

                {/* Bottom area */}
                <div className="border-t border-border p-3">
                    {/* Dark mode toggle */}
                    <div className="mb-2">
                        {sidebarOpen ? (
                            <button
                                onClick={toggleTheme}
                                className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-nebula-50/80 dark:hover:bg-nebula-900/30 hover:text-nebula-600 dark:hover:text-nebula-400 transition-all duration-200"
                            >
                                {dark ? <Sun className="h-4 w-4 text-stardust" /> : <Moon className="h-4 w-4 text-nebula-500" />}
                                <span className="font-exo">{dark ? "Light Mode" : "Dark Mode"}</span>
                            </button>
                        ) : (
                            <button
                                onClick={toggleTheme}
                                className="flex w-full justify-center rounded-lg p-2 text-muted-foreground hover:bg-nebula-50/80 dark:hover:bg-nebula-900/30 hover:text-nebula-600 transition-colors"
                                title={dark ? "Light Mode" : "Dark Mode"}
                            >
                                {dark ? <Sun className="h-4 w-4 text-stardust" /> : <Moon className="h-4 w-4" />}
                            </button>
                        )}
                    </div>

                    {/* Support & Ticket */}
                    {sidebarOpen ? (
                        <div className="flex gap-2 mt-1">
                            <SupportButton />
                            <a
                                href="https://nineinternational.eu/forms/ticket"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex flex-1 items-center justify-center gap-1.5 rounded-md bg-nebula-500 px-2 py-1.5 text-[10px] font-semibold text-white shadow-sm transition-all hover:bg-nebula-600 hover:shadow-md"
                            >
                                <ExternalLink className="h-3 w-3" />
                                Ticket
                            </a>
                        </div>
                    ) : (
                        <div className="flex flex-col gap-1.5 mt-2">
                            <SupportButton collapsed />
                            <a
                                href="https://nineinternational.eu/forms/ticket"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex justify-center rounded-lg bg-nebula-500 p-2 text-white hover:bg-nebula-600 transition-colors"
                                title="Ticket"
                            >
                                <ExternalLink className="h-4 w-4" />
                            </a>
                        </div>
                    )}

                    {/* Copyright */}
                    {sidebarOpen && (
                        <div className="mt-3 text-center">
                            <p className="font-rajdhani text-xs text-muted-foreground/60">
                                Copyright © Developed by
                            </p>
                            <a
                                href="https://nineinternational.eu"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-rajdhani text-sm font-bold text-nebula-500 hover:text-nebula-600 hover:underline transition-colors"
                            >
                                Nine International Group
                            </a>
                        </div>
                    )}
                </div>
            </aside>

            {/* Overlay for mobile */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 z-40 bg-void/30 backdrop-blur-sm lg:hidden"
                    onClick={() => setMobileOpen(false)}
                />
            )}

            {/* ── Main content ── */}
            <main className="flex flex-1 flex-col overflow-hidden">
                {/* Top bar */}
                <header className="relative flex h-16 items-center justify-between border-b border-nebula-100/40 dark:border-nebula-800/40 bg-white/70 dark:bg-card/70 px-6 backdrop-blur-md transition-colors duration-300">
                    {/* Subtle top gradient line */}
                    <div className="absolute inset-x-0 top-0 h-[2px] bg-nebula-gradient opacity-30" />

                    <button
                        onClick={() => setMobileOpen(true)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-nebula-50 dark:hover:bg-nebula-900/30 hover:text-nebula-600 lg:hidden"
                    >
                        <Menu className="h-5 w-5" />
                    </button>
                    <div className="flex-1" />
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 rounded-lg bg-nebula-50/60 dark:bg-nebula-900/30 px-3 py-1.5">
                            <Sparkles className="h-3.5 w-3.5 text-stardust-500" />
                            <span className="font-rajdhani text-sm font-semibold tracking-wide text-slate-600 dark:text-slate-300">
                                {user?.org_name}
                            </span>
                        </div>

                        {/* User profile */}
                        <div className="flex items-center gap-3">
                            <Link to="/profile" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-dragon-gradient text-white shadow-sm transition-transform hover:scale-110 overflow-hidden" title="Profilul Meu">
                                {user?.avatar_url ? (
                                    <img src={user.avatar_url} alt="Avatar" className="h-full w-full object-cover" />
                                ) : (
                                    <span className="font-orbitron text-[10px] font-bold">
                                        {user?.first_name?.[0]}{user?.last_name?.[0]}
                                    </span>
                                )}
                            </Link>
                            <Link to="/profile" className="hidden md:block min-w-0 hover:opacity-80 transition-opacity">
                                <p className="truncate font-exo text-sm font-semibold text-foreground leading-tight">
                                    {user?.first_name} {user?.last_name}
                                </p>
                                <p className="truncate font-rajdhani text-xs text-muted-foreground leading-tight">
                                    {user?.email}
                                </p>
                            </Link>
                            <button
                                onClick={logout}
                                className="rounded-lg p-1.5 text-slate-400 hover:bg-dragon-50 dark:hover:bg-dragon-900/30 hover:text-dragon-500 transition-colors"
                                title="Deconectare"
                            >
                                <LogOut className="h-4 w-4" />
                            </button>
                        </div>
                    </div>
                </header>

                {/* Page content */}
                <div className="flex-1 overflow-y-auto bg-gradient-to-br from-white via-nebula-50/10 to-cosmos-50/10 dark:from-background dark:via-nebula-950/10 dark:to-cosmos-950/10 p-4 md:p-6 scrollbar-cosmic transition-colors duration-300">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={location.pathname}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -12 }}
                            transition={{ duration: 0.2, ease: "easeInOut" }}
                        >
                            <ErrorBoundary>
                                <Outlet />
                            </ErrorBoundary>
                        </motion.div>
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}
