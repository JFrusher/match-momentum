import { useEffect, useRef } from "react";
import { useMatchStore } from "../store/matchStore";

// Rendered only in derivedInput mode. Enter submits current values (defaults
// count), Escape cancels the whole event — no partial derived event exists.
// Inputs handle Enter/Escape themselves because the global hotkey listener
// bails on editable targets; useHotkeys covers the focus-elsewhere case.
export function DerivedInputPanel() {
  const mode = useMatchStore((s) => s.mode);
  const derivedDraft = useMatchStore((s) => s.derivedDraft);
  const stagedTeam = useMatchStore((s) => s.stagedTeam);
  const setDerivedValue = useMatchStore((s) => s.setDerivedValue);
  const submitDerived = useMatchStore((s) => s.submitDerived);
  const cancelDerived = useMatchStore((s) => s.cancelDerived);
  const firstInputRef = useRef<HTMLInputElement | null>(null);

  const open = mode === "derivedInput" && derivedDraft !== null;

  useEffect(() => {
    if (open) firstInputRef.current?.focus();
  }, [open]);

  if (!open || !derivedDraft) return null;

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      submitDerived();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelDerived();
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal derived-panel" onKeyDown={handleKeyDown}>
        <h2>{derivedDraft.entry.label}</h2>
        {!stagedTeam && <p className="modal-warning">Stage a team (Z/X/C) to submit</p>}
        <div className="derived-fields">
          {(derivedDraft.entry.derivedInputs ?? []).map((input, i) => (
            <label key={input.field}>
              {input.label}
              <input
                ref={i === 0 ? firstInputRef : undefined}
                type="number"
                value={derivedDraft.values[input.field] ?? 0}
                min={input.min}
                max={input.max}
                step={input.step}
                onChange={(e) => setDerivedValue(input.field, Number(e.target.value))}
              />
            </label>
          ))}
        </div>
        <div className="modal-actions">
          <button className="submit-button" disabled={!stagedTeam} onClick={submitDerived}>
            Log <kbd>Enter</kbd>
          </button>
          <button onClick={cancelDerived}>
            Cancel <kbd>Esc</kbd>
          </button>
        </div>
      </div>
    </div>
  );
}
