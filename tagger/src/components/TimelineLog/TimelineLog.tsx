import { useState } from "react";
import { useMatchStore } from "../../store/matchStore";
import { TimelineRow } from "./TimelineRow";

export function TimelineLog() {
  const events = useMatchStore((s) => s.events);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // createdAt tiebreak: rapid events share a rounded minute, and newest-first
  // must hold within the tie too (e.g. conversion above its try).
  const sorted = [...events].sort((a, b) => b.minute - a.minute || b.createdAt - a.createdAt);

  return (
    <div className="timeline-log">
      <h2>Timeline</h2>
      {sorted.length === 0 && <p className="empty-hint">No events logged yet</p>}
      <ul>
        {sorted.map((ev) => (
          <TimelineRow
            // Remount on expand/collapse so the edit form re-seeds from the event.
            key={`${ev.id}${expandedId === ev.id ? ":editing" : ""}`}
            event={ev}
            expanded={expandedId === ev.id}
            onToggle={() => setExpandedId(expandedId === ev.id ? null : ev.id)}
          />
        ))}
      </ul>
    </div>
  );
}
