import { useMatchStore } from "../../store/matchStore";
import { useSportConfig } from "../../hooks/useSportConfig";
import { eventLabel } from "../../sport-config";
import { formatClock } from "../../utils/time";

export function TimelineLog() {
  const config = useSportConfig();
  const teamNames = useMatchStore((s) => s.teamNames);
  const events = useMatchStore((s) => s.events);
  // createdAt tiebreak: rapid events share a rounded minute, and newest-first
  // must hold within the tie too (e.g. conversion above its try).
  const sorted = [...events].sort((a, b) => b.minute - a.minute || b.createdAt - a.createdAt);

  function teamLabelFor(team: string): string {
    if (team === "home") return teamNames.home;
    if (team === "away") return teamNames.away;
    return config.teamColumn.neutralLabel;
  }

  return (
    <div className="timeline-log">
      <h2>Timeline</h2>
      {sorted.length === 0 && <p className="empty-hint">No events logged yet</p>}
      <ul>
        {sorted.map((ev) => (
          <li key={ev.id}>
            <span className="timeline-minute">{formatClock(ev.minute * 60000)}</span>
            <span className="timeline-team">{teamLabelFor(ev.team)}</span>
            <span className="timeline-type">{eventLabel(config, ev.type)}</span>
            {ev.modifier && <span className="timeline-modifier">{ev.modifier}</span>}
            {ev.derivedInputs && (
              <span className="timeline-derived">
                {Object.entries(ev.derivedInputs)
                  .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
                  .join(", ")}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
