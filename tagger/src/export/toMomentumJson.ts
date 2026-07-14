import type { TaggedEvent } from "../store/types";

export interface ExportInput {
  teamNames: { home: string; away: string };
  events: TaggedEvent[];
}

export interface MomentumJson {
  teams: { home: string; away: string };
  title: string;
  events: Record<string, unknown>[];
}

// Serializes to match-momentum's CustomJSONSource contract (TAGGER_PLAN.md
// "Ground truth"): team role -> real team name string, neutral events dropped,
// derivedInputs flattened to top-level keys with the exact names the Python
// translator reads, `weight` omitted (the static weight tables own it).
// `points` and `modifier` ride along as harmless extra fields.
export function toMomentumJson({ teamNames, events }: ExportInput): MomentumJson {
  const exported = events
    .filter((ev) => ev.team !== "neutral")
    .sort((a, b) => a.minute - b.minute || a.createdAt - b.createdAt)
    .map((ev) => ({
      minute: ev.minute,
      team: ev.team === "home" ? teamNames.home : teamNames.away,
      type: ev.type,
      points: ev.points,
      ...(ev.modifier ? { modifier: ev.modifier } : {}),
      ...(ev.derivedInputs ?? {}),
    }));

  return {
    teams: { home: teamNames.home, away: teamNames.away },
    title: `${teamNames.home} vs ${teamNames.away}`,
    events: exported,
  };
}
