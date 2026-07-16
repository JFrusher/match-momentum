import { useState } from "react";
import { del as idbDel } from "idb-keyval";
import { useMatchStore } from "../store/matchStore";
import { AUTOSAVE_KEY } from "../hooks/useAutosave";

// Deliberately mouse-only (no hotkey) — clearing a match must not be one
// stray keypress away during live tagging.
export function NewMatchDialog() {
  const [open, setOpen] = useState(false);
  const resetMatch = useMatchStore((s) => s.resetMatch);
  const eventCount = useMatchStore((s) => s.events.length);

  function confirmNewMatch() {
    resetMatch();
    // Drop the autosave too — otherwise a crash before the next debounced
    // write would resurrect the old match.
    idbDel(AUTOSAVE_KEY).catch(() => {});
    setOpen(false);
  }

  return (
    <>
      <button className="new-match-button" onClick={() => setOpen(true)}>
        New Match
      </button>
      {open && (
        <div className="modal-overlay" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Start a new match?</h2>
            <p className="modal-hint">
              This clears the clock, score and all {eventCount} logged event{eventCount === 1 ? "" : "s"}.
              Export first if you need them.
            </p>
            <div className="modal-actions">
              <button className="danger-button" onClick={confirmNewMatch}>
                Clear and start new
              </button>
              <button onClick={() => setOpen(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
