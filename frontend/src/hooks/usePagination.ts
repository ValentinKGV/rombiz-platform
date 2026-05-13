import { useState, useCallback, useMemo } from "react";

interface UsePaginationOptions {
    initialPage?: number;
    initialPageSize?: number;
    total?: number;
}

interface UsePaginationReturn {
    page: number;
    pageSize: number;
    totalPages: number;
    setPage: (page: number) => void;
    setPageSize: (size: number) => void;
    nextPage: () => void;
    prevPage: () => void;
    canNext: boolean;
    canPrev: boolean;
    offset: number;
}

/**
 * Hook for managing pagination state.
 */
export function usePagination({
    initialPage = 1,
    initialPageSize = 25,
    total = 0,
}: UsePaginationOptions = {}): UsePaginationReturn {
    const [page, setPageRaw] = useState(initialPage);
    const [pageSize, setPageSize] = useState(initialPageSize);

    const totalPages = useMemo(
        () => Math.max(1, Math.ceil(total / pageSize)),
        [total, pageSize]
    );

    const setPage = useCallback(
        (p: number) => setPageRaw(Math.max(1, Math.min(p, totalPages))),
        [totalPages]
    );

    const nextPage = useCallback(() => setPage(page + 1), [page, setPage]);
    const prevPage = useCallback(() => setPage(page - 1), [page, setPage]);

    return {
        page,
        pageSize,
        totalPages,
        setPage,
        setPageSize,
        nextPage,
        prevPage,
        canNext: page < totalPages,
        canPrev: page > 1,
        offset: (page - 1) * pageSize,
    };
}
