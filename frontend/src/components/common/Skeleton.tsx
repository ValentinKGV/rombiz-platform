import { cn } from "@/lib/utils";

interface SkeletonProps {
    className?: string;
    count?: number;
}

/**
 * Animated loading skeleton placeholder.
 */
export function Skeleton({ className, count = 1 }: SkeletonProps) {
    if (count === 1) {
        return (
            <div
                className={cn(
                    "animate-pulse rounded-lg bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%]",
                    className
                )}
            />
        );
    }

    return (
        <>
            {Array.from({ length: count }).map((_, i) => (
                <div
                    key={i}
                    className={cn(
                        "animate-pulse rounded-lg bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%]",
                        className
                    )}
                    style={{ animationDelay: `${i * 100}ms` }}
                />
            ))}
        </>
    );
}

/**
 * Skeleton card for dashboard KPI-style cards.
 */
export function SkeletonCard({ className }: { className?: string }) {
    return (
        <div className={cn("card-cosmic space-y-3", className)}>
            <div className="flex items-center justify-between">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-10 w-10 rounded-xl" />
            </div>
            <Skeleton className="h-8 w-20" />
        </div>
    );
}

/**
 * Skeleton for table rows.
 */
export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
    return (
        <div className="space-y-2">
            {Array.from({ length: rows }).map((_, r) => (
                <div key={r} className="flex gap-4 rounded-lg border border-slate-100 p-4">
                    {Array.from({ length: cols }).map((_, c) => (
                        <Skeleton
                            key={c}
                            className={cn("h-4", c === 0 ? "w-1/3" : "w-1/6")}
                        />
                    ))}
                </div>
            ))}
        </div>
    );
}
