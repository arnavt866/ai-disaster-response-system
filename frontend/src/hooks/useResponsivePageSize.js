import { useEffect, useState } from "react";

function computePageSize({ chromePx, rowPx, min, max }) {
  if (typeof window === "undefined") return min;
  const available = window.innerHeight - chromePx;
  return Math.min(max, Math.max(min, Math.floor(available / rowPx)));
}

/**
 * Page size that fills remaining viewport height instead of a hardcoded 10.
 * Typical laptop result is ~15–20 rows; phones stay closer to the min.
 */
export default function useResponsivePageSize({
  chromePx = 240,
  rowPx = 44,
  min = 8,
  max = 24,
} = {}) {
  const [pageSize, setPageSize] = useState(() =>
    computePageSize({ chromePx, rowPx, min, max }),
  );

  useEffect(() => {
    const update = () => setPageSize(computePageSize({ chromePx, rowPx, min, max }));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [chromePx, rowPx, min, max]);

  return pageSize;
}
