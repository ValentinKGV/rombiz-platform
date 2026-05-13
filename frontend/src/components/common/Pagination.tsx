import { cn } from "@/lib/utils";

interface PaginationProps {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    className?: string;
}

export default function Pagination({
    page,
    pageSize,
    total,
    onPageChange,
    className,
}: PaginationProps) {
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return null;

    return (
        <div className={cn("flex items-center justify-center gap-2", className)}>
            <button
                onClick={() => onPageChange(page - 1)}
                disabled={page <= 1}
                className="rounded-xl border border-nebula-200 px-4 py-1.5 font-rajdhani text-sm font-semibold text-nebula-500 hover:bg-nebula-50 disabled:opacity-50 transition-colors"
            >
                Anterior
            </button>
            <span className="font-rajdhani text-sm text-slate-400">
                Pagina {page} din {totalPages}
            </span>
            <button
                onClick={() => onPageChange(page + 1)}
                disabled={page >= totalPages}
                className="rounded-xl border border-nebula-200 px-4 py-1.5 font-rajdhani text-sm font-semibold text-nebula-500 hover:bg-nebula-50 disabled:opacity-50 transition-colors"
            >
                Următor
            </button>
        </div>
    );
}
