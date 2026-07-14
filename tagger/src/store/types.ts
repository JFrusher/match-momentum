export type TeamRole = "home" | "away" | "neutral";

export interface ModifierTag {
  id: string;
  label: string;
}

export interface EventTypeItem {
  key: string;
  label: string;
  modifierGroupId?: string;
}

export interface TaggedEvent {
  id: string;
  minute: number;
  team: TeamRole;
  type: string;
  modifier?: string;
  createdAt: number;
}
