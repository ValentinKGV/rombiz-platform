/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        container: {
            center: true,
            padding: "2rem",
            screens: {
                "2xl": "1400px",
            },
        },
        extend: {
            fontFamily: {
                orbitron: ["Orbitron", "sans-serif"],
                exo: ["Exo 2", "sans-serif"],
                rajdhani: ["Rajdhani", "sans-serif"],
            },
            colors: {
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
                // ═══ COSMIC COLOR PALETTE ═══
                nebula: {
                    50: "#f3f0ff",
                    100: "#e9e2ff",
                    200: "#d4c6ff",
                    300: "#b69aff",
                    400: "#9461ff",
                    500: "#7c3aed",
                    600: "#6d28d9",
                    700: "#5b21b6",
                    800: "#4c1d95",
                    900: "#3b0764",
                },
                cosmos: {
                    50: "#eef6ff",
                    100: "#d9ebff",
                    200: "#bcddff",
                    300: "#8ec8ff",
                    400: "#59a8ff",
                    500: "#3b82f6",
                    600: "#2563eb",
                    700: "#1d4ed8",
                    800: "#1e3a8a",
                    900: "#172554",
                },
                dragon: {
                    50: "#fff5f0",
                    100: "#ffe8db",
                    200: "#ffceb3",
                    300: "#ffa876",
                    400: "#ff7a33",
                    500: "#f97316",
                    600: "#ea580c",
                    700: "#c2410c",
                    800: "#9a3412",
                    900: "#7c2d12",
                    fire: "#ff6b35",
                    blood: "#dc2626",
                },
                stardust: {
                    DEFAULT: "#f59e0b",
                    light: "#fbbf24",
                    bright: "#fcd34d",
                },
                plasma: {
                    DEFAULT: "#a855f7",
                    light: "#c084fc",
                    dark: "#7e22ce",
                },
                void: {
                    DEFAULT: "#1e1b4b",
                    light: "#312e81",
                },
                // RomBiz risk & ESG keep functional
                risk: {
                    A: "#22c55e",
                    B: "#84cc16",
                    C: "#eab308",
                    D: "#f97316",
                    E: "#ef4444",
                },
                esg: {
                    environmental: "#10b981",
                    social: "#3b82f6",
                    governance: "#8b5cf6",
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            backgroundImage: {
                "nebula-gradient": "linear-gradient(135deg, #7c3aed 0%, #3b82f6 50%, #14b8a6 100%)",
                "dragon-gradient": "linear-gradient(135deg, #dc2626 0%, #f97316 50%, #f59e0b 100%)",
                "cosmic-gradient": "linear-gradient(135deg, #7c3aed08 0%, #3b82f606 30%, #14b8a604 60%, #f9731603 100%)",
                "stardust-gradient": "linear-gradient(135deg, #f59e0b 0%, #fbbf24 50%, #fcd34d 100%)",
            },
            boxShadow: {
                "cosmic-sm": "0 0 10px rgba(124, 58, 237, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04)",
                "cosmic": "0 0 20px rgba(124, 58, 237, 0.1), 0 4px 16px rgba(0, 0, 0, 0.06)",
                "cosmic-lg": "0 0 40px rgba(124, 58, 237, 0.15), 0 8px 32px rgba(0, 0, 0, 0.08)",
                "dragon": "0 0 20px rgba(249, 115, 22, 0.15), 0 4px 16px rgba(0, 0, 0, 0.06)",
                "nebula": "0 0 30px rgba(124, 58, 237, 0.2), 0 0 60px rgba(59, 130, 246, 0.1)",
            },
            keyframes: {
                "accordion-down": {
                    from: { height: "0" },
                    to: { height: "var(--radix-accordion-content-height)" },
                },
                "accordion-up": {
                    from: { height: "var(--radix-accordion-content-height)" },
                    to: { height: "0" },
                },
                "nebula-pulse": {
                    "0%, 100%": { opacity: "0.6" },
                    "50%": { opacity: "1" },
                },
                "cosmic-float": {
                    "0%, 100%": { transform: "translateY(0px)" },
                    "50%": { transform: "translateY(-6px)" },
                },
                "dragon-glow": {
                    "0%, 100%": { boxShadow: "0 0 15px rgba(249, 115, 22, 0.1)" },
                    "50%": { boxShadow: "0 0 30px rgba(249, 115, 22, 0.25)" },
                },
                "star-appear": {
                    from: { opacity: "0", transform: "scale(0.8)" },
                    to: { opacity: "1", transform: "scale(1)" },
                },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                "nebula-pulse": "nebula-pulse 3s ease-in-out infinite",
                "cosmic-float": "cosmic-float 6s ease-in-out infinite",
                "dragon-glow": "dragon-glow 2s ease-in-out infinite",
                "star-appear": "star-appear 0.5s ease-out forwards",
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
};
