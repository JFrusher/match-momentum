import { useMatchStore } from "../store/matchStore";

const BADGES = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

// Rendered only in followUp mode. Fully hotkey-driven (1-9 pick, Escape
// dismisses) — key handling lives in useHotkeys; buttons mirror it for mouse.
export function FollowUpModal() {
  const mode = useMatchStore((s) => s.mode);
  const followUp = useMatchStore((s) => s.followUp);
  const resolveFollowUp = useMatchStore((s) => s.resolveFollowUp);
  const dismissFollowUp = useMatchStore((s) => s.dismissFollowUp);

  if (mode !== "followUp" || !followUp) return null;

  return (
    <div className="modal-overlay" onClick={dismissFollowUp}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{followUp.spec.question}</h2>
        <div className="modal-options">
          {followUp.spec.options.map((opt, i) => (
            <button key={opt.label} onClick={() => resolveFollowUp(i)}>
              <kbd>{BADGES[i]}</kbd> {opt.label}
            </button>
          ))}
        </div>
        <p className="modal-hint">
          <kbd>Esc</kbd> skip
        </p>
      </div>
    </div>
  );
}
