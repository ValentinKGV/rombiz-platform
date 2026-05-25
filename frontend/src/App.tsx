import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { useEffect, lazy, Suspense } from "react";
import { wsClient } from "@/lib/websocket";
import { Toaster, toast } from "sonner";
import PageSkeleton from "@/components/common/PageSkeleton";

// Layout (loaded eagerly — always needed)
import DashboardLayout from "@/components/layout/DashboardLayout";

// Lazy-loaded pages — code splitting per route
const LoginPage = lazy(() => import("@/pages/LoginPage"));
const RegisterPage = lazy(() => import("@/pages/RegisterPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const SearchPage = lazy(() => import("@/pages/SearchPage"));
const CompanyProfilePage = lazy(() => import("@/pages/CompanyProfilePage"));
const PortfoliosPage = lazy(() => import("@/pages/PortfoliosPage"));
const AlertsPage = lazy(() => import("@/pages/AlertsPage"));
const SEAPPage = lazy(() => import("@/pages/SEAPPage"));
const NewCompaniesPage = lazy(() => import("@/pages/NewCompaniesPage"));
const ESGDashboardPage = lazy(() => import("@/pages/ESGDashboardPage"));

const ReportsPage = lazy(() => import("@/pages/ReportsPage"));
const AdminPage = lazy(() => import("@/pages/AdminPage"));
const AIAgentPage = lazy(() => import("@/pages/AIAgentPage"));
const PredictivePage = lazy(() => import("@/pages/PredictivePage"));
const RelationshipsPage = lazy(() => import("@/pages/RelationshipsPage"));
const DueDiligencePage = lazy(() => import("@/pages/DueDiligencePage"));
const MarketIntelligencePage = lazy(() => import("@/pages/MarketIntelligencePage"));
const SupplyChainPage = lazy(() => import("@/pages/SupplyChainPage"));
const DocumentIntelligencePage = lazy(() => import("@/pages/DocumentIntelligencePage"));
const RegulatoryCompliancePage = lazy(() => import("@/pages/RegulatoryCompliancePage"));
const GeospatialPage = lazy(() => import("@/pages/GeospatialPage"));
const APIMarketplacePage = lazy(() => import("@/pages/APIMarketplacePage"));
const PortfolioOptimizationPage = lazy(() => import("@/pages/PortfolioOptimizationPage"));
const InternationalExpansionPage = lazy(() => import("@/pages/InternationalExpansionPage"));
const AuditLogPage = lazy(() => import("@/pages/AuditLogPage"));
const CRMDataPage = lazy(() => import("@/pages/CRMDataPage"));
const CO2DataPage = lazy(() => import("@/pages/CO2DataPage"));
const MyESGDataPage = lazy(() => import("@/pages/MyESGDataPage"));
const FacturiFurnizoriPage = lazy(() => import("@/pages/FacturiFurnizoriPage"));
const CompanyComparisonPage = lazy(() => import("@/pages/CompanyComparisonPage"));
const HartaRomaniaPage = lazy(() => import("@/pages/HartaRomaniaPage"));
const ForgotPasswordPage = lazy(() => import("@/pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("@/pages/ResetPasswordPage"));
const ChangePasswordPage = lazy(() => import("@/pages/ChangePasswordPage"));
const ProfilePage = lazy(() => import("@/pages/ProfilePage"));
const CourtCasesPage = lazy(() => import("@/pages/CourtCasesPage"));
const DosarDetaliilePage = lazy(() => import("@/pages/DosarDetaliilePage"));
const BVBPage = lazy(() => import("@/pages/BVBPage"));
const MyCompanyPage = lazy(() => import("@/pages/MyCompanyPage"));

/** Shimmer skeleton for Suspense fallback */
function RouteFallback() {
    return <PageSkeleton />;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
    if (!isAuthenticated) return <Navigate to="/login" replace />;
    return <>{children}</>;
}

export default function App() {
    const { fetchUser, isAuthenticated } = useAuthStore();

    useEffect(() => {
        if (isAuthenticated) {
            fetchUser();
            wsClient.connect();

            // Show toast on WebSocket alerts
            const unsubscribe = wsClient.onAlert((alert) => {
                toast.info(alert.titlu || "Alertă nouă", {
                    description: alert.tip_alerta,
                    duration: 5000,
                });
            });

            return () => {
                unsubscribe();
                wsClient.disconnect();
            };
        }
        return () => wsClient.disconnect();
    }, [isAuthenticated, fetchUser]);

    // Global keyboard shortcuts
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            // Ctrl+K → focus search (if on search page)
            if ((e.ctrlKey || e.metaKey) && e.key === "k") {
                e.preventDefault();
                const searchInput = document.querySelector<HTMLInputElement>('input[placeholder*="Denumire"]');
                if (searchInput) searchInput.focus();
                else window.location.href = "/search";
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, []);

    return (
        <>
            <Toaster
                position="top-right"
                toastOptions={{
                    className: "font-exo",
                    style: {
                        borderRadius: "12px",
                        border: "1px solid rgba(99, 102, 241, 0.15)",
                    },
                }}
                richColors
                closeButton
            />
            <Routes>
                {/* Public */}
                <Route path="/login" element={<Suspense fallback={<RouteFallback />}><LoginPage /></Suspense>} />
                <Route path="/register" element={<Suspense fallback={<RouteFallback />}><RegisterPage /></Suspense>} />
                <Route path="/forgot-password" element={<Suspense fallback={<RouteFallback />}><ForgotPasswordPage /></Suspense>} />
                <Route path="/reset-password" element={<Suspense fallback={<RouteFallback />}><ResetPasswordPage /></Suspense>} />

                {/* Protected */}
                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <DashboardLayout />
                        </ProtectedRoute>
                    }
                >
                    <Route index element={<Suspense fallback={<RouteFallback />}><DashboardPage /></Suspense>} />
                    <Route path="search" element={<Suspense fallback={<RouteFallback />}><SearchPage /></Suspense>} />
                    <Route path="company/:cui" element={<Suspense fallback={<RouteFallback />}><CompanyProfilePage /></Suspense>} />
                    <Route path="portfolios" element={<Suspense fallback={<RouteFallback />}><PortfoliosPage /></Suspense>} />
                    <Route path="alerts" element={<Suspense fallback={<RouteFallback />}><AlertsPage /></Suspense>} />
                    <Route path="seap" element={<Suspense fallback={<RouteFallback />}><SEAPPage /></Suspense>} />
                    <Route path="new-companies" element={<Suspense fallback={<RouteFallback />}><NewCompaniesPage /></Suspense>} />
                    <Route path="esg" element={<Suspense fallback={<RouteFallback />}><ESGDashboardPage /></Suspense>} />

                    <Route path="reports" element={<Suspense fallback={<RouteFallback />}><ReportsPage /></Suspense>} />
                    <Route path="admin" element={<Suspense fallback={<RouteFallback />}><AdminPage /></Suspense>} />
                    <Route path="ai" element={<Suspense fallback={<RouteFallback />}><AIAgentPage /></Suspense>} />
                    <Route path="predictive" element={<Suspense fallback={<RouteFallback />}><PredictivePage /></Suspense>} />
                    <Route path="relationships" element={<Suspense fallback={<RouteFallback />}><RelationshipsPage /></Suspense>} />
                    <Route path="due-diligence" element={<Suspense fallback={<RouteFallback />}><DueDiligencePage /></Suspense>} />
                    <Route path="market" element={<Suspense fallback={<RouteFallback />}><MarketIntelligencePage /></Suspense>} />
                    <Route path="supply-chain" element={<Suspense fallback={<RouteFallback />}><SupplyChainPage /></Suspense>} />
                    <Route path="documents" element={<Suspense fallback={<RouteFallback />}><DocumentIntelligencePage /></Suspense>} />
                    <Route path="compliance" element={<Suspense fallback={<RouteFallback />}><RegulatoryCompliancePage /></Suspense>} />
                    <Route path="geo" element={<Suspense fallback={<RouteFallback />}><GeospatialPage /></Suspense>} />
                    <Route path="marketplace" element={<Suspense fallback={<RouteFallback />}><APIMarketplacePage /></Suspense>} />
                    <Route path="portfolio-opt" element={<Suspense fallback={<RouteFallback />}><PortfolioOptimizationPage /></Suspense>} />
                    <Route path="international" element={<Suspense fallback={<RouteFallback />}><InternationalExpansionPage /></Suspense>} />
                    <Route path="audit-log" element={<Suspense fallback={<RouteFallback />}><AuditLogPage /></Suspense>} />
                    <Route path="crm" element={<Suspense fallback={<RouteFallback />}><CRMDataPage /></Suspense>} />
                    <Route path="co2" element={<Suspense fallback={<RouteFallback />}><CO2DataPage /></Suspense>} />
                    <Route path="my-esg" element={<Suspense fallback={<RouteFallback />}><MyESGDataPage /></Suspense>} />
                    <Route path="facturi-furnizori" element={<Suspense fallback={<RouteFallback />}><FacturiFurnizoriPage /></Suspense>} />
                    <Route path="compare" element={<Suspense fallback={<RouteFallback />}><CompanyComparisonPage /></Suspense>} />
                    <Route path="harta" element={<Suspense fallback={<RouteFallback />}><HartaRomaniaPage /></Suspense>} />
                    <Route path="bvb" element={<Suspense fallback={<RouteFallback />}><BVBPage /></Suspense>} />
                    <Route path="my-company" element={<Suspense fallback={<RouteFallback />}><MyCompanyPage /></Suspense>} />
                    <Route path="dosare" element={<Suspense fallback={<RouteFallback />}><CourtCasesPage /></Suspense>} />
                    <Route path="dosare/detalii" element={<Suspense fallback={<RouteFallback />}><DosarDetaliilePage /></Suspense>} />
                    <Route path="change-password" element={<Suspense fallback={<RouteFallback />}><ChangePasswordPage /></Suspense>} />
                    <Route path="profile" element={<Suspense fallback={<RouteFallback />}><ProfilePage /></Suspense>} />
                </Route>

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </>
    );
}
