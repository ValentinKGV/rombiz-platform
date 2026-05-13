import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { CompanyFull, FinancialData, RiskScore, ESGScore } from "@/types";

/**
 * Hook to fetch company profile by CUI.
 */
export function useCompany(cui: string | undefined) {
    return useQuery<CompanyFull>({
        queryKey: ["company", cui],
        queryFn: async () => (await api.get(`/companies/${cui}`)).data,
        enabled: !!cui,
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook to fetch company financial data.
 */
export function useCompanyFinancials(cui: string | undefined, enabled = true) {
    return useQuery<FinancialData[]>({
        queryKey: ["company", cui, "financial"],
        queryFn: async () => (await api.get(`/companies/${cui}/financial`)).data,
        enabled: !!cui && enabled,
        staleTime: 10 * 60 * 1000,
    });
}

/**
 * Hook to fetch company risk score.
 */
export function useRiskScore(cui: string | undefined, enabled = true) {
    return useQuery<RiskScore>({
        queryKey: ["company", cui, "risk"],
        queryFn: async () => (await api.get(`/risk/${cui}`)).data,
        enabled: !!cui && enabled,
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook to fetch company ESG score.
 */
export function useESGScore(cui: string | undefined, enabled = true) {
    return useQuery<ESGScore>({
        queryKey: ["company", cui, "esg"],
        queryFn: async () => (await api.get(`/esg/${cui}`)).data,
        enabled: !!cui && enabled,
        staleTime: 10 * 60 * 1000,
    });
}
