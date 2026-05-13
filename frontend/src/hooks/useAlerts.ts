import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Alert } from "@/types";

interface UseAlertsOptions {
    page?: number;
    per_page?: number;
    tip?: string;
    enabled?: boolean;
}

/**
 * Hook to fetch user alerts with optional filtering.
 */
export function useAlerts({ page = 1, per_page = 20, tip, enabled = true }: UseAlertsOptions = {}) {
    return useQuery<Alert[]>({
        queryKey: ["alerts", { page, per_page, tip }],
        queryFn: async () =>
            (await api.get("/alerts", { params: { page, per_page, tip: tip || undefined } })).data,
        enabled,
        staleTime: 30 * 1000, // 30 seconds — alerts are time-sensitive
        refetchInterval: 60 * 1000, // Refetch every minute
    });
}

/**
 * Hook to fetch unread alert count.
 */
export function useUnreadAlertCount() {
    return useQuery<number>({
        queryKey: ["alerts", "unread-count"],
        queryFn: async () => {
            const { data } = await api.get("/alerts/analytics");
            return data.unread || 0;
        },
        staleTime: 15 * 1000,
        refetchInterval: 30 * 1000,
    });
}
