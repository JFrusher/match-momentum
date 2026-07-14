import { useMatchStore } from "../store/matchStore";
import { eventItems } from "../data/rugbyInline";

const BADGES = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

export function EventColumn() {
  const stagedType = useMatchStore((s) => s.stagedType);
  const stageType = useMatchStore((s) => s.stageType);
  const submitStaged = useMatchStore((s) => s.submitStaged);

  return (
    <div className="column event-column">
      <h2>Event</h2>
      {eventItems.map((item, i) => (
        <button
          key={item.key}
          className={stagedType === item.key ? "selected" : ""}
          onClick={() => {
            stageType(item.key);
            if (!item.modifierGroupId) submitStaged();
          }}
        >
          <kbd>{BADGES[i]}</kbd> {item.label}
        </button>
      ))}
    </div>
  );
}
