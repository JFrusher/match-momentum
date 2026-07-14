import { useEffect, useState } from "react";
import { useMatchStore } from "../store/matchStore";

/** Re-renders the calling component ~4x/sec while the clock runs, without
 * forcing every store subscriber (event columns, etc.) to re-render too. */
export function useClock(): number {
  const running = useMatchStore((s) => s.clock.running);
  const [, forceTick] = useState(0);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => forceTick((n) => n + 1), 250);
    return () => clearInterval(id);
  }, [running]);

  return useMatchStore.getState().getElapsedMs();
}
