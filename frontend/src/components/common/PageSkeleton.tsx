/** Shimmer skeleton used as Suspense fallback while lazy pages load */
export default function PageSkeleton() {
    return (
        <div className="animate-in fade-in space-y-6">
            {/* Title skeleton */}
            <div className="space-y-2">
                <div className="skeleton h-8 w-64 rounded-lg" />
                <div className="skeleton h-4 w-96 rounded-md" />
            </div>

            {/* KPI cards row */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="card-cosmic rounded-2xl p-5 space-y-3">
                        <div className="skeleton h-4 w-24 rounded" />
                        <div className="skeleton h-8 w-32 rounded-md" />
                        <div className="skeleton h-3 w-20 rounded" />
                    </div>
                ))}
            </div>

            {/* Chart area */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="card-cosmic rounded-2xl p-5 space-y-4">
                    <div className="skeleton h-5 w-40 rounded" />
                    <div className="skeleton h-48 w-full rounded-xl" />
                </div>
                <div className="card-cosmic rounded-2xl p-5 space-y-4">
                    <div className="skeleton h-5 w-40 rounded" />
                    <div className="skeleton h-48 w-full rounded-xl" />
                </div>
            </div>

            {/* Table skeleton */}
            <div className="card-cosmic rounded-2xl p-5 space-y-3">
                <div className="skeleton h-5 w-48 rounded" />
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex gap-4">
                        <div className="skeleton h-4 w-1/4 rounded" />
                        <div className="skeleton h-4 w-1/3 rounded" />
                        <div className="skeleton h-4 w-1/6 rounded" />
                        <div className="skeleton h-4 w-1/5 rounded" />
                    </div>
                ))}
            </div>
        </div>
    );
}
