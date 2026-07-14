import { useMatchStore } from "../store/matchStore";
import { useSportConfig } from "../hooks/useSportConfig";

const BADGES = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

export function EventColumn() {
  const config = useSportConfig();
  const stagedType = useMatchStore((s) => s.stagedType);
  const stageEventType = useMatchStore((s) => s.stageEventType);

  return (
    <div className="column event-column">
      <h2>Event</h2>
      {config.eventColumn.items.map((item, i) => (
        <button
          key={item.key}
          className={stagedType === item.key ? "selected" : ""}
          onClick={() => stageEventType(item.key)}
        >
          <kbd>{BADGES[i]}</kbd> {item.label}
        </button>
      ))}
    </div>
  );
}
