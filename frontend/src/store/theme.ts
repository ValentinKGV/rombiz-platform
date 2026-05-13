import { create } from "zustand";

interface ThemeState {
    dark: boolean;
    toggle: () => void;
}

const stored = localStorage.getItem("ath-theme");
const prefersDark = stored === "dark" || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);

// Apply immediately to avoid flash
if (prefersDark) document.documentElement.classList.add("dark");

export const useThemeStore = create<ThemeState>((set) => ({
    dark: prefersDark,
    toggle: () =>
        set((s) => {
            const next = !s.dark;
            if (next) {
                document.documentElement.classList.add("dark");
                localStorage.setItem("ath-theme", "dark");
            } else {
                document.documentElement.classList.remove("dark");
                localStorage.setItem("ath-theme", "light");
            }
            return { dark: next };
        }),
}));
