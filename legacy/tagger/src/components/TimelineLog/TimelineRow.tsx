import { useState } from "react";
import { useMatchStore } from "../../store/matchStore";
import { useSportConfig } from "../../hooks/useSportConfig";
import { eventLabel, vocabPoints } from "../../sport-config";
import type { TaggedEvent, TeamRole } from "../../store/types";
import { formatClock } from "../../utils/time";

interface Props {
  event: TaggedEvent;
  expanded: boolean;
  onToggle: () => void;
}

export function TimelineRow({ event, expanded, onToggle }: Props) {
  const config = useSportConfig();
  const teamNames = useMatchStore((s) => s.teamNames);
  const editEvent = useMatchStore((s) => s.editEvent);
  const deleteEvent = useMatchStore((s) => s.deleteEvent);

  const [team, setTeam] = useState<TeamRole>(event.team);
  const [type, setType] = useState(event.type);
  const [modifier, setModifier] = useState(event.modifier ?? "");
  const [minute, setMinute] = useState(String(event.minute));

  function teamLabelFor(t: string): string {
    if (t === "home") return teamNames.home;
    if (t === "away") return teamNames.away;
    return config.teamColumn.neutralLabel;
  }

  // Editable type choices: every vocabulary member, follow-up-only types included.
  const typeOptions = Object.keys(vocabPoints(config));
  const typeEntry = config.eventColumn.items.find((i) => i.key === type);
  const modifierGroup = typeEntry?.modifierGroupId
    ? config.modifierGroups[typeEntry.modifierGroupId]
    : undefined;

  function handleTypeChange(next: string) {
    setType(next);
    // Old modifier belongs to the old type's group — reset unless still valid.
    const nextEntry = config.eventColumn.items.find((i) => i.key === next);
    const nextGroup = nextEntry?.modifierGroupId
      ? config.modifierGroups[nextEntry.modifierGroupId]
      : undefined;
    if (!nextGroup?.some((t) => t.id === modifier)) setModifier("");
  }

  function save() {
    const parsedMinute = Number(minute);
    editEvent(event.id, {
      team,
      type,
      modifier: modifier || undefined,
      minute: Number.isFinite(parsedMinute) && parsedMinute >= 0 ? Math.round(parsedMinute * 100) / 100 : event.minute,
    });
    onToggle();
  }

  if (!expanded) {
    return (
      <li className="timeline-row" onClick={onToggle} title="Click to edit">
        <span className="timeline-minute">{formatClock(event.minute * 60000)}</span>
        <span className="timeline-team">{teamLabelFor(event.team)}</span>
        <span className="timeline-type">{eventLabel(config, event.type)}</span>
        {event.modifier && <span className="timeline-modifier">{event.modifier}</span>}
        {event.derivedInputs && (
          <span className="timeline-derived">
            {Object.entries(event.derivedInputs)
              .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
              .join(", ")}
          </span>
        )}
        {event.editedAt && <span className="timeline-edited">edited</span>}
      </li>
    );
  }

  return (
    <li
      className="timeline-row timeline-row-editing"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          onToggle();
        }
      }}
    >
      <div className="timeline-edit-form">
        <label>
          Team
          <select value={team} onChange={(e) => setTeam(e.target.value as TeamRole)}>
            <option value="home">{teamNames.home}</option>
            <option value="away">{teamNames.away}</option>
            {config.teamColumn.includeNeutral && (
              <option value="neutral">{config.teamColumn.neutralLabel}</option>
            )}
          </select>
        </label>
        <label>
          Type
          <select value={type} onChange={(e) => handleTypeChange(e.target.value)}>
            {typeOptions.map((key) => (
              <option key={key} value={key}>
                {eventLabel(config, key)}
              </option>
            ))}
          </select>
        </label>
        {modifierGroup && (
          <label>
            Modifier
            <select value={modifier} onChange={(e) => setModifier(e.target.value)}>
              <option value="">—</option>
              {modifierGroup.map((tag) => (
                <option key={tag.id} value={tag.id}>
                  {tag.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Minute
          <input
            type="number"
            min={0}
            step={0.01}
            value={minute}
            onChange={(e) => setMinute(e.target.value)}
          />
        </label>
        <div className="timeline-edit-actions">
          <button className="submit-button" onClick={save}>
            Save
          </button>
          <button onClick={onToggle}>Cancel</button>
          <button
            className="danger-button"
            onClick={() => {
              deleteEvent(event.id);
              onToggle();
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </li>
  );
}
