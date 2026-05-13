import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Format a Decimal string to a locale-aware Romanian number.
 * Hard constraint #15: Decimal in TS — never use float.
 */
export function formatMoney(value: string | number, currency = "RON"): string {
    const num =
        typeof value === "string" ? parseFloat(value) : value;
    return new Intl.NumberFormat("ro-RO", {
        style: "currency",
        currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(num);
}

export function formatNumber(value: string | number): string {
    const num = typeof value === "string" ? parseFloat(value) : value;
    return new Intl.NumberFormat("ro-RO").format(num);
}

export function formatPercent(value: string | number): string {
    const num = typeof value === "string" ? parseFloat(value) : value;
    return `${(num * 100).toFixed(1)}%`;
}

/**
 * Format ISO date to Romanian locale.
 * Hard constraint #10: UTC storage, Bucharest display.
 */
export function formatDate(isoDate: string): string {
    return new Intl.DateTimeFormat("ro-RO", {
        dateStyle: "medium",
        timeZone: "Europe/Bucharest",
    }).format(new Date(isoDate));
}

export function formatDateTime(isoDate: string): string {
    return new Intl.DateTimeFormat("ro-RO", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Europe/Bucharest",
    }).format(new Date(isoDate));
}

export function riskCategoryColor(cat: string): string {
    const colors: Record<string, string> = {
        A: "text-risk-A bg-risk-A/10",
        B: "text-risk-B bg-risk-B/10",
        C: "text-risk-C bg-risk-C/10",
        D: "text-risk-D bg-risk-D/10",
        E: "text-risk-E bg-risk-E/10",
    };
    return colors[cat] || "text-muted-foreground";
}

export function riskCategoryLabel(cat: string): string {
    const labels: Record<string, string> = {
        A: "Risc Minim",
        B: "Risc Scăzut",
        C: "Risc Mediu",
        D: "Risc Ridicat",
        E: "Risc Foarte Ridicat",
    };
    return labels[cat] || cat;
}

/**
 * CUI validator (mod-11) – client-side.
 * Hard constraint #2.
 */
export function validateCUI(cui: string): boolean {
    const cleaned = cui.replace(/^RO/i, "").replace(/\s/g, "");
    if (!/^\d{1,10}$/.test(cleaned)) return false;

    const digits = cleaned.split("").map(Number);
    const weights = [7, 5, 3, 2, 1, 7, 5, 3, 2];

    const controlDigit = digits.pop()!;
    while (digits.length < 9) digits.unshift(0);

    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += digits[i] * weights[i];
    }

    const remainder = (sum * 10) % 11;
    const expected = remainder === 10 ? 0 : remainder;

    return controlDigit === expected;
}
