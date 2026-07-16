import { useEffect, useState } from "react";
import { useMatchStore } from "../store/matchStore";

/** Re-renders the calling component ~4x/sec while the clock runs, without
 * forcing every store subscriber (event columns, etc.) to re-render too.
 * Subscribes to the whole clock object so paused-state changes (scrub,
 * reset, autosave rehydrate) also refresh the display. */
export function useClock(): number {
  const clock = useMatchStore((s) => s.clock);
  const [, forceTick] = useState(0);

  useEffect(() => {
    if (!clock.running) return;
    const id = setInterval(() => forceTick((n) => n + 1), 250);
    return () => clearInterval(id);
  }, [clock.running]);

  return clock.baseMs + (clock.running && clock.startedAt ? Date.now() - clock.startedAt : 0);
}
