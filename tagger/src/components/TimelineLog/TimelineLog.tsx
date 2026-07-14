import { useMatchStore } from "../../store/matchStore";
import { eventItems, teamNames } from "../../data/rugbyInline";
import { formatClock } from "../../utils/time";

function teamLabelFor(team: string): string {
  if (team === "home") return teamNames.home;
  if (team === "away") return teamNames.away;
  return "Neutral";
}

export function TimelineLog() {
  const events = useMatchStore((s) => s.events);
  const sorted = [...events].sort((a, b) => b.minute - a.minute);

  return (
    <div className="timeline-log">
      <h2>Timeline</h2>
      {sorted.length === 0 && <p className="empty-hint">No events logged yet</p>}
      <ul>
        {sorted.map((ev) => (
          <li key={ev.id}>
            <span className="timeline-minute">{formatClock(ev.minute * 60000)}</span>
            <span className="timeline-team">{teamLabelFor(ev.team)}</span>
            <span className="timeline-type">{eventItems.find((i) => i.key === ev.type)?.label ?? ev.type}</span>
            {ev.modifier && <span className="timeline-modifier">{ev.modifier}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
