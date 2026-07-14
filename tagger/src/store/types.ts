export type TeamRole = "home" | "away" | "neutral";

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
  createdAt: number;
}
