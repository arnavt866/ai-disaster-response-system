import { useCallback, useMemo, useState } from "react";

export default function usePagination(items, pageSize = 10) {
  const [page, setPage] = useState(1);

  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(page, totalPages);

  const pageItems = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return items.slice(start, start + pageSize);
  }, [items, safePage, pageSize]);

  const goToPage = useCallback((nextPage) => {
    setPage(() => {
      const maxPage = Math.max(1, Math.ceil(items.length / pageSize));
      return Math.min(Math.max(1, nextPage), maxPage);
    });
  }, [items.length, pageSize]);

  const resetPage = useCallback(() => {
    setPage(1);
  }, []);

  const rangeStart = totalItems === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const rangeEnd = Math.min(safePage * pageSize, totalItems);

  return {
    page: safePage,
    pageItems,
    totalPages,
    totalItems,
    rangeStart,
    rangeEnd,
    goToPage,
    resetPage,
    hasPrevious: safePage > 1,
    hasNext: safePage < totalPages,
  };
}
