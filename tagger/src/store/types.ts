export type TeamRole = "home" | "away" | "neutral";

/** Autosaved to IndexedDB (single active match). Bump `v` on breaking shape changes. */
export interface MatchSnapshot {
  v: 1;
  sportKey: string;
  teamNames: { home: string; away: string };
  events: TaggedEvent[];
  scoreOverride: { home: number; away: number };
  /** Clock position at save time; always rehydrated paused. */
  clockMs: number;
  savedAt: number;
}

export interface TaggedEvent {
  id: string;
  minute: number;
  team: TeamRole;
  type: string;
  modifier?: string;
  /** Flattened at export time to top-level keys (exact translator field names). */
  derivedInputs?: Record<string, number>;
  /** id of the primary event whose follow-up logged this one (e.g. try -> conversion). */
  followUpOf?: string;
  /** Real match points (scoreboard) — unrelated to momentum weight, which the Python side owns. */
  points: number;
  createdAt: number;
  editedAt?: number;
}
