import { useMatchStore } from "../store/matchStore";
import { useClock } from "../hooks/useClock";
import { formatClock } from "../utils/time";

const MAX_SCRUB_MS = 130 * 60 * 1000; // 130 minutes — generous upper bound for any sport

export function ClockController() {
  const elapsedMs = useClock();
  const running = useMatchStore((s) => s.clock.running);
  const resetPending = useMatchStore((s) => s.resetPending);
  const toggleClock = useMatchStore((s) => s.toggleClock);
  const scrubClockTo = useMatchStore((s) => s.scrubClockTo);

  return (
    <div className="clock-controller">
      <span className="clock-display">{formatClock(elapsedMs)}</span>
      <button onClick={toggleClock}>
        {running ? "Pause" : "Start"} <kbd>Space</kbd>
      </button>
      <span className="clock-reset-hint">
        {resetPending ? "Press Enter to confirm reset (any other key cancels)" : <kbd>Shift+Space</kbd>}
      </span>
      <input
        className="clock-scrub"
        type="range"
        min={0}
        max={MAX_SCRUB_MS}
        step={1000}
        value={Math.min(elapsedMs, MAX_SCRUB_MS)}
        disabled={running}
        onChange={(e) => scrubClockTo(Number(e.target.value))}
        // Drop focus once the drag ends — a focused slider is an editable
        // target, which would swallow every tagging hotkey until a click-away.
        onPointerUp={(e) => e.currentTarget.blur()}
        aria-label="Manually scrub match clock"
      />
    </div>
  );
}
