/**
 * Auth store — Zustand.
 */
import { create } from "zustand";
import type { User, AuthTokens } from "@/types";
import api from "@/lib/api";

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (data: {
        email: string;
        password: string;
        first_name: string;
        last_name: string;
        org_name: string;
    }) => Promise<void>;
    logout: () => void;
    fetchUser: () => Promise<void>;
    updateProfile: (data: { first_name?: string; last_name?: string }) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    isAuthenticated: !!localStorage.getItem("access_token"),
    isLoading: false,

    login: async (email, password) => {
        set({ isLoading: true });
        try {
            const { data } = await api.post<AuthTokens>("/auth/login", {
                email,
                password,
            });
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("refresh_token", data.refresh_token);

            // Fetch user profile
            const { data: user } = await api.get<User>("/auth/me");
            set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
            set({ isLoading: false });
            throw error;
        }
    },

    register: async (data) => {
        set({ isLoading: true });
        try {
            await api.post("/auth/register", data);
            set({ isLoading: false });
        } catch (error) {
            set({ isLoading: false });
            throw error;
        }
    },

    logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ user: null, isAuthenticated: false });
        window.location.href = "/login";
    },

    updateProfile: async (data) => {
        await api.patch("/auth/me", data);
        // Re-fetch user to get updated data
        const { data: user } = await api.get<User>("/auth/me");
        set({ user });
    },

    fetchUser: async () => {
        try {
            const { data: user } = await api.get<User>("/auth/me");
            set({ user, isAuthenticated: true });
        } catch (err: unknown) {
            // Only clear auth on 401 (unauthorized) — not on network errors or 500s
            const status = (err as { response?: { status?: number } })?.response?.status;
            if (status === 401 || status === 403) {
                set({ user: null, isAuthenticated: false });
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
            }
        }
    },
}));
